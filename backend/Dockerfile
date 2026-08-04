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

# Solo el runtime del driver ODBC (sin gcc/g++/*-dev de la etapa builder).
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl gnupg unixodbc \
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

# Subido de 1 a 2 workers (2026-08-04): app/services/redis_pubsub.py ya
# saca el estado de WebSocket de la memoria de un solo proceso (pub/sub
# sobre Redis, validado en Fase A/B/C del plan de migracion) -- un evento
# emitido en un worker ahora si le llega a un cliente conectado a otro.
# Se subio tras confirmar con pruebas de carga reales que el cuello de
# botella en concurrencia era contencion de GIL/CPU en un solo proceso
# (no la base de datos, que respondia en milisegundos incluso a 200
# consultas concurrentes) -- ver k8s/configmap-backend.yaml, el pool de
# conexiones se bajo por proceso al mismo tiempo para no multiplicar el
# total de conexiones a SQL Server.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
