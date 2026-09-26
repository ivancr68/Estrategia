"""
Aplicación Principal del Sistema de Trading Cuantitativo NYSE & Opciones
Servidor web interactivo con panel de control, gráficos interactivos de velas japonesas estilo TradingView,
escáner multi-estrategia en vivo, backtesting, opciones y gestión dinámica de credenciales de brokers.
"""

import os
from flask import Flask, render_template, jsonify, request
import pandas as pd
import numpy as np

import config
from core.market_data import MarketDataProvider
from strategies.multi_strategy_engine import MultiStrategyEngine
from core.backtester import NYSEBacktester
from core.portfolio import PortfolioAllocator
from core.brokers.broker_manager import BrokerManager
from core.notifier import dispatcher
from indicators.trend import add_moving_averages
from indicators.momentum import add_rsi
from indicators.volatility import add_atr, add_bollinger_bands
from indicators.time_filters import add_nyse_session_filters

app = Flask(__name__)

# Instancias compartidas
provider = MarketDataProvider()
engine = MultiStrategyEngine(symbols=config.ETFS_PRINCIPALES)
allocator = PortfolioAllocator(symbols=config.ETFS_PRINCIPALES)
backtester = NYSEBacktester(initial_capital=config.CAPITAL_INICIAL)
broker_manager = BrokerManager(default_broker="ALPACA")
dispatcher.telegram_bot.broker_manager = broker_manager

ETF_NAMES = {
    "SPY": "S&P 500 Index ETF (Mercado General)",
    "QQQ": "Invesco Nasdaq 100 ETF (Tecnología y Crecimiento)",
    "IWM": "Russell 2000 ETF (Small Caps y Reversión a Media)",
    "DIA": "SPDR Dow Jones Industrial Average (Blue Chips)"
}

PHASE_STRINGS = {
    0: "Fuera de Sesión",
    1: "Apertura / Subasta (09:30 - 10:00)",
    2: "Prime Trend (10:00 - 11:30)",
    3: "Midday Chop (11:30 - 14:00)",
    4: "Afternoon Push (14:00 - 15:30)",
    5: "Power Hour / Cierre (15:30 - 16:00)"
}


@app.route("/")
def dashboard():
    market_data = {}
    etfs_summary = []

    for sym in config.ETFS_PRINCIPALES:
        df = provider.get_historical_bars(sym, days=30, interval_mins=5)
        df = add_moving_averages(df)
        df = add_rsi(df)
        df = add_atr(df)
        df = add_nyse_session_filters(df)
        market_data[sym] = df

        last_row = df.iloc[-1]
        phase_num = last_row.get("session_phase", 2)

        etfs_summary.append({
            "symbol": sym,
            "name": ETF_NAMES.get(sym, sym),
            "close": round(last_row["close"], 2),
            "ema_200": round(last_row["ema_200"], 2) if not pd.isna(last_row["ema_200"]) else round(last_row["close"], 2),
            "rsi": round(last_row["rsi"], 1) if not pd.isna(last_row["rsi"]) else 50.0,
            "atr_14": round(last_row["atr_14"], 2) if not pd.isna(last_row["atr_14"]) else 1.5,
            "trend_regime": int(last_row.get("trend_regime", 0)),
            "session_phase_str": PHASE_STRINGS.get(phase_num, "Sesión Regular")
        })

    # Escanear señales (sin disparar alertas masivas históricas al recargar la web)
    signals = engine.scan_market(market_data, mode="HYBRID", trigger_alerts=False)

    # Backtesting institucional
    df_trades, df_equity, metrics = backtester.run(market_data, signals)
    recent_trades = df_trades.tail(12).to_dict(orient="records") if not df_trades.empty else []

    # Asignación de portafolio
    vols = {etf["symbol"]: etf["atr_14"] for etf in etfs_summary}
    momentum = {etf["symbol"]: etf["rsi"] for etf in etfs_summary}

    portfolio_methods = {
        "equal": allocator.allocate("EQUAL_WEIGHT", config.CAPITAL_INICIAL),
        "volatility": allocator.allocate("VOLATILITY_PARITY", config.CAPITAL_INICIAL, volatilities=vols),
        "kelly": allocator.allocate("KELLY", config.CAPITAL_INICIAL),
        "momentum": allocator.allocate("MOMENTUM_WEIGHTED", config.CAPITAL_INICIAL, momentum_scores=momentum)
    }

    brokers_status = broker_manager.get_all_brokers_status()
    brokers_map = {b["id"]: b for b in brokers_status}
    active_account = broker_manager.active_broker.get_account_summary()
    alerts = dispatcher.recent_alerts

    broker_creds = {
        "alpaca_api_key": os.getenv("ALPACA_API_KEY", getattr(config, "ALPACA_API_KEY", "")),
        "alpaca_secret_key": os.getenv("ALPACA_SECRET_KEY", getattr(config, "ALPACA_SECRET_KEY", "")),
        "alpaca_paper_mode": str(os.getenv("ALPACA_PAPER_MODE", getattr(config, "ALPACA_PAPER_MODE", True))).lower() == "true",
        "ibkr_account_id": os.getenv("IBKR_ACCOUNT_ID", getattr(config, "IBKR_ACCOUNT_ID", "DU1234567")),
        "ibkr_gateway_url": os.getenv("IBKR_GATEWAY_URL", getattr(config, "IBKR_GATEWAY_URL", "https://localhost:5000/v1/api")),
        "tradier_access_token": os.getenv("TRADIER_ACCESS_TOKEN", getattr(config, "TRADIER_ACCESS_TOKEN", "")),
        "tradier_account_id": os.getenv("TRADIER_ACCOUNT_ID", getattr(config, "TRADIER_ACCOUNT_ID", "VA12345678")),
        "tradier_paper_mode": str(os.getenv("TRADIER_PAPER_MODE", getattr(config, "TRADIER_PAPER_MODE", True))).lower() == "true",
    }

    return render_template(
        "dashboard.html",
        etfs_summary=etfs_summary,
        signals=signals[:40],
        metrics=metrics,
        recent_trades=recent_trades,
        portfolio_methods=portfolio_methods,
        brokers_status=brokers_status,
        brokers_map=brokers_map,
        combined_summary=broker_manager.get_combined_summary(),
        active_broker=broker_manager.active_broker_name,
        active_account=active_account,
        alerts=alerts,
        min_confluence_score=config.MIN_CONFLUENCE_SCORE,
        broker_creds=broker_creds
    )


