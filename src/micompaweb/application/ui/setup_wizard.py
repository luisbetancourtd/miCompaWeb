"""Wizard de configuracion inicial de API keys."""
import os
from pathlib import Path
from typing import Optional

import httpx
import questionary
from rich.console import Console

console = Console()


class SetupWizard:
    """Wizard de primer uso: configura API keys y guarda en .env."""

    ENV_PATH = Path(".env")

    # Descripcion de cada key
    KEYS = {
        "google_places_api_key": {
            "name": "Google Places API",
            "env": "GOOGLE_PLACES_API_KEY",
            "obligatoria": False,
            "hint": "AIzaSy... (sin esta solo funciona modo fixture/demo)",
            "url": "https://developers.google.com/maps/documentation/places/web-service",
            "validate_format": lambda v: v.startswith("AIza") and len(v) > 20,
            "validate_online": True,
            "test_endpoint": (
                "https://places.googleapis.com/v1/places:searchText",
                lambda key: {
                    "headers": {
                        "Content-Type": "application/json",
                        "X-Goog-Api-Key": key,
                        "X-Goog-FieldMask": "places.displayName",
                    },
                    "json": {"textQuery": "plumber"},
                    "timeout": 10,
                },
                lambda r: r.status_code in (200, 400),  # 400=bad request pero key valida
            ),
        },
        "groq_api_key": {
            "name": "Groq API",
            "env": "GROQ_API_KEY",
            "obligatoria": False,
            "hint": "gsk_... (rapida y barata para analisis)",
            "url": "https://console.groq.com/keys",
            "validate_format": lambda v: v.startswith("gsk_") and len(v) > 20,
            "validate_online": False,  # No validar online para no gastar tokens
            "test_endpoint": None,
        },
        "openrouter_api_key": {
            "name": "OpenRouter API",
            "env": "OPENROUTER_API_KEY",
            "obligatoria": False,
            "hint": "sk-or-... (alternativa multi-modelo)",
            "url": "https://openrouter.ai/keys",
            "validate_format": lambda v: v.startswith("sk-or-") and len(v) > 20,
            "validate_online": False,
            "test_endpoint": None,
        },
    }

    def run(self) -> None:
        """Ejecuta el wizard completo de setup."""
        self._show_welcome()

        current_values = self._load_current_env()
        new_values = {}

        for key_id, meta in self.KEYS.items():
            value = self._ask_key(key_id, meta, current_values.get(key_id))
            if value:
                new_values[key_id] = value

        # Ollama se configura solo como URL, no key
        ollama_url = self._ask_ollama(current_values.get("ollama_base_url"))
        if ollama_url:
            new_values["ollama_base_url"] = ollama_url

        if new_values:
            self._save_to_env(new_values)
            console.print("\n[bold green]✅ Configuracion guardada en .env[/bold green]")
            console.print("[dim]Puedes editar .env manualmente en cualquier momento.[/dim]\n")
        else:
            console.print("\n[yellow]⚠️  Sin cambios. Puedes configurar mas tarde con:[/yellow]")
            console.print("[cyan]  micompaweb setup[/cyan]\n")

    def _show_welcome(self) -> None:
        console.print()
        console.rule("[bold cyan]miCompaWeb - Configuracion Inicial[/bold cyan]")
        console.print()
        console.print(
            "Este wizard te ayuda a configurar las API keys necesarias.",
            style="italic",
        )
        console.print()
        console.print(
            "[bold yellow]OBLIGATORIAS:[/bold yellow]  Ninguna — la app funciona en modo demo con --fixture.",
        )
        console.print(
            "[bold green]RECOMENDADAS:[/bold green] Google Places API (para leads reales).",
        )
        console.print(
            "[dim]OPCIONALES:[/dim]     Groq, OpenRouter, Ollama (para analisis con LLM).",
        )
        console.print()
        console.print(
            "Presiona [bold]Enter[/bold] para saltar una key, o pega tu valor.",
            style="dim",
        )
        console.print()

    def _load_current_env(self) -> dict:
        """Carga valores actuales del .env si existe."""
        values = {}
        if not self.ENV_PATH.exists():
            return values
        for line in self.ENV_PATH.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, _, v = line.partition("=")
                values[k.strip()] = v.strip()
        return values

    def _ask_key(self, key_id: str, meta: dict, current: Optional[str]) -> Optional[str]:
        """Pide una key al usuario, validando formato y opcionalmente online."""
        oblig = "[bold red](OBLIGATORIA)[/bold red]" if meta["obligatoria"] else "[dim](opcional)[/dim]"
        default_display = "[bold green]✓ configurada[/bold green]" if current else ""

        console.print(f"\n{oblig} {meta['name']}")
        console.print(f"   Obtener en: [link]{meta['url']}[/link]")
        console.print(f"   Formato: {meta['hint']}")
        if default_display:
            console.print(f"   Actual: {default_display}")

        value = questionary.text(
            f"Pega tu {meta['name']}:",
            default=current or "",
        ).ask()

        if not value or value == current:
            return current if current else None

        # Validar formato
        if meta["validate_format"] and not meta["validate_format"](value):
            console.print(
                "[bold red]❌ Formato invalido.[/bold red] "
                f"Se esperaba: {meta['hint']}",
            )
            return self._ask_key(key_id, meta, current)

        # Validar online si es posible
        if meta.get("validate_online") and meta.get("test_endpoint"):
            endpoint, build_req, check_resp = meta["test_endpoint"]
            try:
                req = build_req(value)
                r = httpx.post(endpoint, **req)
                if check_resp(r):
                    console.print("[bold green]✅ Key validada correctamente.[/bold green]")
                else:
                    console.print(
                        f"[bold yellow]⚠️  Respuesta inesperada ({r.status_code})."
                        f" Puede que la key este invalida o sin quota.[/bold yellow]",
                    )
            except Exception as e:
                console.print(
                    f"[bold yellow]⚠️  No se pudo validar online ({e})."
                    f" La key se guardara igual.[/bold yellow]",
                )

        return value

    def _ask_ollama(self, current: Optional[str]) -> Optional[str]:
        """Pregunta URL de Ollama (LLM local, gratis)."""
        console.print("\n[dim](opcional)[/dim] Ollama (LLM local — gratuito)")
        console.print("   Instalar: https://ollama.com")
        default = current or "http://localhost:11434"
        url = questionary.text(
            "URL de Ollama:",
            default=default,
        ).ask()

        if url == default:
            return current if current else default
        return url

    def _save_to_env(self, values: dict) -> None:
        """Guarda/actualiza keys en .env."""
        lines = []
        existing = {}
        if self.ENV_PATH.exists():
            for line in self.ENV_PATH.read_text(encoding="utf-8").splitlines():
                if "=" in line and not line.strip().startswith("#"):
                    k, _, _ = line.partition("=")
                    existing[k.strip()] = line
                else:
                    lines.append(line)
            # Reconstruir con valores nuevos
            for key_id, value in values.items():
                meta = self.KEYS.get(key_id)
                if meta:
                    env_key = meta["env"]
                else:
                    env_key = key_id.upper()
                existing[env_key] = f"{env_key}={value}"
            lines = []
            for k in existing:
                lines.append(existing[k])
        else:
            for key_id, value in values.items():
                meta = self.KEYS.get(key_id)
                if meta:
                    env_key = meta["env"]
                else:
                    env_key = key_id.upper()
                lines.append(f"{env_key}={value}")

        self.ENV_PATH.write_text(
            "# miCompaWeb - Configuracion generada por setup wizard\n" + "\n".join(lines) + "\n",
            encoding="utf-8",
        )
