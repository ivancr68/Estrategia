"""
Estrategia de Opciones Financieras (Options Execution Engine):
Convierte señales técnicas de acciones/ETFs en contratos de opciones financieras de alta probabilidad:
1. Long Calls / Puts direccionales (DTE 21-45, Delta 0.50 - 0.65)
2. Vertical Spreads de Débito (Bull Call Spread / Bear Put Spread) con riesgo matemáticamente definido
"""

from typing import Dict, List, Optional
from core.options_engine import OptionsEngine


class OptionsStrategyAdapter:
    """
    Traduce señales del mercado al contado (ETFs) a estrategias óptimas con Opciones Financieras.
    """

    def __init__(self, risk_free_rate: float = 0.045, default_dte: int = 30, default_iv: float = 0.18):
        self.engine = OptionsEngine(risk_free_rate=risk_free_rate)
        self.default_dte = default_dte
        self.default_iv = default_iv

    def convert_signal_to_options(self, signal: Dict, prefer_spreads: bool = True) -> Dict:
        """
        Toma una señal de acción/ETF y genera la recomendación y parámetros de la opción financiera.
        """
        symbol = signal["symbol"]
        price = signal["entry_price"]
        action = signal["action"]
        is_bullish = "BUY" in action

        # Definir strikes redondeados según el precio del subyacente
        strike_step = 1.0 if price < 150 else (2.0 if price < 300 else 5.0)
        atm_strike = round(price / strike_step) * strike_step

        if is_bullish:
            # Estrategia Alcista
            if prefer_spreads:
                # Bull Call Spread: Comprar strike ATM/ITM y Vender strike OTM (ancho de 1 o 2 pasos)
                k_long = atm_strike
                k_short = atm_strike + strike_step
                spread_metrics = self.engine.evaluate_vertical_spread(
                    s=price,
                    k_long=k_long,
                    k_short=k_short,
                    dte=self.default_dte,
                    sigma=self.default_iv,
                    spread_type="BULL_CALL_SPREAD"
                )
                return {
                    **signal,
                    "action": "BUY_CALL_SPREAD",
                    "instrument": "OPTION",
                    "strategy_type": "BULL_CALL_SPREAD",
                    "details": {
                        "long_strike": k_long,
                        "short_strike": k_short,
                        "dte": self.default_dte,
                        "cost_per_contract": spread_metrics["max_risk_dollars"],
                        "max_profit": spread_metrics["max_profit_dollars"],
                        "risk_reward_ratio": spread_metrics["risk_reward_ratio"],
                        "net_delta": spread_metrics["net_delta"],
                        "instruction": f"Comprar Call {k_long} / Vender Call {k_short} ({self.default_dte} DTE)"
                    }
                }
            else:
                # Long Call directo
                bs = self.engine.black_scholes(s=price, k=atm_strike, t_years=self.default_dte/365.0, sigma=self.default_iv, option_type="CALL")
                return {
                    **signal,
                    "action": "BUY_CALL",
                    "instrument": "OPTION",
                    "strategy_type": "LONG_CALL",
                    "details": {
                        "strike": atm_strike,
                        "dte": self.default_dte,
                        "option_price": bs["price"],
                        "cost_per_contract": round(bs["price"] * 100, 2),
                        "delta": bs["delta"],
                        "theta_daily": bs["theta_daily"],
                        "instruction": f"Comprar Call ATM strike {atm_strike} ({self.default_dte} DTE, Delta {bs['delta']})"
                    }
                }
        else:
            # Estrategia Bajista
            if prefer_spreads:
                # Bear Put Spread
                k_long = atm_strike
                k_short = atm_strike - strike_step
                spread_metrics = self.engine.evaluate_vertical_spread(
                    s=price,
                    k_long=k_long,
                    k_short=k_short,
                    dte=self.default_dte,
                    sigma=self.default_iv,
                    spread_type="BEAR_PUT_SPREAD"
                )
                return {
                    **signal,
                    "action": "BUY_PUT_SPREAD",
                    "instrument": "OPTION",
                    "strategy_type": "BEAR_PUT_SPREAD",
                    "details": {
                        "long_strike": k_long,
                        "short_strike": k_short,
                        "dte": self.default_dte,
                        "cost_per_contract": spread_metrics["max_risk_dollars"],
                        "max_profit": spread_metrics["max_profit_dollars"],
                        "risk_reward_ratio": spread_metrics["risk_reward_ratio"],
                        "net_delta": spread_metrics["net_delta"],
                        "instruction": f"Comprar Put {k_long} / Vender Put {k_short} ({self.default_dte} DTE)"
                    }
                }
            else:
                # Long Put directo
                bs = self.engine.black_scholes(s=price, k=atm_strike, t_years=self.default_dte/365.0, sigma=self.default_iv, option_type="PUT")
                return {
                    **signal,
                    "action": "BUY_PUT",
                    "instrument": "OPTION",
                    "strategy_type": "LONG_PUT",
                    "details": {
                        "strike": atm_strike,
                        "dte": self.default_dte,
                        "option_price": bs["price"],
                        "cost_per_contract": round(bs["price"] * 100, 2),
                        "delta": bs["delta"],
                        "theta_daily": bs["theta_daily"],
                        "instruction": f"Comprar Put ATM strike {atm_strike} ({self.default_dte} DTE, Delta {bs['delta']})"
                    }
                }
