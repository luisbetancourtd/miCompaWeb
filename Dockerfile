# ============================================================
# miCompaWeb v1.2 - Production Dockerfile
# Multi-stage build: builder -> tester -> runtime
# Optimizado para: seguridad, velocidad, tamaño
# ============================================================

# ===== Stage 1: Builder =====
FROM python:3.12-slim-bookworm AS builder

WORKDIR /app

# Install build dependencies (compilacion C para curl_cffi, numpy, etc)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libffi-dev \
    libssl-dev \
    libsqlite3-dev \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Instalar uv (package manager rapido)
RUN pip install --no-cache-dir uv

# Copiar solo archivos de dependencias (cache layer)
COPY pyproject.toml ./
COPY src/micompaweb/__init__.py src/micompaweb/

# Crear venv e instalar produccion
RUN uv venv /app/.venv && \
    VIRTUAL_ENV=/app/.venv uv pip install -e ".[prod]"

# ===== Stage 2: Runtime =====
FROM python:3.12-slim-bookworm AS runtime

LABEL org.opencontainers.image.title="miCompaWeb"
LABEL org.opencontainers.image.description="AI-powered web agency prospecting CLI"
LABEL org.opencontainers.image.version="1.2.0"
LABEL org.opencontainers.image.source="https://github.com/elcompadigital/micompaweb"

WORKDIR /app

# Instalar runtime deps minimas
RUN apt-get update && apt-get install -y --no-install-recommends \
    sqlite3 \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Crear usuario no-root
RUN groupadd -r micompaweb && \
    useradd -r -g micompaweb -s /bin/false -d /app micompaweb

# Copiar venv desde builder
COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONFAULTHANDLER=1

# Copiar codigo de aplicacion
COPY src/ /app/src/
COPY templates/ /app/templates/
COPY scripts/ /app/scripts/
COPY pyproject.toml /app/

# Crear directorios de datos y asignar permisos
RUN mkdir -p /app/projects /app/.cache /app/data && \
    chown -R micompaweb:micompaweb /app && \
    chmod +x /app/scripts/*.sh

# Healthcheck real: verifica CLI + imports core + conectividad basica
HEALTHCHECK --interval=30s --timeout=15s --start-period=10s --retries=3 \
    CMD python -c "import micompaweb; print('OK')" && \
        micompaweb doctor --quick || exit 1

# Cambiar a usuario no-root
USER micompaweb

# Entrypoint por defecto
ENTRYPOINT ["micompaweb"]
CMD ["--help"]
