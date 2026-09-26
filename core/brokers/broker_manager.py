"""
Gestor Central de Brokers Regulados (Multi-Broker Router):
Permite alternar dinámicamente entre Alpaca, Interactive Brokers (IBKR) y Tradier,
y actualizar credenciales de acceso directamente desde el Dashboard Web.
"""

from typing import Dict, List, Optional
from core.brokers.alpaca_broker import AlpacaBroker
from core.brokers.interactive_brokers import InteractiveBrokers
from core.brokers.tradier_broker import TradierBroker
from core.brokers.base_broker import BaseBroker
import config


class BrokerManager:
    """
    Enrutador multibróker para ejecución, consulta de saldos y configuración de credenciales.
    """

    def __init__(self, default_broker: str = "ALPACA"):
        self.brokers: Dict[str, BaseBroker] = {
            "ALPACA": AlpacaBroker(
                api_key=getattr(config, "ALPACA_API_KEY", "PKJ4MJOYYRRLM33DWVNL2CFUT5"),
                secret_key=getattr(config, "ALPACA_SECRET_KEY", "3vyygErLE3Q3itKceGobFKa2qCy4sxdvFVEqZtSbyZXS"),
                paper_mode=True
            ),
            "IBKR": InteractiveBrokers(
                gateway_url=getattr(config, "IBKR_GATEWAY_URL", "https://localhost:5000/v1/api"),
                account_id=getattr(config, "IBKR_ACCOUNT_ID", "DU1234567"),
                paper_mode=True
            ),
            "TRADIER": TradierBroker(
                access_token=getattr(config, "TRADIER_ACCESS_TOKEN", "DEMO_TRADIER_TOKEN"),
                account_id=getattr(config, "TRADIER_ACCOUNT_ID", "VA12345678"),
                paper_mode=True
            )
        }
        self.active_broker_name = default_broker.upper() if default_broker.upper() in self.brokers else "ALPACA"

    @property
    def active_broker(self) -> BaseBroker:
        return self.brokers[self.active_broker_name]

    def set_active_broker(self, name: str) -> bool:
        name_clean = name.upper()
        if name_clean in self.brokers:
            self.active_broker_name = name_clean
            return True
        return False

    def update_credentials(self, broker_id: str, creds: Dict) -> Dict:
        """Actualiza credenciales, persiste a .env y verifica la conexión inmediatamente."""
        broker_id = broker_id.upper()
        if broker_id not in self.brokers:
            return {"success": False, "message": f"Broker {broker_id} no reconocido"}

        env_updates = {}
        if broker_id == "ALPACA":
            api_key = creds.get("api_key", "").strip() or getattr(config, "ALPACA_API_KEY", "")
            secret_key = creds.get("secret_key", "").strip() or getattr(config, "ALPACA_SECRET_KEY", "")
            paper_mode = creds.get("paper_mode", True)
            if isinstance(paper_mode, str):
                paper_mode = paper_mode.lower() == "true"
            self.brokers["ALPACA"] = AlpacaBroker(api_key=api_key, secret_key=secret_key, paper_mode=paper_mode)
            env_updates["ALPACA_API_KEY"] = api_key
            env_updates["ALPACA_SECRET_KEY"] = secret_key
            env_updates["ALPACA_PAPER_MODE"] = str(paper_mode)

        elif broker_id == "IBKR":
            gateway_url = creds.get("gateway_url", "https://localhost:5000/v1/api").strip()
            account_id = creds.get("account_id", "DU1234567").strip()
            self.brokers["IBKR"] = InteractiveBrokers(gateway_url=gateway_url, account_id=account_id, paper_mode=True)
            env_updates["IBKR_GATEWAY_URL"] = gateway_url
            env_updates["IBKR_ACCOUNT_ID"] = account_id

        elif broker_id == "TRADIER":
            access_token = creds.get("access_token", "").strip()
            account_id = creds.get("account_id", "").strip()
            paper_mode = creds.get("paper_mode", True)
            if isinstance(paper_mode, str):
                paper_mode = paper_mode.lower() == "true"
            self.brokers["TRADIER"] = TradierBroker(access_token=access_token, account_id=account_id, paper_mode=paper_mode)
            env_updates["TRADIER_ACCESS_TOKEN"] = access_token
            env_updates["TRADIER_ACCOUNT_ID"] = account_id
            env_updates["TRADIER_PAPER_MODE"] = str(paper_mode)

        # Guardar en archivo .env
        self._persist_to_env(env_updates)

        connected = self.brokers[broker_id].is_connected()
        status_text = "En línea y validado con API oficial ✅" if connected else "Conectado en Modo Simulado (Paper) 🛡️"
        return {
            "success": True,
            "broker_id": broker_id,
            "connected": connected,
            "message": f"Credenciales de {self.brokers[broker_id].name} guardadas con éxito. Estado: {status_text}"
        }

    def _persist_to_env(self, updates: Dict[str, str]):
        """Persiste las llaves al archivo .env local para recordarlas en reinicios."""
        try:
            import os
            env_path = config.BASE_DIR / ".env"
            env_dict = {}
            if env_path.exists():
                with open(env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line_clean = line.strip()
                        if line_clean and not line_clean.startswith("#") and "=" in line_clean:
                            k, v = line_clean.split("=", 1)
                            env_dict[k.strip()] = v.strip()
            for k, v in updates.items():
                if v:
                    env_dict[k] = str(v)
                    os.environ[k] = str(v)
            with open(env_path, "w", encoding="utf-8") as f:
                for k, v in env_dict.items():
                    f.write(f"{k}={v}\n")
        except Exception:
            pass

    def get_all_brokers_status(self) -> List[Dict]:
        """Retorna el estado de conexión y cuenta de los 3 brokers."""
        statuses = []
        for key, broker in self.brokers.items():
            acc = broker.get_account_summary()
            statuses.append({
                "id": key,
                "name": broker.name,
                "is_active": (key == self.active_broker_name),
                "connected": acc["connected"],
                "status": acc["status"],
                "equity": acc["equity"],
                "buying_power": acc["buying_power"],
                "mode": acc["mode"],
                "account_number": acc.get("account_number", "")
            })
        return statuses
