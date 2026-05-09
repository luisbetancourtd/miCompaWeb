#!/usr/bin/env python3
"""Instalador visual de miCompaWeb con barra de progreso rojo-verde."""

import subprocess
import sys
import tomllib
from pathlib import Path


def extract_deps(pyproject_path: Path) -> list[str]:
    """Extrae dependencias core + extras del pyproject.toml."""
    deps = []
    with open(pyproject_path, "rb") as f:
        data = tomllib.load(f)

    # Core dependencies
    project = data.get("project", {})
    deps.extend(project.get("dependencies", []))

    # Optional extras (full)
    extras = project.get("optional-dependencies", {})
    for group in extras.values():
        deps.extend(group)

    # De-duplicate and normalize
    seen = set()
    clean = []
    for dep in deps:
        name = dep.split("[")[0].split(";")[0].strip().lower()
        if name and name not in seen:
            seen.add(name)
            clean.append(dep.strip())
    return clean


def color_for_pct(pct: float) -> str:
    """Devuelve color ANSI: 0% = rojo, 100% = verde."""
    if pct < 50:
        return "\033[91m"  # bright red
    elif pct < 80:
        return "\033[93m"  # yellow
    else:
        return "\033[92m"  # bright green


def reset_color() -> str:
    return "\033[0m"


def draw_bar(current: int, total: int, width: int = 40) -> str:
    pct = current / total if total else 1.0
    filled = int(width * pct)
    bar_char = "█"
    color = color_for_pct(pct * 100)
    bar = color + (bar_char * filled) + " " * (width - filled) + reset_color()
    return f"[{bar}] {pct*100:.1f}%"


def install_package(dep: str, current: int, total: int) -> bool:
    color = color_for_pct((current / total) * 100)
    label = f"{color}[{current}/{total}]{reset_color()} {dep}"
    print(f"\r{draw_bar(current, total)} {label}", end="", flush=True)

    # Use pip to install single package
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-q", dep],
        capture_output=True,
    )
    return result.returncode == 0


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    pyproject = root / "pyproject.toml"

    if not pyproject.exists():
        print("Error: pyproject.toml no encontrado.")
        return 1

    print("🔍 Leyendo dependencias de pyproject.toml...\n")
    deps = extract_deps(pyproject)
    total = len(deps)
    print(f"📦 {total} paquetes por instalar. Comenzando...\n")

    ok = 0
    failed = []

    for i, dep in enumerate(deps, 1):
        success = install_package(dep, i, total)
        if success:
            ok += 1
        else:
            failed.append(dep)

    print()  # newline after progress bar

    # Final summary
    print(f"\n{'='*50}")
    if failed:
        print(f"✅ Instalados: {ok}/{total}")
        print(f"❌ Fallaron: {len(failed)}")
        for f in failed:
            print(f"   - {f}")
        print("\n💡 Tip: Si hay errores de compilación (C++), prueba WSL o Python 3.12")
        return 1
    else:
        print(f"\033[92m🎉 ¡Todo listo! {ok}/{total} paquetes instalados.\033[0m")
        print(f"\n👉 Prueba con: micompaweb doctor")
        return 0


if __name__ == "__main__":
    sys.exit(main())
