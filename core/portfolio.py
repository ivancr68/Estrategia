"""
Gestor de Portafolio Multiactivo (5 Métodos de Asignación de Capital - Video 18):
1. Equal Weight (Equitativo)
2. Volatility Parity / Inverse Volatility (Paridad de Riesgo)
3. Fixed Fractional (Fraccional Fijo)
4. Half-Kelly Criterion (Criterio Kelly Prudencial)
5. Momentum Weighted (Ponderado por Fuerza Relativa)
"""

from typing import Dict, List
import numpy as np
import pandas as pd


class PortfolioAllocator:
    """
    Motor de asignación y balanceo de capital para los principales ETFs (SPY, QQQ, IWM, DIA).
    """

    def __init__(self, symbols: List[str] = None):
        self.symbols = symbols or ["SPY", "QQQ", "IWM", "DIA"]

    def allocate(
        self,
        method: str,
        total_capital: float,
        volatilities: Dict[str, float] = None,
        win_rates: Dict[str, float] = None,
        rr_ratios: Dict[str, float] = None,
        momentum_scores: Dict[str, float] = None
    ) -> Dict[str, float]:
        """
        Calcula la asignación de dólares a cada ETF según el método seleccionado.
        """
        n = len(self.symbols)
        if n == 0 or total_capital <= 0:
            return {}

        method = method.upper()

        # 1. EQUAL WEIGHT (Equitativo)
        if method == "EQUAL_WEIGHT":
            weight = 1.0 / n
            return {sym: round(total_capital * weight, 2) for sym in self.symbols}

        # 2. INVERSE VOLATILITY (Paridad de Riesgo)
        elif method == "VOLATILITY_PARITY":
            vols = volatilities or {sym: 1.0 for sym in self.symbols}
            inv_vols = {sym: (1.0 / max(0.001, vols.get(sym, 1.0))) for sym in self.symbols}
            sum_inv = sum(inv_vols.values())
            weights = {sym: inv_vols[sym] / sum_inv for sym in self.symbols}
            return {sym: round(total_capital * weights[sym], 2) for sym in self.symbols}

        # 3. HALF-KELLY CRITERION
        elif method == "KELLY":
            weights = {}
            for sym in self.symbols:
                w = win_rates.get(sym, 0.45) if win_rates else 0.45
                r = rr_ratios.get(sym, 2.0) if rr_ratios else 2.0
                # Formula Kelly: K = W - (1-W)/R
                kelly = w - ((1.0 - w) / r)
                # Usar Half-Kelly por prudencia institucional
                safe_kelly = max(0.05, min(0.30, (kelly * 0.5)))
                weights[sym] = safe_kelly

            sum_w = sum(weights.values())
            norm_weights = {sym: weights[sym] / sum_w for sym in self.symbols}
            return {sym: round(total_capital * norm_weights[sym], 2) for sym in self.symbols}

        # 4. MOMENTUM WEIGHTED
        elif method == "MOMENTUM_WEIGHTED":
            scores = momentum_scores or {sym: 50.0 for sym in self.symbols}
            min_score = min(scores.values())
            shifted_scores = {sym: max(1.0, scores.get(sym, 50.0) - min_score + 10.0) for sym in self.symbols}
            sum_scores = sum(shifted_scores.values())
            weights = {sym: shifted_scores[sym] / sum_scores for sym in self.symbols}
            return {sym: round(total_capital * weights[sym], 2) for sym in self.symbols}

        # 5. FIXED FRACTIONAL POR DEFECTO
        else:
            weight = 1.0 / n
            return {sym: round(total_capital * weight, 2) for sym in self.symbols}
