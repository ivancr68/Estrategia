"""
Estrategia Tendencial de Momentum (Trend Following) Optimizada:
Diseñada para SPY y QQQ con filtros de alta convicción:
- Solo un disparo por ciclo de cruce MACD (evita sobreoperación)
- Filtro de tendencia macro con EMA 200 y alineación EMA 20 > EMA 50
- Confirmación de ruptura de volatilidad (ATR(14) > SMA(ATR))
- Ratio asimétrico de beneficio (1:2 mínimo con SL a 1.5 ATR)
"""

from typing import Dict, List
import pandas as pd
from indicators.trend import add_moving_averages
from indicators.momentum import add_macd
from indicators.volatility import add_atr
from indicators.time_filters import add_nyse_session_filters
from strategies.base_strategy import BaseNYSEStrategy


class TrendFollowingStrategy(BaseNYSEStrategy):
    """
    Estrategia de seguimiento de tendencia institucional con Stop Loss dinámico por ATR.
    """

    def __init__(self, symbols: List[str] = None, atr_mult_sl: float = 1.5, rr_ratio: float = 2.0):
        super().__init__(name="TrendFollowing_Momentum", symbols=symbols or ["SPY", "QQQ"])
        self.atr_mult_sl = atr_mult_sl
        self.rr_ratio = rr_ratio

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        data = add_moving_averages(df)
        data = add_macd(data)
        data = add_atr(data)
        data = add_nyse_session_filters(data)
        return data

    def generate_signals(self, df_dict: Dict[str, pd.DataFrame]) -> List[Dict]:
        signals = []

        for symbol in self.symbols:
            if symbol not in df_dict or df_dict[symbol].empty:
                continue

            df = self.calculate_indicators(df_dict[symbol])
            last_signal_idx = -50  # Cooldown de al menos 10 velas entre operaciones

            for i in range(2, len(df)):
                if i - last_signal_idx < 10:
                    continue

                prev = df.iloc[i - 1]
                curr = df.iloc[i]

                if pd.isna(curr["atr_14"]) or pd.isna(curr["ema_200"]) or pd.isna(curr["macd"]):
                    continue

                # Horario preferente: Prime Trend (10:00 - 11:30) y Afternoon (14:00 - 15:30)
                phase = curr.get("session_phase", 0)
                if phase not in [2, 4]:
                    continue

                price = curr["close"]
                atr = curr["atr_14"]
                dist_sl = atr * self.atr_mult_sl

                # SEÑAL ALCISTA DE ALTA CONVICCIÓN:
                # 1. Precio sobre EMA 200 y EMA 20 > EMA 50
                # 2. Cruce fresco de MACD
                # 3. Volatilidad en expansión
                if (curr["close"] > curr["ema_200"] and curr["ema_20"] > curr["ema_50"] and
                    prev["macd"] <= prev["macd_signal"] and curr["macd"] > curr["macd_signal"] and
                    curr.get("volatility_expansion", True)):

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
                        "rationale": "Tendencia alcista sobre EMA 200 + Cruce fresco MACD + Expansión ATR"
                    })
                    last_signal_idx = i

                # SEÑAL BAJISTA:
                elif (curr["close"] < curr["ema_200"] and curr["ema_20"] < curr["ema_50"] and
                      prev["macd"] >= prev["macd_signal"] and curr["macd"] < curr["macd_signal"] and
                      curr.get("volatility_expansion", True)):

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
                        "rationale": "Tendencia bajista bajo EMA 200 + Cruce fresco MACD + Expansión ATR"
                    })
                    last_signal_idx = i

        return signals
