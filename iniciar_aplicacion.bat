@echo off
title NYSE Quant Options Trading Terminal
echo ========================================================
echo   INICIANDO TERMINAL DE TRADING ALGORITMICO (NYSE)
echo   ETFs: SPY, QQQ, IWM, DIA + Opciones Financieras
echo ========================================================
echo.

:: 1. Crear .env si no existe
if not exist .env (
    echo [INFO] Configurando archivo de entorno local .env...
    copy .env.example .env >nul
)

:: 2. Instalar dependencias si faltan
echo [INFO] Verificando paquetes y dependencias Python...
pip install -r requirements.txt --quiet

:: 3. Abrir automáticamente en el navegador web
echo.
echo [OK] Abriendo Dashboard en http://localhost:5050...
start http://localhost:5050

:: 4. Iniciar el servidor Flask del terminal
echo [OK] Iniciando motor cuantitativo NYSE...
python app.py
pause
