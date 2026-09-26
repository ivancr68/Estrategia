"""
Motor Orquestador Multi-Estrategia Integral para NYSE:
Coordina el escaneo simultáneo de las 4 estrategias técnicas principales,
calcula la Puntuación de Convicción Profesional (0-100%) y despacha alertas automáticas.
"""

from typing import Dict, List
import pandas as pd
from strategies.trend_following import TrendFollowingStrategy
from strategies.mean_reversion import MeanReversionStrategy
from strategies.orb_breakout import OpeningRangeBreakoutStrategy
from strategies.pullback_rejection import PullbackRejectionStrategy
from strategies.options_strategy import OptionsStrategyAdapter
from strategies.confluence_scorer import ConfluenceScorer
from indicators.trend import add_moving_averages
from indicators.momentum import add_macd, add_rsi
from indicators.volatility import add_atr, add_bollinger_bands
from indicators.time_filters import add_nyse_session_filters
from core.notifier import dispatcher


class MultiStrategyEngine:
    """
    Motor central que unifica el catálogo completo de estrategias cuantitativas para Wall Street.
    """

    def __init__(self, symbols: List[str] = None):
        self.symbols = symbols or ["SPY", "QQQ", "IWM", "DIA"]
        self.trend_strategy = TrendFollowingStrategy(symbols=["SPY", "QQQ"])
        self.mean_rev_strategy = MeanReversionStrategy(symbols=["IWM", "DIA"])
        self.orb_strategy = OpeningRangeBreakoutStrategy(symbols=["SPY", "QQQ"])
        self.pullback_strategy = PullbackRejectionStrategy(symbols=["SPY", "QQQ", "DIA"])
        self.options_adapter = OptionsStrategyAdapter(default_dte=30, default_iv=0.18)

    def scan_market(self, df_dict: Dict[str, pd.DataFrame], mode: str = "HYBRID", trigger_alerts: bool = True) -> List[Dict]:
        """
        Escanea el mercado ejecutando todas las estrategias y califica su confluencia.
        """
        # 0. Enriquecer los dataframes con todos los indicadores institucionales
        enriched_dict = {}
        for sym, df in df_dict.items():
            if df is not None and not df.empty:
                data = add_moving_averages(df)
                data = add_macd(data)
                data = add_rsi(data)
                data = add_atr(data)
                data = add_bollinger_bands(data)
                data = add_nyse_session_filters(data)
                enriched_dict[sym] = data
            else:
                enriched_dict[sym] = df
        df_dict = enriched_dict

        raw_signals = []

        # 1. Ejecutar las 4 estrategias en paralelo
        raw_signals.extend(self.trend_strategy.generate_signals(df_dict))
        raw_signals.extend(self.mean_rev_strategy.generate_signals(df_dict))
        raw_signals.extend(self.orb_strategy.generate_signals(df_dict))
        raw_signals.extend(self.pullback_strategy.generate_signals(df_dict))

        # 2. Puntuación de Convicción Profesional y deduplicación
        scored_signals = []
        seen = set()

        for sig in raw_signals:
            key = f"{sig['symbol']}_{sig['time']}_{sig['action']}"
            if key in seen:
                continue
            seen.add(key)

            df = df_dict.get(sig["symbol"], pd.DataFrame())
            score = ConfluenceScorer.score_signal(sig, df)
            sig["confluence_score"] = score
            sig["is_high_conviction"] = (score >= 80)
            scored_signals.append(sig)

        # Ordenar por puntuación de convicción descendente
        scored_signals = sorted(scored_signals, key=lambda x: x["confluence_score"], reverse=True)

        # 3. Procesar y traducir a opciones
        final_signals = []
        for sig in scored_signals:
            if mode in ["EQUITY_ONLY", "HYBRID"]:
                final_signals.append(sig)
                if trigger_alerts and sig.get("is_high_conviction", False):
                    dispatcher.dispatch_alert(sig)

            if mode in ["OPTIONS_ONLY", "HYBRID"]:
                opt_sig = self.options_adapter.convert_signal_to_options(sig, prefer_spreads=True)
                final_signals.append(opt_sig)

        return final_signals
