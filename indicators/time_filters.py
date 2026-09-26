"""
Filtros de Sesión y Horarios de la Bolsa de Nueva York (NYSE / NASDAQ - Eastern Time)
Permite discriminar fases operativas: Rango de Apertura, Tendencia Matutina, Chop Zone y Power Hour.
"""

from datetime import datetime, time
import pandas as pd


def add_nyse_session_filters(df: pd.DataFrame) -> pd.DataFrame:
    """
    Agrega marcas temporales y clasifica la vela en una fase de la sesión de NYSE.
    """
    data = df.copy()

    # Asegurar formato datetime UTC y convertir a US/Eastern (New York)
    if not pd.api.types.is_datetime64_any_dtype(data["time"]):
        data["time"] = pd.to_datetime(data["time"])

    # Si no tiene timezone, asumir UTC
    if data["time"].dt.tz is None:
        times_ny = data["time"].dt.tz_localize("UTC").dt.tz_convert("America/New_York")
    else:
        times_ny = data["time"].dt.tz_convert("America/New_York")

    data["ny_time"] = times_ny
    data["ny_hour"] = times_ny.dt.hour
    data["ny_minute"] = times_ny.dt.minute
    data["ny_date"] = times_ny.dt.date

    # Clasificación de Fases de la Sesión
    # 0 = Fuera de sesión
    # 1 = Apertura / Price Discovery (09:30 - 10:00)
    # 2 = Prime Trend Window (10:00 - 11:30)
    # 3 = Midday Chop Zone (11:30 - 14:00)
    # 4 = Afternoon Momentum (14:00 - 15:30)
    # 5 = Power Hour / Cierre (15:30 - 16:00)
    time_float = data["ny_hour"] + (data["ny_minute"] / 60.0)

    data["session_phase"] = 0
    data.loc[(time_float >= 9.5) & (time_float < 10.0), "session_phase"] = 1
    data.loc[(time_float >= 10.0) & (time_float < 11.5), "session_phase"] = 2
    data.loc[(time_float >= 11.5) & (time_float < 14.0), "session_phase"] = 3
    data.loc[(time_float >= 14.0) & (time_float < 15.5), "session_phase"] = 4
    data.loc[(time_float >= 15.5) & (time_float <= 16.0), "session_phase"] = 5

    # Rango de apertura de 30 minutos (09:30 - 10:00)
    or_bars = data[data["session_phase"] == 1]
    if not or_bars.empty:
        or_highs = or_bars.groupby("ny_date")["high"].max()
        or_lows = or_bars.groupby("ny_date")["low"].min()
        data["or_high"] = data["ny_date"].map(or_highs)
        data["or_low"] = data["ny_date"].map(or_lows)
    else:
        data["or_high"] = None
        data["or_low"] = None

    return data
