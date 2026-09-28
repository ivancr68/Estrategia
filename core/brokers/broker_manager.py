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
    Enrutador multibróker institucional para ejecución simultánea,
    consulta combinada de saldos y configuración de credenciales.
    Soporta modo Multi-Bróker Concurrente (todos activos a la vez).
    """

    def __init__(self, default_broker: str = "ALL"):
        import os
        self.brokers: Dict[str, BaseBroker] = {
            "ALPACA": AlpacaBroker(
                api_key=os.getenv("ALPACA_API_KEY", getattr(config, "ALPACA_API_KEY", "PKJ4MJOYYRRLM33DWVNL2CFUT5")),
                secret_key=os.getenv("ALPACA_SECRET_KEY", getattr(config, "ALPACA_SECRET_KEY", "3vyygErLE3Q3itKceGobFKa2qCy4sxdvFVEqZtSbyZXS")),
                paper_mode=str(os.getenv("ALPACA_PAPER_MODE", getattr(config, "ALPACA_PAPER_MODE", True))).lower() == "true"
            ),
            "IBKR": InteractiveBrokers(
                gateway_url=os.getenv("IBKR_GATEWAY_URL", getattr(config, "IBKR_GATEWAY_URL", "https://localhost:5000/v1/api")),
                account_id=os.getenv("IBKR_ACCOUNT_ID", getattr(config, "IBKR_ACCOUNT_ID", "DUR220661")),
                paper_mode=True
            ),
            "TRADIER": TradierBroker(
                access_token=os.getenv("TRADIER_ACCESS_TOKEN", getattr(config, "TRADIER_ACCESS_TOKEN", "DEMO_TRADIER_TOKEN")),
                account_id=os.getenv("TRADIER_ACCOUNT_ID", getattr(config, "TRADIER_ACCOUNT_ID", "VA12345678")),
                paper_mode=True
            )
        }
        # Conjunto de brokers activos concurrentemente (Alpaca + IBKR + Tradier Sandbox)
        self.active_brokers_set: set = {"ALPACA", "IBKR", "TRADIER"}

    def _is_configured(self, b_id: str) -> bool:
        if b_id == "ALPACA":
            return bool(getattr(self.brokers["ALPACA"], "api_key", "") not in ["", "TU_ALPACA_API_KEY"])
        if b_id == "IBKR":
            return bool(getattr(self.brokers["IBKR"], "account_id", "") not in ["", "DU1234567"])
        if b_id == "TRADIER":
            token = getattr(self.brokers["TRADIER"], "access_token", "")
            return bool(token and token not in ["", "DEMO_TRADIER_TOKEN", "DEMO_TOKEN_123", "TU_TRADIER_TOKEN"])
        return False

    @property
    def active_broker(self) -> BaseBroker:
        """Retorna un broker representativo de los activos (preferencia ALPACA > IBKR > TRADIER)."""
        if len(self.active_brokers_set) == 1:
            name = next(iter(self.active_brokers_set))
            if name in self.brokers:
                return self.brokers[name]
        for name in ["ALPACA", "IBKR", "TRADIER"]:
            if name in self.active_brokers_set and name in self.brokers:
                return self.brokers[name]
        return self.brokers["ALPACA"]

    @property
    def active_broker_name(self) -> str:
        count = len(self.active_brokers_set)
        if count == 3:
            return "Multi-Bróker (Alpaca + IBKR + Tradier)"
        elif count > 0:
            return f"Multi-Bróker ({' + '.join(sorted(self.active_brokers_set))})"
        return "Ningún Bróker Activo"

    def is_broker_active(self, broker_id: str) -> bool:
        return broker_id.upper() in self.active_brokers_set

    def toggle_broker_active(self, broker_id: str, active: Optional[bool] = None) -> bool:
        b_id = broker_id.upper()
        if b_id in ["ALL", "MULTI"]:
            if active is False:
                self.active_brokers_set.clear()
            else:
                self.active_brokers_set = {"ALPACA", "IBKR", "TRADIER"}
            return True

        if b_id in self.brokers:
            if active is None:
                if b_id in self.active_brokers_set:
                    self.active_brokers_set.remove(b_id)
                else:
                    self.active_brokers_set.add(b_id)
            elif active:
                self.active_brokers_set.add(b_id)
            else:
                self.active_brokers_set.discard(b_id)
            return True
        return False

    def set_active_broker(self, name: str) -> bool:
        name_clean = name.upper()
        if name_clean in ["ALL", "MULTI"]:
            self.active_brokers_set = {"ALPACA", "IBKR", "TRADIER"}
            return True
        if name_clean in self.brokers:
            self.active_brokers_set = {name_clean}
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
        self.set_active_broker(broker_id)

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
                    try:
                        setattr(config, k, v)
                    except Exception:
                        pass
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
            is_act = key in self.active_brokers_set
            statuses.append({
                "id": key,
                "name": broker.name,
                "is_active": is_act,
                "connected": acc["connected"],
                "status": acc["status"],
                "equity": acc["equity"],
                "buying_power": acc["buying_power"],
                "mode": acc["mode"],
                "account_number": acc.get("account_number", "")
            })
        return statuses

    def get_combined_summary(self) -> Dict:
        """Calcula el balance y poder de compra combinado de todos los brokers activos."""
        statuses = self.get_all_brokers_status()
        active_list = [s for s in statuses if s["is_active"]]
        total_equity = sum(s["equity"] for s in active_list)
        total_buying_power = sum(s["buying_power"] for s in active_list)
        active_ids = [s["id"] for s in active_list]

        if len(active_list) == 3:
            title = "Multi-Bróker Activo (Alpaca + IBKR + Tradier) 🟢"
        elif len(active_list) > 0:
            title = f"Multi-Bróker ({' + '.join(active_ids)}) 🟢"
        else:
            title = "Ningún Bróker Activo ⚪"

        return {
            "total_equity": total_equity,
            "total_buying_power": total_buying_power,
            "active_count": len(active_list),
            "active_ids": active_ids,
            "display_title": title
        }
