# 🏛️ NYSE Quant Options Trading Terminal
### Sistema Algorítmico Multiactivo: Acciones, ETFs Principales (`SPY`, `QQQ`, `IWM`, `DIA`) y Opciones Financieras

Sistema profesional de trading cuantitativo para la Bolsa de Nueva York (NYSE / NASDAQ), fundamentado en las 18 estrategias y lecciones institucionales de Wall Street.

---

## 🌟 Características Principales

* 📊 **4 Estrategias Técnicas Cuantitativas:**
  * **Trend Following Momentum:** Triple EMA (20/50/200) + Expansión MACD (SPY / QQQ).
  * **Mean Reversion:** RSI(14) en sobrecompra/sobreventa + Rebote en Bandas de Bollinger (IWM / DIA).
  * **Opening Range Breakout (ORB 30 min):** Ruptura del rango de apertura (09:30 - 10:00 EST) con volumen.
  * **EMA 50 Pullback Rejection:** Pinbars y martillos testeando soporte dinámico con tendencia macro.
* 🎯 **Motor de Opciones Financieras:**
  * Modelo de Black-Scholes-Merton y cálculo en tiempo real de Griegas ($\Delta, \Gamma, \Theta, \nu$).
  * Contratos automáticos de **Bull Call Spreads**, **Bear Put Spreads**, **Long Calls** y **Long Puts** (21-45 DTE).
* 🏆 **Evaluador de Confluencia y Convicción (0-100%):**
  * Pondera tendencia macro, momentum, volatilidad ATR, fases horarias de NYSE y asimetría R:R.
  * Clasifica oportunidades de Alta Convicción ($\ge 80\%$) para ejecución prioritaria.
* 📈 **Terminal Web con Gráficos TradingView:**
  * Velas japonesas M5, volumen, superposición de EMAs (20, 50, 200), bandas de Bollinger y sub-gráfico de RSI.
* 🔌 **Enrutamiento Multibróker Regulado en EE.UU. (SEC / FINRA / SIPC):**
  * **Alpaca Markets:** Integración REST API nativa (Paper & Live Trading).
  * **Interactive Brokers (IBKR):** Soporte para Client Portal Gateway API y TWS (Trader Workstation).
  * **Tradier Brokerage:** Conector REST para acciones y spreads de opciones financieras con Sandbox ilimitado.
* 📱 **Alertas Interactivas en Telegram:**
  * Despacho automático a Telegram con botones interactivos de decisión directa: `[🦙 Alpaca]`, `[🏛️ IBKR]`, `[📈 Tradier]` y `[❌ Rechazar]`.
* 💼 **5 Modelos de Asignación de Portafolio:**
  * Equal Weight, Volatility Parity (Risk Parity), Half-Kelly Criterion, Momentum Weighted y Fixed Fractional (1.0%).
* 🛡️ **Backtesting Institucional con Fricciones:**
  * Simulación realista con slippage ($\pm \$0.02$), comisiones CBOE/FINRA ($\$0.65$/opción), esperanza matemática ($E$) y Kill-Switch diario (2.0% Max Drawdown).

---

## 📁 Estructura del Proyecto

```
Estrategia/
├── indicators/
│   ├── trend.py                    # Medias Móviles (EMA 20, 50, 200) y Régimen Tendencial
│   ├── momentum.py                 # MACD (12, 26, 9) y RSI (14)
│   ├── volatility.py               # ATR (14) con filtro de expansión y Bandas de Bollinger
│   └── time_filters.py             # Fases de sesión NYSE (Opening Range, Prime Trend, Midday Chop, Power Hour)
├── strategies/
│   ├── base_strategy.py            # Interfaz abstracta para estrategias de acciones y opciones
│   ├── trend_following.py          # Estrategia Tendencial de Momentum (SPY / QQQ)
│   ├── mean_reversion.py           # Estrategia Anti-tendencial / Reversión a Media (IWM / DIA)
│   ├── orb_breakout.py             # Opening Range Breakout (30 min)
│   ├── pullback_rejection.py       # Rechazo en EMA 50 institucional
│   ├── options_strategy.py         # Adaptador a Calls, Puts y Vertical Spreads con Griegas
│   ├── confluence_scorer.py        # Puntuación de convicción profesional (0-100%)
│   └── multi_strategy_engine.py    # Orquestador central de mercado
├── core/
│   ├── brokers/
│   │   ├── base_broker.py          # Interfaz abstracta de corretaje
│   │   ├── alpaca_broker.py        # Conector Alpaca Markets (Paper / Live)
│   │   ├── interactive_brokers.py  # Conector Interactive Brokers (Client Portal / TWS)
│   │   ├── tradier_broker.py       # Conector Tradier Brokerage (Sandbox / Live)
│   │   └── broker_manager.py       # Enrutador central dinámico con persistencia
│   ├── options_engine.py           # Modelo Black-Scholes y cálculo de Delta, Gamma, Theta, Vega
│   ├── market_data.py              # Proveedor de datos históricos e intradía de NYSE
│   ├── risk_manager.py             # Dimensionamiento dinámico, Kill-Switch (2% DD) y Esperanza Matemática
│   ├── portfolio.py                # 5 Métodos de Asignación de Capital (Equal, Volatility, Kelly, Momentum)
│   ├── backtester.py               # Simulador con fricciones reales (Slippage y comisiones de opciones)
│   ├── notifier.py                 # Despachador multicanal de alertas
│   └── telegram_bot.py             # Escuchador y procesador de callbacks interactivos de Telegram
├── templates/
│   └── dashboard.html              # Panel web interactivo TradingView (Dark Mode)
├── config.py                       # Parámetros institucionales editables (tickers, riesgo, horarios)
├── app.py                          # Servidor web Flask del Terminal Cuantitativo (puerto 5050)
├── main.py                         # Ejecutable por consola / terminal
├── iniciar_aplicacion.bat          # Lanzador directo con doble clic para Windows
├── requirements.txt                # Dependencias del proyecto
└── Estrategia.ipynb                # Cuaderno de trabajo interactivo Jupyter
```

---

## 🚀 Instalación y Puesta en Marcha

### 1. Clonar el repositorio
```bash
git clone https://github.com/ivancr68/<tu-repositorio>.git
cd <tu-repositorio>
```

### 2. Crear entorno virtual e instalar dependencias
```bash
python -m venv venv
venv\Scripts\activate   # En Windows
pip install -r requirements.txt
```

### 3. Configurar variables de entorno
Copia el archivo `.env.example` a `.env` y coloca tus credenciales:
```bash
copy .env.example .env
```

### 4. Iniciar la Terminal Web
Haz doble clic en `iniciar_aplicacion.bat` o ejecuta:
```bash
python app.py
```
Abre tu navegador en: **`http://localhost:5050`**

---

## 🔒 Seguridad y Privacidad
El archivo `.env` está excluido de control de versiones en `.gitignore`. Nunca compartas tus API Keys ni tus Tokens de Telegram públicamente.