@app.route("/api/chart_data/<symbol>")
def api_chart_data(symbol):
    symbol = symbol.upper()
    df = provider.get_historical_bars(symbol, days=15, interval_mins=5)
    df = add_moving_averages(df)
    df = add_rsi(df)
    df = add_atr(df)
    df = add_bollinger_bands(df)

    candles = []
    ema_20 = []
    ema_50 = []
    ema_200 = []
    bb_upper = []
    bb_lower = []
    rsi = []
    volume = []

    for _, row in df.iterrows():
        t = int(row["time"].timestamp())
        candles.append({
            "time": t,
            "open": round(float(row["open"]), 2),
            "high": round(float(row["high"]), 2),
            "low": round(float(row["low"]), 2),
            "close": round(float(row["close"]), 2)
        })
        if not pd.isna(row.get("ema_20")):
            ema_20.append({"time": t, "value": round(float(row["ema_20"]), 2)})
        if not pd.isna(row.get("ema_50")):
            ema_50.append({"time": t, "value": round(float(row["ema_50"]), 2)})
        if not pd.isna(row.get("ema_200")):
            ema_200.append({"time": t, "value": round(float(row["ema_200"]), 2)})
        if not pd.isna(row.get("bb_upper")):
            bb_upper.append({"time": t, "value": round(float(row["bb_upper"]), 2)})
        if not pd.isna(row.get("bb_lower")):
            bb_lower.append({"time": t, "value": round(float(row["bb_lower"]), 2)})
        if not pd.isna(row.get("rsi")):
            rsi.append({"time": t, "value": round(float(row["rsi"]), 2)})
        volume.append({
            "time": t,
            "value": int(row.get("volume", 0)),
            "color": "rgba(0, 208, 132, 0.4)" if row["close"] >= row["open"] else "rgba(255, 71, 87, 0.4)"
        })

    return jsonify({
        "symbol": symbol,
        "candles": candles,
        "ema_20": ema_20,
        "ema_50": ema_50,
        "ema_200": ema_200,
        "bb_upper": bb_upper,
        "bb_lower": bb_lower,
        "rsi": rsi,
        "volume": volume
    })


@app.route("/api/equity_data")
def api_equity_data():
    market_data = {sym: provider.get_historical_bars(sym, days=30, interval_mins=5) for sym in config.ETFS_PRINCIPALES}
    signals = engine.scan_market(market_data, mode="HYBRID", trigger_alerts=False)
    _, df_equity, _ = backtester.run(market_data, signals)

    curve = []
    if not df_equity.empty:
        for _, row in df_equity.iterrows():
            t = int(row["time"].timestamp())
            curve.append({"time": t, "value": round(float(row["equity"]), 2)})

    return jsonify({"equity_curve": curve})


