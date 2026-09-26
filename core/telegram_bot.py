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

        action_emoji = "🟢 COMPRA" if "BUY" in alert["action"] else "🔴 VENTA"
        text = (
            f"🏛️ *NUEVA OPORTUNIDAD CUANTITATIVA (NYSE)*\n\n"
            f"📌 *Símbolo:* `{alert['symbol']}`\n"
            f"⚡ *Acción:* {action_emoji} ({alert.get('instrument', 'EQUITY')})\n"
            f"🎯 *Estrategia:* {alert.get('strategy', 'Multi-Strategy')}\n"
            f"⭐ *Convicción Institucional:* `{alert.get('confluence_score', 85)}%`\n\n"
            f"💵 *Precio Entrada:* `${alert['entry_price']}`\n"
            f"🛑 *Stop Loss:* `${alert['stop_loss']}`\n"
            f"🎯 *Take Profit:* `${alert['take_profit']}`\n"
            f"📊 *Motivo:* _{alert.get('rationale', 'Alta confluencia de filtros')}_\n"
        )

        opt = alert.get("option_details") or alert.get("details")
        if opt:
            text += f"\n💡 *Opción:* `{opt.get('instruction', 'N/A')}`\n"
            text += f"💰 *Riesgo:* `${opt.get('cost_per_contract', 0)}` | *Max Beneficio:* `${opt.get('max_profit', 0)}`\n"

        text += "\n¿En qué broker deseas autorizar la ejecución?"

        # Botones individuales por broker
        reply_markup = {
            "inline_keyboard": [
                [
                    {"text": "🦙 Alpaca", "callback_data": f"EXEC:ALPACA:{alert_id}"},
                    {"text": "🏛️ IBKR", "callback_data": f"EXEC:IBKR:{alert_id}"},
                    {"text": "📈 Tradier", "callback_data": f"EXEC:TRADIER:{alert_id}"}
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
                "parse_mode": "Markdown",
                "reply_markup": reply_markup
            }, timeout=6)
            return r.status_code == 200
        except Exception:
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
            # 1. Seleccionar el broker solicitado
            self.broker_manager.set_active_broker(broker_key)
            target_broker = self.broker_manager.active_broker

            symbol = alert.get("symbol", "SPY")
            side = "buy" if "BUY" in alert.get("action", "BUY") else "sell"
            instrument = alert.get("instrument", "EQUITY").lower()

            # Enviar orden
            order_res = target_broker.submit_order(
                symbol=symbol,
                qty=1,
                side=side,
                order_type="market",
                instrument_type=instrument
            )

            # 2. Responder al callback
            self._answer_callback(query_id, f"✅ ¡Orden enviada exitosamente a {target_broker.name}!")

            # 3. Editar mensaje
            time_now = datetime.now().strftime("%H:%M:%S")
            edited_text = (
                f"{message.get('text', '')}\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"✅ *ORDEN APROBADA Y EJECUTADA*\n"
                f"👤 Trader: *{from_user}* a las `{time_now}`\n"
                f"🏦 Broker Seleccionado: *{target_broker.name}*\n"
                f"📋 Estado: `ORDEN ENVIADA A MERCADO`"
            )
            self._edit_message(message_id, edited_text)

        elif action == "REJECT":
            self._answer_callback(query_id, "❌ Operación descartada.")
            time_now = datetime.now().strftime("%H:%M:%S")
            edited_text = (
                f"{message.get('text', '')}\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━━\n"
                f"❌ *OPERACIÓN DESCARTADA*\n"
                f"👤 Decisión por: *{from_user}* a las `{time_now}`\n"
                f"🚫 Estado: `NO EJECUTADA EN NINGÚN BROKER`"
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
                "parse_mode": "Markdown",
                "reply_markup": {"inline_keyboard": []}
            }, timeout=4)
        except Exception:
            pass
