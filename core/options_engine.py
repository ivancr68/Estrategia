"""
Motor de Valoración y Gestión de Opciones Financieras (Black-Scholes & Griegas)
Calcula precios teóricos, Delta, Gamma, Theta, Vega y estructuras de spreads para ETFs (SPY, QQQ, etc.).
"""

import math
from typing import Dict, Literal, Optional
import numpy as np


def normal_cdf(x: float) -> float:
    """Función de distribución acumulada de la normal estándar (precisión analítica)."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def normal_pdf(x: float) -> float:
    """Función de densidad de probabilidad de la normal estándar."""
    return (1.0 / math.sqrt(2.0 * math.pi)) * math.exp(-0.5 * x * x)


class OptionsEngine:
    """
    Calculadora cuantitativa de Opciones Financieras basada en Black-Scholes-Merton.
    """

    def __init__(self, risk_free_rate: float = 0.045):
        self.r = risk_free_rate

    def black_scholes(
        self,
        s: float,          # Precio del subyacente (ej. SPY a $570)
        k: float,          # Strike / Precio de ejercicio
        t_years: float,    # Tiempo hasta expiración en años (DTE / 365.0)
        sigma: float,      # Volatilidad implícita (ej. 0.18 para 18%)
        option_type: Literal["CALL", "PUT"] = "CALL"
    ) -> Dict[str, float]:
        """
        Calcula precio teórico y las 4 griegas clave (Delta, Gamma, Theta, Vega).
        """
        if t_years <= 0 or sigma <= 0 or s <= 0 or k <= 0:
            # Vencimiento o parámetros inválidos
            intrinsic = max(0.0, (s - k) if option_type == "CALL" else (k - s))
            return {
                "price": intrinsic,
                "delta": 1.0 if (option_type == "CALL" and s > k) else (-1.0 if (option_type == "PUT" and k > s) else 0.0),
                "gamma": 0.0,
                "theta": 0.0,
                "vega": 0.0
            }

        sqrt_t = math.sqrt(t_years)
        d1 = (math.log(s / k) + (self.r + 0.5 * sigma * sigma) * t_years) / (sigma * sqrt_t)
        d2 = d1 - sigma * sqrt_t

        nd1 = normal_cdf(d1)
        nd2 = normal_cdf(d2)
        n_neg_d1 = normal_cdf(-d1)
        n_neg_d2 = normal_cdf(-d2)
        pdf_d1 = normal_pdf(d1)

        discount = math.exp(-self.r * t_years)

        # Precios teóricos
        if option_type == "CALL":
            price = s * nd1 - k * discount * nd2
            delta = nd1
            theta_annual = -(s * pdf_d1 * sigma) / (2.0 * sqrt_t) - self.r * k * discount * nd2
        else:
            price = k * discount * n_neg_d2 - s * n_neg_d1
            delta = nd1 - 1.0  # o -n_neg_d1
            theta_annual = -(s * pdf_d1 * sigma) / (2.0 * sqrt_t) + self.r * k * discount * n_neg_d2

        gamma = pdf_d1 / (s * sigma * sqrt_t)
        vega = s * sqrt_t * pdf_d1 * 0.01  # Sensibilidad ante cambio de 1% en volatilidad
        theta_daily = theta_annual / 365.0  # Pérdida de valor por el paso de un día

        return {
            "price": round(max(0.0, price), 2),
            "delta": round(delta, 4),
            "gamma": round(gamma, 5),
            "theta_daily": round(theta_daily, 4),
            "vega": round(vega, 4),
            "d1": round(d1, 4),
            "d2": round(d2, 4)
        }

    def evaluate_vertical_spread(
        self,
        s: float,
        k_long: float,
        k_short: float,
        dte: int,
        sigma: float,
        spread_type: Literal["BULL_CALL_SPREAD", "BEAR_PUT_SPREAD"]
    ) -> Dict[str, float]:
        """
        Calcula el coste neto, beneficio máximo y ratios de un Spread Vertical.
        """
        t = dte / 365.0
        if spread_type == "BULL_CALL_SPREAD":
            leg_long = self.black_scholes(s, k_long, t, sigma, "CALL")
            leg_short = self.black_scholes(s, k_short, t, sigma, "CALL")
            net_debit = leg_long["price"] - leg_short["price"]
            max_profit = (k_short - k_long) - net_debit
            net_delta = leg_long["delta"] - leg_short["delta"]
        else:  # BEAR_PUT_SPREAD
            leg_long = self.black_scholes(s, k_long, t, sigma, "PUT")
            leg_short = self.black_scholes(s, k_short, t, sigma, "PUT")
            net_debit = leg_long["price"] - leg_short["price"]
            max_profit = (k_long - k_short) - net_debit
            net_delta = leg_long["delta"] - leg_short["delta"]

        max_risk = max(0.01, net_debit)
        risk_reward_ratio = max_profit / max_risk if max_risk > 0 else 0.0

        return {
            "spread_type": spread_type,
            "net_debit_cost": round(net_debit, 2),
            "max_risk_dollars": round(net_debit * 100, 2),     # 1 contrato = 100 acciones
            "max_profit_dollars": round(max_profit * 100, 2),
            "risk_reward_ratio": round(risk_reward_ratio, 2),
            "net_delta": round(net_delta, 4)
        }
