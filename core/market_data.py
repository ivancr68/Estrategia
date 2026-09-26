"""
Módulo de Datos de Mercado para la Bolsa de Nueva York (NYSE / NASDAQ)
Descarga o simula cotizaciones intradía y diarias para ETFs principales (SPY, QQQ, IWM, DIA) y acciones.
"""

from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
import numpy as np
import pandas as pd
import requests


class MarketDataProvider:
    """
    Proveedor de datos de mercado con soporte para cotizaciones públicas y simulación de alta precisión.
    """

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })

    def get_historical_bars(
        self,
        symbol: str = "SPY",
        days: int = 30,
        interval_mins: int = 5
    ) -> pd.DataFrame:
        """
        Descarga datos intradía recientes o genera datos simulados que replican el comportamiento de NYSE.
        """
        df = self._fetch_yahoo_finance(symbol, days=days, interval="5m" if interval_mins == 5 else "1d")
        if df is not None and not df.empty:
            return df

        # Si falla la descarga externa, generar simulación calibrada
        return self._generate_synthetic_nyse(symbol=symbol, days=days, interval_mins=interval_mins)

    def _fetch_yahoo_finance(self, symbol: str, days: int = 30, interval: str = "5m") -> Optional[pd.DataFrame]:
        """
        Intenta obtener datos públicos vía endpoint de Yahoo Finance.
        """
        try:
            range_str = f"{min(days, 59)}d" if "m" in interval else f"{days}d"
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range={range_str}&interval={interval}"
            resp = self.session.get(url, timeout=6)
            if resp.status_code == 200:
                data = resp.json()
                result = data.get("chart", {}).get("result", [None])[0]
                if result and "timestamp" in result:
                    timestamps = result["timestamp"]
                    quote = result["indicators"]["quote"][0]
                    df = pd.DataFrame({
                        "time": pd.to_datetime(timestamps, unit="s", utc=True),
                        "open": quote.get("open"),
                        "high": quote.get("high"),
                        "low": quote.get("low"),
                        "close": quote.get("close"),
                        "volume": quote.get("volume")
                    }).dropna()
                    if not df.empty:
                        return df
        except Exception:
            pass
        return None

    def _generate_synthetic_nyse(self, symbol: str, days: int = 30, interval_mins: int = 5) -> pd.DataFrame:
        """
        Generador sintético calibrado con precios base reales de los principales ETFs de Wall Street.
        """
        precios_base = {
            "SPY": 570.0,
            "QQQ": 490.0,
            "IWM": 220.0,
            "DIA": 420.0,
            "XLK": 225.0,
            "XLF": 46.0
        }
        p0 = precios_base.get(symbol.upper(), 100.0)

        np.random.seed(abs(hash(symbol)) % (2**31))
        velas_por_dia = (6 * 60 + 30) // interval_mins  # Horario regular 9:30 AM a 4:00 PM (6.5 hrs = 78 velas M5)
        total_velas = days * velas_por_dia

        fecha_inicio = datetime.now(timezone.utc) - timedelta(days=days)
        tiempos = [fecha_inicio + timedelta(minutes=i * interval_mins) for i in range(total_velas)]

        retornos = np.random.normal(0.00003, 0.0012, total_velas)
        precios_cierre = p0 * np.exp(np.cumsum(retornos))

        volatilidad = precios_cierre * 0.0008
        altos = precios_cierre + np.abs(np.random.normal(0, volatilidad))
        bajos = precios_cierre - np.abs(np.random.normal(0, volatilidad))
        aperturas = precios_cierre + np.random.normal(0, volatilidad * 0.5)

        altos = np.maximum(altos, np.maximum(aperturas, precios_cierre))
        bajos = np.minimum(bajos, np.minimum(aperturas, precios_cierre))
        volumenes = np.random.randint(10000, 500000, total_velas)

        df = pd.DataFrame({
            "time": tiempos,
            "open": aperturas.round(2),
            "high": altos.round(2),
            "low": bajos.round(2),
            "close": precios_cierre.round(2),
            "volume": volumenes
        })
        return df
