# syntax=docker/dockerfile:1
FROM python:3.12-slim-bookworm AS builder

# Driver ODBC de Microsoft + toolchain para compilar pyodbc/dependencias sin
# wheel prebuilt. curl/gnupg solo hacen falta para agregar el repo de MS.
# La línea del repo se escribe directa (no se descarga prod.list y se le
# mete sed) porque el prod.list oficial ya trae su propio "[arch=...]", y
# agregarle un segundo bloque "[signed-by=...]" con sed produce una entrada
# malformada que apt rechaza ("Malformed entry ... URI parse").
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl gnupg unixodbc-dev gcc g++ \
    && curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/microsoft-prod.gpg] https://packages.microsoft.com/debian/12/prod bookworm main" > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y --no-install-recommends msodbcsql17 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


FROM python:3.12-slim-bookworm AS production

# Solo el runtime del driver ODBC (sin gcc/g++/*-dev de la etapa builder) +
# libgomp1 -- el wheel manylinux de lightgbm (plan_accion_ml_service.py) usa
# OpenMP para paralelismo en su núcleo C++ y lo busca vía dlopen en tiempo de
# import, no en build -- pip install nunca lo detecta, recién explota al
# hacer "import lightgbm" en producción ("libgomp.so.1: cannot open shared
# object file"). Confirmado en vivo: la app no se cae por esto (el import
# vive en un try/except con fallback a la fórmula vieja), pero el
# entrenamiento del modelo sí fallaba 100% de las veces sin este paquete.
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl gnupg unixodbc libgomp1 \
    && curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/microsoft-prod.gpg] https://packages.microsoft.com/debian/12/prod bookworm main" > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y --no-install-recommends msodbcsql17 \
    && apt-get purge -y --auto-remove curl gnupg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=builder /install /usr/local

# COPY selectivo por lista blanca: nunca "COPY . .". Deja fuera de la imagen
# los ~33 scripts sueltos de debug/diagnóstico de la raíz de backend/ (siguen
# en el repo para uso manual, solo no entran a producción), .env, logs, etc.
COPY app/ ./app/
COPY alembic/ ./alembic/
COPY alembic.ini ./

# UID numérico explícito (no solo el nombre): Kubernetes con
# securityContext.runAsNonRoot no puede verificar que un usuario nombrado
# sea distinto de root sin resolverlo primero, y rechaza el contenedor
# (CreateContainerConfigError) — con un UID numérico lo verifica directo.
RUN useradd --create-home --shell /bin/false --uid 10001 appuser \
    && chown -R appuser:appuser /app
USER 10001

EXPOSE 8000

# 1 solo worker: app/websockets/manager.py + app/services/realtime.py
# mantienen las conexiones WebSocket activas en memoria de UN proceso — con
# más workers, un evento emitido en el worker A nunca llegaría a un cliente
# conectado al worker B. Ver plan de despliegue para el camino a escalar
# (mover ese estado a pub/sub sobre Redis).
#
# --proxy-headers + --forwarded-allow-ips='*': sin esto, uvicorn ignora el
# X-Forwarded-Proto que manda el nginx del frontend (ver frontend/nginx.conf)
# y Starlette cree que TODA conexión es http plano -- cualquier URL absoluta
# que construya (ej. el Location de una redirección 307 por slash) sale como
# http://, y el navegador la bloquea por CSP en visitas reales por https.
# '*' es seguro acá: este proceso solo es alcanzable vía el Service interno
# del cluster (nunca expuesto directo a internet), así que no hay un
# atacante externo que pueda falsificar el header saltándose a nginx.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--proxy-headers", "--forwarded-allow-ips=*"]
