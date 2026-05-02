# miCompaWeb — CONTEXTO para reanudar sesión

> Última actualización: 2026-04-21
> Estado: Post-migración WSL, listo para implementación Phase 1

---

## Dónde estamos

**Copia de trabajo**: `/home/mr-k/projects/micompaweb/` (WSL Ubuntu-24.04)
**Copia Windows**: `C:\Users\mr-k0\OneDrive - Université de Poitiers\Documents\00 Proyectos Web\miCompaWeb-V1.1\` — YA NO USAR, es solo backup.

**Para empezar a trabajar**:
```bash
cd ~/projects/micompaweb
source .venv/bin/activate
code .   # VS Code con WSL extension
```

---

## Qué se ha hecho

1. **Análisis completo** de V0.1 (miCompaWeb original) y V1.1 (arquitectura hexagonal)
2. **Lectura de 3 documentos de referencia**: problem-solucion.md, propuesta.md, scoring-matrix-propuesta.docx
3. **Evaluación de 9 features** de V0.1 que V1.1 perdió
4. **Creación de miCompaWeb-RECARGADO.md** — especificación técnica completa en raíz del proyecto
5. **Migración a WSL** completada:
   - Archivos copiados (sin .venv, caches)
   - Python 3.12 + venv creado
   - Todas las dependencias instaladas
   - Crawl4AI 0.8.6 + Playwright + Chromium v1208 funcionando
   - Bug `Optional` import corregido en `exporter.py`
   - 47 tests pasando, 0 fallos

---

## Qué falta (Phases de implementación)

### Phase 1: Foundation (Semanas 1-2)
- [ ] Scoring Matrix 3D: Authority 30%, Digital Neglect 45%, Sales Readiness 25% (max 150)
  - Añadir `_score_sales_readiness()` (merge de readiness + opportunity)
  - Añadir criterios nuevos: Local Signals, Tech Obsolete, Mobile Broken, Contact Missing
  - Depth adjustment: exhaustiva=1.0x, estandar=0.95x, rapida=0.90x
  - **Archivos**: `scoring_service.py`, `scoring.py`, `test_scoring_service.py`
- [ ] InputGuardian: `domain/rules/guardian.py`
  - normalize_niche(), normalize_location(), disqualify_chain(), validate_coherence()
- [ ] Deps cleanup: pyproject.toml (añadir questionary, tenacity, structlog; limpiar extras)
- [ ] Tenacity: `infrastructure/retry.py`
- [ ] Structlog: `infrastructure/logging/setup.py`
- [ ] DependencyManager: `infrastructure/deps_manager.py`

### Phase 2: UX + Wizard (Semanas 3-4)
- [ ] Wizard interactivo: `app/wizard.py` (Questionary)
- [ ] InputAgent: `app/input_agent.py` (LLM 1-2B vía Ollama + difflib fallback)
- [ ] TUI completa: `presentation/tui/` (welcome, progress, panels, tables, closing_menu, styles)
- [ ] Integrar TUI callbacks en ProspectingService

### Phase 3: Intelligence (Semanas 5-6)
- [ ] CompetitorService: `application/services/competitor_service.py`
- [ ] SentimentAdapter: `infrastructure/adapters/llm/sentiment_adapter.py`
- [ ] Google Places details completos (photo_refs, business_status, is_claimed real, owner_response_rate)
- [ ] Mobile checker + Contact extractor enhancements en SimpleAuditor

### Phase 4: Revenue + Email (Semanas 7-8)
- [ ] CostGuardian: `infrastructure/cost_guardian.py` (DAILY_LIMIT_USD=2.00)
- [ ] Outreach email templates: `infrastructure/adapters/llm/prompts.py` (es/en/fr)
- [ ] Market health score multi-factor (5 señales ponderadas)
- [ ] Comando configure-niche

### Phase 5: WSL QA
- [ ] Verificar Crawl4AI + Playwright end-to-end
- [ ] micompaweb doctor completo
- [ ] micompaweb m1 --fixture con TUI

---

## Decisiones clave (del usuario)

1. **No es MVP, es producto final por fases** — cada feature se implementa completa o casi completa
2. **Wizard + Agente LLM 1-2B** — valida semánticamente el input (Plumber no se traduce a Plomero automáticamente), difflib como fallback
3. **TUI completa** — Rich LiveDisplay + panels + welcome + progress + closing menu
4. **NocoDB se queda** + sqliteviz como Phase 2 + dashboard propio como Phase 3
5. **Email borrador solo** — nunca auto-envío
6. **Review Sentiment IN** — simplificado pero necesario
7. **Competitor Comparison IN** — con los leads de la misma búsqueda
8. **Market Health multi-factor** — no solo no_website_pct

---

## Arquitectura (no se toca)

```
src/micompaweb/
├── app/                    # CLI
│   └── cli.py              # Typer: m1, doctor
├── domain/                 # Lógica pura
│   ├── models/             # Lead, Scoring, Project, Revenue, Niche
│   └── rules/              # (vacío — InputGuardian va aquí)
├── application/           # Casos de uso
│   ├── ports/              # Protocols: LeadSource, WebAuditor, LLMClient, Cache, Exporter
│   └── services/           # ProspectingService, ScoringService, RevenueService
├── infrastructure/         # Adaptadores
│   ├── adapters/
│   │   ├── audit/          # SimpleAuditor, Crawl4Auditor
│   │   ├── exports/        # HTML, CSV, JSON
│   │   ├── lead_sources/   # GooglePlaces, Fixture, Cached, LeadSourceManager
│   │   └── llm/            # Groq, Ollama, Heuristic, LLMChain
│   ├── cache/              # SQLiteCache
│   ├── config/             # Pydantic Settings
│   └── logging/            # (vacío — structlog va aquí)
└── presentation/           # UI (vacío — TUI va aquí)
```

---

## Scoring Matrix RECARGADO (referencia rápida)

**A. Authority (30%, 0-100)**: Review Volume 0-40, Review Rating 0-30, Local Signals 0-30

**B. Digital Neglect (45%, 0-145)**: No Website +50, SSL +20, Tech Obsolete +15, No Tracking +10, Mobile Broken +15, Contact Missing +10, Content Outdated +25

**C. Sales Readiness (25%, 0-100)**: Active GBP +30, Competitor Density +20, Recent Activity +25, Category Value +25

**Tiers**: ULTRA HOT 120-150 | HOT 80-119 | WARM 50-79 | COLD 25-49 | DISCARD 0-24

**Depth adjustment**: exhaustiva=1.0x, estandar=0.95x, rapida=0.90x

---

## Pipeline RECARGADO

```
Wizard → InputAgent → InputGuardian →
  Discovery → CompetitorAnalysis → WebAudit → SentimentAnalysis → VigencyCheck →
  Scoring(3D) → RevenueEstimation → Export → ClosingMenu → TUI Summary
```

---

## Bugs pendientes

- Coverage al 62% (config exige 80%) — se subirá al implementar nuevas features con tests
- pyproject.toml tiene `exports` como extra pero el nombre correcto es `export` (warning menor en instalación)

---

## Referencia rápida

| Comando | Qué hace |
|---------|----------|
| `source .venv/bin/activate` | Activa el venv |
| `python -m pytest tests/ -v` | Corre tests |
| `micompaweb doctor` | Diagnóstico del entorno |
| `micompaweb m1 --fixture` | Pipeline con datos de prueba |
| `micompaweb m1` | Pipeline completo (necesita API key) |

**Spec completo**: `miCompaWeb-RECARGADO.md` en raíz del proyecto.