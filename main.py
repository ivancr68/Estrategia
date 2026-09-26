"""
Script de Ejecución por Consola del Sistema de Trading Algorítmico NYSE
Permite escanear el mercado, visualizar señales de opciones y evaluar métricas sin iniciar el servidor web.
"""

import config
from core.market_data import MarketDataProvider
from strategies.multi_strategy_engine import MultiStrategyEngine
from core.backtester import NYSEBacktester
from core.portfolio import PortfolioAllocator
from tabulate import tabulate


def main():
    print("=" * 65)
    print("  SISTEMA DE TRADING ALGORITMICO: BOLSA DE NUEVA YORK (NYSE)")
    print("  ETFs Principales (SPY, QQQ, IWM, DIA) + Opciones Financieras")
    print("=" * 65)

    # 1. Carga de datos
    print("\n[1/4] Descargando cotizaciones para la cesta de ETFs...")
    provider = MarketDataProvider()
    market_data = {sym: provider.get_historical_bars(sym, days=30, interval_mins=5) for sym in config.ETFS_PRINCIPALES}
    for sym, df in market_data.items():
        print(f"  - {sym}: {len(df)} barras M5 cargadas. Ultimo precio: ${df['close'].iloc[-1]:.2f}")

    # 2. Escáner Multi-Estrategia
    print("\n[2/4] Escaneando mercado con estrategias Tendenciales y de Reversion...")
    engine = MultiStrategyEngine(symbols=config.ETFS_PRINCIPALES)
    signals = engine.scan_market(market_data, mode="HYBRID")
    print(f"  -> Total de oportunidades detectadas: {len(signals)}")

    equity_sigs = [s for s in signals if s["instrument"] == "EQUITY"]
    option_sigs = [s for s in signals if s["instrument"] == "OPTION"]
    print(f"     * Senales en Acciones/ETFs: {len(equity_sigs)}")
    print(f"     * Estrategias en Opciones:  {len(option_sigs)}")

    if option_sigs:
        print("\nEjemplo de Contratos de Opciones Seleccionados:")
        opt_table = []
        for s in option_sigs[:5]:
            d = s["details"]
            opt_table.append([
                s["symbol"],
                s["strategy_type"],
                d["instruction"],
                f"${d['cost_per_contract']}",
                f"${d['max_profit']}",
                d.get("risk_reward_ratio", 2.0)
            ])
        print(tabulate(opt_table, headers=["Simbolo", "Tipo", "Estructura", "Costo", "Max Beneficio", "R:R"], tablefmt="grid"))

    # 3. Backtesting
    print("\n[3/4] Ejecutando simulacion historica con comisiones y deslizamiento...")
    backtester = NYSEBacktester(initial_capital=config.CAPITAL_INICIAL)
    df_trades, df_equity, metrics = backtester.run(market_data, signals)

    if metrics:
        print("\n" + "=" * 45)
        print("     REPORTE INSTITUCIONAL DE RENDIMIENTO")
        print("=" * 45)
        print(f"Total de Operaciones:    {metrics['total_trades']}")
        print(f"Tasa de Acierto (Win):   {metrics['win_rate_pct']}%")
        print(f"Profit Factor:           {metrics['profit_factor']}")
        print(f"Esperanza Matematica:   ${metrics['expectancy']} por dolar")
        print(f"Beneficio Neto Total:    ${metrics['net_profit']:,.2f}")
        print(f"Retorno Acumulado:       {metrics['total_return_pct']}%")
        print(f"Maximo Drawdown:         {metrics['max_drawdown_pct']}%")
        print(f"Balance Final:           ${metrics['final_balance']:,.2f}")
        print("=" * 45)

    # 4. Asignación de Portafolio
    print("\n[4/4] Calculo de Asignacion de Capital (5 Metodos de Gestion):")
    allocator = PortfolioAllocator(symbols=config.ETFS_PRINCIPALES)
    alloc_eq = allocator.allocate("EQUAL_WEIGHT", config.CAPITAL_INICIAL)
    alloc_vol = allocator.allocate("VOLATILITY_PARITY", config.CAPITAL_INICIAL)
    alloc_kelly = allocator.allocate("KELLY", config.CAPITAL_INICIAL)

    p_table = [
        ["Equal Weight (25%)", alloc_eq["SPY"], alloc_eq["QQQ"], alloc_eq["IWM"], alloc_eq["DIA"]],
        ["Volatility Parity", alloc_vol["SPY"], alloc_vol["QQQ"], alloc_vol["IWM"], alloc_vol["DIA"]],
        ["Half-Kelly Criterion", alloc_kelly["SPY"], alloc_kelly["QQQ"], alloc_kelly["IWM"], alloc_kelly["DIA"]],
    ]
    print(tabulate(p_table, headers=["Metodo", "SPY ($)", "QQQ ($)", "IWM ($)", "DIA ($)"], tablefmt="grid"))
    print("\n[OK] Proceso completado exitosamente.\n")


if __name__ == "__main__":
    main()
