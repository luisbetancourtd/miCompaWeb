#!/bin/bash
# WSL Migration Script for miCompaWeb V1.1
set -e

SRC="/mnt/c/Users/mr-k0/OneDrive - Université de Poitiers/Documents/00 Proyectos Web/miCompaWeb-V1.1"
DST="/home/mr-k/projects/micompaweb"

echo "=== Step 1: Copy project files ==="
mkdir -p "$DST"

# Copy with exclusions
for item in "$SRC"/*; do
  name=$(basename "$item")
  case "$name" in
    .venv|htmlcov|.pytest_cache)
      echo "  Skip: $name"
      ;;
    *)
      cp -r "$item" "$DST/" && echo "  OK: $name"
      ;;
  esac
done

# Copy dotfiles
for item in "$SRC"/.*; do
  name=$(basename "$item")
  case "$name" in
    .|..|.venv|.pytest_cache|.git)
      echo "  Skip: $name"
      ;;
    *)
      cp -r "$item" "$DST/" 2>/dev/null && echo "  OK: $name"
      ;;
  esac
done

echo ""
echo "=== Step 2: Create virtual environment ==="
cd "$DST"
python3 -m venv .venv
source .venv/bin/activate

echo ""
echo "=== Step 3: Upgrade pip ==="
pip install --upgrade pip wheel setuptools

echo ""
echo "=== Step 4: Install dependencies ==="
pip install -e ".[dev,audit,llm-cloud,places,exports]"

echo ""
echo "=== Step 5: Install Crawl4AI ==="
pip install crawl4ai
playwright install chromium 2>/dev/null || echo "Playwright chromium install skipped (may need manual install)"

echo ""
echo "=== Step 6: Verify installation ==="
python3 -c "
import sys
print(f'Python: {sys.version}')
deps = ['crawl4ai', 'httpx', 'pydantic', 'rich', 'typer', 'jinja2']
for dep in deps:
    try:
        __import__(dep)
        print(f'{dep}: OK')
    except ImportError as e:
        print(f'{dep}: MISSING - {e}')
"

echo ""
echo "=== Step 7: Run tests ==="
cd "$DST"
python3 -m pytest tests/ -v --tb=short -x 2>&1 | head -60 || true

echo ""
echo "==========================================="
echo "  Migration complete!"
echo "==========================================="
echo ""
echo "Next steps:"
echo "1. cd $DST"
echo "2. source .venv/bin/activate"
echo "3. Edit .env with your API keys"
echo "4. micompaweb doctor"
echo ""
echo "For VS Code: code ."