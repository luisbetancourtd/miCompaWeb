"""CLI entry point - comandos Typer."""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, List
from dataclasses import dataclass, field, asdict

import typer
import yaml
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box

from micompaweb.infrastructure.config.settings import Settings
from micompaweb.infrastructure.cache.sqlite_cache import SQLiteCache


def _safe_async_run(coro):
    """Ejecuta una coroutine, incluso si ya hay un event loop corriendo (ej: Typer + questionary)."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    if loop and loop.is_running():
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(asyncio.run, coro)
            return future.result()
    return asyncio.run(coro)
from micompaweb.infrastructure.adapters import (
    GooglePlacesSource,
    FixtureSource,
    CachedSource,
    LeadSourceManager,
    SimpleAuditor,
    LLMChain,
    HTMLReportExporter,
    CSVExporter,
    JSONExporter,
)
from micompaweb.application.services.prospecting_service import ProspectingService
from micompaweb.application.services.email_generator import EmailGenerator
from micompaweb.application.services.competitor_service import CompetitorService
from micompaweb.application.services.sentiment_adapter import SentimentAdapter
from micompaweb.application.ui.wizard import Wizard
from micompaweb.domain.models import (
    Project, ProjectConfig, ProjectStatus,
    Lead, WebsiteStatus, PriorityTier,
)
from micompaweb.domain.rules.guardian import InputGuardian
from micompaweb.presentation.tui.welcome_banner import WelcomeBanner
from micompaweb.application.ports.exporter import ExportConfig, ExportResult

console = Console()
app = typer.Typer(
    name="micompaweb",
    help="🏆 AI-powered CLI para agencias web — Encuentra, analiza, cierra",
    no_args_is_help=False,
    add_completion=False,
    rich_markup_mode="rich",
)


# ──────────────────────────────────────────────────────────────
# Comando principal sin subcomando → banner + help
# ──────────────────────────────────────────────────────────────

@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: bool = typer.Option(False, "--version", "-v", help="Versión"),
) -> None:
    """AI-powered CLI para agencias web."""
    if version:
        console.print("[bold cyan]miCompaWeb[/] [dim]v1.2.0 — M1 RECARGADO[/]")
        raise typer.Exit()
    
    # Sin subcomando: banner + ayuda
    if not ctx.invoked_subcommand:
        WelcomeBanner().show()
        console.print("\n[cyan]Comandos disponibles:[/]")
        console.print("  [bold]m1[/]               — Pipeline de prospeccion")
        console.print("  [bold]wizard[/]           — Asistente interactivo")
        console.print("  [bold]setup[/]            — Configurar API keys (primer uso)")
        console.print("  [bold]doctor[/]           — Diagnostico del entorno")
        console.print("  [bold]projects[/]         — Listar proyectos")
        console.print("  [bold]export[/]           — Exportar a HTML/CSV/JSON")
        console.print("  [bold]email[/]            — Generar borrador email")
        console.print("  [bold]revenue[/]          — Revenue dashboard de un proyecto")
        console.print("  [bold]configure-niche[/]  — Gestionar nichos")
        console.print("\n[dim]Ejecuta [cyan]micompaweb COMMAND --help[/] para mas info.[/]")
        raise typer.Exit()


# ──────────────────────────────────────────────────────────────
# MICOMPAWEB WIZARD
# ──────────────────────────────────────────────────────────────

@app.command()
def wizard(
    project_dir: Path = typer.Option(Path("./projects"), "--projects-dir", help="Directorio de proyectos"),
) -> None:
    """🧙 Asistente interactivo: guía paso a paso para configurar y lanzar M1."""
    WelcomeBanner().show()
    console.print()

    try:
        w = Wizard()
        config = w.run()
    except Exception as e:
        console.print(f"\n[red]Error en wizard:[/] {e}")
        raise typer.Exit(1)

    # Guardian: validar inputs
    guardian = InputGuardian(suggestions=[])
    normalized_niche = guardian.normalize_niche(config.niche, w.niches)
    
    # Guardiar chain stores
    config = ProjectConfig(
        niche=normalized_niche,
        location=config.location,
        depth=config.depth,
        max_leads=config.max_leads,
        target_language=config.target_language,
    )

    console.print(f"\n[bold green]✓ Configuración válida[/]")
    console.print(f"  Nicho: [cyan]{config.niche}[/]")
    console.print(f"  Ubicación: [cyan]{config.location}[/]")
    console.print(f"  Profundidad: [cyan]{config.depth}[/]")
    console.print(f"  Leads máx: [cyan]{config.max_leads}[/]")
    console.print(f"  Idioma: [cyan]{config.target_language}[/]")

    if not typer.confirm("\n¿Lanzar pipeline M1 con esta configuración?"):
        console.print("[yellow]Cancelado por usuario.[/]")
        raise typer.Exit()

    # Crear proyecto y ejecutar
    _launch_m1(config, project_dir)


# ──────────────────────────────────────────────────────────────
# MICOMPAWEB M1
# ──────────────────────────────────────────────────────────────

@app.command()
def m1(
    niche: Optional[str] = typer.Option(None, "--niche", "-n", help="Nicho (ej: plomeros)"),
    location: Optional[str] = typer.Option(None, "--location", "-l", help="Ubicación (ej: CDMX)"),
    depth: str = typer.Option("estandar", "--depth", "-d", help="Profundidad: rapida/estandar/exhaustiva"),
    max_leads: int = typer.Option(50, "--max-leads", "-m", help="Máximo de leads", min=1, max=500),
    language: str = typer.Option("es", "--lang", help="Idioma: es/en/fr"),
    fixture: bool = typer.Option(False, "--fixture", "-f", help="Usar datos de prueba (gratis)"),
    offline: bool = typer.Option(False, "--offline", "-o", help="Solo usar caché"),
    wizard_mode: bool = typer.Option(False, "--wizard", "-w", help="Lanzar wizard interactivo primero"),
    list_projects: bool = typer.Option(False, "--list", help="Listar proyectos M1 completados"),
    resume: Optional[str] = typer.Option(None, "--resume", help="Reanudar proyecto por slug o ID"),
    project_dir: Path = typer.Option(Path("./projects"), "--projects-dir", help="Directorio de proyectos"),
) -> None:
    """🔍 M1: Descubrimiento, auditoría y scoring de leads."""
    settings = Settings()

    # ─── MODO: List proyectos ────────────────────────────
    if list_projects:
        _list_projects(project_dir)
        return

    # ─── MODO: Resume proyecto ───────────────────────────
    if resume:
        _resume_project(resume, project_dir)
        return

    # ─── MODO: Wizard ────────────────────────────────────
    if wizard_mode:
        WelcomeBanner().show()
        try:
            w = Wizard()
            config = w.run()
        except Exception as e:
            console.print(f"\n[red]Error en wizard:[/] {e}")
            raise typer.Exit(1)
        
        # Guardian
        guardian = InputGuardian(suggestions=[])
        normalized = guardian.normalize_niche(config.niche, w.niches)
        config = ProjectConfig(
            niche=normalized,
            location=config.location,
            depth=config.depth,
            max_leads=config.max_leads,
            target_language=config.target_language,
        )
        _launch_m1(config, project_dir)
        return

    # ─── MODO: Flags directos ────────────────────────────
    if not niche:
        niche = typer.prompt("¿Qué nicho buscas? (ej: plomeros)")
    if not location:
        location = typer.prompt("¿En qué ciudad? (ej: Ciudad de México)")

    config = ProjectConfig(
        niche=niche,
        location=location,
        depth=depth,
        max_leads=max_leads,
        target_language=language,
    )
    _launch_m1(config, project_dir, fixture=fixture, offline_mode=offline)


def _list_projects(projects_dir: Path) -> None:
    """Lista proyectos M1 completados como tabla Rich."""
    if not projects_dir.exists():
        console.print(f"[yellow]📂 Directorio no encontrado: {projects_dir}[/]")
        raise typer.Exit()

    projects = []
    for project_dir in sorted(projects_dir.iterdir()):
        if not project_dir.is_dir():
            continue
        state_file = project_dir / "_state" / "m1_complete.json"
        leads_file = project_dir / "leads.json"
        scores_file = project_dir / "scores.json"
        
        if state_file.exists():
            import json
            state = json.loads(state_file.read_text()) if state_file.stat().st_size > 0 else {}
            lead_count = 0
            ultra_hot = hot = warm = 0
            
            if leads_file.exists():
                try:
                    leads_data = json.loads(leads_file.read_text())
                    leads = leads_data.get("leads", [])
                    lead_count = len(leads)
                    for l in leads:
                        p = l.get("priority", "")
                        if p == "ULTRA HOT":
                            ultra_hot += 1
                        elif p == "HOT":
                            hot += 1
                        elif p == "WARM":
                            warm += 1
                except Exception:
                    pass
            
            projects.append({
                "slug": project_dir.name,
                "name": state.get("business_name", state.get("niche", project_dir.name)),
                "location": state.get("location", "—"),
                "m1_score": state.get("score", "—"),
                "leads": lead_count,
                "ultra_hot": ultra_hot,
                "hot": hot,
                "warm": warm,
                "date": state.get("date", "—"),
                "has_m2": (project_dir / "m2" / "_state" / "m2_complete.json").exists(),
            })

    if not projects:
        console.print(f"\n[yellow]📂 No hay proyectos completados en {projects_dir}[/]")
        console.print("[dim]Usa [cyan]micompaweb m1[/] o [cyan]micompaweb wizard[/] para crear uno.[/]")
        raise typer.Exit()

    table = Table(
        title="[bold cyan]📂 Proyectos M1 Completados[/]",
        header_style="bold bright_white",
        border_style="bright_blue",
        show_header=True,
        box=box.ROUNDED,
    )
    table.add_column("#", style="dim", justify="center", width=4)
    table.add_column("Negocio", style="bold", min_width=18)
    table.add_column("Ubicación", style="bright_white", min_width=12)
    table.add_column("Score", justify="right", style="cyan")
    table.add_column("Leads", justify="right", style="bright_white")
    table.add_column("🔥", justify="right", style="bold red")
    table.add_column("🟠", justify="right", style="bold yellow")
    table.add_column("M2", justify="center", style="dim")

    for i, p in enumerate(projects[:50], 1):
        score_str = str(p["m1_score"]) if p["m1_score"] != "—" else "—"
        m2_status = "[green]✓[/]" if p["has_m2"] else "[dim]—[/]"
        table.add_row(
            str(i),
            p["name"],
            p["location"],
            score_str,
            str(p["leads"]),
            str(p["ultra_hot"]),
            str(p["hot"]),
            m2_status,
        )

    console.print()
    console.print(table)
    console.print(f"\n[dim]Total: {len(projects)} proyecto(s). Usa --resume SLUG para ver detalles.[/]")
    console.print("[dim]Ejemplo: [cyan]micompaweb m1 --resume {projects[0]['slug']}[/][/]")


def _resume_project(slug: str, projects_dir: Path) -> None:
    """Muestra detalles de un proyecto y permite exportar/email."""
    project_dir = projects_dir / slug
    if not project_dir.exists():
        console.print(f"[red]❌ Proyecto no encontrado: {slug}[/]")
        raise typer.Exit(1)

    state_file = project_dir / "_state" / "m1_complete.json"
    if not state_file.exists():
        console.print(f"[yellow]⚠️ Proyecto existe pero M1 no está completado: {slug}[/]")
        raise typer.Exit(1)

    import json
    state = json.loads(state_file.read_text()) if state_file.stat().st_size > 0 else {}
    
    # Panel resumen
    leads_file = project_dir / "leads.json"
    lead_count = 0
    ultra_hot = hot = warm = 0
    if leads_file.exists():
        try:
            leads_data = json.loads(leads_file.read_text())
            leads = leads_data.get("leads", [])
            lead_count = len(leads)
            for l in leads:
                p = l.get("priority", "")
                if p == "ULTRA HOT": ultra_hot += 1
                elif p == "HOT": hot += 1
                elif p == "WARM": warm += 1
        except Exception:
            pass

    console.print()
    panel = Panel(
        f"""[bold]{slug}[/]

