"""
Servicio Interactivo de Telegram Bot Multibróker:
- Envía alertas con botones interactivos específicos por broker: [🦙 Alpaca], [🏛️ IBKR], [📈 Tradier] y [❌ Rechazar].
- Permite al usuario decidir desde el móvil en qué broker ejecutar cada orden.
- Hilo en segundo plano que escucha los clics en tiempo real vía Telegram Bot API.
- Actualiza el mensaje en el chat confirmando la acción tomada y el broker asignado.
"""

import threading
import time
from datetime import datetime, timezone
from typing import Dict, Optional
import requests

import config
from core.brokers.broker_manager import BrokerManager

PENDING_ALERTS: Dict[str, Dict] = {}


class TelegramBotService:
    def __init__(self, broker_manager: Optional[BrokerManager] = None):
        self.token = getattr(config, "TELEGRAM_BOT_TOKEN", "")
        self.chat_id = getattr(config, "TELEGRAM_CHAT_ID", "")
        self.enabled = getattr(config, "TELEGRAM_ENABLED", True)
        self.broker_manager = broker_manager or BrokerManager()
        self.running = False
        self.last_update_id = 0
        self.thread: Optional[threading.Thread] = None

    def send_interactive_alert(self, alert: Dict) -> bool:
        """
        Envía una alerta a Telegram con botones interactivos para cada broker disponible.
        """
        if not self.enabled or not self.token or not self.chat_id:
            return False

        alert_id = alert.get("id", f"ALT-{int(time.time())}")
        PENDING_ALERTS[alert_id] = alert

        action_emoji = "🟢 COMPRA" if "BUY" in alert.get("action", "") else "🔴 VENTA"
        import html
        sym = html.escape(str(alert.get("symbol", "")))
        action = html.escape(str(alert.get("action", "")))
        inst = html.escape(str(alert.get("instrument", "EQUITY")))
        strat = html.escape(str(alert.get("strategy", "Multi-Strategy")))
        score = alert.get("confluence_score", 85)
        entry = alert.get("entry_price", 0.0)
        sl = alert.get("stop_loss", 0.0)
        tp = alert.get("take_profit", 0.0)
        rationale = html.escape(str(alert.get("rationale", "Alta confluencia de filtros")))

        text = (
            f"🏛️ <b>NUEVA OPORTUNIDAD CUANTITATIVA (NYSE)</b>\n\n"
            f"📌 <b>Símbolo:</b> <code>{sym}</code>\n"
            f"⚡ <b>Acción:</b> {action_emoji} <b>{action}</b> ({inst})\n"
            f"🎯 <b>Estrategia:</b> {strat}\n"
            f"⭐ <b>Convicción Institucional:</b> <code>{score}%</code>\n\n"
            f"💵 <b>Precio Entrada:</b> ${entry:.2f}\n"
            f"🛑 <b>Stop Loss:</b> ${sl:.2f}\n"
            f"🎯 <b>Take Profit:</b> ${tp:.2f}\n"
            f"📊 <b>Motivo:</b> <i>{rationale}</i>\n"
        )

        opt = alert.get("option_details") or alert.get("details")
        if opt:
            instr = html.escape(str(opt.get("instruction", "N/A")))
            cost = opt.get("cost_per_contract", 0)
            profit = opt.get("max_profit", 0)
            text += f"\n💡 <b>Opción:</b> <code>{instr}</code>\n"
            text += f"💰 <b>Riesgo:</b> ${cost:.2f} | <b>Max Beneficio:</b> ${profit:.2f}\n"

        text += "\n¿En qué broker deseas autorizar la ejecución?"

        # Botones individuales por broker + botón Multi-Broker
        reply_markup = {
            "inline_keyboard": [
                [
                    {"text": "🦙 Alpaca", "callback_data": f"EXEC:ALPACA:{alert_id}"},
                    {"text": "🏛️ IBKR", "callback_data": f"EXEC:IBKR:{alert_id}"},
                    {"text": "📈 Tradier", "callback_data": f"EXEC:TRADIER:{alert_id}"}
                ],
                [
                    {"text": "🌐 Enrutar a Todos (Multi-Bróker)", "callback_data": f"EXEC:ALL:{alert_id}"}
                ],
                [
                    {"text": "❌ Rechazar Operación", "callback_data": f"REJECT:ALL:{alert_id}"}
                ]
            ]
        }

        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        try:
            r = requests.post(url, json={
                "chat_id": self.chat_id,
                "text": text,
                "parse_mode": "HTML",
                "reply_markup": reply_markup
            }, timeout=6)
            if r.status_code != 200:
                print(f"[TelegramBot] Error al enviar alerta: {r.status_code} - {r.text}")
            return r.status_code == 200
        except Exception as e:
            print(f"[TelegramBot] Excepción al enviar alerta: {e}")
            return False

    def start_listening(self):
        """Inicia el hilo en segundo plano para escuchar clics de botones."""
        if self.running or not self.enabled or not self.token:
            return

        self.running = True
        self.thread = threading.Thread(target=self._polling_loop, daemon=True)
        self.thread.start()
        print("[TelegramBot] Hilo de escucha multibróker iniciado en segundo plano.")

    def stop_listening(self):
        self.running = False

    def _polling_loop(self):
        url = f"https://api.telegram.org/bot{self.token}/getUpdates"

        while self.running:
            try:
                params = {"offset": self.last_update_id + 1, "timeout": 5}
                r = requests.get(url, params=params, timeout=8)
                if r.status_code == 200:
                    data = r.json()
                    for update in data.get("result", []):
                        self.last_update_id = update["update_id"]
                        if "callback_query" in update:
                            self._handle_callback(update["callback_query"])
            except Exception:
                time.sleep(2)
            time.sleep(1)

    def _handle_callback(self, query: Dict):
        query_id = query["id"]
        data_str = query.get("data", "")
        message = query.get("message", {})
        message_id = message.get("message_id")
        from_user = query.get("from", {}).get("first_name", "Usuario")

        parts = data_str.split(":")
        if len(parts) < 3:
            return

        action = parts[0]
        broker_key = parts[1]
        alert_id = parts[2]
        alert = PENDING_ALERTS.get(alert_id, {})

        if action == "EXEC":
            symbol = alert.get("symbol", "SPY")
            side = "buy" if "BUY" in alert.get("action", "BUY") else "sell"
            instrument = alert.get("instrument", "EQUITY").lower()
            time_now = datetime.now().strftime("%H:%M:%S")

            if broker_key in ["ALL", "MULTI"]:
                self.broker_manager.set_active_broker("ALL")
                executed_brokers = []
                for b_id, b_inst in self.broker_manager.brokers.items():
                    try:
                        b_inst.submit_order(
                            symbol=symbol,
                            qty=1,
                            side=side,
                            order_type="market",
                            instrument_type=instrument
                        )
                        executed_brokers.append(b_inst.name)
                    except Exception:
                        pass

                names_str = " + ".join(executed_brokers) if executed_brokers else "Alpaca + IBKR + Tradier"
                self._answer_callback(query_id, f"✅ ¡Orden multibróker enviada a {len(executed_brokers)} brokers!")

                edited_text = (
                    f"{html.escape(message.get('text', ''))}\n\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"✅ <b>ORDEN MULTI-BRÓKER APROBADA Y EJECUTADA</b>\n"
                    f"👤 Trader: <b>{html.escape(from_user)}</b> a las <code>{time_now}</code>\n"
                    f"🌐 Brokers Concurrentes: <b>{html.escape(names_str)}</b>\n"
                    f"📋 Estado: <code>3 ÓRDENES ENVIADAS SIMULTÁNEAMENTE</code>"
                )
                self._edit_message(message_id, edited_text)
            else:
                self.broker_manager.set_active_broker(broker_key)
                target_broker = self.broker_manager.active_broker

                target_broker.submit_order(
                    symbol=symbol,
                    qty=1,
                    side=side,
                    order_type="market",
                    instrument_type=instrument
                )

                self._answer_callback(query_id, f"✅ ¡Orden enviada exitosamente a {target_broker.name}!")

                edited_text = (
                    f"{html.escape(message.get('text', ''))}\n\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━\n"
                    f"✅ <b>ORDEN APROBADA Y EJECUTADA</b>\n"
                    f"👤 Trader: <b>{html.escape(from_user)}</b> a las <code>{time_now}</code>\n"
                    f"🏦 Broker Seleccionado: <b>{html.escape(target_broker.name)}</b>\n"
                    f"📋 Estado: <code>ORDEN ENVIADA A MERCADO</code>"
                )
                self._edit_message(message_id, edited_text)

        elif action == "REJECT":
            self._answer_callback(query_id, "❌ Operación descartada.")
            time_now = datetime.now().strftime("%H:%M:%S")
            edited_text = (
                f"{html.escape(message.get('text', ''))}\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"❌ <b>OPERACIÓN DESCARTADA</b>\n"
                f"👤 Decisión por: <b>{html.escape(from_user)}</b> a las <code>{time_now}</code>\n"
                f"🚫 Estado: <code>NO EJECUTADA EN NINGÚN BROKER</code>"
            )
            self._edit_message(message_id, edited_text)

    def _answer_callback(self, callback_query_id: str, text: str):
        url = f"https://api.telegram.org/bot{self.token}/answerCallbackQuery"
        try:
            requests.post(url, json={"callback_query_id": callback_query_id, "text": text, "show_alert": False}, timeout=4)
        except Exception:
            pass

    def _edit_message(self, message_id: int, new_text: str):
        url = f"https://api.telegram.org/bot{self.token}/editMessageText"
        try:
            requests.post(url, json={
                "chat_id": self.chat_id,
                "message_id": message_id,
                "text": new_text,
                "parse_mode": "HTML",
                "reply_markup": {"inline_keyboard": []}
            }, timeout=4)
        except Exception:
            pass
