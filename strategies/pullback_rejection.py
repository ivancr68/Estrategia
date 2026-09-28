"""
Estrategia 4: Retroceso a EMA 50 con Patrón de Vela de Rechazo (Videos 7 y 10):
Aprovecha correcciones dentro de una tendencia macro fuerte (Pullbacks):
- El precio retrocede hacia la EMA 50 mientras la EMA 200 mantiene la tendencia.
- Se identifica una vela de rechazo (Pinbar / Martillo o vela envolvente).
- Entrada a precio de descuento con Stop Loss estrecho por ATR.
"""

from typing import Dict, List
import pandas as pd
from indicators.trend import add_moving_averages
from indicators.volatility import add_atr
from indicators.time_filters import add_nyse_session_filters
from strategies.base_strategy import BaseNYSEStrategy


class PullbackRejectionStrategy(BaseNYSEStrategy):
    """
    Estrategia de retroceso y rechazo en soporte dinámico (EMA 50) para continuación tendencial.
    """

    def __init__(self, symbols: List[str] = None, atr_mult_sl: float = 2.2, rr_ratio: float = 2.0):
        super().__init__(name="EMA50_Pullback_Rejection", symbols=symbols or ["SPY", "QQQ", "DIA"])
        self.atr_mult_sl = atr_mult_sl
        self.rr_ratio = rr_ratio

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        data = add_moving_averages(df)
        data = add_atr(data)
        data = add_nyse_session_filters(data)
        return data

    def generate_signals(self, df_dict: Dict[str, pd.DataFrame]) -> List[Dict]:
        signals = []

        for symbol in self.symbols:
            if symbol not in df_dict or df_dict[symbol].empty:
                continue

            df = self.calculate_indicators(df_dict[symbol])

            for i in range(2, len(df)):
                curr = df.iloc[i]
                prev = df.iloc[i - 1]

                if pd.isna(curr["ema_50"]) or pd.isna(curr["ema_200"]) or pd.isna(curr["atr_14"]):
                    continue

                phase = curr.get("session_phase", 0)
                if phase not in [2, 3, 4]:
                    continue

                open_p = curr["open"]
                close_p = curr["close"]
                high_p = curr["high"]
                low_p = curr["low"]
                ema_50 = curr["ema_50"]
                ema_200 = curr["ema_200"]
                atr = curr["atr_14"]
                dist_sl = atr * self.atr_mult_sl

                # PULLBACK ALCISTA:
                # 1. Tendencia alcista macro (EMA 50 > EMA 200)
                # 2. La mecha inferior toca o perfora la EMA 50 pero el cierre queda por encima (Rechazo)
                # 3. Vela de rebote (Cierre > Apertura)
                if (ema_50 > ema_200 and low_p <= ema_50 and close_p > ema_50 and close_p > open_p):
                    # Comprobar mecha inferior significativa (Patrón Martillo / Pinbar)
                    lower_wick = min(open_p, close_p) - low_p
                    body = abs(close_p - open_p)
                    if lower_wick >= body * 0.8:
                        sl = low_p - (atr * 0.5)
                        tp = close_p + (dist_sl * self.rr_ratio)
                        signals.append({
                            "symbol": symbol,
                            "time": curr["time"],
                            "strategy": self.name,
                            "action": "BUY_STOCK",
                            "instrument": "EQUITY",
                            "entry_price": round(close_p, 2),
                            "stop_loss": round(sl, 2),
                            "take_profit": round(tp, 2),
                            "atr": round(atr, 2),
                            "rationale": f"Rechazo en EMA 50 (Pinbar alcista con mecha de soporte) a favor de tendencia macro"
                        })

                # PULLBACK BAJISTA:
                elif (ema_50 < ema_200 and high_p >= ema_50 and close_p < ema_50 and close_p < open_p):
                    upper_wick = high_p - max(open_p, close_p)
                    body = abs(close_p - open_p)
                    if upper_wick >= body * 0.8:
                        sl = high_p + (atr * 0.5)
                        tp = close_p - (dist_sl * self.rr_ratio)
                        signals.append({
                            "symbol": symbol,
                            "time": curr["time"],
                            "strategy": self.name,
                            "action": "SELL_STOCK",
                            "instrument": "EQUITY",
                            "entry_price": round(close_p, 2),
                            "stop_loss": round(sl, 2),
                            "take_profit": round(tp, 2),
                            "atr": round(atr, 2),
                            "rationale": f"Rechazo en EMA 50 (Pinbar bajista con mecha de resistencia) a favor de tendencia macro"
                        })

        return signals
