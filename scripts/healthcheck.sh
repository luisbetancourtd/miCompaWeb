#!/bin/bash
# ============================================================
# miCompaWeb - Healthcheck Script
# Verifica: imports core, conectividad, servicios externos
# ============================================================

set -euo pipefail

ERROR_COUNT=0

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

check_pass() { echo -e "${GREEN}[OK]${NC} $1"; }
check_fail() { echo -e "${RED}[FAIL]${NC} $1"; ((ERROR_COUNT++)) || true; }
check_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }

echo "=== miCompaWeb Healthcheck v1.2 ==="
echo ""

# 1. Python imports core
echo "--- Core Imports ---"
if python -c "import micompaweb, pydantic, typer, rich" 2>/dev/null; then
    check_pass "Core packages importados"
else
    check_fail "Core packages fallan al importar"
fi

# 2. M2 stack imports
if python -c "from micompaweb.infrastructure.m2 import M2Pipeline" 2>/dev/null; then
    check_pass "M2 Anti-Bot stack disponible"
else
    check_warn "M2 Anti-Bot stack no disponible (opcional)"
fi

# 3. Configuracion
echo ""
echo "--- Configuracion ---"
if [ -f "/app/.env" ] || [ -f "./.env" ]; then
    check_pass "Archivo .env encontrado"
else
    check_warn "Archivo .env no encontrado (usa defaults)"
fi

# 4. Directorios
echo ""
echo "--- Directorios ---"
for dir in "$PROJECTS_DIR" "$CACHE_DIR"; do
    if [ -d "$dir" ]; then
        check_pass "Directorio $dir existe"
    else
        check_warn "Directorio $dir no existe (se creara)"
    fi
done

# 5. Conectividad externa (solo si no es modo quick)
if [ "${1:-}" != "--quick" ]; then
    echo ""
    echo "--- Conectividad Externa ---"
    if curl -sf https://www.google.com >/dev/null 2>&1; then
        check_pass "Internet disponible"
    else
        check_warn "Sin conexion a Internet (modo offline)"
    fi

    # Qdrant
    if [ -n "${QDRANT_URL:-}" ]; then
        if curl -sf "${QDRANT_URL}/healthz" >/dev/null 2>&1; then
            check_pass "Qdrant responde"
        else
            check_warn "Qdrant no responde (usara fallback en memoria)"
        fi
    fi

    # SearXNG
    if [ -n "${SEARXNG_URL:-}" ]; then
        if curl -sf "${SEARXNG_URL}/healthz" >/dev/null 2>&1 || \
           curl -sf "${SEARXNG_URL}" >/dev/null 2>&1; then
            check_pass "SearXNG responde"
        else
            check_warn "SearXNG no responde"
        fi
    fi
fi

# 6. LLM providers
echo ""
echo "--- LLM Providers ---"
if [ -n "${GROQ_API_KEY:-}" ] && [ "$GROQ_API_KEY" != "your_groq_api_key_here" ]; then
    check_pass "Groq API key configurada"
else
    check_warn "Groq API key no configurada"
fi

# Resumen
echo ""
echo "==========================="
if [ $ERROR_COUNT -eq 0 ]; then
    echo -e "${GREEN}HEALTHY${NC}: Todos los checks pasaron"
    exit 0
else
    echo -e "${RED}UNHEALTHY${NC}: $ERROR_COUNT checks fallaron"
    exit 1
fi
