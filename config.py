"""
Configuración del Sistema de Trading Algorítmico para NYSE / NASDAQ
Soporte para Acciones, ETFs Principales, Opciones Financieras y Sistema de Alertas.
"""

import os
from datetime import time
from pathlib import Path
from dotenv import load_dotenv

# --- RUTAS ---
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

# --- MERCADOS Y ACTIVOS PRINCIPALES ---
ETFS_PRINCIPALES = [
    "SPY",   # S&P 500 (Índice de referencia global y alta liquidez en opciones)
    "QQQ",   # Nasdaq 100 (Tecnología y alto crecimiento / volatilidad)
    "IWM",   # Russell 2000 (Small Caps y sensibilidad a tipos de interés)
    "DIA",   # Dow Jones Industrial Average (Blue chips industriales)
]

ETFS_SECTORIALES = [
    "XLK", "XLF", "XLE", "XLV", "XLI", "XLY", "XLP"
]

WATCHLIST = ETFS_PRINCIPALES

# --- HORARIOS DE LA BOLSA DE NUEVA YORK (NYSE / NASDAQ - Eastern Time / EST) ---
HORA_APERTURA_REGULAR = time(9, 30)   # 09:30 AM EST
HORA_CIERRE_REGULAR = time(16, 0)     # 04:00 PM EST

# --- GESTIÓN DE RIESGO INSTITUCIONAL ---
CAPITAL_INICIAL = 25000.0            # Balance base (cumple con regla PDT de FINRA)
RIESGO_MAXIMO_POR_OPERACION_PCT = 0.01  # 1.0% de riesgo por trade
MAX_POSICIONES_SIMULTANEAS = 4
MAX_DRAWDOWN_DIARIO_PCT = 0.02       # Kill-switch si cae 2.0% en el día
RATIO_RIESGO_BENEFICIO_MIN = 2.0     # 1:2 mínimo

# --- SISTEMA DE ALERTAS Y BOT DE TELEGRAM DEDICADO (@IvanAlgoQuantBot) ---
MIN_CONFLUENCE_SCORE = 80            # Umbral mínimo (0-100%) para calificar como "Alta Convicción" y emitir alerta
TELEGRAM_ENABLED = True              # Alertas push automáticas activadas
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "TU_TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "TU_TELEGRAM_CHAT_ID")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")                     # URL opcional para n8n, Discord o Slack

# --- CONFIGURACIÓN DE OPCIONES FINANCIERAS ---
OPCIONES_CONFIG = {
    "DTE_MIN": 7,
    "DTE_MAX": 45,
    "DELTA_TARGET_BUY": 0.50,
    "DELTA_TARGET_SPREAD": 0.30,
    "TASA_LIBRE_RIESGO": 0.045
}

# --- BROKERS REGULADOS EE.UU. (SEC / FINRA / SIPC) ---
ALPACA_API_KEY = os.getenv("ALPACA_API_KEY", "TU_ALPACA_API_KEY")
ALPACA_SECRET_KEY = os.getenv("ALPACA_SECRET_KEY", "TU_ALPACA_SECRET_KEY")
ALPACA_PAPER_MODE = os.getenv("ALPACA_PAPER_MODE", "True").lower() == "true"

IBKR_GATEWAY_URL = os.getenv("IBKR_GATEWAY_URL", "https://localhost:5000/v1/api")
IBKR_ACCOUNT_ID = os.getenv("IBKR_ACCOUNT_ID", "DU1234567")
IBKR_PAPER_MODE = os.getenv("IBKR_PAPER_MODE", "True").lower() == "true"

TRADIER_ACCESS_TOKEN = os.getenv("TRADIER_ACCESS_TOKEN", "DEMO_TRADIER_TOKEN")
TRADIER_ACCOUNT_ID = os.getenv("TRADIER_ACCOUNT_ID", "VA12345678")
TRADIER_PAPER_MODE = os.getenv("TRADIER_PAPER_MODE", "True").lower() == "true"

