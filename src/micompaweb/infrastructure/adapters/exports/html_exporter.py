"""HTML report exporter - informe premium ejecutivo."""

import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import List

from jinja2 import Environment, PackageLoader, select_autoescape, BaseLoader

from micompaweb.domain.models import Lead, Project
from micompaweb.application.ports.exporter import (
    Exporter,
    ExportResult,
    ExportConfig,
    ExportError,
)


class HTMLReportExporter:
    """Exporta informe HTML premium con diseño ejecutivo.

    Usa Jinja2 templates con diseño responsive.
    """

    def __init__(self):
        self._env = None

    @property
    def env(self):
        if self._env is None:
            try:
                self._env = Environment(
                    loader=PackageLoader("micompaweb", "templates/m1"),
                    autoescape=select_autoescape(["html", "xml"]),
                )
            except Exception:
                self._env = Environment(
                    loader=BaseLoader(),
                    autoescape=select_autoescape(["html", "xml"]),
                )
        return self._env

    async def export(
        self,
        leads: List[Lead],
        project: Project,
        config: ExportConfig,
    ) -> ExportResult:
        """Genera informe HTML."""
        try:
            template = self.env.get_template("informe-premium.html.j2")
        except Exception:
            # Fallback a template inline si no existe
            template = self.env.from_string(self._get_fallback_template())

        # Preparar datos para template
        hot_leads = [l for l in leads if l.priority in ["ULTRA HOT", "HOT"]]
        warm_leads = [l for l in leads if l.priority == "WARM"]

        context = {
            "project": project,
            "leads": leads,
            "hot_leads": hot_leads,
            "warm_leads": warm_leads,
            "generated_at": datetime.now(),
            "language": config.language,
        }

        html_content = template.render(**context)

        # Guardar archivo
        output_path = config.output_dir / f"{config.filename_prefix}_report.html"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(html_content, encoding="utf-8")

        # Calcular checksum
        content_hash = hashlib.md5(html_content.encode()).hexdigest()

        return ExportResult(
            file_path=output_path,
            format="html",
            records_exported=len(leads),
            file_size_bytes=len(html_content.encode()),
            duration_ms=0,  # TODO: Track timing
            checksum=content_hash,
        )

    def _get_fallback_template(self) -> str:
        """Template inline de fallback."""
        return '''
<!DOCTYPE html>
<html lang="{{ language }}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Informe - {{ project.config.niche }} - {{ project.config.location }}</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #333;
            background: #f5f5f5;
        }
        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            border-radius: 12px;
            margin-bottom: 30px;
        }
        .header h1 { font-size: 2.5em; margin-bottom: 10px; }
        .header p { opacity: 0.9; }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .stat-card {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .stat-card h3 { font-size: 2em; color: #667eea; }
        .stat-card label { color: #666; font-size: 0.9em; }
        .lead-section { margin-bottom: 30px; }
        .lead-section h2 {
            color: #333;
            border-bottom: 3px solid #667eea;
            padding-bottom: 10px;
            margin-bottom: 20px;
        }
        .lead-card {
            background: white;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 15px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .lead-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }
        .lead-name { font-size: 1.3em; font-weight: bold; color: #333; }
        .priority-badge {
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 0.85em;
            font-weight: bold;
        }
        .priority-ultra-hot { background: #ff4757; color: white; }
        .priority-hot { background: #ff6348; color: white; }
        .priority-warm { background: #ffa502; color: white; }
        .priority-cold { background: #747d8c; color: white; }
        .score { font-size: 1.5em; font-weight: bold; color: #667eea; }
        .meta { color: #666; font-size: 0.9em; margin-top: 5px; }
        .revenue { color: #2ed573; font-weight: bold; }
        table {
            width: 100%;
            background: white;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #eee;
        }
        th { background: #667eea; color: white; font-weight: 600; }
        tr:hover { background: #f8f9fa; }
        .footer {
            text-align: center;
            padding: 20px;
            color: #666;
            font-size: 0.9em;
            margin-top: 40px;
        }
        @media print {
            body { background: white; }
            .lead-card { break-inside: avoid; }
        }
    </style>
</head>
<body>
    <div class="container">
        <header class="header">
            <h1>📊 Informe de Prospección</h1>
            <p>{{ project.config.niche|title }} en {{ project.config.location }}</p>
            <p style="margin-top: 10px; opacity: 0.8;">
                Generado: {{ generated_at.strftime('%Y-%m-%d %H:%M') }}
            </p>
        </header>

        <div class="stats-grid">
            <div class="stat-card">
                <h3>{{ project.stats.total_leads }}</h3>
                <label>Total Leads</label>
            </div>
            <div class="stat-card">
                <h3 style="color: #ff4757;">{{ project.stats.ultra_hot_leads }}</h3>
                <label>ULTRA HOT 🔥</label>
            </div>
            <div class="stat-card">
                <h3 style="color: #ff6348;">{{ project.stats.hot_leads }}</h3>
                <label>HOT ⚡</label>
            </div>
            <div class="stat-card">
                <h3 style="color: #ffa502;">{{ project.stats.warm_leads }}</h3>
                <label>WARM 💡</label>
            </div>
        </div>

        {% if hot_leads %}
        <section class="lead-section">
            <h2>🔥 Leads Prioritarios (HOT/ULTRA HOT)</h2>
            {% for lead in hot_leads[:10] %}
            <div class="lead-card">
                <div class="lead-header">
                    <span class="lead-name">{{ lead.business_name }}</span>
                    <span class="priority-badge priority-{{ lead.priority.lower().replace(' ', '-') }}">
                        {{ lead.priority }}
                    </span>
                </div>
                <div class="score">{{ lead.pepita_score }} pts</div>
                <div class="meta">
                    ⭐ {{ lead.rating }} | 📝 {{ lead.review_count }} reviews
                    {% if lead.website_status == "none" %}| 🚫 Sin web{% endif %}
                    {% if lead.phone %}| 📞 {{ lead.phone }}{% endif %}
                </div>
                {% if lead.revenue_loss.monthly_mid > 0 %}
                <div class="meta revenue">
                    💰 Pérdida estimada: ${{ "%.0f"|format(lead.revenue_loss.monthly_mid) }}/mes
                </div>
                {% endif %}
            </div>
            {% endfor %}
        </section>
        {% endif %}

        <section class="lead-section">
            <h2>📋 Todos los Leads</h2>
            <table>
                <thead>
                    <tr>
                        <th>Negocio</th>
                        <th>Prioridad</th>
                        <th>Score</th>
                        <th>Reviews</th>
                        <th>Web</th>
                        <th>Contacto</th>
                    </tr>
                </thead>
                <tbody>
                    {% for lead in leads %}
                    <tr>
                        <td><strong>{{ lead.business_name }}</strong></td>
                        <td>
                            <span class="priority-badge priority-{{ lead.priority.lower().replace(' ', '-') }}">
                                {{ lead.priority }}
                            </span>
                        </td>
                        <td>{{ lead.pepita_score }}</td>
                        <td>{{ lead.review_count }}</td>
                        <td>
                            {% if lead.website_status == "none" %}🚫{%
                            elif lead.website_status == "http_only" %}⚠️{%
                            else %}✅{% endif %}
                        </td>
                        <td>{{ lead.phone or lead.email or "-" }}</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </section>

        <footer class="footer">
            <p>Generado con miCompaWeb v1.1</p>
            <p>Metodología: Score basado en autoridad local, abandono digital y disposición comercial</p>
        </footer>
    </div>
</body>
</html>
'''

    @property
    def format_name(self) -> str:
        return "html"

    @property
    def file_extension(self) -> str:
        return "html"

    @property
    def requires_template(self) -> bool:
        return True

    def estimate_size(self, num_leads: int) -> int:
        return num_leads * 1500  # ~1.5KB por lead aprox
