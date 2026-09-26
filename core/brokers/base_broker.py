"""
Interfaz Base para Brokers Regulados en EE.UU. (SEC / FINRA / SIPC)
Define el contrato estándar para conectar brokers algorítmicos: Alpaca, Interactive Brokers y Tradier.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional


class BaseBroker(ABC):
    """
    Clase abstracta que define las operaciones estándar que todo broker debe implementar.
    """

    def __init__(self, name: str, paper_mode: bool = True):
        self.name = name
        self.paper_mode = paper_mode
        self.connected = False

    @abstractmethod
    def get_account_summary(self) -> Dict:
        """
        Retorna balance de cuenta, poder de compra, equity y estado de Pattern Day Trader (PDT).
        """
        pass

    @abstractmethod
    def get_positions(self) -> List[Dict]:
        """
        Retorna las posiciones abiertas en acciones, ETFs y opciones.
        """
        pass

    @abstractmethod
    def submit_order(
        self,
        symbol: str,
        qty: int,
        side: str,          # 'buy' o 'sell'
        order_type: str,    # 'market' o 'limit'
        limit_price: Optional[float] = None,
        instrument_type: str = "equity",  # 'equity' o 'option'
        option_symbol: Optional[str] = None
    ) -> Dict:
        """
        Envía una orden al mercado para acciones o contratos de opciones.
        """
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """Verifica si las credenciales y la conexión con el broker están activas."""
        pass
