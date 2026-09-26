"""
Evaluador de Confluencia y Convicción Profesional (Institutional Quality Scorer):
Califica cada oportunidad de trading en una escala de 0 a 100% evaluando múltiples factores
(Tendencia, Momentum, Volatilidad, Horario de Wall Street y Ratio Asimétrico).
Solo las oportunidades con puntuación >= 80% activan alertas institucionales.
"""

from typing import Dict
import pandas as pd


class ConfluenceScorer:
    """
    Motor cuantitativo de ponderación y filtrado de señales profesionales.
    """

    @staticmethod
    def score_signal(signal: Dict, df: pd.DataFrame) -> int:
        score = 0
        symbol = signal["symbol"]
        price = signal["entry_price"]
        sl = signal["stop_loss"]
        tp = signal["take_profit"]
        action = signal.get("action", "")
        is_buy = "BUY" in action or "CALL" in action
        strategy = signal.get("strategy", "")

        if df.empty:
            return 75

        # Localizar la vela correspondiente al momento exacto de la señal
        sig_time = signal.get("time")
        if sig_time is not None and "time" in df.columns:
            matched = df[df["time"] <= sig_time]
            candle = matched.iloc[-1] if not matched.empty else df.iloc[-1]
        else:
            candle = df.iloc[-1]

        # 1. Alineación de Tendencia Macro (25 Puntos)
        if "ema_200" in candle and not pd.isna(candle["ema_200"]):
            ema_200 = candle["ema_200"]
            if (is_buy and price > ema_200) or (not is_buy and price < ema_200):
                score += 15
            elif "MeanReversion" in strategy:
                # En reversión a la media se permite contratendencia moderada
                score += 10

        if "ema_20" in candle and "ema_50" in candle:
            if not pd.isna(candle["ema_20"]) and not pd.isna(candle["ema_50"]):
                if (is_buy and candle["ema_20"] > candle["ema_50"]) or (not is_buy and candle["ema_20"] < candle["ema_50"]):
                    score += 10
                elif "MeanReversion" in strategy:
                    score += 5

        # 2. Confluencia de Momentum (25 Puntos)
        if "rsi" in candle and not pd.isna(candle["rsi"]):
            rsi = candle["rsi"]
            if "MeanReversion" in strategy:
                # Reversión a la media busca extremos
                if (is_buy and rsi <= 35) or (not is_buy and rsi >= 65):
                    score += 15
            else:
                # Seguimiento de tendencia busca momentum sano
                if is_buy and (40 <= rsi <= 68):
                    score += 15
                elif not is_buy and (32 <= rsi <= 60):
                    score += 15

        if "macd_hist" in candle and not pd.isna(candle["macd_hist"]):
            if (is_buy and candle["macd_hist"] > 0) or (not is_buy and candle["macd_hist"] < 0):
                score += 10
            elif "MeanReversion" in strategy:
                score += 5

        # 3. Expansión de Volatilidad (20 Puntos)
        if candle.get("volatility_expansion", True):
            score += 20

        # 4. Filtro de Horario Institucional NYSE (15 Puntos)
        phase = candle.get("session_phase", 2)
        if phase in [2, 4]:  # Prime Trend (10:00 - 11:30) o Afternoon Push (14:00 - 15:30)
            score += 15
        elif phase == 3:  # Midday Chop
            score += 5

        # 5. Ratio Riesgo / Beneficio Asimétrico (15 Puntos)
        risk = abs(price - sl)
        reward = abs(tp - price)
        if risk > 0 and (reward / risk) >= 2.0:
            score += 15
        elif risk > 0 and (reward / risk) >= 1.5:
            score += 10

        return min(100, max(0, score))
