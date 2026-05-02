# miCompaWeb RECARGADO — Especificación Técnica

> **Base**: V1.1 (arquitectura hexagonal, Pydantic v2, dependency injection)
> **Objetivo**: Producto final por fases — no solo MVP
> **Fecha**: 2026-04-20
> **Fuentes**: problem-solucion.md, propuesta.md, scoring-matrix-propuesta.docx, V0.1 features

---

## 1. Visión RECARGADO

### 1.1 Qué tiene V1.1 correcto

V1.1 es la base sólida. Su arquitectura hexagonal (domain → application/ports → infrastructure/adapters) con protocols Python, Pydantic v2, dependency injection, y separación estricta de capas es el fundamento que no se toca.

**Lo que funciona**:
- Ports & Adapters: `LeadSource`, `WebAuditor`, `LLMClient`, `Cache`, `Exporter` como Protocols
- `LeadSourceManager` con fallback chain, health checks, cost estimation
- `ScoreBreakdown` con criterion, category, points, max_points, evidence, confidence
- `NicheRepository` con datos validados por nicho + fuentes + seasonality
- `RevenueCalculator` con metodología 3-escenarios + sensitivity analysis
- `FixtureSource` para desarrollo offline (`--fixture`)
- `SQLiteCache` con TTL + offline-first
- `LLMChain`: Groq → Ollama → Heuristic fallback
- Pydantic Settings para config vía env vars

**Lo que necesita**:
- 9 features de V0.1 que se perdieron (evaluadas abajo)
- Scoring Matrix expandida a 3 dimensiones
- TUI premium completa
- Infraestructura de retries, logging, y validación de inputs

### 1.2 Principio rector

> No estamos creando un MVP. Estamos creando un producto final por fases.

Cada feature se implementa en su forma final o cercana a ella. Si algo se simplifica, es por velocidad de implementación, no por recortar funcionalidad.

---

## 2. Alineación con Problem-Solucion

Los 3 problemas críticos identificados en `problem-solucion.md`:

### P1: Empaquetado (12+ dependencias complejas)

| Aspecto | Estado V1.1 | Acción RECARGADO |
|---------|-------------|------------------|
| Extras modulares en pyproject.toml | Existe con grupos: audit, audit-heavy, places, llm-local, llm-cloud, export, integrations, full, dev | **Limpiar**: eliminar solapamiento audit/audit-heavy (ambos tienen bs4+lxml), renombrar audit-heavy → audit-crawl4ai |
| Graceful degradation | No existe DependencyManager | **Crear**: `src/micompaweb/infrastructure/deps_manager.py` — comprueba availability de extras con try/import |
| Comando Doctor | Existe con checks básicos | **Mejorar**: añadir connectivity test, LLM provider test, cache stats, install recommendations por grupo |
| UV support | No documentado | **Documentar**: instrucciones `uv tool install micompaweb[full]` |

**pyproject.toml RECARGADO (extras)**:
```toml
[project.optional-dependencies]
audit = [
    "crawl4ai>=0.4.0",
    "beautifulsoup4>=4.12.0",
    "lxml>=5.0.0",
    "python-whois>=0.9.0",
]
llm-local = [
    "ollama>=0.2.0",
]
llm-cloud = [
    "groq>=0.4.0",
    "openrouter>=0.1.0",
]
export = [
    "openpyxl>=3.1.0",
    "pandas>=2.2.0",
]
integrations = [
    "notion-client>=2.0.0",
]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.23",
    "pytest-cov>=5.0",
    "respx>=0.21",
    "pytest-mock>=3.14",
    "ruff>=0.4",
    "mypy>=1.10",
    "pre-commit>=3.7",
]
full = ["micompaweb[audit,llm-local,llm-cloud,export,integrations]"]
test = ["micompaweb[full,dev]"]
```

**Nuevas dependencias core**:
```toml
dependencies = [
    "typer>=0.12.0",
    "rich>=13.7.0",
    "questionary>=2.0.0",     # NUEVO: Wizard interactivo
    "pydantic>=2.6.0",
    "pydantic-settings>=2.0.0",
    "httpx>=0.27.0",
    "aiosqlite>=0.20.0",
    "jinja2>=3.1.0",
    "python-dotenv>=1.0.0",
    "beautifulsoup4>=4.12.0",
    "lxml>=5.0.0",
    "tenacity>=8.0.0",        # NUEVO: Retry logic
    "structlog>=24.0.0",      # NUEVO: Structured logging
]
```

### P2: Dependencia única de Google Places API

| Aspecto | Estado V1.1 | Acción RECARGADO |
|---------|-------------|------------------|
| LeadSource Protocol | Existe | **Completo** — no se necesita acción |
| LeadSourceManager con fallback | Existe con priority chain | **Completo** |
| CachedSource | Existe como decorator | **Completo** |
| FixtureSource | Existe con data determinista | **Completo** |
| CostGuardian | No existe | **Crear**: `src/micompaweb/infrastructure/cost_guardian.py` — DAILY_LIMIT_USD=2.00, preview_cost(), can_proceed() |
| OutscraperSource | No existe | **Documentar** como adapter futuro (Phase 3+) |

**Resolución**: V1.1 ya resolvió este problema con la arquitectura multi-provider. Solo falta CostGuardian.

### P3: Revenue Loss sin metodología

