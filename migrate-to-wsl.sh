#!/bin/bash
# Script de migración de miCompaWeb a WSL
# Ejecutar: bash migrate-to-wsl.sh

set -e

echo "=========================================="
echo "  Migrando miCompaWeb a WSL Ubuntu"
echo "=========================================="

# Configuración
PROJECT_NAME="miCompaWeb-V1.1"
SOURCE_DIR="/mnt/c/Users/mr-k0/OneDrive - Université de Poitiers/Documents/00 Proyectos Web/${PROJECT_NAME}"
TARGET_DIR="$HOME/projects/micompaweb"

echo ""
echo "1. Actualizando sistema..."
sudo apt update && sudo apt upgrade -y

echo ""
echo "2. Instalando dependencias del sistema..."
sudo apt install -y \
    python3-pip \
    python3-venv \
    python3-dev \
    build-essential \
    libssl-dev \
    libffi-dev \
    chromium-browser \
    chromium-chromedriver \
    sqlite3 \
    git \
    curl \
    unzip

echo ""
echo "3. Creando directorio destino..."
mkdir -p ~/projects
rm -rf "$TARGET_DIR"
mkdir -p "$TARGET_DIR"

echo ""
echo "4. Copiando archivos del proyecto..."
# Copiar todo excepto .venv y archivos temporales
rsync -av --progress \
    --exclude='.venv' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.pytest_cache' \
    --exclude='*.db' \
    --exclude='htmlcov' \
    --exclude='.git/objects' \
    "$SOURCE_DIR/" "$TARGET_DIR/"

cd "$TARGET_DIR"

echo ""
echo "5. Creando entorno virtual Python..."
python3 -m venv .venv
source .venv/bin/activate

echo ""
echo "6. Actualizando pip..."
pip install --upgrade pip wheel setuptools

echo ""
echo "7. Instalando dependencias..."
# Instalar primero las dependencias de sistema
pip install aiofiles chardet colorama cssselect faiss-cpu greenlet joblib lark \
    multidict nltk numpy outcome pillow propcache psutil pycparser pyee \
    pyopenssl rank-bm25 regex requests selenium sniffio snowballstemmer \
    sortedcontainers tiktoken tqdm trio wsproto yarl

# Luego las dependencias principales
pip install -e ".[dev,audit,places,llm-cloud,exports]"

echo ""
echo "8. Instalando Crawl4AI y sus dependencias..."
pip install crawl4ai
playwright install chromium

echo ""
echo "9. Configurando variables de entorno..."
if [ ! -f .env ]; then
    cat > .env << 'EOF'
# ============================================
# miCompaWeb - WSL Environment
# ============================================

# Copy your actual API keys here
GOOGLE_PLACES_API_KEY=
GROQ_API_KEY=

# LLM Configuration
DEFAULT_LLM_PROVIDER=groq
OLLAMA_BASE_URL=http://localhost:11434

# Cache & Storage (WSL paths)
CACHE_DIR=./projects/.cache
PROJECTS_DIR=./projects

# Cost Control
MAX_DAILY_COST_USD=2.00
ENABLE_COST_TRACKING=true

# Feature Flags
ENABLE_VIGENCY_CHECK=true
EOF
    echo "   Archivo .env creado. Edita con tus API keys."
fi

echo ""
echo "10. Verificando instalación..."
python3 -c "
import sys
print(f'Python: {sys.version}')
print('')

# Verificar dependencias críticas
try:
    import crawl4ai
    print(f'Crawl4AI: OK')
except ImportError as e:
    print(f'Crawl4AI: ERROR - {e}')

try:
    import playwright
    print(f'Playwright: OK')
except ImportError as e:
    print(f'Playwright: ERROR - {e}')

try:
    import httpx
    print(f'HTTPX: OK')
except ImportError as e:
    print(f'HTTPX: ERROR - {e}')

try:
    import pydantic
    print(f'Pydantic: OK')
except ImportError as e:
    print(f'Pydantic: ERROR - {e}')
"

echo ""
echo "11. Ejecutando tests..."
python3 -m pytest tests/ -v --tb=short -x 2>&1 | head -60 || true

echo ""
echo "=========================================="
echo "  Migración completada!"
echo "=========================================="
echo ""
echo "Próximos pasos:"
echo "1. cd $TARGET_DIR"
echo "2. source .venv/bin/activate"
echo "3. Edita .env con tus API keys reales"
echo "4. python -m pytest tests/"
echo ""
echo "Para usar VS Code:"
echo "code ."
echo ""
echo "Directorio del proyecto: $TARGET_DIR"
