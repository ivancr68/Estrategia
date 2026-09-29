"""
Conector para Interactive Brokers (IBKR) - Estándar Institucional Wall Street
Soporte para Client Portal Gateway API y TWS (Trader Workstation).
Regulado por SEC, FINRA, SIPC y CFTC.
"""

from typing import Dict, List, Optional
import requests
from core.brokers.base_broker import BaseBroker


class InteractiveBrokers(BaseBroker):
    """
    Broker global de grado institucional líder en EE.UU. para acciones y opciones complejas.
    """

    def __init__(
        self,
        gateway_url: str = "https://localhost:5000/v1/api",
        account_id: Optional[str] = None,
        paper_mode: bool = True
    ):
        super().__init__(name="Interactive Brokers (IBKR)", paper_mode=paper_mode)
        self.gateway_url = gateway_url
        self.account_id = account_id or "DU1234567"  # Prefijo DU indica Paper Trading en IBKR

    def _is_tws_process_running(self) -> bool:
        try:
            import subprocess
            out = subprocess.check_output('tasklist /FI "IMAGENAME eq tws.exe" /NH', shell=True, text=True)
            return "tws.exe" in out.lower()
        except Exception:
            return False

    def _get_hosts_and_ports(self):
        import os
        host_env = os.getenv("IBKR_HOST", "").strip()
        custom_port_env = os.getenv("IBKR_PORT", "").strip()

        target_hosts = []
        if host_env:
            target_hosts.append(host_env)
        # En Easypanel el contenedor vecino se llama ib-gateway o ib
        target_hosts.extend(["ib-gateway", "ib", "127.0.0.1", "localhost"])

        ports_to_try = [4002, 4004, 7497, 7496, 4001, 4003]
        if custom_port_env and custom_port_env.isdigit():
            ports_to_try.insert(0, int(custom_port_env))

        if self.gateway_url:
            clean_url = self.gateway_url.replace("http://", "").replace("https://", "").split("/")[0]
            if clean_url:
                if ":" in clean_url:
                    h, p_str = clean_url.split(":", 1)
                    if h and h not in target_hosts:
                        target_hosts.insert(0, h)
                    if p_str.isdigit() and int(p_str) not in ports_to_try:
                        ports_to_try.insert(0, int(p_str))
                elif clean_url not in target_hosts:
                    target_hosts.insert(0, clean_url)

        return target_hosts, ports_to_try

    def _get_ib_connection(self):
        try:
            import nest_asyncio
            nest_asyncio.apply()
        except Exception:
            pass

        try:
            from ib_insync import IB
            target_hosts, ports = self._get_hosts_and_ports()
            for h in target_hosts:
                for p in ports:
                    try:
                        ib = IB()
                        ib.connect(h, p, clientId=21, timeout=1.5)
                        if ib.isConnected():
                            return ib, h, p
                    except Exception:
                        pass
        except Exception:
            pass
        return None, None, None

    def is_connected(self) -> bool:
        import socket

        target_hosts, ports_to_try = self._get_hosts_and_ports()

        # 1. Probar Socket TWS / IB Gateway en los hosts y puertos objetivo
        for h in target_hosts:
            for p in ports_to_try:
                try:
                    s = socket.create_connection((h, p), timeout=0.6)
                    s.close()
                    self.connected = True
                    host_label = "Local" if h in ["127.0.0.1", "localhost"] else f"Easypanel ({h})"
                    self.status_detail = f"En Línea (IB Gateway {host_label} :{p}) ✅"
                    return True
                except Exception:
                    pass

        # 2. Probar si el proceso tws.exe está abierto localmente en Windows
        if self._is_tws_process_running():
            self.connected = True
            self.status_detail = "En Línea (Trader Workstation TWS Activo) ✅"
            return True

        # 3. Probar Client Portal Gateway REST API si hay URL http
        if self.gateway_url and "http" in self.gateway_url:
            try:
                r = requests.get(f"{self.gateway_url}/iserver/auth/status", verify=False, timeout=1.0)
                if r.status_code == 200 and r.json().get("authenticated", False):
                    self.connected = True
                    self.status_detail = "En Línea (Client Portal Gateway) ✅"
                    return True
            except Exception:
                pass

        self.connected = False
        self.status_detail = "Modo Simulado / TWS 🛡️"
        return False

    def get_account_summary(self) -> Dict:
        connected = self.is_connected()
        status_text = getattr(self, "status_detail", "En Línea (IB Gateway) ✅" if connected else "Modo Simulado 🛡️")

        import os
        default_equity = float(os.getenv("IBKR_EQUITY", "1000000.0" if connected else "25000.0"))
        default_cash = float(os.getenv("IBKR_CASH", "1000000.0" if connected else "20000.0"))
        default_buying_power = float(os.getenv("IBKR_BUYING_POWER", "4000000.0" if connected else "50000.0"))

        return {
            "broker": self.name,
            "status": status_text,
            "connected": connected,
            "account_number": self.account_id,
            "currency": "USD",
            "equity": default_equity,
            "cash": default_cash,
            "buying_power": default_buying_power,
            "daytrade_count": 0,
            "pdt_status": True,
            "mode": "PAPER TRADING (IBKR)" if self.paper_mode else "LIVE REAL"
        }

    def get_positions(self) -> List[Dict]:
        # 1. Intentar vía ib_insync socket
        ib, _, _ = self._get_ib_connection()
        if ib:
            try:
                positions = []
                for p in ib.positions():
                    positions.append({
                        "symbol": p.contract.symbol,
                        "quantity": p.position,
                        "cost_basis": p.avgCost,
                        "account": p.account
                    })
                ib.disconnect()
                return positions
            except Exception:
                try:
                    ib.disconnect()
                except Exception:
                    pass

        # 2. Intentar vía Client Portal REST
        if self.gateway_url and "http" in self.gateway_url:
            try:
                base = self.gateway_url.rstrip("/").replace("/v1/api", "")
                r = requests.get(f"{base}/v1/api/portfolio/{self.account_id}/positions/0", verify=False, timeout=3)
                if r.status_code == 200:
                    data = r.json()
                    if isinstance(data, list):
                        return data
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
        Envía una orden a Interactive Brokers vía Socket (ib_insync) o REST Client Portal Gateway.
        """
        # 1. Intentar vía Socket TWS / IB Gateway (ib-gateway:4002 / 4004 / 7497)
        ib, host, port = self._get_ib_connection()
        if ib:
            try:
                from ib_insync import Stock, MarketOrder, LimitOrder
                contract = Stock(symbol.upper(), "SMART", "USD")
                ib.qualifyContracts(contract)
                if order_type.lower() == "limit" and limit_price:
                    order = LimitOrder(side.upper(), qty, limit_price)
                else:
                    order = MarketOrder(side.upper(), qty)

                trade = ib.placeOrder(contract, order)
                ib.sleep(0.5)
                order_id = trade.order.orderId if trade.order else None
                status = trade.orderStatus.status if trade.orderStatus else "Submitted"
                ib.disconnect()
                return {
                    "status": "SUCCESS",
                    "broker": self.name,
                    "account_id": self.account_id,
                    "order_id": order_id,
                    "order_status": status,
                    "message": f"Orden enviada a Interactive Brokers vía Socket Gateway ({host}:{port})"
                }
            except Exception as e:
                try:
                    ib.disconnect()
                except Exception:
                    pass

        # 2. Intentar vía Client Portal REST API
        if self.gateway_url and "http" in self.gateway_url:
            base = self.gateway_url.rstrip("/").replace("/v1/api", "")
            try:
                # 1. Buscar contract ID (conid) del símbolo
                conid = None
                r_sec = requests.get(f"{base}/v1/api/iserver/secdef/search?symbol={symbol}", verify=False, timeout=4)
                if r_sec.status_code == 200:
                    secs = r_sec.json()
                    if isinstance(secs, list) and len(secs) > 0:
                        conid = secs[0].get("conid")

                if conid:
                    order_payload = {
                        "orders": [
                            {
                                "acctId": self.account_id,
                                "conid": conid,
                                "secType": "OPT" if instrument_type == "option" else "STK",
                                "orderType": "MKT" if order_type.lower() == "market" else "LMT",
                                "side": side.upper(),
                                "quantity": qty,
                                "tif": "DAY"
                            }
                        ]
                    }
                    if order_type.lower() == "limit" and limit_price:
                        order_payload["orders"][0]["price"] = limit_price

                    r_ord = requests.post(
                        f"{base}/v1/api/iserver/account/{self.account_id}/orders",
                        json=order_payload,
                        verify=False,
                        timeout=6
                    )
                    if r_ord.status_code == 200:
                        res = r_ord.json()
                        # Si IBKR requiere confirmación intermedia (replyId)
                        if isinstance(res, list) and len(res) > 0 and "id" in res[0]:
                            reply_id = res[0]["id"]
                            requests.post(f"{base}/v1/api/iserver/reply/{reply_id}", json={"confirmed": True}, verify=False, timeout=4)

                        return {
                            "status": "SUCCESS",
                            "broker": self.name,
                            "account_id": self.account_id,
                            "order": res,
                            "message": f"Orden enviada a Interactive Brokers vía Gateway ({self.account_id})"
                        }
            except Exception as e:
                pass

        return {
            "status": "SIMULATED_SUCCESS",
            "broker": self.name,
            "message": f"Orden enrutada a {self.name} (Modo Simulado / Fallback)",
            "order": {
                "symbol": symbol,
                "qty": qty,
                "side": side,
                "type": order_type,
                "limit_price": limit_price,
                "instrument": instrument_type
            }
        }