| Aspecto | Estado V1.1 | Acción RECARGADO |
|---------|-------------|------------------|
| NicheRepository con fuentes | Existe (8 nichos) | **Completo** — datos validados con sources |
| RevenueCalculator 3-escenarios | Existe con conservative/mid/optimistic | **Completo** |
| Sensitivity analysis | Existe | **Completo** |
| RevenueMethodology model | Existe con formula, steps, assumptions | **Completo** |
| Comando configure-niche | No existe | **Crear**: `micompaweb configure-niche` — permite al usuario registrar nichos con SUS datos |

**Resolución**: V1.1 ya resolvió este problema. Solo falta el comando `configure-niche`.

---

## 3. Scoring Matrix RECARGADO

### 3.1 Arquitectura de Puntuación (3 Dimensiones)

Adopta el modelo de `scoring-matrix-propuesta.docx` con max 150:

```
pepita_score = (
    authority_score * 0.30 +
    digital_neglect * 0.45 +
    sales_readiness * 0.25
)

# Ajuste por profundidad
if depth == "exhaustiva": pepita_score *= 1.0
elif depth == "estandar": pepita_score *= 0.95
elif depth == "rapida":    pepita_score *= 0.90

pepita_score = min(round(pepita_score), 150)
```

### 3.2 A. Authority Score (30%, 0-100)

Mide la fortaleza offline / reputación del negocio.

| Criterio | Puntos | Condición | Fuente |
|----------|--------|-----------|--------|
| Review Volume | 0-40 | >50 reviews = 40, >30 = 30, >10 = 15 | `lead.review_count` |
| Review Rating | 0-30 | 4.5+ = 30, 4.0+ = 20, 3.5+ = 10 | `lead.rating` |
| Local Signals | 0-30 | Photos>20 = 10, atributos completos = 10, horarios presentes = 10 | `lead.gbp_health` |

**Detalle Local Signals**:
- `has_photos`: `gbp_health.photos_count > 20` → +10
- `has_attributes`: `gbp_health.has_categories and gbp_health.has_phone` → +10
- `has_hours`: `gbp_health.has_hours` → +10

### 3.3 B. Digital Neglect Score (45%, 0-100)

Mide el abandono o deficiencia digital (oportunidad para agencia).

| Criterio | Puntos | Condición | Fuente |
|----------|--------|-----------|--------|
| No Website | +50 | `website_status == "none"` | places_data |
| SSL Insecure | +20 | HTTP only o certificado inválido | `audit.ssl_valid == False` |
| Tech Obsolete | +15 | Wix/GoDaddy Builder + copyright >2 años | `audit.cms` + `audit.copyright_year` |
| No Tracking | +10 | Sin Meta Pixel, GTM, ni Analytics | `audit.has_meta_pixel/gtm/analytics` |
| Mobile Broken | +15 | Viewport no responsive | `audit.mobile_friendly == False` |
| Contact Missing | +10 | Sin email ni teléfono en la web | `audit.emails_found` + `audit.phones_found` |
| Content Outdated | +25 | Copyright >2 años o LLM detecta obsoleto | `vigency.is_outdated` |

**Detalle Tech Obsolete**:
- CMS en `OBSOLETE_CMS = {"wix", "godaddy", "weebly", "sitebuilder"}` Y copyright_year < (current_year - 2)
- O: CMS es builder básico Y no tiene tracking (señal doble de abandono)

**Detalle Contact Missing**:
- `len(audit.emails_found) == 0 AND len(audit.phones_found) == 0` → +10

**Cap**: `digital_neglect = min(sum(criteria), 145)` (no puede exceder la suma lógica)

### 3.4 C. Sales Readiness (25%, 0-100)

Mide la propensión a comprar servicios digitales. Reemplaza Readiness + Opportunity de V1.1.

| Criterio | Puntos | Condición | Fuente |
|----------|--------|-----------|--------|
| Active GBP | +30 | Responds a reviews (owner_response_rate > 0.25) | `lead.owner_response_rate` |
| Competitor Density | +20 | >5 competidores con web en radio de búsqueda | `lead.competitor_count` |
| Recent Activity | +25 | Reviews en últimos 30 días | `lead.has_recent_reviews` |
| Category Value | +25 | Nicho de alto ticket (dentistas, abogados, clínicas) | `NicheRepository` avg_ticket |

**Detalle Category Value**:
- Si `NicheRepository.get(niche).avg_ticket_usd >= 200` → +25 (alto ticket)
- Si `avg_ticket_usd >= 100` → +15 (medio ticket)
- Si `avg_ticket_usd < 100` → +5 (bajo ticket)

### 3.5 Tiers de Prioridad (Calibrados)

| Tier | Score | Descripción | Acción |
|------|-------|-------------|--------|
| ULTRA HOT | 120-150 | Autoridad + abandono + listos para comprar | Contactar hoy |
| HOT | 80-119 | Alta prioridad: buena combinación | Agregar a pipeline esta semana |
| WARM | 50-79 | Interés moderado: requiere nurturing | Seguimiento mensual |
| COLD | 25-49 | Baja prioridad: posible futuro | Descartar por ahora |
| DISCARD | 0-24 | Sin valor: negocio irrelevante | No contactar |

### 3.6 Cambios en código