[cyan]Nicho:[/]      {state.get('niche', '—')}
[cyan]Ubicación:[/]  {state.get('location', '—')}
[cyan]Score:[/]      {state.get('score', '—')}/150
[cyan]Fecha:[/]      {state.get('date', '—')}

[bold green]Leads:[/] {lead_count} total
  🔥🔥 ULTRA HOT: {ultra_hot}
  🔥 HOT:         {hot}
  🌡️ WARM:        {warm}
""",
        title="[bold cyan]📊 Resumen del Proyecto[/]",
        border_style="bright_blue",
        box=box.ROUNDED,
    )
    console.print(panel)

    console.print("\n[cyan]Opciones:[/]")
    console.print(f"  Exportar HTML: [dim]{project_dir}/informe.html[/]")
    console.print(f"  Exportar CSV:  [dim]{project_dir}/leads.csv[/]")
    has_m2 = (project_dir / "m2" / "_state" / "m2_complete.json").exists()
    if has_m2:
        console.print(f"  [green]M2 completado:[/] [dim]{project_dir}/m2/[/]")
    else:
        console.print("  M2: [dim]Pendiente — usa micompaweb m2 cuando esté disponible[/]")


def _launch_m1(
    config: ProjectConfig,
    project_dir: Path,
    fixture: bool = False,
    offline_mode: bool = False,
) -> None:
    """Helper común para crear proyecto y lanzar pipeline."""
    import time
    slug = f"{config.niche.lower().replace(' ', '-')}-{config.location.lower().replace(' ', '-')}-{int(time.time())}"
    project_path = project_dir / slug
    project_path.mkdir(parents=True, exist_ok=True)

    project = Project(
        slug=slug,
        config=config,
        project_path=str(project_path),
    )

    settings = Settings()

    if not fixture:
        console.print(f"\n[cyan]💰 Costo estimado:[/] ~${config.max_leads * 0.005:.2f} USD")
        if not typer.confirm("¿Proceder?"):
            console.print("[yellow]Cancelado por usuario.[/]")
            raise typer.Exit()

    try:
        leads = _safe_async_run(_run_pipeline_core(
            settings=settings,
            project=project,
            project_path=project_path,
            use_fixture=fixture,
            offline_mode=offline_mode,
        ))
    except Exception as e:
        console.print(f"\n[red]Error:[/] {e}")
        raise typer.Exit(1)

    # Actualizar stats del proyecto para que HTML/template los muestre correctamente
    project.stats.total_leads = len(leads)
    project.stats.ultra_hot_leads = sum(1 for l in leads if l.priority == PriorityTier.ULTRA_HOT)
    project.stats.hot_leads = sum(1 for l in leads if l.priority == PriorityTier.HOT)
    project.stats.warm_leads = sum(1 for l in leads if l.priority == PriorityTier.WARM)
    project.stats.cold_leads = sum(1 for l in leads if l.priority == PriorityTier.COLD)
    project.stats.total_scanned = len(leads)

    # Mostrar closing screen (sync, fuera del asyncio loop)
    from micompaweb.presentation.tui import ClosingScreen, ClosingMenu
    cs = ClosingScreen()
    cs.show(
        total_leads=len(leads),
        ultra_hot=sum(1 for l in leads if l.priority == PriorityTier.ULTRA_HOT),
        hot=sum(1 for l in leads if l.priority == PriorityTier.HOT),
        warm=sum(1 for l in leads if l.priority == PriorityTier.WARM),
        revenue_total=f"${project.total_estimated_revenue_loss_low:,.0f}-${project.total_estimated_revenue_loss_high:,.0f}",
    )

    # Closing menu interactivo (sync, questionary/prompt_toolkit necesita loop propio)
    menu = ClosingMenu(project=project, leads=leads, project_dir=project_path)
    while True:
        action = menu.show()
        if action == "exit":
            break
        elif action == "view_leads":
            menu.view_leads()
        elif action == "open_html":
            menu.open_html()
        elif action == "export_csv":
            menu.export_csv()
        elif action == "email_top":
            menu.email_top()
        elif action == "email_batch":
            menu.email_batch()
        elif action == "revenue_dashboard":
            menu.revenue_dashboard()
        input("\nPresiona Enter para continuar...")

    console.print("\n[green]✔ Session completada. Hasta la proxima! 🦊")


async def _run_pipeline_core(
    settings: Settings,
    project: Project,
    project_path: Path,
    use_fixture: bool = False,
    offline_mode: bool = False,
) -> list[Lead]:
    """Ejecuta el pipeline M1 async y retorna los leads."""
    from micompaweb.presentation.tui import ProgressPanel

    cache_db = project_path / "cache.db"
    cache = SQLiteCache(cache_db)

    lead_source_manager = LeadSourceManager(max_cost_per_operation=2.00)

    if use_fixture:
        lead_source_manager.add_source(FixtureSource(), priority=1)
    elif offline_mode:
        cached_fixture = CachedSource(FixtureSource(), cache)
        lead_source_manager.add_source(cached_fixture, priority=1)
    else:
        if settings.google_places_api_key:
            google_source = GooglePlacesSource(settings.google_places_api_key)
            cached_google = CachedSource(google_source, cache)
            lead_source_manager.add_source(cached_google, priority=1)
        lead_source_manager.add_source(FixtureSource(), priority=99)

    web_auditor = SimpleAuditor(timeout_seconds=30)
    llm_client = LLMChain.from_settings(settings)

    exporters = [
        HTMLReportExporter(),
        CSVExporter(),
        JSONExporter(),
    ]

    service = ProspectingService(
        lead_source=lead_source_manager,
        web_auditor=web_auditor,
        llm_client=llm_client,
        cache=cache,
        exporters=exporters,
        project_path=project_path,
        competitor_service=CompetitorService(),
        sentiment_adapter=SentimentAdapter(),
        input_guardian=InputGuardian(suggestions=[]),
    )

    # Progress Panel TUI
    progress = ProgressPanel()
    with progress:
        def on_progress(stage: str, current: int, total: int) -> None:
            if stage not in progress.STAGES:
                return
            idx = progress.STAGES.index(stage)
            # Si cambiamos de stage, completa el anterior
            if idx != progress.current_stage_idx and progress.task_id is not None:
                progress.complete_stage()
            # Si no hay task activa para este stage, crearla
            if progress.task_id is None:
                progress.start_stage(stage, total)
            # Advance desde la posicion actual
            if progress.task_id is not None:
                task = progress.progress.tasks[progress.task_id]
                delta = current - task.completed
                if delta > 0:
                    progress.advance(delta)

        progress.start_stage("validation", 1)
        service.on_progress(on_progress)

        leads = await service.execute(project)

        progress.complete_stage("Exportacion completada")
        progress.complete_stage()

    return leads


# ──────────────────────────────────────────────────────────────
# MICOMPAWEB DOCTOR
# ──────────────────────────────────────────────────────────────

@app.command()
def doctor() -> None:
    """🩺 Diagnóstico del entorno."""
    settings = Settings()
    WelcomeBanner().show()
    console.print()

    table = Table(title="[bold cyan]miCompaWeb Doctor[/] [dim]v1.2.0[/]")
    table.add_column("Componente", style="cyan")
    table.add_column("Estado", style="bold")
    table.add_column("Nota", style="dim")

    # Python
    import sys
    py = sys.version_info
    ok = py >= (3, 11)
    table.add_row("Python", "[green]✓[/]" if ok else "[red]✗[/]", f"{py.major}.{py.minor}.{py.micro} {'(≥3.11)' if ok else '(REQUIERE ≥3.11)'}" )

    # Google Places API
    if settings.google_places_api_key:
        # Connectivity test básico
        import httpx
        try:
            r = httpx.get("https://maps.googleapis.com", timeout=5)
            table.add_row("Google Places API", "[green]✓[/]", "API key configurada + conectividad OK")
        except Exception:
            table.add_row("Google Places API", "[yellow]○[/]", "API key OK pero sin conectividad")
    else:
        table.add_row("Google Places API", "[yellow]○[/]", "Opcional (usa --fixture)")

    # Groq
    if settings.groq_api_key:
        table.add_row("Groq API", "[green]✓[/]", "Configurada")
    else:
        table.add_row("Groq API", "[yellow]○[/]", "Opcional (fallback a Ollama/heurística)")

    # Ollama
    import httpx
    try:
        r = httpx.get("http://localhost:11434", timeout=3)
        if r.status_code == 200:
            table.add_row("Ollama (local)", "[green]✓[/]", "Running en localhost:11434")
        else:
            table.add_row("Ollama (local)", "[yellow]○[/]", f"Responde HTTP {r.status_code}")
    except Exception:
        table.add_row("Ollama (local)", "[dim]—[/]", "No detectado (opcional)")

    # NocoDB
    if settings.nocodb_url:
        try:
            httpx.get(settings.nocodb_url, timeout=3)
            table.add_row("NocoDB", "[green]✓[/]", settings.nocodb_url)
        except Exception:
            table.add_row("NocoDB", "[yellow]○[/]", "URL configurada pero no responde")
    else:
        table.add_row("NocoDB", "[dim]—[/]", "Opcional (Phase 2)")

    # LLM Provider Test
    llm = LLMChain.from_settings(settings)
    try:
        if hasattr(llm, "test_connectivity"):
            test_resp = llm.test_connectivity()
            if test_resp:
                table.add_row("LLM Provider", "[green]✓[/]", "Groq/Ollama responde OK")
            else:
                table.add_row("LLM Provider", "[yellow]○[/]", "Conectado pero respuesta vacia")
        else:
            table.add_row("LLM Provider", "[dim]—[/]", "No soporta test de conectividad")
    except Exception as e:
        table.add_row("LLM Provider", "[dim]—[/]", f"No disponible: {str(e)[:40]}")

    # Cache stats
    cache_path = Path("./projects/cache.db")
    if cache_path.exists():
        size_kb = cache_path.stat().st_size / 1024
        table.add_row("Cache (SQLite)", "[green]✓[/]", f"{size_kb:.1f} KB")
    else:
        table.add_row("Cache (SQLite)", "[blue]○[/]", "Se creará automáticamente")

    # Cache entries count
    try:
        from micompaweb.infrastructure.cache.sqlite_cache import SQLiteCache
        cache = SQLiteCache(cache_path.parent / "cache.db")
        entries = cache.count_entries() if hasattr(cache, "count_entries") else "N/A"
        table.add_row("Cache entries", "[dim]—[/]" if entries == "N/A" else "[green]✓[/]", str(entries))
    except Exception:
        pass

    # Extras
    try:
        import questionary
        table.add_row("questionary", "[green]✓[/]", "Interfaz TUI")
    except ImportError:
        table.add_row("questionary", "[yellow]○[/]", "pip install questionary")

    try:
        import structlog
        table.add_row("structlog", "[green]✓[/]", "Logging estructurado")
    except ImportError:
        table.add_row("structlog", "[dim]—[/]", "Opcional: pip install structlog")

    # Disk space
    import shutil
    total, used, free = shutil.disk_usage(".")
    free_gb = free / (1024**3)
    color = "green" if free_gb > 5 else "yellow" if free_gb > 1 else "red"
    table.add_row("Disco libre", f"[{color}]✓[/]" if free_gb > 1 else f"[{color}]![/]", f"{free_gb:.1f} GB")

    console.print(table)
    console.print()

    # Fuentes
    sources = Table(title="[bold cyan]Fuentes de Leads[/]")
    sources.add_column("Fuente", style="cyan")
    sources.add_column("Estado", style="bold")
    sources.add_column("Costo/100", style="dim")
    sources.add_row("Google Places", "✓" if settings.has_places_api else "○", "$0.50")
    sources.add_row("Fixture (Mock)", "✓", "$0.00")
    sources.add_row("Cache (SQLite)", "✓", "$0.00")
    console.print(sources)
    console.print()

    # Exporters
    exporters = Table(title="[bold cyan]Exportadores[/]")
    exporters.add_column("Formato", style="cyan")
    exporters.add_column("Requiere", style="dim")
    exporters.add_row("HTML", "core")
    exporters.add_row("CSV", "core")
    exporters.add_row("JSON", "core")
    console.print(exporters)
    console.print()

    console.print("[dim]Para instalar extras:[/] [cyan]pip install micompaweb[full][/]")


# ──────────────────────────────────────────────────────────────
# MICOMPAWEB PROJECTS (alias para --list)
# ──────────────────────────────────────────────────────────────

@app.command()
def projects(
    project_dir: Path = typer.Option(Path("./projects"), "--projects-dir", help="Directorio de proyectos"),
) -> None:
    """📂 Listar proyectos completados. Equivalente a 'm1 --list'."""
    _list_projects(project_dir)


# ──────────────────────────────────────────────────────────────
# Helpers de carga de proyecto
# ──────────────────────────────────────────────────────────────

def _get_niche_config_dir() -> Path:
    """Retorna directorio de config de nichos: ~/.config/micompaweb."""
    config_dir = Path.home() / ".config" / "micompaweb"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def _load_niche_config() -> dict:
    """Carga archivo de nichos personalizados. Retorna dict vacío si no existe."""
    config_file = _get_niche_config_dir() / "niches.yaml"
    if not config_file.exists():
        return {}
    try:
        return yaml.safe_load(config_file.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}


def _save_niche_config(data: dict) -> Path:
    """Guarda archivo de nichos personalizados."""
    config_file = _get_niche_config_dir() / "niches.yaml"
    config_file.parent.mkdir(parents=True, exist_ok=True)
    config_file.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return config_file


def _load_project_state(slug: str, projects_dir: Path) -> Optional[dict]:
    """Carga el estado m1_complete.json de un proyecto."""
    state_file = projects_dir / slug / "_state" / "m1_complete.json"
    if not state_file.exists():
        return None
    try:
        return json.loads(state_file.read_text(encoding="utf-8"))
    except Exception:
        return None


def _load_project_leads(slug: str, projects_dir: Path) -> list:
    """Carga leads desde archivo JSON del proyecto. Soporta exports/*_leads.json o leads.json."""
    project_dir = projects_dir / slug

    # 1. Intentar archivo de export principal (más completo)
    leads_file = project_dir / "leads.json"
    if leads_file.exists():
        try:
            data = json.loads(leads_file.read_text(encoding="utf-8"))
            if isinstance(data, dict) and "leads" in data:
                return data["leads"]
            if isinstance(data, list):
                return data
        except Exception:
            pass

    # 2. Buscar en exports/
    exports_dir = project_dir / "exports"
    if exports_dir.exists():
        for f in sorted(exports_dir.glob("*_leads.json"), reverse=True):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                if isinstance(data, dict) and "leads" in data:
                    return data["leads"]
                if isinstance(data, list):
                    return data
            except Exception:
                continue

    return []


# ──────────────────────────────────────────────────────────────
# MICOMPAWEB EXPORT
# ──────────────────────────────────────────────────────────────

@app.command()
def export(
    slug: str = typer.Argument(..., help="Slug del proyecto a exportar"),
    formato: str = typer.Option("html", "--format", "-f", help="Formato: html, csv, json"),
    output: Optional[Path] = typer.Option(None, "--output", "-o", help="Ruta de salida (default: auto)"),
    project_dir: Path = typer.Option(Path("./projects"), "--projects-dir", help="Directorio de proyectos"),
) -> None:
    """📤 Exportar un proyecto M1 a HTML, CSV o JSON."""
    WelcomeBanner().show()
    console.print()

    state = _load_project_state(slug, project_dir)
    if state is None:
        console.print(f"[red]❌ Proyecto no encontrado o sin estado M1: {slug}[/]")
        raise typer.Exit(1)

    raw_leads = _load_project_leads(slug, project_dir)
    if not raw_leads:
        console.print(f"[yellow]⚠️ Proyecto encontrado pero sin leads exportados: {slug}[/]")
        console.print("[dim]Asegúrate de que el pipeline M1 se completó y generó leads.[/]")
        raise typer.Exit(1)

    # Reconstruir leads como objetos Lead
    leads: List[Lead] = []
    for rl in raw_leads:
        try:
            leads.append(Lead(**rl))
        except Exception:
            pass

    if not leads:
        console.print("[red]❌ No se pudieron reconstruir leads del archivo.[/]")
        raise typer.Exit(1)

    config = ProjectConfig(
        niche=state.get("niche", "desconocido"),
        location=state.get("location", ""),
        depth="estandar",
    )
    project = Project(
        slug=slug,
        config=config,
        project_path=str(project_dir / slug),
        status=ProjectStatus.COMPLETED,
    )

    # Elegir exporter
    exporter_map = {
        "html": HTMLReportExporter(),
        "csv": CSVExporter(),
        "json": JSONExporter(),
    }

    if formato not in exporter_map:
        console.print(f"[red]❌ Formato no soportado: {formato}[/]")
        console.print("[dim]Formatos: html, csv, json[/]")
        raise typer.Exit(1)

    exporter = exporter_map[formato]

    out_dir = output or (project_dir / slug / "exports")
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    export_cfg = ExportConfig(
        output_dir=out_dir,
        filename_prefix=slug,
        format=formato,
        language="es",
    )

    try:
        # Algunos exporters son async, otros sync. Usar asyncio.run si es async.
        if asyncio.iscoroutinefunction(exporter.export):
            result = _safe_async_run(exporter.export(leads, project, export_cfg))
        else:
            result = exporter.export(leads, project, export_cfg)
    except Exception as e:
        console.print(f"[red]❌ Error de exportación: {e}[/]")
        raise typer.Exit(1)

    console.print(f"\n[bold green]✅ Exportado exitosamente[/]")
    console.print(f"  Archivo: [cyan]{result.file_path}[/]")
    console.print(f"  Registros: [cyan]{result.records_exported}[/]")
    console.print(f"  Tamaño: [cyan]{result.file_size_bytes:,} bytes[/]")
    console.print(f"  Checksum: [dim]{result.checksum[:8]}...[/]")


# ──────────────────────────────────────────────────────────────
# MICOMPAWEB EMAIL
# ──────────────────────────────────────────────────────────────

@app.command()
def email(
    slug: str = typer.Argument(..., help="Slug del proyecto"),
    lead_index: int = typer.Option(0, "--lead", "-l", help="Índice del lead (0 = top)", min=0),
    tone: str = typer.Option("data", "--tone", "-t", help="Tono: formal, casual, data"),
    language: str = typer.Option("es", "--lang", help="Idioma: es/en"),
    project_dir: Path = typer.Option(Path("./projects"), "--projects-dir", help="Directorio de proyectos"),
) -> None:
    """📧 Generar borrador de email para lead top de un proyecto."""
    WelcomeBanner().show()
    console.print()

    state = _load_project_state(slug, project_dir)
    if state is None:
        console.print(f"[red]❌ Proyecto no encontrado: {slug}[/]")
        raise typer.Exit(1)

    raw_leads = _load_project_leads(slug, project_dir)
    if not raw_leads:
        console.print(f"[yellow]⚠️ Sin leads en proyecto: {slug}[/]")
        raise typer.Exit(1)

    leads: List[Lead] = []
    for rl in raw_leads:
        try:
            leads.append(Lead(**rl))
        except Exception:
            pass

    if not leads:
        console.print("[red]❌ No se pudieron reconstruir leads.[/]")
        raise typer.Exit(1)

    # Ordenar por score descendente
    valid_leads = []
    for l in leads:
        try:
            if hasattr(l, "pepita_score") and l.pepita_score is not None:
                valid_leads.append(l)
        except Exception:
            pass
    valid_leads.sort(key=lambda l: l.pepita_score, reverse=True)
    leads = valid_leads

    if not leads:
        console.print("[red]No se pudieron reconstruir leads válidos para email.[/]")
        raise typer.Exit(1)

    if lead_index >= len(leads):
        console.print(f"[red]❌ Índice {lead_index} fuera de rango (total: {len(leads)}).[/]")
        raise typer.Exit(1)

    target = leads[lead_index]

    # Generar signals simples
    signals = []
    if target.website_status == WebsiteStatus.NONE:
        signals.append("Sin sitio web detectado")
    elif target.website_status == WebsiteStatus.HTTP_ONLY:
        signals.append("Sitio web sin HTTPS")
    if target.audit and not getattr(target.audit, "ssl_valid", True):
        signals.append("Certificado SSL inválido o ausente")
    if target.review_count and target.review_count > 20:
        signals.append(f"{target.review_count} reviews en Google — alta visibilidad local")
    if target.rating and target.rating >= 4.0:
        signals.append(f"Excelente reputación ({target.rating}/5)")

    gen = EmailGenerator()
    result = gen.generate(
        business_name=target.business_name,
        niche=state.get("niche", "negocio local"),
        signals=signals or ["Presencia digital optimizable"],
        language=language,
        tone=tone,
    )

    console.print(f"\n[bold cyan]📧 Borrador de Email[/]")
    console.print(f"[dim]Para:[/] [bold]{target.business_name}[/]")
    console.print(f"[dim]Score:[/] [bold]{target.pepita_score}[/] pts | [dim]Prioridad:[/] [bold]{target.priority.value}[/]")
    console.print()
    console.print(Panel(
        f"[bold yellow]Asunto:[/] {result.subject}\n\n{result.body}",
        title="[bold]Email Generado[/]",
        border_style="bright_blue",
        box=box.ROUNDED,
    ))

    # Opción de guardar a archivo
    email_dir = project_dir / slug / "emails"
    email_dir.mkdir(parents=True, exist_ok=True)
    safe_name = target.business_name.replace(" ", "_").replace("/", "_")[:30]
    email_file = email_dir / f"borrador_{safe_name}_{lead_index}.txt"
    email_file.write_text(
        f"Asunto: {result.subject}\n\n{result.body}",
        encoding="utf-8",
    )
    console.print(f"\n[dim]Guardado en:[/] [cyan]{email_file}[/]")


# ──────────────────────────────────────────────────────────────
# MICOMPAWEB REVENUE (standalone)
# ──────────────────────────────────────────────────────────────

@app.command()
def revenue(
    slug: str = typer.Argument(..., help="Slug del proyecto"),
    project_dir: Path = typer.Option(Path("./projects"), "--projects-dir", help="Directorio de proyectos"),
) -> None:
    """📈 Revenue dashboard: muestra proyeccion de perdida de ingresos por nicho."""
    WelcomeBanner().show()
    console.print()

    state = _load_project_state(slug, project_dir)
    if state is None:
        console.print(f"[red]❌ Proyecto no encontrado: {slug}[/]")
        raise typer.Exit(1)

    raw_leads = _load_project_leads(slug, project_dir)
    if not raw_leads:
        console.print(f"[yellow]⚠️ Proyecto encontrado pero sin leads: {slug}[/]")
        raise typer.Exit(1)

    leads: List[Lead] = []
    for rl in raw_leads:
        try:
            leads.append(Lead(**rl))
        except Exception:
            pass

    if not leads:
        console.print("[red]❌ No se pudieron reconstruir leads.[/]")
        raise typer.Exit(1)

    from micompaweb.presentation.tui import ClosingMenu
    config = ProjectConfig(
        niche=state.get("niche", "desconocido"),
        location=state.get("location", ""),
        depth="estandar",
    )
    project = Project(
        slug=slug,
        config=config,
        project_path=str(project_dir / slug),
        status=ProjectStatus.COMPLETED,
    )
    menu = ClosingMenu(project=project, leads=leads, project_dir=project_dir / slug)
    menu.revenue_dashboard()


# ──────────────────────────────────────────────────────────────
# MICOMPAWEB CONFIGURE-NICHE
# ──────────────────────────────────────────────────────────────

@app.command()
def configure_niche(
    add: Optional[str] = typer.Option(None, "--add", "-a", help="Añadir nicho personalizado"),
    remove: Optional[str] = typer.Option(None, "--remove", "-r", help="Eliminar nicho personalizado"),
    list_niches: bool = typer.Option(False, "--list", "-l", help="Listar nichos conocidos"),
) -> None:
    """⚙️ Gestionar nichos personalizados para prospección."""
    WelcomeBanner().show()
    console.print()

    config = _load_niche_config()
    custom_niches = config.get("custom_niches", {})

    # Añadir
    if add:
        parts = add.split("::")
        name = parts[0].strip().lower()
        display = parts[1].strip() if len(parts) > 1 else name.title()
        category = parts[2].strip() if len(parts) > 2 else "general"

        if name in custom_niches:
            console.print(f"[yellow]⚠️ Nicho '{name}' ya existe. Sobrescribiendo.[/]")

        custom_niches[name] = {
            "display": display,
            "category": category,
            "added_at": str(datetime.now().isoformat()),
        }
        config["custom_niches"] = custom_niches
        _save_niche_config(config)
        console.print(f"[bold green]✅ Nicho añadido:[/] [cyan]{name}[/] ({display}, {category})")
        console.print(f"[dim]Archivo: {_get_niche_config_dir() / 'niches.yaml'}[/]")
        return

    # Eliminar
    if remove:
        name = remove.strip().lower()
        if name not in custom_niches:
            console.print(f"[red]❌ Nicho '{name}' no encontrado en lista personalizada.[/]")
            raise typer.Exit(1)
        del custom_niches[name]
        config["custom_niches"] = custom_niches
        _save_niche_config(config)
        console.print(f"[bold green]✅ Nicho eliminado:[/] [cyan]{name}[/]")
        return

    # Listar (default)
    table = Table(
        title="[bold cyan]Nichos Conocidos[/]",
        header_style="bold bright_white",
        border_style="bright_blue",
        show_header=True,
        box=box.ROUNDED,
    )
    table.add_column("Nicho", style="bold", min_width=20)
    table.add_column("Display", style="bright_white", min_width=15)
    table.add_column("Categoría", style="cyan")
    table.add_column("Origen", style="dim")

    # Nichos built-in desde Wizard
    built_in = {}
    try:
        w = Wizard()
        for n in w.niches:
            built_in[n] = {"display": n.replace("_", " ").title(), "category": "built-in"}
    except Exception:
        pass

    all_niches = {}
    all_niches.update(built_in)
    all_niches.update(custom_niches)

    for name, data in sorted(all_niches.items()):
        display = data.get("display", name.title()) if isinstance(data, dict) else name.title()
        category = data.get("category", "general") if isinstance(data, dict) else "general"
        origin = "personalizado" if name in custom_niches else "built-in"
        table.add_row(name, display, category, origin)

    console.print(table)
    console.print(f"\n[dim]Total: {len(all_niches)} nichos ({len(custom_niches)} personalizados)[/]")
    console.print("[dim]Tip: Usa [cyan]--add nombre::Nombre Bonito::categoria[/] para añadir.[/]")


# ──────────────────────────────────────────────────────────────
# MICOMPAWEB SETUP — Wizard de API keys
# ──────────────────────────────────────────────────────────────

@app.command()
def setup() -> None:
    """🔑 Configurar API keys (primer uso)."""
    from micompaweb.application.ui.setup_wizard import SetupWizard
    SetupWizard().run()


# ──────────────────────────────────────────────────────────────
# WEB GUI — Levanta FastAPI local
# ──────────────────────────────────────────────────────────────

@app.command()
def web(
    host: str = typer.Option("127.0.0.1", "--host", help="Host para escuchar"),
    port: int = typer.Option(8000, "--port", "-p", help="Puerto"),
    reload: bool = typer.Option(False, "--reload", help="Auto-reload en desarrollo"),
) -> None:
    """🌐 Abrir GUI web local (FastAPI + HTMX)."""
    import uvicorn
    console.print(f"[bold green]🚀 GUI web en http://{host}:{port}[/]")
    uvicorn.run("micompaweb.app.api:app", host=host, port=port, reload=reload)


# ──────────────────────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app()
