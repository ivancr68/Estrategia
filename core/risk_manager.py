"""
Gestor de Riesgo Institucional y Control de Fricciones:
- Cálculo de tamaño dinámico de posición (Acciones y Opciones)
- Kill-Switch diario (2.0% Drawdown)
- Evaluación de Esperanza Matemática y Profit Factor
- Modelo de fricciones: Deslizamiento (Slippage) y Comisiones
"""

import math
from typing import Dict, List, Optional, Tuple
import pandas as pd


class RiskManager:
    """
    Controlador de riesgo cuantitativo para la cartera NYSE.
    """

    def __init__(
        self,
        capital: float = 25000.0,
        risk_per_trade_pct: float = 0.01,
        max_daily_drawdown_pct: float = 0.02,
        commission_per_option: float = 0.65,
        commission_per_share: float = 0.005,
        default_slippage_points: float = 0.03
    ):
        self.initial_capital = capital
        self.current_capital = capital
        self.risk_per_trade_pct = risk_per_trade_pct
        self.max_daily_drawdown_pct = max_daily_drawdown_pct
        self.commission_per_option = commission_per_option
        self.commission_per_share = commission_per_share
        self.default_slippage_points = default_slippage_points

        self.daily_pnl = 0.0
        self.kill_switch_triggered = False

    def calculate_equity_position_size(self, entry_price: float, stop_loss_price: float) -> int:
        """
        Calcula el número de acciones a comprar para arriesgar exactamente el 1.0% del capital.
        """
        if self.kill_switch_triggered:
            return 0

        risk_dollars = self.current_capital * self.risk_per_trade_pct
        risk_per_share = abs(entry_price - stop_loss_price)

        if risk_per_share <= 0:
            return 0

        shares = math.floor(risk_dollars / risk_per_share)
        # Límite de apalancamiento: nunca superar el poder de compra disponible (ej. 2x)
        max_shares_capital = math.floor((self.current_capital * 2.0) / entry_price)
        return min(shares, max_shares_capital)

    def calculate_option_contracts(self, cost_per_contract: float) -> int:
        """
        Calcula el número de contratos de opciones a comprar según el riesgo permitido.
        """
        if self.kill_switch_triggered or cost_per_contract <= 0:
            return 0

        risk_dollars = self.current_capital * self.risk_per_trade_pct
        contracts = math.floor(risk_dollars / cost_per_contract)
        return max(1, min(contracts, 10))

    def check_daily_drawdown(self, new_pnl: float) -> bool:
        """
        Actualiza el P&L diario y activa el Kill-Switch si se supera el 2.0% de pérdida.
        """
        self.daily_pnl += new_pnl
        self.current_capital += new_pnl

        max_allowed_loss = -(self.initial_capital * self.max_daily_drawdown_pct)
        if self.daily_pnl <= max_allowed_loss:
            self.kill_switch_triggered = True
            return True
        return False

    def reset_daily_metrics(self):
        """Reinicia el monitor diario al inicio de una nueva sesión de NYSE."""
        self.daily_pnl = 0.0
        self.kill_switch_triggered = False

    @staticmethod
    def calculate_mathematical_expectancy(trades_pnl: List[float]) -> Dict[str, float]:
        """
        Calcula la fórmula de la Esperanza Matemática:
        E = (Win_Rate * Avg_Win) - (Loss_Rate * Avg_Loss)
        """
        if not trades_pnl:
            return {"expectancy": 0.0, "profit_factor": 0.0, "win_rate": 0.0}

        wins = [p for p in trades_pnl if p > 0]
        losses = [abs(p) for p in trades_pnl if p < 0]

        total_trades = len(trades_pnl)
        win_rate = len(wins) / total_trades if total_trades > 0 else 0.0
        loss_rate = len(losses) / total_trades if total_trades > 0 else 0.0

        avg_win = sum(wins) / len(wins) if wins else 0.0
        avg_loss = sum(losses) / len(losses) if losses else 0.0

        expectancy = (win_rate * avg_win) - (loss_rate * avg_loss)
        gross_profit = sum(wins)
        gross_loss = sum(losses)
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else 99.0

        return {
            "expectancy": round(expectancy, 2),
            "win_rate_pct": round(win_rate * 100, 1),
            "loss_rate_pct": round(loss_rate * 100, 1),
            "avg_win": round(avg_win, 2),
            "avg_loss": round(avg_loss, 2),
            "profit_factor": round(profit_factor, 2),
            "total_trades": total_trades
        }
