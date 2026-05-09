# miCompaWeb v1.1 🎯

> **AI-powered CLI for web agency prospecting & automation**

Transforma Google Maps y la web pública en un pipeline de oportunidades priorizadas. Versión 1.1 con arquitectura limpia, offline-first, y Docker-ready.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Docker Ready](https://img.shields.io/badge/docker-ready-blue.svg)](https://www.docker.com/)

---

## ✨ Features

- **🏗️ Arquitectura Ports & Adapters**: Fácil de testear, extender y mantener
- **📦 Empaquetado Modular**: Instala solo lo que necesitas
- **💰 Offline-First**: Modo fixture y caché persistente (SQLite)
- **📊 Scoring Explicable**: Cada punto trazable con evidencia
- **🐳 Docker Ready**: Contenedor optimizado para producción
- **🔧 Múltiples Fuentes**: Google Places + Fixtures + Cache
- **💸 Control de Costos**: Límites diarios y estimaciones antes de ejecutar

---

## 🚀 Quick Start

### Opción 1: Instalación Directa (Recomendado)

```bash
# Usando pip (instalación básica ~5MB)
pip install micompaweb

# Con todas las extras (~150MB)
pip install micompaweb[full]
```

### Opción 2: Docker

```bash
# Clonar repositorio
git clone https://github.com/elcompadigital/micompaweb.git
cd micompaweb

# Ejecutar con Docker Compose
docker-compose run --rm micompaweb m1 --fixture

# O construir imagen local
docker build -t micompaweb .
docker run -it --rm micompaweb m1 --fixture
```

### Opción 3: Desarrollo

```bash
# Usando uv (recomendado)
uv venv
uv pip install -e ".[full,dev]"

# Usando pip
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[full,dev]"
```

---

## 📋 Usage

### Modo Fixture (Gratis, Offline)

```bash
# Genera 50 leads de prueba sin costo API
micompaweb m1 --niche plomeros --location "Ciudad de México" --fixture

# O con prompts interactivos
micompaweb m1 --fixture
```

### Modo Normal (con Google Places API)

```bash
# Configurar API key
export GOOGLE_PLACES_API_KEY="your-key-here"

# Ejecutar prospección
micompaweb m1 --niche dentistas --location Guadalajara --depth estandar
```

### Verificar Entorno

```bash
micompaweb doctor
```

---

## 🏗️ Arquitectura

```
src/micompaweb/
├── domain/              # Lógica de negocio pura
│   ├── models/          # Entidades (Lead, Project, ScoreBreakdown)
│   ├── rules/           # Reglas de negocio (disqualification, etc.)
│   └── services/        # Servicios de dominio
│
├── application/         # Casos de uso
│   ├── ports/           # Interfaces/Protocolos (LeadSource, WebAuditor, etc.)
│   └── services/        # Servicios de aplicación (ProspectingService, ScoringService)
│
├── infrastructure/      # Implementaciones concretas
│   ├── adapters/        # Adaptadores externos (GooglePlacesSource, SQLiteCache)
│   ├── cache/           # Caché (SQLite)
│   └── config/          # Configuración
│
└── app/                 # CLI y entry points
    └── cli.py
```

---

## 🔌 Ports (Interfaces)

| Port | Implementaciones |
|------|-----------------|
| `LeadSource` | `GooglePlacesSource`, `FixtureSource`, `CachedSource` |
| `WebAuditor` | `SimpleAuditor`, `Crawl4Auditor` |
| `LLMClient` | `GroqClient`, `OllamaClient`, `HeuristicClient` |
| `Cache` | `SQLiteCache` |
| `Exporter` | `HTMLReportExporter`, `CSVExporter`, `JSONExporter` |

---

## 💰 Cost Control

| Operación | Costo Est. | Descripción |
|-----------|-----------|-------------|
| `--fixture` | **$0** | Datos de prueba, ideal para desarrollo |
| `--offline` | **$0** | Usa caché existente |
| 100 leads | **~$0.50** | Via Google Places API |
| 500 leads | **~$2.50** | Via Google Places API |

Configura límites en `.env`:
```env
MAX_DAILY_COST_USD=2.00
ENABLE_COST_TRACKING=true
```

---

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=micompaweb --cov-report=html

# Run specific tests
pytest tests/unit/test_scoring.py
pytest tests/integration/test_places_source.py
```

---

## 📁 Project Structure

```
projects/
└── {slug}/
    ├── cache.db           # SQLite cache (offline access)
    ├── project.json       # Metadata
    ├── leads.json         # Datos completos
    └── exports/
        ├── informe.html   # Reporte ejecutivo
        ├── leads.csv      # CSV para análisis
        └── leads.json     # JSON completo
```

---

## 🔧 Configuración

Copia `.env.example` a `.env` y configura:

```bash
# Required
GOOGLE_PLACES_API_KEY=your_key

# Optional LLM
GROQ_API_KEY=your_key
OLLAMA_BASE_URL=http://localhost:11434

# Optional Integrations
NOCODB_URL=http://localhost:8080
NOCODB_API_TOKEN=token
```

---

## 🐳 Docker Compose

```yaml
# Solo miCompaWeb
docker-compose run --rm micompaweb m1 --fixture

# Con NocoDB (dashboard)
docker-compose --profile with-nocodb up

# Con Ollama (LLM local)
docker-compose --profile with-ollama up

# Todo junto
docker-compose --profile with-nocodb --profile with-ollama up
```

---

## 📊 Roadmap v1.2

- [ ] **M2 ANALYZE**: SEO analysis & competitor research
- [ ] **M3 DESIGN**: Generate copy & site structure
- [ ] **M4 PROPOSAL**: Generate commercial proposal
- [ ] **Web Dashboard**: React frontend for leads management

---

## 🤝 Contributing

1. Fork the repo
2. Create feature branch (`git checkout -b feature/amazing`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing`)
5. Open Pull Request

---

## 📜 License

MIT © El Compa Digital

---

<p align="center">
  <sub>Built with ❤️ for web agencies and freelancers</sub>
</p>