@app.route("/api/broker/select", methods=["POST"])
def select_broker():
    broker_id = request.json.get("broker_id", "ALL")
    success = broker_manager.set_active_broker(broker_id)
    return jsonify({
        "success": success,
        "active_broker": broker_manager.active_broker_name,
        "combined": broker_manager.get_combined_summary(),
        "brokers": broker_manager.get_all_brokers_status()
    })


@app.route("/api/broker/toggle", methods=["POST"])
def toggle_broker():
    data = request.json or {}
    broker_id = data.get("broker_id", "ALL")
    active = data.get("active", None)
    success = broker_manager.toggle_broker_active(broker_id, active)
    return jsonify({
        "success": success,
        "active_broker": broker_manager.active_broker_name,
        "combined": broker_manager.get_combined_summary(),
        "brokers": broker_manager.get_all_brokers_status()
    })


@app.route("/api/broker/credentials", methods=["POST"])
def update_broker_credentials():
    data = request.json or {}
    broker_id = data.get("broker_id", "TRADIER")
    result = broker_manager.update_credentials(broker_id, data)
    return jsonify(result)


@app.route("/api/alerts")
def api_alerts():
    return jsonify({
        "alerts_count": len(dispatcher.recent_alerts),
        "alerts": dispatcher.recent_alerts
    })


test_counter = 0

@app.route("/api/alerts/test", methods=["POST"])
def api_test_alert():
    global test_counter
    test_counter += 1
    t_id = int(pd.Timestamp.now().timestamp())

    if test_counter % 2 == 1:
        # Alerta Alcista: Bull Call Spread en SPY
        sample_signal = {
            "id": f"ALT-CALL-{t_id}",
            "symbol": "SPY",
            "action": "BUY_CALL_SPREAD",
            "instrument": "OPTION",
            "strategy": "TrendFollowing + ORB Breakout",
            "entry_price": 572.50,
            "stop_loss": 568.00,
            "take_profit": 581.50,
            "confluence_score": 95,
            "rationale": "Confluencia Alcista de Alta Convicción: Triple EMA + Ruptura de Rango Matutino de NYSE",
            "details": {
                "instruction": "Comprar Call 570 / Vender Call 575 (30 DTE)",
                "cost_per_contract": 240.0,
                "max_profit": 260.0,
                "risk_reward_ratio": 1.08
            }
        }
    else:
        # Alerta Bajista: Bear Put Spread en QQQ
        sample_signal = {
            "id": f"ALT-PUT-{t_id}",
            "symbol": "QQQ",
            "action": "BUY_PUT_SPREAD",
            "instrument": "OPTION",
            "strategy": "MeanReversion + Pullback Rejection",
            "entry_price": 495.20,
            "stop_loss": 500.50,
            "take_profit": 484.00,
            "confluence_score": 92,
            "rationale": "Confluencia Bajista de Alta Convicción: Sobrecompra RSI + Rechazo en Banda Superior Bollinger",
            "details": {
                "instruction": "Comprar Put 495 / Vender Put 490 (30 DTE)",
                "cost_per_contract": 220.0,
                "max_profit": 280.0,
                "risk_reward_ratio": 1.27
            }
        }

    dispatcher.dispatch_alert(sample_signal)
    tipo = "CALL (Alcista) 🟢" if "CALL" in sample_signal["action"] else "PUT (Bajista) 🔴"
    return jsonify({
        "success": True,
        "message": f"Alerta {tipo} enviada a Telegram con botones interactivos multibróker",
        "alert": sample_signal
    })


@app.route("/api/scan")
def api_scan():
    market_data = {sym: provider.get_historical_bars(sym, days=30, interval_mins=5) for sym in config.ETFS_PRINCIPALES}
    signals = engine.scan_market(market_data, mode="HYBRID", trigger_alerts=False)
    return jsonify({"total_signals": len(signals), "signals": signals})


if __name__ == "__main__":
    print("\n" + "=" * 55)
    print("   INICIANDO TERMINAL DE TRADING CUANTITATIVO NYSE")
    print("   Brokers: Alpaca, Interactive Brokers (IBKR), Tradier")
    print("   Telegram Bot: @IvanAlgoQuantBot")
    print("   Panel disponible en: http://localhost:5050")
    print("=" * 55 + "\n")

    dispatcher.telegram_bot.start_listening()
    app.run(host="0.0.0.0", port=5050, debug=False)
