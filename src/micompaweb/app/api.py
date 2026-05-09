"""FastAPI web app - GUI local para miCompaWeb."""

import json
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

from micompaweb.infrastructure.config.settings import Settings

app = FastAPI(title="miCompaWeb", version="1.2.0")
settings = Settings()
templates = Jinja2Templates(directory="templates")

settings.ensure_directories()


def _load_projects() -> list[dict]:
    """Carga metadatos de proyectos desde disco."""
    projects: list[dict] = []
    if not settings.projects_dir.exists():
        return projects
    for p in sorted(settings.projects_dir.iterdir()):
        if p.is_dir() and (p / "project.json").exists():
            with open(p / "project.json", encoding="utf-8") as f:
                projects.append(json.load(f))
    return projects


def _load_leads(project_slug: str) -> list[dict]:
    """Carga leads de un proyecto."""
    leads_path = settings.projects_dir / project_slug / "leads.json"
    if not leads_path.exists():
        return []
    with open(leads_path, encoding="utf-8") as f:
        return json.load(f)


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request) -> HTMLResponse:
    """Pagina principal - lista de proyectos."""
    return templates.TemplateResponse(
        request,
        "web/dashboard.html",
        {"projects": _load_projects()},
    )


@app.get("/api/health")
async def health() -> dict:
    """Health check."""
    return {"status": "ok", "version": "1.2.0"}


@app.get("/api/leads")
async def list_leads(project_slug: Optional[str] = None) -> dict:
    """Lista leads de un proyecto."""
    return {"leads": _load_leads(project_slug) if project_slug else []}
