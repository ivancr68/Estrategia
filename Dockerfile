# Imagen base oficial optimizada de Python
FROM python:3.11-slim

# Evita que Python escriba archivos .pyc y asegura logs en tiempo real
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=5050

# Directorio de trabajo
WORKDIR /app

# Instalar herramientas básicas del sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Instalar dependencias de Python
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copiar el código del proyecto
COPY . .

# Exponer el puerto del dashboard
EXPOSE 5050

# Comando de inicio: ejecuta el servidor web y el bot de Telegram en segundo plano
CMD ["python", "app.py"]
