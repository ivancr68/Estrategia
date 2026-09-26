"""
Indicadores de Momentum: MACD (Moving Average Convergence Divergence) y RSI (Relative Strength Index).
"""

import pandas as pd


def add_macd(df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    """
    Calcula la línea MACD, la línea de señal y el histograma.
    """
    data = df.copy()
    ema_fast = data["close"].ewm(span=fast, adjust=False).mean()
    ema_slow = data["close"].ewm(span=slow, adjust=False).mean()
    data["macd"] = ema_fast - ema_slow
    data["macd_signal"] = data["macd"].ewm(span=signal, adjust=False).mean()
    data["macd_hist"] = data["macd"] - data["macd_signal"]
    return data


def add_rsi(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """
    Calcula el RSI (Índice de Fuerza Relativa) estándar de 14 períodos.
    """
    data = df.copy()
    delta = data["close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    # Wilder's Smoothing
    avg_gain = gain.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, min_periods=period, adjust=False).mean()

    rs = avg_gain / avg_loss.replace(0, 1e-9)
    data["rsi"] = 100 - (100 / (1 + rs))
    return data
