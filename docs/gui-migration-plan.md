# Plan de Migración CLI → GUI para miCompaWeb

## Fecha: 2026-05-08
## Estado: Análisis completo, a la espera de decisión
## Autor: Hermes Agent

---

## 1. Contexto

miCompaWeb v1.2 es un CLI Python de prospecting para agencias web. M1 está COMPLETO: 345 tests, 82% coverage, motor anti-bot con 3 ejecutores (FAST/STRONG/HEAVY), exportación local (CSV, HTML, JSON), y pipeline de leads con scoring.

**Problema que resuelve este plan:** El usuario necesita una interfaz gráfica que se ejecute en local, pero cuyos datos vivan online para poder acceder desde cualquier lugar. Se descarta Notion (token API, rate limits, schema dependiente). Se propone una arquitectura híbrida local+nube con costo cero.

---

## 2. Requisitos (User Story)

| # | Requisito | Prioridad |
|---|-----------|-----------|
| R1 | GUI moderna, ligera, visual, bien optimizada | Alta |
| R2 | Motor Python actual (anti-bot, prospecting) se reutiliza sin reescribir | Alta |
| R3 | Datos accesibles desde cualquier lugar (cloud) | Alta |
| R4 | Costo mensual = $0 USD | Alta |
| R5 | Ejecutable sin dependencia de Node.js en runtime (si es posible) | Media |
| R6 | Offline-first: si no hay internet, sigue funcionando el scraping local | Media |

---

## 3. Servicios de Datos en la Nube (Gratis)

| Servicio | Free Tier Real | Pros | Contras | ¿Para `miCompaWeb`? |
|----------|---------------|------|---------|---------------------|
| **Supabase** | 500 MB PostgreSQL, Shared CPU, API REST auto, Auth, 50K MAU | API REST auto, dashboard, extensible, estable | 500 MB límite, shared CPU | **⭐ RECOMENDADA** |
| **Neon** | 500 MB Postgres, pausa tras inactividad | Serverless, branching | Pausa = latencia al reactivar, API menos conveniente | ⚠️ Viable pero menos estable |
| **Turso/libSQL** | 500 MB-1 GB, SQLite distribuido | SQLite nativo (encaja con tu stack actual), edge | SDK específico, overkill para un solo usuario | ⚠️ Natural pero innecesario |
| **Cloudflare D1** | 5 GB SQLite, 100K lecturas/día | Muy generoso, serverless | Requiere Workers, binding, complejidad | ⚠️ Overkill para este caso |
| **GitHub Gists** | Sin límite estricto para gists | URLs públicas/secretas para JSON snapshots | No es DB, solo blobs | **✅ BACKUP ideal** |

**Decisión:** Usar **Supabase** como base de datos online (PostgreSQL + PostgREST). Usar **GitHub Gists** como mecanismo de export snapshot (JSON) para compartir reports sin login.

---

## 4. Tecnologías GUI Evaluadas

### 4.1 Tabla Comparativa

| Stack | Tecnología | Peso Bundled | Curva Aprendizaje | Reutiliza Lógica Python | Aspecto Visual | Costo |
|-------|-----------|-------------|-------------------|-------------------------|----------------|-------|
| **FastAPI + HTMX + Tailwind** | Python puro + HTML parciales | ~0 MB (CDN) | Baja | ✅ 100%, importa servicios existentes | ✅ Moderno, SaaS-like | $0 |
| **Next.js 15 + FastAPI** | React/TS/Tailwind + Python API | ~200 MB node_modules | Media | ✅ Vía HTTP API (FastAPI) | ✅ Premium, el mejor | $0 (Vercel) |
| **Tauri + React + Python sidecar** | Rust (glue) + React + Python subprocess | ~2-3 MB ejecutable | Alta (Rust) | ⚠️ Inter-proceso (IPC) | ✅ Nativo del SO | $0 |
| **Reflex** | Python puro (compila a React) | Python only | Media | ✅ Python | ⚠️ Comunidad pequeña | $0 |
| **Streamlit / Gradio** | Python | ~50 MB | Muy baja | ✅ Python | ❌ No es CRM profesional | $0 |

### 4.2 Análisis por Opción

**A. FastAPI + HTMX + Tailwind — ⭐ RECOMENDADA**
- **Por qué:** Reusa TODO tu código Python actual (`micompaweb.application.services.*`) sin modificar un archivo de dominio. Solo añades una capa `app/api.py` con endpoints y templates HTML con HTMX.
- **HTML parciales vía HTMX:** Botones que llaman endpoints y reemplazan fragmentos de la página. Sin SPA, sin build step, sin webpack.
- **Tailwind CDN o build:** Se ve como un producto SaaS moderno.
- **No necesita Node.js:** Corre todo con Python + navegador.
- **Contra:** Menos hype que React, pero igual de funcional.

**B. Next.js 15 + FastAPI**
- **Por qué:** Si tu target es "vender esto a agencias web", un Next.js se ve mejor. Vercel free tier soporta hasta 100 GB bandwidth / mes.
- **Contra:** El motor de scraping (anti-bot) no puede correr en Next.js. Necesitarías tener FastAPI corriendo en algún lado (local o cloud) y Next.js hace fetch a él. Esto es complejo.
- **Veredicto:** Overkill para un uso personal.

**C. Tauri + React + Python sidecar**
- **Por qué:** Distribuyes un `.exe` que se ve nativo en Windows. 3MB vs 200MB de Electron.
- **Contra:** Rust como glue. La comunicación entre Tauri y Python subprocess es más compleja que una web app corriendo en `localhost:8000`.
- **Veredicto:** Ingenioso pero introduce complejidad sin ganar usabilidad real para este caso.