**`src/micompaweb/domain/models/scoring.py`**:
```python
class ScoreCategory(str, Enum):
    AUTHORITY = "authority"
    DIGITAL_NEGLECT = "digital_neglect"
    SALES_READINESS = "sales_readiness"  # Reemplaza READINESS + OPPORTUNITY

CATEGORY_WEIGHTS = {
    ScoreCategory.AUTHORITY: 0.30,
    ScoreCategory.DIGITAL_NEGLECT: 0.45,
    ScoreCategory.SALES_READINESS: 0.25,
}
CATEGORY_MAX = {
    ScoreCategory.AUTHORITY: 100,
    ScoreCategory.DIGITAL_NEGLECT: 145,
    ScoreCategory.SALES_READINESS: 100,
}
```

**`src/micompaweb/application/services/scoring_service.py`**:
- Rewriter `_score_authority()`: añadir local_signals (3 subcriterios)
- Rewriter `_score_digital_neglect()`: añadir tech_obsolete, mobile_broken, contact_missing
- Merge `_score_readiness()` + `_score_opportunity()` → `_score_sales_readiness()`
- Añadir `OBSOLETE_CMS` set y `HIGH_TICKET_THRESHOLD = 200`
- Añadir depth adjustment post-cálculo

---

## 4. Features V0.1 → V1.1 RECARGADO

### 4.1 Wizard + Agente de Validación Semántica

**Decisión**: IN

**Problema**: Si el usuario escribe "Plumber" en contexto México, el sistema no debe traducir a "Plomero" automáticamente. El agente interpreta la intención y confirma.

**Archivos nuevos**:
- `src/micompaweb/app/wizard.py` — ProspectarWizard (Questionary)
- `src/micompaweb/app/input_agent.py` — InputValidationAgent

**ProspectarWizard**:
```python
class ProspectarWizard:
    NICHE_SUGGESTIONS = NicheRepository.list_available()  # ["plomeros", "dentistas", ...]
    CITIES_SUGGESTIONS = ["Ciudad de México", "Guadalajara", "Monterrey", ...]

    def run(self) -> ProjectConfig:
        # Paso 1: Nicho (Questionary select + text fallback)
        # Paso 2: Ubicación (Questionary select + text fallback)
        # Paso 3: Profundidad (rapida/estandar/exhaustiva)
        # Paso 4: Idioma (es/en/fr)
        # Paso 5: Max leads (1-500)
        # → Retorna ProjectConfig validado
```

**InputValidationAgent**:
```python
class InputValidationAgent:
    """Agente LLM local ligero para validación semántica de inputs."""

    def __init__(self, ollama_base_url: str = "http://localhost:11434"):
        self.ollama_url = ollama_base_url
        self.model = "qwen2:1.5b"  # Modelo ligero 1-2B

    async def validate_niche(
        self,
        user_input: str,
        available_niches: List[str],
        location: str,
    ) -> ValidationResult:
        """
        Valida coherencia semántica del input del usuario.

        Retorna:
            interpreted_niche: str — slug del nicho interpretado
            confidence: float — 0-1 confianza en la interpretación
            needs_confirmation: bool — si requiere confirmación del usuario
            suggested_alternatives: List[str] — alternativas si hay ambigüedad
        """
        # 1. Intentar con Ollama (modelo 1-2B)
        #    Prompt: "El usuario busca '{input}' en '{location}'.
        #            Nichos disponibles: {niches}.
        #            ¿A cuál se refiere? Responde solo el slug."
        # 2. Si Ollama no disponible: fallback a difflib.get_close_matches()
        # 3. Si confidence < 0.7: marcar needs_confirmation = True
```

**Flujo UX**:
```
? ¿Qué tipo de negocios buscas? Plumber
🤖 Agente: Detectado "Plumber" (inglés) en Ciudad de México.
   ¿Buscar "Plumber" literal, o prefieres "Plomero"?
  → Buscar "Plumber"  |  → Buscar "Plomero"
```

**Dependencia**: `questionary>=2.0.0` (core), Ollama con modelo 1-2B (opcional, difflib como fallback)

**Integración con CLI**:
- `micompaweb m1` (sin flags) → lanza Wizard → InputAgent → pipeline
- `micompaweb m1 --niche X --location Y` → salta Wizard, InputAgent valida flags

---

### 4.2 TUI Completa (Rich)

**Decisión**: IN COMPLETO

**Directorio nuevo**: `src/micompaweb/presentation/tui/`

**Componentes**:

| Archivo | Contenido |
|---------|-----------|
| `welcome.py` | ASCII art logo + Panel de branding con Rich. Muestra: nombre, versión, tagline |
| `progress.py` | Rich `Live` display con `Progress` bars por etapa. Integra con `ProspectingService._notify_progress()` via callbacks. Etapas: Discovery, Audit, Vigency, Scoring, Export |
| `panels.py` | `create_lead_card(lead)` — Panel con nombre, score, tier, señales. `create_summary_panel(project)` — stats globales. `create_error_panel(error)` — errores accionables |
| `tables.py` | Rich `Table` con colores por tier (rojo=ULTRA HOT, naranja=HOT, amarillo=WARM, gris=COLD). Columnas: negocio, score, website, SSL, tracking. Sortable por score |
| `closing_menu.py` | Menú post-scan interactivo con Questionary. Opciones: abrir informe, ver top leads, exportar CSV, sincronizar NocoDB, generar email borrador, salir |
| `styles.py` | `PRIORITY_COLORS`, `PRIORITY_EMOJIS`, `THEME` config. Constantes de estilo centralizadas |
| `__init__.py` | Package init con re-exports |

