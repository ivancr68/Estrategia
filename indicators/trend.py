"""
Indicadores de Tendencia para NYSE: Medias Móviles Exponenciales (EMA 20, 50, 200) y Detección de Régimen.
"""

import pandas as pd


def add_moving_averages(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calcula EMA 20, 50 y 200 para determinar la alineación tendencial.
    """
    data = df.copy()
    data["ema_20"] = data["close"].ewm(span=20, adjust=False).mean()
    data["ema_50"] = data["close"].ewm(span=50, adjust=False).mean()
    data["ema_200"] = data["close"].ewm(span=200, adjust=False).mean()

    # Régimen tendencial: 1 = Alcista fuerte, -1 = Bajista fuerte, 0 = Mixto / Lateral
    data["trend_regime"] = 0
    bullish_mask = (data["ema_20"] > data["ema_50"]) & (data["ema_50"] > data["ema_200"]) & (data["close"] > data["ema_20"])
    bearish_mask = (data["ema_20"] < data["ema_50"]) & (data["ema_50"] < data["ema_200"]) & (data["close"] < data["ema_20"])

    data.loc[bullish_mask, "trend_regime"] = 1
    data.loc[bearish_mask, "trend_regime"] = -1

    return data
