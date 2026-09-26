"""
Estrategia 3: Opening Range Breakout (ORB 30 Minutos) con Expansión ATR (Videos 3, 4 y 15):
Identifica los máximos y mínimos de los primeros 30 minutos de NYSE (09:30 - 10:00 EST)
y ejecuta entradas direccionales en rupturas con expansión de volumen y volatilidad.
"""

from typing import Dict, List
import pandas as pd
from indicators.volatility import add_atr
from indicators.time_filters import add_nyse_session_filters
from strategies.base_strategy import BaseNYSEStrategy


class OpeningRangeBreakoutStrategy(BaseNYSEStrategy):
    """
    Estrategia institucional de ruptura del rango de apertura matutino (09:30 - 10:00 EST).
    """

    def __init__(self, symbols: List[str] = None, atr_mult_sl: float = 1.2, rr_ratio: float = 2.0):
        super().__init__(name="OpeningRange_Breakout", symbols=symbols or ["SPY", "QQQ"])
        self.atr_mult_sl = atr_mult_sl
        self.rr_ratio = rr_ratio

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        data = add_atr(df)
        data = add_nyse_session_filters(data)
        return data

    def generate_signals(self, df_dict: Dict[str, pd.DataFrame]) -> List[Dict]:
        signals = []

        for symbol in self.symbols:
            if symbol not in df_dict or df_dict[symbol].empty:
                continue

            df = self.calculate_indicators(df_dict[symbol])

            for i in range(2, len(df)):
                prev = df.iloc[i - 1]
                curr = df.iloc[i]

                if pd.isna(curr.get("or_high")) or pd.isna(curr.get("or_low")) or pd.isna(curr["atr_14"]):
                    continue

                # Solo operar inmediatamente después de la apertura: Prime Trend (Fase 2: 10:00 - 11:30 EST)
                phase = curr.get("session_phase", 0)
                if phase != 2:
                    continue

                price = curr["close"]
                or_high = curr["or_high"]
                or_low = curr["or_low"]
                atr = curr["atr_14"]
                dist_sl = atr * self.atr_mult_sl

                # Ruptura alcista del rango matutino con vela cerrada por encima
                if prev["close"] <= or_high and price > or_high and curr.get("volatility_expansion", True):
                    sl = price - dist_sl
                    tp = price + (dist_sl * self.rr_ratio)
                    signals.append({
                        "symbol": symbol,
                        "time": curr["time"],
                        "strategy": self.name,
                        "action": "BUY_STOCK",
                        "instrument": "EQUITY",
                        "entry_price": round(price, 2),
                        "stop_loss": round(sl, 2),
                        "take_profit": round(tp, 2),
                        "atr": round(atr, 2),
                        "rationale": f"Ruptura alcista del rango de apertura ({or_high:.2f}) con expansión de volatilidad ATR"
                    })

                # Ruptura bajista del rango matutino
                elif prev["close"] >= or_low and price < or_low and curr.get("volatility_expansion", True):
                    sl = price + dist_sl
                    tp = price - (dist_sl * self.rr_ratio)
                    signals.append({
                        "symbol": symbol,
                        "time": curr["time"],
                        "strategy": self.name,
                        "action": "SELL_STOCK",
                        "instrument": "EQUITY",
                        "entry_price": round(price, 2),
                        "stop_loss": round(sl, 2),
                        "take_profit": round(tp, 2),
                        "atr": round(atr, 2),
                        "rationale": f"Ruptura bajista del rango de apertura ({or_low:.2f}) con expansión de volatilidad ATR"
                    })

        return signals
