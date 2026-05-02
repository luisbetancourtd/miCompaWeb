#!/bin/bash
# ============================================================
# miCompaWeb - Entrypoint Script
# Maneja: migraciones, pre-start checks, signal handling
# ============================================================

set -euo pipefail

# Directorios por defecto
export PROJECTS_DIR="${PROJECTS_DIR:-/app/projects}"
export CACHE_DIR="${CACHE_DIR:-/app/.cache}"

# Crear directorios si no existen
mkdir -p "$PROJECTS_DIR" "$CACHE_DIR"

# Logging
log_info() { echo "[ENTRYPOINT] INFO: $1"; }
log_warn() { echo "[ENTRYPOINT] WARN: $1"; }

log_info "Iniciando miCompaWeb v1.2"

# Verificar que el venv este activo
if ! command -v micompaweb &>/dev/null; then
    log_warn "micompaweb no encontrado en PATH, usando python -m"
    export PATH="/app/.venv/bin:$PATH"
fi

# Healthcheck rapido antes de arrancar
if [ "${SKIP_HEALTHCHECK:-false}" != "true" ]; then
    log_info "Ejecutando healthcheck pre-start..."
    if ! bash /app/scripts/healthcheck.sh --quick; then
        log_warn "Healthcheck rapido fallo, continuando de todos modos"
    fi
fi

# Manejar signals para shutdown graceful
cleanup() {
    log_info "Recibida senal de terminacion, limpiando..."
    exit 0
}
trap cleanup SIGTERM SIGINT

# Ejecutar comando proporcionado o default
if [ $# -eq 0 ]; then
    log_info "No se proporciono comando, ejecutando: micompaweb --help"
    exec micompaweb --help
else
    log_info "Ejecutando: micompaweb $*"
    exec micompaweb "$@"
fi
