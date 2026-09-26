# Estrategia de Trading Algorítmico e Institucional: Documento Maestro

Este documento reúne las bases teóricas, operativas, de gestión de riesgo y configuración técnica para el desarrollo y análisis de la estrategia de trading algorítmico. Diseñado para ser cargado como fuente de conocimiento en **NotebookLM**.

---

## 1. Filosofía y Principios Operativos

El sistema está fundamentado en principios de trading cuantitativo e institucional (inspirado en la metodología de traders institucionales como Tute Bevacqua en *Vive Para Contarlo*):

1. **Eliminación Total del Factor Emocional:** Las decisiones de entrada, cálculo de posición, stop loss y toma de beneficios se ejecutan bajo criterios matemáticos estrictos y reglas predefinidas.
2. **Preservación Estricta de Capital (Reglas tipo Prop Firm):**
   - **Riesgo Fijo por Operación:** 0.5% del balance por trade.
   - **Dimensionamiento Dinámico del Lotaje:** El tamaño de la posición no es fijo; se calcula de forma exacta según la distancia al Stop Loss en puntos para que nunca supere el 0.5% de riesgo.
   - **Kill-Switch Diario:** Si la cuenta alcanza un drawdown intradía del **2.0%**, el robot cierra inmediatamente todas las posiciones abiertas y se bloquea hasta el inicio del siguiente día operativo (00:00 UTC).
   - **Control de Sobreoperación:** Máximo **2 operaciones por día**.
   - **Bloqueo de Ganancias (Profit Target Lock):** Parada preventiva al alcanzar +2.0% de ganancia en el día para proteger beneficios.

---

## 2. Definición Técnica de la Estrategia (Session Breakout + Filtros)

### A. Activo y Temporalidad
- **Activo principal:** Oro (`XAUUSD`) o pares mayores de Forex (`EURUSD`, `GBPUSD`).
- **Temporalidades recomendadas:** M5 o M15.

### B. Niveles Clave y Sesiones
- **Sesión de Referencia (Asia):** Se toma el rango entre las **00:00 y las 07:00 UTC**. Se registran el Máximo de Sesión (`Session High`) y el Mínimo de Sesión (`Session Low`).
- **Ventana de Operación:** Las operaciones se ejecutan únicamente entre las **07:00 y las 15:00 UTC** (coincidiendo con las sesiones de Frankfurt, Londres y solapamiento con Nueva York).

### C. Filtro de Tendencia Macro
- **Media Móvil Exponencial de 200 períodos (EMA 200):**
  - Solo se permiten **Compras (BUY)** si el precio actual está por encima de la EMA 200.
  - Solo se permiten **Ventas (SELL)** si el precio actual está por debajo de la EMA 200.

### D. Filtro de Volatilidad y Gestión de Stop Loss
- **Average True Range (ATR de 14 períodos):**
  - Garantiza que el mercado tenga la volatilidad mínima requerida para evitar rangos muertos.
  - **Stop Loss Dinámico:** Distancia = $1.5 \times \text{ATR(14)}$.
  - **Take Profit Dinámico:** Ratio Riesgo:Beneficio mínimo de $1:2$ ($2.0 \times \text{Distancia del Stop Loss}$).
  - **Break-Even Dinámico:** Al alcanzar un recorrido favorable de $1:1$, el Stop Loss se traslada automáticamente al punto de entrada para eliminar el riesgo del trade.

---

## 3. Reglas de Entrada al Mercado

### Señal de Compra (BUY):
1. La vela previa cerró por debajo o dentro del rango del máximo de sesión asiática.
2. La vela actual rompe y cierra con fuerza por **encima del Máximo de Sesión**.
3. El precio se sitúa con claridad por **encima de la EMA 200**.
4. La hora actual se encuentra dentro de la ventana de liquidez (07:00 a 15:00 UTC).
5. El Kill-Switch diario no está activo y no se han superado las 2 operaciones diarias.

### Señal de Venta (SELL):
1. La vela previa cerró por encima o dentro del rango del mínimo de sesión asiática.
2. La vela actual rompe y cierra con fuerza por **debajo del Mínimo de Sesión**.
3. El precio se sitúa con claridad por **debajo de la EMA 200**.
4. La hora actual se encuentra dentro de la ventana de liquidez (07:00 a 15:00 UTC).
5. El Kill-Switch diario no está activo y no se han superado las 2 operaciones diarias.

---

## 4. Métricas Clave de Evaluación (Backtesting)

Para validar la solidez de la estrategia frente a datos históricos de mercado se evalúan las siguientes métricas:
- **Win Rate:** Porcentaje de operaciones con balance positivo (objetivo esperado: 35% - 45% dado el ratio asimétrico 1:2).
- **Profit Factor:** Ratio entre ganancias brutas y pérdidas brutas (objetivo institucional: > 1.4).
- **Drawdown Máximo:** Caída máxima porcentual del capital (debe mantenerse siempre inferior al 4.0% para cumplir con requerimientos de cuentas fondeadas).
- **Curva de Equidad:** Crecimiento sostenido con retrocesos controlados.