**Progress display**:
```
🔍 Discovery     ━━━━━━━━━━━━━━━━━━━━━━━━ 100% 52/52 leads
🔎 Web Audit     ━━━━━━━━━━━━━━━━━━━━━━━━ 100% 30/30 sites
📋 Vigency Check ━━━━━━━━━━━━━━━━━━━━━━━━ 100% 30/30 sites
📊 Scoring       ━━━━━━━━━━━━━━━━━━━━━━━━ 100% 52/52 leads
📤 Export        ━━━━━━━━━━━━━━━━━━━━━━━━ 100% 3/3 files
```

**Closing menu**:
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ✅ Análisis completado: plomeros-cdmx
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  📊 52 leads | 🔥 8 ULTRA HOT | 🟠 12 HOT | 🟡 15 WARM

? ¿Qué deseas hacer?
  → Ver Top 10 leads en tabla
    Abrir informe HTML
    Exportar CSV
    Sincronizar NocoDB
    Generar email borrador (top lead)
    Salir
```

**Wiring**:
- CLI → `welcome.py` al inicio
- `ProspectingService.__init__()` acepta progress_callback
- `_notify_progress()` → Rich Live display update
- Post-pipeline → `closing_menu.py`

---

### 4.3 NocoDB + Dashboard Roadmap

**Decisión**: NocoDB se queda como está. sqliteviz como Phase 2.

**Estado actual**:
- `Settings` tiene `nocodb_url`, `nocodb_api_token`, `has_nocodb`
- Doctor command lo verifica
- No hay adapter NocoDBSync en V1.1 (solo config stubs)

**Roadmap de dashboards**:

| Phase | Solución | Implementación |
|-------|----------|----------------|
| **Actual** | NocoDB sync | Si se implementa el adapter NocoDBSync (de V0.1) |
| **Phase 2** | sqliteviz | `docker-compose.yml` añade `sqliteviz` container montando `projects/*.db`. UI web para queries SQL sobre los datos. Solo lectura y análisis. |
| **Phase 3** | Dashboard propio | App web local (FastAPI + React/Vue) en Docker. Gráficos de market health, scoring distribution, revenue estimates. Interfaz gráfica amigable dedicada. |

**docker-compose RECARGADO (Phase 2)**:
```yaml
services:
  micompaweb:
    build: .
    volumes:
      - ./projects:/app/projects
  sqliteviz:
    image: litchin/sqliteviz:latest
    ports:
      - "8080:8080"
    volumes:
      - ./projects:/data
```

---

### 4.4 Outreach Email (Borrador)

**Decisión**: IN (solo borrador, nunca auto-envío)

**Principio**: No queremos un email random o malo para un posible cliente. El borrador se genera, se muestra, y el usuario decide si lo usa.

**Implementación**:

`LLMClient.generate_opening_angle()` ya existe en V1.1. Se mejora:

**Prompt templates (multi-idioma)**:
```python
# src/micompaweb/infrastructure/adapters/llm/prompts.py

OUTREACH_PROMPTS = {
    "es": (
        "Eres un experto en ventas de servicios web. Genera un email de apertura "
        "para {business_name}, un negocio de {niche} en {location}. "
        "Señales de oportunidad: {pain_points}. "
        "El email debe ser profesional, personalizado, y no agresivo. "
        "Máximo 150 palabras."
    ),
    "en": (
        "You are a web services sales expert. Generate an opening email "
        "for {business_name}, a {niche} business in {location}. "
        "Opportunity signals: {pain_points}. "
        "The email should be professional, personalized, and not aggressive. "
        "Maximum 150 words."
    ),
    "fr": (
        "Vous êtes un expert en vente de services web. Générez un email d'ouverture "
        "pour {business_name}, une entreprise de {niche} à {location}. "
        "Signaux d'opportunité: {pain_points}. "
        "L'email doit être professionnel, personnalisé et non agressif. "
        "Maximum 150 mots."
    ),
}
```

**HeuristicClient fallback** (sin LLM):
```python
def generate_opening_angle(self, lead_name: str, niche: str, pain_points: list) -> str:
    pain_text = ", ".join(pain_points[:3]) if pain_points else "presencia digital"
    return (
        f"Hola {lead_name},\n\n"
        f"Me puse en contacto porque noté que su negocio de {niche} "
        f"podría beneficiarse de mejorar su {pain_text}.\n\n"
        f"Me encantaría mostrarle cómo podemos ayudar. "
        f"¿Tienen 15 minutos esta semana?\n\n"
        f"Atentamente,\n[Tu nombre]"
    )
```

**Pain points desde scoring breakdowns**:
```python
def extract_pain_points(lead: Lead) -> List[str]:
    """Extrae pain points del scoring breakdown para el email."""
    points = []
    for b in lead.score_breakdown:
        if b.category == ScoreCategory.DIGITAL_NEGLECT and b.points > 0:
            points.append(b.evidence)
    return points[:5]  # Top 5
```

**En HTML reporte**: Sección "Opening Angle" por lead (colapsable), con el borrador.

**En closing menu**: "Generar email borrador (top lead)" → imprime en terminal con syntax highlighting.

---

### 4.5 InputGuardian

**Decisión**: IN

**Archivo nuevo**: `src/micompaweb/domain/rules/guardian.py`

```python
class InputGuardian:
    """Validación y normalización de inputs del usuario."""

    CHAIN_KEYWORDS = [
        "walmart", "costco", "soriana", "chedraui", "oxxo",
        "sanborns", "farmacias", "7-eleven", "burger king",
        "mcdonalds", "starbucks", "subway", "kfc",
        "home depot", "lowes", "ikea",
    ]

    @staticmethod
    def normalize_niche(input_str: str, available: List[str]) -> str:
        """Fuzzy match del input a nichos disponibles.

        Usa difflib.get_close_matches() con cutoff=0.6.
        Si no hay match: retorna input limpio (lower, strip).
        """
        cleaned = input_str.lower().strip()
        matches = difflib.get_close_matches(cleaned, available, n=1, cutoff=0.6)
        return matches[0] if matches else cleaned

    @staticmethod
    def normalize_location(input_str: str) -> str:
        """Normaliza ubicación: strip, title case."""
        return input_str.strip().title()

    @staticmethod
    def disqualify_chain(business_name: str) -> bool:
        """True si el nombre contiene keyword de cadena."""
        name_lower = business_name.lower()
        return any(kw in name_lower for kw in InputGuardian.CHAIN_KEYWORDS)

    @staticmethod
    def validate_coherence(niche: str, location: str, language: str) -> CoherenceResult:
        """Valida coherencia de la búsqueda completa."""
        # Integración con InputValidationAgent (feature 4.1)
        # Retorna: is_valid, warnings, suggestions
```

**`src/micompaweb/domain/rules/__init__.py`**:
```python
from .guardian import InputGuardian

__all__ = ["InputGuardian"]
```

**Wire en pipeline**:
- Después del Wizard / parsing de CLI flags
- Antes de `ProspectingService.execute()`
- Si `disqualify_chain()` → marcar lead como disqualified
- Si `validate_coherence()` falla → warning al usuario, opción de proceder o corregir

---

### 4.6 Review Sentiment

**Decisión**: IN (simplificado para implementación rápida, pero feature del producto final)

**Modelo**: `ReviewSentiment` ya existe en V1.1 con: `common_themes`, `digital_mentions`, `digital_opportunities`, `quotable_testimonials`, `average_sentiment`.

**Archivo nuevo**: `src/micompaweb/infrastructure/adapters/llm/sentiment_adapter.py`

```python
class SentimentAdapter:
    """Análisis de sentimiento de reviews vía LLMChain + heurística."""

    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client

    async def analyze(self, reviews: List[str], niche: str) -> ReviewSentiment:
        """Analiza reviews y retorna sentimiento estructurado."""
        if self.llm.is_available():
            return await self._llm_analysis(reviews, niche)
        return self._heuristic_analysis(reviews, niche)

    async def _llm_analysis(self, reviews: List[str], niche: str) -> ReviewSentiment:
        """Análisis con LLM (Groq/Ollama)."""
        # Prompt: "Analiza estas reviews de un negocio de {niche}.
        #          Identifica: 1) Temas comunes 2) Menciones de problemas digitales
        #          3) Oportunidades digitales 4) Testimonial citable
        #          Reviews: {reviews_text}"
        ...

    def _heuristic_analysis(self, reviews: List[str], niche: str) -> ReviewSentiment:
        """Fallback: keyword matching."""
        DIGITAL_KEYWORDS = [
            "website", "web", "página", "pagina", "online",
            "internet", "app", "aplicación", "aplicacion",
            "reserva", "booking", "digital", "redes",
        ]
        # Contar menciones de keywords digitales en reviews
        # Extraer testimonials de reviews >4 estrellas
        # average_sentiment: positivo si rating alto, negativo si bajo
        ...
```

**Wire en pipeline**:
- Nueva etapa en `ProspectingService`: `_analyze_sentiment()` entre audit y vigency
- Solo se ejecuta si hay reviews textuales disponibles (Google Place Details)
- Si no hay reviews textuales: `lead.review_sentiment` queda `None`
- Costo: ~$0.005/lead con Groq (si disponible), $0 con heurística

---

### 4.7 Competitor Comparison

**Decisión**: IN (completo — los modelos ya existen, implementar resultado final)

**Modelo**: `CompetitorComparison` ya existe con: `competitor_name`, `competitor_rating`, `competitor_reviews`, `has_website`, `advantage`.

**Archivo nuevo**: `src/micompaweb/application/services/competitor_service.py`

```python
class CompetitorService:
    """Análisis de competencia entre leads de la misma búsqueda."""

    def analyze(self, leads: List[Lead]) -> None:
        """Para cada lead, identifica competidores cercanos y ventajas."""
        for lead in leads:
            competitors = self._find_nearby_competitors(lead, leads, max_count=5)
            lead.competitor_comparison = [
                CompetitorComparison(
                    competitor_name=c.business_name,
                    competitor_rating=c.rating,
                    competitor_reviews=c.review_count,
                    has_website=c.website_status != WebsiteStatus.NONE,
                    advantage=self._calculate_advantage(lead, c),
                )
                for c in competitors
            ]
            lead.competitor_count = len([l for l in leads if l.id != lead.id])

    def _find_nearby_competitors(
        self, lead: Lead, all_leads: List[Lead], max_count: int = 5
    ) -> List[Lead]:
        """Encuentra competidores más cercanos por distancia geográfica."""
        if lead.latitude is None or lead.longitude is None:
            return []
        # haversine distance sort, top max_count
        ...

    def _calculate_advantage(self, lead: Lead, competitor: Lead) -> str:
        """Determina ventaja competitiva del lead vs competidor."""
        if lead.website_status == WebsiteStatus.NONE and competitor.website_status != WebsiteStatus.NONE:
            return "Competidor tiene web, el lead no"
        if not lead.audit.ssl_valid and competitor.audit.ssl_valid:
            return "Competidor tiene HTTPS, el lead no"
        return "Sin ventaja clara"
```

**Wire en pipeline**:
- En `ProspectingService`: nueva etapa `_analyze_competitors()` después de discovery, antes de audit
- Los leads de la misma búsqueda son naturalmente competidores entre sí
- Alimenta directamente a `_score_sales_readiness()` (Competitor Density criterion)

---

### 4.8 Google Places Details Completos

**Decisión**: IN

**Archivo a modificar**: `src/micompaweb/infrastructure/adapters/lead_sources/google_places_source.py`

**Mejoras en `_parse_details()`**:

```python
async def _parse_details(self, place: dict, niche: str) -> Lead:
    """Convierte Place Details completo a Lead."""

    # Photo references (top 5)
    photo_refs = [
        p.get("photo_reference") or p.get("name", "")
        for p in place.get("photos", [])[:5]
    ]

    # Opening hours
    opening_hours = place.get("opening_hours", {})
    periods = opening_hours.get("periods", [])

    # Business status real
    business_status = place.get("businessStatus", "OPERATIONAL")
    is_operational = business_status == "OPERATIONAL"

    # is_claimed: verificar si hay author_attributions en reviews
    reviews = place.get("reviews", [])
    is_claimed = any(
        r.get("authorAttribution") is not None
        for r in reviews
    ) if reviews else True  # Asumir claimed si no hay reviews

    # Owner response rate real
    owner_responses = sum(
        1 for r in reviews
        if r.get("reply", {}).get("text")
    )
    owner_response_rate = owner_responses / len(reviews) if reviews else 0.0

    # GBP Health completo
    gbp_health = GBPHealth(
        score=self._calculate_gbp_score(place),
        has_photos=len(place.get("photos", [])) > 0,
        has_hours="openingHours" in place or "opening_hours" in place,
        has_description=bool(place.get("editorialSummary", {}).get("text")),
        has_categories=len(place.get("types", [])) > 1,
        has_phone=bool(place.get("nationalPhoneNumber") or place.get("internationalPhoneNumber")),
        has_website=bool(place.get("websiteUri")),
        has_attributes=len(place.get("attributions", [])) > 0,
        is_claimed=is_claimed,
        photos_count=len(place.get("photos", [])),
    )

    return Lead(
        ...
        gbp_health=gbp_health,
        owner_response_rate=owner_response_rate,
        photo_references=photo_refs,       # Nuevo campo en Lead
        business_status=business_status,    # Nuevo campo
        ...
    )
```

**Nuevos campos en Lead**:
- `photo_references: List[str] = []` — references a fotos de Google
- `business_status: str = "OPERATIONAL"` — OPERATIONAL, CLOSED_TEMPORARILY, CLOSED_PERMANENTLY

---

### 4.9 Market Health Score Robusto

**Decisión**: IN

**Problema actual**: `market_health_score = no_website_pct * 100` — demasiado simple.

**Fórmula RECARGADO**:
```python
def _calculate_market_health(self, leads: List[Lead]) -> float:
    """Market health multi-factor (0-100).

    HIGH = mercado con mucho abandono digital = mucha oportunidad.
    """
    if not leads:
        return 0.0

    # Factor 1: Porcentaje sin website (35%)
    no_website_pct = sum(
        1 for l in leads if l.website_status == "none"
    ) / len(leads)

    # Factor 2: Tasa de fallos SSL (20%)
    leads_with_site = [l for l in leads if l.website_url]
    ssl_failure_rate = (
        sum(1 for l in leads_with_site if not l.audit.ssl_valid)
        / len(leads_with_site)
    ) if leads_with_site else 0.0

    # Factor 3: Falta de tracking (15%)
    tracking_adoption_rate = (
        sum(1 for l in leads_with_site
            if l.audit.has_meta_pixel or l.audit.has_gtm or l.audit.has_analytics)
        / len(leads_with_site)
    ) if leads_with_site else 0.0

    # Factor 4: Contenido desactualizado (15%)
    audited_leads = [l for l in leads_with_site if l.vigency]
    content_outdated_pct = (
        sum(1 for l in audited_leads if l.vigency.is_outdated)
        / len(audited_leads)
    ) if audited_leads else 0.0

    # Factor 5: Densidad competitiva normalizada (15%)
    avg_competitors = sum(l.competitor_count for l in leads) / len(leads)
    avg_competitor_normalized = min(avg_competitors / 30.0, 1.0)  # Cap at 30 = 1.0

    # Weighted sum
    market_health = (
        no_website_pct * 0.35 +
        ssl_failure_rate * 0.20 +
        (1 - tracking_adoption_rate) * 0.15 +
        content_outdated_pct * 0.15 +
        avg_competitor_normalized * 0.15
    ) * 100

    return round(market_health, 1)
```

**Nuevos campos en ProjectStats**:
```python
class ProjectStats(BaseModel):
    # ... existing fields ...
    ssl_failure_rate: float = 0.0
    tracking_adoption_rate: float = 0.0
    content_outdated_pct: float = 0.0
    avg_competitor_count: float = 0.0
```

---

## 5. Infraestructura Adicional

### 5.1 Tenacity Retries

**Archivo nuevo**: `src/micompaweb/infrastructure/retry.py`

```python
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import httpx

# Retry para API calls externas
api_retry = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type((httpx.TimeoutException, httpx.ConnectError)),
    reraise=True,
)

# Retry para web scraping (más tolerante)
scrape_retry = retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=2, min=2, max=30),
    retry=retry_if_exception_type((
        httpx.TimeoutException, httpx.ConnectError, httpx.HTTPStatusError
    )),
    reraise=True,
)
```

**Wire**: Decorar `GooglePlacesSource.search()`, `SimpleAuditor.audit()`, `GroqClient.analyze_vigency()` con `@api_retry` o `@scrape_retry`.

### 5.2 Structlog

**Archivo nuevo**: `src/micompaweb/infrastructure/logging/setup.py`

```python
import structlog

def setup_logging(level: str = "INFO", json_logs: bool = False):
    """Configura structlog para logs estructurados."""
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer() if json_logs
                else structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        cache_logger_on_first_use=True,
    )

def get_logger(name: str = "micompaweb"):
    return structlog.get_logger(name)
```

**Wire**: `setup_logging()` al inicio de `cli.py`. Cada service/adaptor usa `get_logger()`.

### 5.3 Mobile Checker (en SimpleAuditor)

Añadir al `SimpleAuditor.audit()`:
```python
# Detectar viewport meta tag
viewport = soup.find("meta", attrs={"name": "viewport"})
mobile_friendly = (
    viewport is not None
    and "width=device-width" in (viewport.get("content", "") or "")
)
```

### 5.4 Contact Extractor (en SimpleAuditor)

Enhance el email extraction existente + añadir:
```python
# Phone regex (México/internacional)
phone_pattern = re.compile(
    r'(?:\+?52\s?)?(?:\(?\d{2,3}\)?[\s.-]?)?\d{3,4}[\s.-]?\d{4}'
)

# Social links
social_patterns = {
    "facebook": re.compile(r'facebook\.com/[\w.-]+'),
    "instagram": re.compile(r'instagram\.com/[\w.-]+'),
    "whatsapp": re.compile(r'wa\.me/[\d]+'),
    "tiktok": re.compile(r'tiktok\.com/@[\w.-]+'),
}
```

### 5.5 Doctor Mejorado

Añadir al `doctor` command:
- Connectivity test: `httpx.get("https://maps.googleapis.com", timeout=5)`
- LLM provider test: verificar Ollama running + Groq key validity
- Cache stats: `cache.get_stats()` (entries, hits, size)
- Install recommendations: "Para auditoría avanzada: `pip install micompaweb[audit]`"

---

## 6. Pipeline RECARGADO (Orden Final)

```
┌─────────────────────────────────────────────────────────────────┐
│                     miCompaWeb M1 Pipeline                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  INPUT LAYER                                                     │
│  ┌──────────┐    ┌──────────────┐    ┌──────────────┐           │
│  │  Wizard   │───→│  InputAgent  │───→│ InputGuardian│           │
│  │(Question) │    │ (LLM 1-2B)  │    │ (normalize)  │           │
│  └──────────┘    └──────────────┘    └──────────────┘           │
│                                            │                     │
│  PIPELINE                                  ▼                     │
│  ┌──────────────┐    ┌────────────────────────┐                │
│  │  Discovery    │───→│  Competitor Analysis    │                │
│  │(LeadSource)  │    │  (CompetitorService)    │                │
│  └──────────────┘    └────────────────────────┘                │
│         │                        │                               │
│         ▼                        ▼                               │
│  ┌──────────────┐    ┌────────────────────────┐                │
│  │  Web Audit    │───→│  Sentiment Analysis     │                │
│  │(WebAuditor)   │    │  (SentimentAdapter)     │                │
│  └──────────────┘    └────────────────────────┘                │
│         │                        │                               │
│         ▼                        ▼                               │
│  ┌──────────────┐    ┌────────────────────────┐                │
│  │ Vigency Check │───→│  Scoring (3D Matrix)   │                │
│  │(LLMChain)    │    │  (ScoringService)        │                │
│  └──────────────┘    └────────────────────────┘                │
│         │                        │                               │
│         ▼                        ▼                               │
│  ┌──────────────┐    ┌────────────────────────┐                │
│  │ Revenue Est.  │───→│  Export (HTML/CSV/JSON) │                │
│  │(RevenueCalc)  │    │  (Exporter adapters)     │                │
│  └──────────────┘    └────────────────────────┘                │
│                                 │                                │
│  OUTPUT LAYER                   ▼                                │
│  ┌──────────────────────────────────────┐                       │
│  │  Closing Menu + TUI Summary          │                       │
│  │  (Rich Tables, Email Draft, NocoDB)  │                       │
│  └──────────────────────────────────────┘                       │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**Estado de proyecto por etapa**:
```python
class PipelineStage(str, Enum):
    WIZARD = "wizard"
    VALIDATION = "validation"
    DISCOVERY = "discovery"
    COMPETITORS = "competitors"
    AUDIT = "audit"
    SENTIMENT = "sentiment"
    VIGENCY = "vigency"
    SCORING = "scoring"
    REVENUE = "revenue"
    EXPORT = "export"
```

---

## 7. Migración a WSL

### 7.1 Preparación

1. Copiar RECARGADO.md a V1.1 root: `miCompaWeb-V1.1/miCompaWeb-RECARGADO.md`
2. WSL Ubuntu-24.04 ya está corriendo
3. `migrate-to-wsl.sh` ya existe en V1.1

### 7.2 Ejecución

```bash
# En WSL
bash /mnt/c/Users/mr-k0/OneDrive\ -\ Université\ de\ Poitiers/Documents/00\ Proyectos\ Web/miCompaWeb-V1.1/migrate-to-wsl.sh
```

### 7.3 Verificación Post-Migración

```bash
cd ~/projects/micompaweb
source .venv/bin/activate

# 1. Imports críticos
python -c "import crawl4ai; print('Crawl4AI: OK')"
python -c "import playwright; print('Playwright: OK')"

# 2. Doctor
micompaweb doctor

# 3. Pipeline con fixtures
micompaweb m1 --fixture

# 4. Tests
pytest tests/ -v
```

### 7.4 Desarrollo en WSL + VS Code

```bash
cd ~/projects/micompaweb
code .  # VS Code con WSL extension
```

---

## 8. Resumen de Archivos

### Archivos nuevos

| Archivo | Propósito |
|---------|-----------|
| `src/micompaweb/app/wizard.py` | Wizard interactivo (Questionary) |
| `src/micompaweb/app/input_agent.py` | Agente LLM 1-2B para validación semántica |
| `src/micompaweb/presentation/tui/welcome.py` | ASCII art + branding |
| `src/micompaweb/presentation/tui/progress.py` | Rich Live display |
| `src/micompaweb/presentation/tui/panels.py` | Lead cards, summary, error panels |
| `src/micompaweb/presentation/tui/tables.py` | Rich Tables con colores por tier |
| `src/micompaweb/presentation/tui/closing_menu.py` | Menú post-scan |
| `src/micompaweb/presentation/tui/styles.py` | Constantes de estilo |
| `src/micompaweb/presentation/tui/__init__.py` | Package init |
| `src/micompaweb/domain/rules/guardian.py` | InputGuardian |
| `src/micompaweb/domain/rules/__init__.py` | Re-exports |
| `src/micompaweb/infrastructure/adapters/llm/sentiment_adapter.py` | Sentiment analysis |
| `src/micompaweb/infrastructure/adapters/llm/prompts.py` | Prompt templates multi-idioma |
| `src/micompaweb/infrastructure/retry.py` | Tenacity retry decorators |
| `src/micompaweb/infrastructure/logging/setup.py` | Structlog config |
| `src/micompaweb/infrastructure/cost_guardian.py` | CostGuardian (DAILY_LIMIT) |
| `src/micompaweb/infrastructure/deps_manager.py` | DependencyManager |
| `src/micompaweb/application/services/competitor_service.py` | CompetitorService |

### Archivos a modificar

| Archivo | Cambio |
|---------|--------|
| `pyproject.toml` | Añadir questionary, tenacity, structlog; limpiar extras |
| `src/micompaweb/app/cli.py` | Integrar Wizard, TUI, closing menu |
| `src/micompaweb/domain/models/scoring.py` | ScoreCategory: SALES_READINESS; nuevos weights/max |
| `src/micompaweb/domain/models/lead.py` | Añadir photo_references, business_status |
| `src/micompaweb/domain/models/project.py` | ProjectStats: nuevos campos market health |
| `src/micompaweb/application/services/scoring_service.py` | Rewrite 3 dimensiones |
| `src/micompaweb/application/services/prospecting_service.py` | Añadir etapas: competitors, sentiment; rewire market health |
| `src/micompaweb/infrastructure/adapters/audit/simple_auditor.py` | Mobile + contact enhancement |
| `src/micompaweb/infrastructure/adapters/lead_sources/google_places_source.py` | Details completos |
| `src/micompaweb/infrastructure/adapters/llm/heuristic_client.py` | Outreach templates |
| `tests/unit/test_scoring_service.py` | Update para 3 dimensiones |
| `tests/conftest.py` | Actualizar fixtures |

---

## 9. Phases de Implementación

| Phase | Contenido | Semanas |
|-------|-----------|---------|
| **Foundation** | Scoring 3D, InputGuardian, Deps cleanup, Tenacity, Structlog | 1-2 |
| **UX + Wizard** | TUI completa, Wizard + InputAgent, Closing menu | 3-4 |
| **Intelligence** | CompetitorService, SentimentAdapter, Places details completos | 5-6 |
| **Revenue + Email** | CostGuardian, Outreach templates, Market health robusto | 7-8 |
| **WSL Migration** | Migrar, Crawl4AI, Playwright, QA final | 9 |

---

*Fin del documento — miCompaWeb RECARGADO v1.0*