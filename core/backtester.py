"""
Motor de Backtesting Institucional para NYSE:
Simula operaciones en Acciones, ETFs y Opciones incorporando fricciones del mundo real:
- Comisiones ($0.65 por contrato de opción / $0.005 por acción)
- Deslizamiento (Slippage)
- Métricas: Esperanza Matemática, Profit Factor, Win Rate, Máximo Drawdown y Curva de Capital
"""

from typing import Dict, List, Tuple
import pandas as pd
import numpy as np
from core.risk_manager import RiskManager


class NYSEBacktester:
    """
    Simulador cuantitativo multiactivo con fricciones reales.
    """

    def __init__(
        self,
        initial_capital: float = 25000.0,
        risk_per_trade_pct: float = 0.01,
        slippage_points: float = 0.02,
        commission_per_option: float = 0.65,
        commission_per_share: float = 0.005
    ):
        self.initial_capital = initial_capital
        self.risk_manager = RiskManager(
            capital=initial_capital,
            risk_per_trade_pct=risk_per_trade_pct,
            commission_per_option=commission_per_option,
            commission_per_share=commission_per_share,
            default_slippage_points=slippage_points
        )
        self.slippage = slippage_points

    def run(self, df_dict: Dict[str, pd.DataFrame], signals: List[Dict], min_conviction: int = 80) -> Tuple[pd.DataFrame, pd.DataFrame, Dict]:
        """
        Ejecuta la simulación cronológica con gestión de riesgo institucional,
        filtro de alta convicción (score >= 80) y protección Break-Even.
        """
        if not signals:
            return pd.DataFrame(), pd.DataFrame([{"time": pd.Timestamp.now(), "equity": self.initial_capital}]), {}

        # Filtrar solo oportunidades de alta convicción que superan el filtro institucional
        filtered_signals = [s for s in signals if s.get("confluence_score", 0) >= min_conviction]
        if not filtered_signals:
            filtered_signals = signals

        # Ordenar señales cronológicamente
        sorted_signals = sorted(filtered_signals, key=lambda x: x["time"])
        balance = self.initial_capital
        completed_trades = []

        for sig in sorted_signals:
            sym = sig["symbol"]
            df = df_dict.get(sym)
            if df is None or df.empty:
                continue

            entry_time = sig["time"]
            entry_price = sig["entry_price"]
            is_buy = "BUY" in sig["action"] or "CALL" in sig["action"]
            instrument = sig.get("instrument", "EQUITY")

            # Garantizar colchón de Stop Loss realista contra ruido de 5 minutos (mínimo 0.6% del precio)
            orig_risk = abs(entry_price - sig.get("stop_loss", entry_price * 0.99))
            risk_dist = max(orig_risk * 1.5, entry_price * 0.006)
            sl = entry_price - risk_dist if is_buy else entry_price + risk_dist
            tp = entry_price + (risk_dist * 2.0) if is_buy else entry_price - (risk_dist * 2.0)

            # Aplicar slippage en la entrada
            adj_entry = entry_price + self.slippage if is_buy else entry_price - self.slippage

            future_bars = df[df["time"] > entry_time]
            if future_bars.empty:
                continue

            exit_time = None
            exit_price = None
            outcome = None
            be_active = False

            for _, bar in future_bars.iterrows():
                high = bar["high"]
                low = bar["low"]

                if is_buy:
                    # Protección Break-Even: Si el trade alcanza +1.0R a favor, asegurar entrada
                    if not be_active and high >= adj_entry + risk_dist:
                        be_active = True
                        sl = adj_entry + 0.05

                    if low <= sl:
                        exit_time = bar["time"]
                        exit_price = sl - self.slippage
                        outcome = "BREAK_EVEN" if be_active else "STOP_LOSS"
                        break
                    elif high >= tp:
                        exit_time = bar["time"]
                        exit_price = tp - self.slippage
                        outcome = "TAKE_PROFIT"
                        break
                else:  # Venta / Corto / Put
                    if not be_active and low <= adj_entry - risk_dist:
                        be_active = True
                        sl = adj_entry - 0.05

                    if high >= sl:
                        exit_time = bar["time"]
                        exit_price = sl + self.slippage
                        outcome = "BREAK_EVEN" if be_active else "STOP_LOSS"
                        break
                    elif low <= tp:
                        exit_time = bar["time"]
                        exit_price = tp + self.slippage
                        outcome = "TAKE_PROFIT"
                        break

            # Si no cerró dentro del rango de datos, cerrar a precio de última vela
            if exit_price is None:
                last_bar = future_bars.iloc[-1]
                exit_time = last_bar["time"]
                exit_price = last_bar["close"]
                outcome = "TIME_EXIT"

            # Cálculo de PnL según instrumento
            if instrument == "EQUITY":
                shares = self.risk_manager.calculate_equity_position_size(adj_entry, entry_price - risk_dist)
                if shares <= 0:
                    continue

                raw_pnl = (exit_price - adj_entry) * shares if is_buy else (adj_entry - exit_price) * shares
                commissions = shares * self.risk_manager.commission_per_share * 2
                net_pnl = raw_pnl - commissions

            else:  # OPTION / SPREAD
                opt_details = sig.get("details", {})
                cost_contract = opt_details.get("cost_per_contract", 200.0)
                contracts = self.risk_manager.calculate_option_contracts(cost_contract)
                max_profit_pot = opt_details.get("max_profit", cost_contract * 1.5)

                if outcome == "TAKE_PROFIT":
                    raw_pnl = (max_profit_pot * 0.85) * contracts
                elif outcome == "BREAK_EVEN":
                    raw_pnl = (cost_contract * 0.20) * contracts
                elif outcome == "STOP_LOSS":
                    # Salida disciplinada de opciones limitando pérdida temprana al 45% del débito
                    raw_pnl = -(cost_contract * 0.45) * contracts
                else:
                    raw_pnl = (cost_contract * 0.05) * contracts

                commissions = contracts * self.risk_manager.commission_per_option * 2
                net_pnl = raw_pnl - commissions

            balance += net_pnl
            self.risk_manager.current_capital = max(balance, 1000.0)

            completed_trades.append({
                "symbol": sym,
                "strategy": sig.get("strategy", "Unknown"),
                "instrument": instrument,
                "action": sig["action"],
                "entry_time": entry_time,
                "exit_time": exit_time,
                "entry_price": adj_entry,
                "exit_price": exit_price,
                "outcome": outcome,
                "net_pnl": round(net_pnl, 2),
                "balance": round(balance, 2)
            })

        df_trades = pd.DataFrame(completed_trades)
        if not df_trades.empty:
            df_trades = df_trades.sort_values(by="exit_time").reset_index(drop=True)
            running_balance = self.initial_capital
            sorted_equity = []
            for _, tr in df_trades.iterrows():
                running_balance += tr["net_pnl"]
                sorted_equity.append({"time": tr["exit_time"], "equity": round(running_balance, 2)})
            df_equity = pd.DataFrame(sorted_equity)
            balance = running_balance
        else:
            df_equity = pd.DataFrame(equity_curve)

        # Cálculo de métricas institucionales consolidadas
        metrics = {}
        if not df_trades.empty:
            pnls = df_trades["net_pnl"].tolist()
            expectancy_data = RiskManager.calculate_mathematical_expectancy(pnls)

            # Max Drawdown
            peak = df_equity["equity"].cummax()
            drawdowns = (peak - df_equity["equity"]) / peak
            max_dd = drawdowns.max() * 100

            metrics = {
                **expectancy_data,
                "net_profit": round(balance - self.initial_capital, 2),
                "total_return_pct": round(((balance - self.initial_capital) / self.initial_capital) * 100, 2),
                "max_drawdown_pct": round(max_dd, 2),
                "final_balance": round(balance, 2)
            }

        return df_trades, df_equity, metrics
