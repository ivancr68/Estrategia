"""
Conector Oficial para Alpaca Markets (Bolsa de Nueva York - Acciones y Opciones)
Soporte para Paper Trading y Live Trading mediante API REST v2.
"""

from typing import Dict, List, Optional
import requests
from core.brokers.base_broker import BaseBroker


class AlpacaBroker(BaseBroker):
    """
    Broker algorítmico moderno regulado por FINRA y SIPC con soporte para Acciones y Opciones.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        paper_mode: bool = True
    ):
        super().__init__(name="Alpaca Markets", paper_mode=paper_mode)
        import os
        self.api_key = api_key or os.getenv("ALPACA_API_KEY", "PKLYBDE6TEEGYHRGLPFQ2ULQTT")
        self.secret_key = secret_key or os.getenv("ALPACA_SECRET_KEY", "C5kWhJZFZPKxtuJtRnxF8XQq9SPurxMXNh49epVYx6hV")
        self.base_url = "https://paper-api.alpaca.markets" if paper_mode else "https://api.alpaca.markets"
        self.headers = {
            "APCA-API-KEY-ID": self.api_key,
            "APCA-API-SECRET-KEY": self.secret_key,
            "Content-Type": "application/json"
        }

    def is_connected(self) -> bool:
        try:
            r = requests.get(f"{self.base_url}/v2/account", headers=self.headers, timeout=4)
            if r.status_code == 200:
                self.connected = True
                return True
        except Exception:
            pass
        self.connected = False
        return False

    def get_account_summary(self) -> Dict:
        """Consulta el estado real de la cuenta o retorna simulación calibrada si está desconectado."""
        if self.is_connected():
            try:
                r = requests.get(f"{self.base_url}/v2/account", headers=self.headers, timeout=5)
                if r.status_code == 200:
                    data = r.json()
                    equity = float(data.get("equity", 25000.0))
                    cash = float(data.get("cash", 25000.0))
                    last_equity = float(data.get("last_equity", equity))
                    long_mv = abs(float(data.get("long_market_value", 0.0)))
                    short_mv = abs(float(data.get("short_market_value", 0.0)))
                    invested = round(long_mv + short_mv, 2)
                    open_pl = round(equity - last_equity, 2)
                    return {
                        "broker": self.name,
                        "status": data.get("status", "ACTIVE"),
                        "connected": True,
                        "account_number": data.get("account_number", "ALPACAPAPER1"),
                        "currency": data.get("currency", "USD"),
                        "equity": equity,
                        "cash": cash,
                        "invested": invested,
                        "open_pl": open_pl,
                        "buying_power": float(data.get("buying_power", 50000.0)),
                        "daytrade_count": int(data.get("daytrade_count", 0)),
                        "pdt_status": data.get("pattern_day_trader", False),
                        "mode": "PAPER TRADING" if self.paper_mode else "LIVE REAL"
                    }
            except Exception:
                pass

        # Fallback offline / demostración
        return {
            "broker": self.name,
            "status": "SANDBOX / SIMULADO",
            "connected": False,
            "account_number": "ALPACAPAPER_DEMO",
            "currency": "USD",
            "equity": 25000.0,
            "cash": 25000.0,
            "invested": 0.0,
            "open_pl": 0.0,
            "buying_power": 50000.0,
            "daytrade_count": 0,
            "pdt_status": False,
            "mode": "PAPER TRADING" if self.paper_mode else "LIVE REAL"
        }

    def get_positions(self) -> List[Dict]:
        if self.is_connected():
            try:
                r = requests.get(f"{self.base_url}/v2/positions", headers=self.headers, timeout=5)
                if r.status_code == 200:
                    return r.json()
            except Exception:
                pass
        return []

    def submit_order(
        self,
        symbol: str,
        qty: int,
        side: str,
        order_type: str = "market",
        limit_price: Optional[float] = None,
        instrument_type: str = "equity",
        option_symbol: Optional[str] = None
    ) -> Dict:
        """
        Envía una orden al endpoint /v2/orders de Alpaca.
        """
        payload = {
            "symbol": option_symbol if instrument_type == "option" and option_symbol else symbol,
            "qty": str(qty),
            "side": side.lower(),
            "type": order_type.lower(),
            "time_in_force": "day"
        }
        if order_type.lower() == "limit" and limit_price:
            payload["limit_price"] = str(limit_price)

        if self.is_connected():
            try:
                r = requests.post(f"{self.base_url}/v2/orders", json=payload, headers=self.headers, timeout=6)
                if r.status_code in [200, 201]:
                    return {"status": "SUCCESS", "order": r.json(), "broker": self.name}
                else:
                    return {"status": "FAILED", "error": r.text, "broker": self.name}
            except Exception as e:
                return {"status": "ERROR", "error": str(e), "broker": self.name}

        # Simulación local si no está conectado en vivo
        return {
            "status": "SIMULATED_SUCCESS",
            "broker": self.name,
            "message": f"Orden simulada ejecutada en {self.name}",
            "order": payload
        }
