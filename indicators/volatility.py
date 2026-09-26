"""
Indicadores de Volatilidad: ATR (Average True Range) y Bandas de Bollinger.
"""

import pandas as pd


def add_atr(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """
    Calcula el ATR (Rango Verdadero Promedio) para dimensionamiento de stops y volatilidad.
    """
    data = df.copy()
    prev_close = data["close"].shift(1)
    tr1 = data["high"] - data["low"]
    tr2 = (data["high"] - prev_close).abs()
    tr3 = (data["low"] - prev_close).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    data["atr_14"] = tr.rolling(window=period).mean()
    # SMA del ATR para detectar expansión vs compresión de volatilidad (Video 15)
    data["atr_sma_50"] = data["atr_14"].rolling(window=50).mean()
    data["volatility_expansion"] = data["atr_14"] > data["atr_sma_50"]
    return data


def add_bollinger_bands(df: pd.DataFrame, period: int = 20, num_std: float = 2.0) -> pd.DataFrame:
    """
    Calcula las Bandas de Bollinger para estrategias de reversión a la media y canales.
    """
    data = df.copy()
    data["bb_middle"] = data["close"].rolling(window=period).mean()
    std = data["close"].rolling(window=period).std()
    data["bb_upper"] = data["bb_middle"] + (std * num_std)
    data["bb_lower"] = data["bb_middle"] - (std * num_std)
    data["bb_bandwidth"] = (data["bb_upper"] - data["bb_lower"]) / data["bb_middle"]
    return data
