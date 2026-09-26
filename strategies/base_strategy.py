"""
Interfaz Base para Estrategias de Trading Algorítmico (Acciones, ETFs y Opciones)
Permite implementar múltiples variantes y combinaciones de estrategias según las fuentes de estudio.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional
import pandas as pd


class BaseNYSEStrategy(ABC):
    """
    Clase abstracta que define el contrato de cualquier estrategia para el mercado estadounidense.
    """

    def __init__(self, name: str, symbols: List[str] = None):
        self.name = name
        self.symbols = symbols or ["SPY", "QQQ", "IWM", "DIA"]

    @abstractmethod
    def generate_signals(self, df_dict: Dict[str, pd.DataFrame]) -> List[Dict]:
        """
        Evalúa el estado del mercado para los símbolos y genera señales estructuradas.

        Cada señal retornada es un diccionario con:
        - symbol: str ('SPY', 'QQQ', etc.)
        - timestamp: datetime
        - action: 'BUY_STOCK', 'SELL_STOCK', 'BUY_CALL', 'BUY_PUT', 'SPREAD', etc.
        - instrument: 'EQUITY' o 'OPTION'
        - entry_price: float
        - stop_loss: float
        - take_profit: float
        - option_details: dict (strike, dte, delta, spread_type) si aplica
        - rationale: str (explicación de la regla que disparó la señal)
        """
        pass

    @abstractmethod
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calcula los indicadores técnicos requeridos por la estrategia."""
        pass
