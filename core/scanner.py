"""
Servicio Demonio de Escaneo de Mercado en Vivo (Live Market Scanner Daemon):
Monitorea continuamente los ETFs de NYSE en tiempo real durante la sesión de mercado.
En cada ciclo, detecta nuevas señales de alta convicción (Score >= 80%) y las despacha
automáticamente a Telegram con botones interactivos para cada broker.
"""

import time
import threading
from datetime import datetime, timezone, time as dt_time
from typing import Dict, Set
import pandas as pd
import config
from core.market_data import MarketDataProvider
from strategies.multi_strategy_engine import MultiStrategyEngine
from core.notifier import dispatcher


class LiveMarketScanner:
    """
    Escáner automático en segundo plano que corre en bucle continuo durante la sesión de NYSE.
    """

    def __init__(self, check_interval_seconds: int = 60):
        self.interval = check_interval_seconds
        self.provider = MarketDataProvider()
        self.engine = MultiStrategyEngine(symbols=config.ETFS_PRINCIPALES)
        self.dispatched_keys: Set[str] = set()
        self.is_running = False
        self._thread = None

    def start(self):
        """Inicia el hilo en segundo plano."""
        if self.is_running:
            return
        self.is_running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="LiveMarketScannerThread")
        self._thread.start()
        print("[LiveScanner] Motor de escaneo automatico en vivo iniciado (chequeo cada 60s)")

    def stop(self):
        self.is_running = False

    def is_market_hours(self) -> bool:
        """Verifica si la Bolsa de Nueva York está abierta (Lunes a Viernes 09:30 - 16:00 EST)."""
        now_utc = datetime.now(timezone.utc)
        if now_utc.weekday() >= 5:  # Fin de semana
            return False
        # 09:30 a 16:00 EST = 13:30 a 20:00 UTC (o 14:30 a 21:00 UTC en horario de invierno)
        t = now_utc.time()
        return dt_time(13, 0) <= t <= dt_time(20, 30)

    def scan_once(self):
        """Ejecuta una pasada de escaneo sobre los 4 ETFs principales."""
        try:
            market_data = {sym: self.provider.get_historical_bars(sym, days=2, interval_mins=5) for sym in config.ETFS_PRINCIPALES}
            signals = self.engine.scan_market(market_data, mode="HYBRID", trigger_alerts=False)

            now_utc = datetime.now(timezone.utc)
            min_score = getattr(config, "MIN_CONFLUENCE_SCORE", 80)

            for sig in signals:
                score = sig.get("confluence_score", 0)
                if score < min_score:
                    continue

                sig_time = pd.to_datetime(sig["time"])
                if sig_time.tzinfo is None:
                    sig_time = sig_time.replace(tzinfo=timezone.utc)

                # Si la señal ocurrió en los últimos 20 minutos (vela reciente)
                age_minutes = (now_utc - sig_time).total_seconds() / 60.0
                if 0 <= age_minutes <= 25:
                    key = f"{sig['symbol']}_{sig['action']}_{sig_time.strftime('%Y%m%d%H%M')}"
                    if key not in self.dispatched_keys:
                        self.dispatched_keys.add(key)
                        print(f"[LiveScanner] NUEVA SENAL ALTA CONVICCION ({sig['symbol']} {sig['action']} {score}%) -> Despachando a Telegram...")
                        dispatcher.dispatch_alert(sig)
        except Exception as e:
            print(f"[LiveScanner] Excepcion en ciclo de escaneo: {e}")

    def _run_loop(self):
        while self.is_running:
            self.scan_once()
            time.sleep(self.interval)