**D. Reflex**
- **Por qué:** Todo en Python, sin aprender React.
- **Contra:** Comunidad pequeña, menos flexible que React/FastAPI. No es ideal para productos que quieres mantener años.
- **Veredicto:** Descartado.

### 4.3 Arquitectura Recomendada

```
┌─────────────────────────────────────────────────────────────┐
│                  LAPTOP / WSL (Local)                        │
│                                                              │
│   ┌──────────────┐      ┌──────────────┐                     │
│   │  GUI Web     │      │  CLI Typer   │                     │
│   │  (FastAPI)   │      │  (existente) │                     │
│   │  + HTMX +    │ ◄─── │  Reutiliza   │                     │
│   │  Tailwind    │      │  servicios   │                     │
│   └──────────────┘      └──────────────┘                     │
│          │                                                   │
│          │ HTTP (localhost:8000)                              │
│          ▼                                                   │
│   ┌──────────────┐      ┌─────────────────────────┐         │
│   │  FastAPI     │      │  SQLite Local           │         │
│   │  (nuevo)     │─────►│  (aiosqlite)            │         │
│   │  Reusa los   │      │  Cache + datos sesión   │         │
│   │  servicios   │      └─────────────────────────┘         │
│   │  de app/     │                   │                       │
│   └──────────────┘                   │ Sync (a demanda)      │
│          │                           ▼                        │
│          │                    ┌──────────────────┐           │
│          │                    │  Supabase (nube) │           │
│          │                    │  PostgreSQL      │           │
│          │                    │  API REST        │           │
│          │                    └──────────────────┘           │
│          │                           ▲                        │
│          │ HTTP (API key)           │                        │
│          └───────────────────────────┘                        │
│                   Desde cualquier navegador                  │
│                    (acceso remoto opcional)                 │
└─────────────────────────────────────────────────────────────┘
```

**Flujo de datos:**
1. Trabajas local (scans, leads, reports) → SQLite local.
2. Cuando terminas un proyecto, haces click "Sync a Supabase" → batch insert.
3. Desde cualquier navegador (o móvil) puedes ver los leads en Supabase dashboard.

---

## 5. Costos

| Componente | Servicio | Costo | Nota |
|------------|----------|-------|------|
| Base de datos nube | Supabase Free | $0/mes | 500 MB, shared CPU |
| Host GUI local | localhost:8000 | $0 | Tu laptop |
| Backup snapshots | GitHub Gists | $0 | JSON por proyecto |
| **TOTAL** | | **$0/mes** | |

---

## 6. Plan de Implementación (si se aprueba)

### Fase 0: Setup Supabase (1-2 horas)
- Crear proyecto en supabase.com
- Obtener `SUPABASE_URL`, `SUPABASE_KEY`
- Crear tablas: `leads` (id, url, name, contact_info, score, category, created_at, project_id), `projects` (id, slug, niche_name, location, created_at)

### Fase 1: FastAPI Backend (4-6 horas)
- Añadir `fastapi`, `uvicorn[standard]` a `pyproject.toml`
- Crear `src/micompaweb/app/api.py` con endpoints:
  - `GET /` → HTML dashboard (Jinja2 template)
  - `POST /scans/start` → inicia prospecting (background task)
  - `GET /leads?project_id=` → lista leads de SQLite local
  - `GET /leads/{id}` → detalle de lead
  - `POST /sync/supabase` → push batch a Supabase
- Reutilizar `ProspectingService`, `ScoringService`, etc.

### Fase 2: Templates HTMX (6-8 horas)
- Crear `templates/web/`:
  - `dashboard.html`: tabla de leads, filtros, paginación, score color-coded
  - `scan_wizard.html`: formulario de nuevo escaneo (location, niche, radius)
  - `lead_detail.html`: panel con datos, web, score, email, botón "generar email"
  - `reports.html`: lista de reports generados, botón export CSV/HTML
- Tailwind CDN + HTMX CDN (zero build).

### Fase 3: Sync a Supabase (2-3 horas)
- Cliente Supabase (`supabase-py` o `httpx` directo a PostgREST).
- Botón "Sync a Nube" en dashboard.
- Manejar conflictos (UPSERT por `id` o `url` + `project_id`).

### Fase 4: Tests (2-3 horas)
- Tests de endpoints FastAPI con `TestClient`.
- Tests de sync con Supabase mockeado.
- Verificar que no baja coverage por debajo de 65%.

---

## 7. Decisiones Pendientes del Usuario

| # | Decisión | Opciones |
|---|----------|----------|
| 1 | ¿Aprobar esta arquitectura? | Sí → Fase 0. No → Revisar. |
| 2 | ¿Empezar con solo SQLite local (sin nube)? | Más rápido, sin Supabase. |
| 3 | ¿Prioridad GUI primero o sync primero? | GUI local → luego nube. O viceversa. |
| 4 | ¿Quitar `notion-client` de `pyproject.toml`? | Sí → ya no es necesario. |

---

## 8. Notas de Descarte

- **Notion vía API:** Descartado. Rate limit 3 req/s, token requerido, schema rígido.
- **Tauri/Escritorio nativo:** Descartado. Añade Rust sin ganar usabilidad real para uso personal.
- **Next.js puro:** Descartado. No puede ejecutar el motor Python de scraping.
- **sqliteviz.com en local:** Descartado. Es una herramienta de visualización, no un CRM. Y "en local" pierde el sentido de acceso remoto.

