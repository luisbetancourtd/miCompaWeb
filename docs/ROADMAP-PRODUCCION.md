# Roadmap: De v1.2.0 (M1 Completo) a Produccion

## Estado actual (2026-05-09)

- **M1 Pipeline 100% funcional**: 351 tests, 83.45% coverage
- **CLI completa**: `micompaweb m1`, `micompaweb doctor`, `micompaweb web`
- **Web GUI basica**: FastAPI + HTMX + Tailwind (localhost)
- **Datos reales**: Google Places, reviews, sentiment, competitor analysis, revenue estimation
- **Control de costos**: SQLite daily budget tracking ($2.00 USD)

---

## Fase A: Inmediata (esta semana) — Estabilidad + UX

| # | Tarea | Archivo(s) | Esfuerzo | Bloqueante? |
|---|-------|------------|----------|-------------|
| A1 | Script `check_env.py` — detecta Python version, OS, sugiere WSL/3.12 | `scripts/check_env.py` | 2h | No |
| A2 | Actualizar README.md a v1.2.0 + instrucciones Windows/WSL | `README.md` | 1h | No |
| A3 | Crear CHANGELOG.md | `CHANGELOG.md` | 30min | No |
| A4 | Crear .dockerignore (faltaba) | `.dockerignore` | 15min | No |
| A5 | Script `install.ps1` / `install.sh` one-liner | `scripts/install.ps1`, `scripts/install.sh` | 1h | No |
| A6 | Fix: `micompaweb m1 --fixture` sin error asyncio en TTY | `app/cli.py`, `presentation/tui/closing_menu.py` | 2h | No |

---

## Fase B: Pre-produccion (2–3 semanas) — SaaS Multi-Usuario

| # | Tarea | Por que importa | Esfuerzo estimado |
|---|-------|-----------------|-------------------|
| B1 | **Auth system**: login/register con JWT + hashed passwords | Sin esto, cualquiera con la URL ve los leads de otros | 3–4 dias |
| B2 | **PostgreSQL** + SQLAlchemy + Alembic migrations | SQLite en disco no permite replicas ni multi-usuario | 2 dias |
| B3 | **Celery + Redis** para jobs async | El pipeline M1 tarda minutos; en web bloquea el request HTTP | 2–3 dias |
| B4 | **S3/MinIO** para storage de proyectos/exports | Cada replica de Docker debe ver los mismos archivos | 1–2 dias |
| B5 | **Rate limiting** en API + CORS | Proteccion contra abuso de API | 4h |
| B6 | **Admin panel basico**: listar usuarios, proyectos, usage | Para que tu revises quien usa la plataforma | 1–2 dias |

**Stack propuesto:**
- Auth: `fastapi-users` (JWT + SQLAlchemy)
- DB: PostgreSQL 15 + `asyncpg` + Alembic
- Jobs: Celery 5 + Redis 7
- Storage: MinIO (self-hosted S3-compatible)
- Cache: Redis (reemplaza SQLiteCache en prod)

---

## Fase C: Escalabilidad + Monetizacion (1–2 meses)

| # | Tarea | Impacto | Esfuerzo |
|---|-------|---------|----------|
| C1 | Sistema de planes/subscripciones (Stripe) | Cobrar mensualmente por leads/usuario | 3–4 dias |
| C2 | Multi-idioma en la web (es/en/fr) | Expandir mercado a Francia/Canada | 2 dias |
| C3 | White-label / custom domain | Agencias quieren parecer que es suyo | 2–3 dias |
| C4 | Webhooks para CRMs (HubSpot, Pipedrive) | Integracion con herramientas de ventas | 2 dias |
| C5 | Reportes PDF automatizados (WeasyPrint) | Cliente recibe PDF en email semanal | 1–2 dias |
| C6 | A/B testing de email templates | Saber cual template cierra mas leads | 2 dias |

---

## Fase D: Observabilidad + Ops

| # | Tarea | Esfuerzo |
|---|-------|----------|
| D1 | Sentry integration (error tracking) | 30min |
| D2 | Prometheus metrics endpoint (/metrics) | 2h |
| D3 | Health checks profundos (DB, Redis, LLM provider) | 2h |
| D4 | Logging estructurado a stdout en Docker | Ya existe (structlog), verificar formato JSON | 1h |
| D5 | CI/CD: deploy automatico a VPS (GitHub Actions → SSH) | 4h |

---

## Infraestructura sugerida para produccion (VPS ~$20/mes)

| Servicio | Rol | Memoria minima |
|----------|-----|----------------|
| Nginx | Reverse proxy + SSL | 50MB |
| 2x API (FastAPI + Uvicorn) | App workers | 512MB c/u |
| PostgreSQL | Datos persistentes | 512MB |
| Redis | Cache + Celery broker | 256MB |
| Celery Worker | Background jobs (M1 pipeline) | 1GB |
| MinIO | Archivos (exports, screenshots) | 256MB |

**Total recomendado:** VPS con 4GB RAM, 2 vCPU, 80GB SSD (~$15–25/mes en Hetzner/Linode/DigitalOcean).

---

## Decisiones pendientes

1. **Self-hosted CLI (1 usuario, tu)** → Saltar a Fase A, ignorar B/C
2. **SaaS web (multi-usuario, cobrar)** → Fase A + B primero, luego C
3. **Agency white-label (multi-tenant)** → Requiere B + C3 primero

¿Cual camino te interesa? Con eso priorizo las tareas.