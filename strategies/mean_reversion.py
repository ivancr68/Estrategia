"""
Estrategia Anti-tendencial / Reversión a la Media Optimizada:
Diseñada para IWM y DIA con control de sobreoperación:
- Extremos de RSI (< 30 o > 70)
- Perforación y reingreso con confirmación en Bandas de Bollinger
- Cooldown entre operaciones para evitar entradas repetidas en la misma vela de retroceso
"""

from typing import Dict, List
import pandas as pd
from indicators.momentum import add_rsi
from indicators.volatility import add_atr, add_bollinger_bands
from indicators.time_filters import add_nyse_session_filters
from strategies.base_strategy import BaseNYSEStrategy


class MeanReversionStrategy(BaseNYSEStrategy):
    """
    Estrategia de captura de reversiones a la media con protección por ATR.
    """

    def __init__(
        self,
        symbols: List[str] = None,
        rsi_oversold: float = 30.0,
        rsi_overbought: float = 70.0,
        atr_mult_sl: float = 2.2
    ):
        super().__init__(name="MeanReversion_RSI_BB", symbols=symbols or ["IWM", "DIA"])
        self.rsi_oversold = rsi_oversold
        self.rsi_overbought = rsi_overbought
        self.atr_mult_sl = atr_mult_sl

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        data = add_rsi(df)
        data = add_bollinger_bands(data)
        data = add_atr(data)
        data = add_nyse_session_filters(data)
        return data

    def generate_signals(self, df_dict: Dict[str, pd.DataFrame]) -> List[Dict]:
        signals = []

        for symbol in self.symbols:
            if symbol not in df_dict or df_dict[symbol].empty:
                continue

            df = self.calculate_indicators(df_dict[symbol])
            last_signal_idx = -50

            for i in range(2, len(df)):
                if i - last_signal_idx < 10:
                    continue

                prev = df.iloc[i - 1]
                curr = df.iloc[i]

                if pd.isna(curr["rsi"]) or pd.isna(curr["bb_lower"]) or pd.isna(curr["atr_14"]):
                    continue

                # Evitar apertura en los primeros 30 min (fase 1)
                phase = curr.get("session_phase", 0)
                if phase not in [2, 3, 4]:
                    continue

                price = curr["close"]
                atr = curr["atr_14"]
                dist_sl = atr * self.atr_mult_sl

                # REVERSIÓN ALCISTA:
                if prev["close"] < prev["bb_lower"] and price >= curr["bb_lower"] and curr["rsi"] <= self.rsi_oversold + 5:
                    sl = price - dist_sl
                    tp = price + (dist_sl * 2.0)

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
                        "rationale": f"Reversión alcista a la media: RSI en sobreventa ({curr['rsi']:.1f}) y rebote en Banda Inferior"
                    })
                    last_signal_idx = i

                # REVERSIÓN BAJISTA:
                elif prev["close"] > prev["bb_upper"] and price <= curr["bb_upper"] and curr["rsi"] >= self.rsi_overbought - 5:
                    sl = price + dist_sl
                    tp = price - (dist_sl * 2.0)

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
                        "rationale": f"Reversión bajista a la media: RSI en sobrecompra ({curr['rsi']:.1f}) y rechazo en Banda Superior"
                    })
                    last_signal_idx = i

        return signals
