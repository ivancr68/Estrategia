"""
Módulo de Alertas Profesionales Multicanal:
- Notificaciones Push a Telegram con Botones Interactivos [Aceptar / Rechazar]
- Notificaciones Web en Tiempo Real (Audio Chime + Toast en el Dashboard)
- Webhooks configurables (n8n / Discord / Slack)
- Registro histórico persistente en archivo JSON
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional
import requests
import config
from core.telegram_bot import TelegramBotService

ALERTS_LOG_FILE = Path("alerts_history.json")


class AlertDispatcher:
    """
    Despachador central de alertas institucionales con soporte para botones interactivos de ejecución.
    """

    def __init__(self):
        self.telegram_enabled = getattr(config, "TELEGRAM_ENABLED", True)
        self.webhook_url = getattr(config, "WEBHOOK_URL", "")
        self.telegram_bot = TelegramBotService()
        self.recent_alerts: List[Dict] = self._load_recent_alerts()

    def dispatch_alert(self, signal: Dict) -> bool:
        """
        Envía la alerta por todos los canales activos con botones de decisión si supera el umbral.
        """
        score = signal.get("confluence_score", 85)
        min_score = getattr(config, "MIN_CONFLUENCE_SCORE", 80)

        if score < min_score:
            return False

        alert_item = {
            "id": f"ALT-{int(datetime.now().timestamp())}-{signal['symbol']}",
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
            "symbol": signal["symbol"],
            "strategy": signal.get("strategy", "Estrategia Cuantitativa"),
            "action": signal["action"],
            "instrument": signal.get("instrument", "EQUITY"),
            "entry_price": signal["entry_price"],
            "stop_loss": signal["stop_loss"],
            "take_profit": signal["take_profit"],
            "confluence_score": score,
            "rationale": signal.get("rationale", "Confluencia de filtros institucionales"),
            "option_details": signal.get("details", {})
        }

        # Guardar en memoria y persistir
        self.recent_alerts.insert(0, alert_item)
        self.recent_alerts = self.recent_alerts[:50]
        self._save_alerts()

        # 1. Enviar a Telegram con Botones Interactivos [Aceptar] / [Rechazar]
        if self.telegram_enabled:
            self.telegram_bot.send_interactive_alert(alert_item)

        # 2. Enviar a Webhook si aplica
        if self.webhook_url:
            self._send_webhook(alert_item)

        return True

    def _send_webhook(self, alert: Dict) -> bool:
        try:
            r = requests.post(self.webhook_url, json=alert, timeout=4)
            return r.status_code in [200, 201, 204]
        except Exception:
            return False

    def _load_recent_alerts(self) -> List[Dict]:
        if ALERTS_LOG_FILE.exists():
            try:
                with open(ALERTS_LOG_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return []

    def _save_alerts(self):
        try:
            with open(ALERTS_LOG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.recent_alerts, f, ensure_ascii=False, indent=2)
        except Exception:
            pass


# Instancia compartida
dispatcher = AlertDispatcher()
