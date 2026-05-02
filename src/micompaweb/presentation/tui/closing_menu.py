"""Closing menu - menu post-scan con questionary."""

import os
import webbrowser
from typing import Optional
from pathlib import Path

import questionary
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

from micompaweb.domain.models.lead import Lead
from micompaweb.domain.models.project import Project

console = Console()


class ClosingMenu:
    """Menu post-scan con acciones disponibles."""

    OPTIONS = [
        ("📊  Ver Top 10 leads", "view_leads"),
        ("🌐  Abrir informe HTML", "open_html"),
        ("📤  Exportar CSV", "export_csv"),
        ("📧  Generar email borrador (top lead)", "email_top"),
        ("📧  Generar emails batch (all hot)", "email_batch"),
        ("💰  Ver Revenue Dashboard", "revenue_dashboard"),
        ("🚪  Salir", "exit"),
    ]

    def __init__(
        self,
        project: Project,
        leads: list[Lead],
        project_dir: Path,
    ):
        self.project = project
        self.leads = leads
        self.project_dir = project_dir

    def show(self) -> str:
        """Muestra menu y retorna accion seleccionada."""
        # Header
        total = len(self.leads)
        ultra = sum(1 for l in self.leads if l.priority.value == "ULTRA HOT")
        hot = sum(1 for l in self.leads if l.priority.value == "HOT")
        warm = sum(1 for l in self.leads if l.priority.value == "WARM")
        cold = sum(1 for l in self.leads if l.priority.value == "COLD")

        header = (
            f"[bold green]✅ Analisis completado:[/] [cyan]{self.project.slug}[/]\n\n"
            f"[bold]{total}[/] leads | "
            f"[bold red]{ultra}[/] ULTRA HOT | "
            f"[bold yellow]{hot}[/] HOT | "
            f"[bold green]{warm}[/] WARM | "
            f"[dim]{cold}[/] COLD"
        )

        if self.project.market_health_score:
            header += f"\n[bold]Market Health:[/] {self.project.market_health_score}/100"
        if self.project.total_estimated_revenue_loss_high:
            rev = f"${self.project.total_estimated_revenue_loss_low:,.0f}-${self.project.total_estimated_revenue_loss_high:,.0f}"
            header += f"\n[bold]Revenue estimado:[/] {rev} USD/mes"

        console.print()
        console.print(Panel(header, title="[bold]Resumen miCompaWeb[/]", border_style="green", box=box.ROUNDED))
        console.print()

        choice = questionary.select(
            "Que deseas hacer?",
            choices=[opt[0] for opt in self.OPTIONS],
            default=self.OPTIONS[0][0],
        ).ask()

        for label, action in self.OPTIONS:
            if label == choice:
                return action

        return "exit"

    def view_leads(self) -> None:
        """Muestra tabla de top 10 leads."""
        from .result_table import ResultTable, LeadRow

        sorted_leads = sorted(self.leads, key=lambda l: l.pepita_score, reverse=True)[:10]

        rows = []
        for i, lead in enumerate(sorted_leads, 1):
            signals = []
            if lead.website_status.value == "none":
                signals.append("Sin web")
            elif lead.website_status.value == "http_only":
                signals.append("Sin SSL")
            if lead.competitor_count and lead.competitor_count > 5:
                signals.append(f"{lead.competitor_count} competidores")
            if lead.review_count and lead.review_count > 10:
                signals.append(f"{lead.review_count} reviews")

            rows.append(LeadRow(
                rank=i,
                name=lead.business_name,
                priority_tier=lead.priority.value,
                score=lead.pepita_score,
                signals=signals,
                phone=lead.phone,
                email=lead.email,
                revenue_estimate=f"${getattr(lead.revenue_loss, 'monthly_mid', 0):,.0f}" if hasattr(lead, 'revenue_loss') else "",
            ))

        table = ResultTable()
        console.print(table.render(rows, title=f"Top 10 - {self.project.slug}"))

    def open_html(self) -> None:
        """Abre informe HTML en navegador si existe."""
        html_file = self.project_dir / "exports" / f"{self.project.slug}_report.html"
        if not html_file.exists():
            html_file = self.project_dir / "informe.html"

        if html_file.exists():
            webbrowser.open(f"file://{html_file.absolute()}")
            console.print(f"[green]Abriendo:[/] {html_file}")
        else:
            console.print("[yellow]Informe HTML no encontrado. Ejecuta export primero.[/]")

    def export_csv(self) -> None:
        """Exporta leads a CSV."""
        from micompaweb.infrastructure.adapters.exports.csv_exporter import CSVExporter
        from micompaweb.application.ports.exporter import ExportConfig

        out_dir = self.project_dir / "exports"
        out_dir.mkdir(parents=True, exist_ok=True)

        exporter = CSVExporter()
        config = ExportConfig(
            output_dir=out_dir,
            filename_prefix=self.project.slug,
            format="csv",
            language="es",
        )
        result = exporter.export(self.leads, self.project, config)
        console.print(f"[green]CSV exportado:[/] {result.file_path} ({result.records_exported} registros)")

    def email_top(self) -> None:
        """Genera email para top lead."""
        from micompaweb.application.services.email_generator import EmailGenerator

        sorted_leads = sorted(self.leads, key=lambda l: l.pepita_score, reverse=True)
        if not sorted_leads:
            console.print("[yellow]No hay leads para generar email.[/]")
            return

        top = sorted_leads[0]
        signals = self._signals_for_lead(top)

        gen = EmailGenerator()
        email = gen.generate(
            business_name=top.business_name,
            niche=self.project.config.niche,
            signals=signals,
            language=self.project.config.target_language,
        )

        console.print()
        console.print(Panel(
            f"[bold yellow]Asunto:[/] {email.subject}\n\n{email.body}",
            title=f"[bold]Email: {top.business_name}[/]",
            border_style="bright_blue",
            box=box.ROUNDED,
        ))

        # Guardar
        email_dir = self.project_dir / "emails"
        email_dir.mkdir(parents=True, exist_ok=True)
        safe = top.business_name.replace(" ", "_").replace("/", "_")[:30]
        path = email_dir / f"borrador_{safe}.txt"
        path.write_text(f"Asunto: {email.subject}\n\n{email.body}", encoding="utf-8")
        console.print(f"[dim]Guardado en:[/] {path}")

    def email_batch(self) -> None:
        """Genera emails batch para leads HOT+."""
        from micompaweb.application.services.email_generator import EmailGenerator

        hot_leads = [l for l in self.leads if l.priority.value in ("ULTRA HOT", "HOT")]
        if not hot_leads:
            console.print("[yellow]No hay leads HOT o ULTRA HOT para batch.[/]")
            return

        gen = EmailGenerator()
        emails = []
        for lead in hot_leads:
            signals = self._signals_for_lead(lead)
            email = gen.generate(
                business_name=lead.business_name,
                niche=self.project.config.niche,
                signals=signals,
                language=self.project.config.target_language,
            )
            emails.append(email)

        email_dir = self.project_dir / "emails"
        email_dir.mkdir(parents=True, exist_ok=True)

        for lead, email in zip(hot_leads, emails):
            safe = lead.business_name.replace(" ", "_").replace("/", "_")[:30]
            path = email_dir / f"borrador_{safe}.txt"
            path.write_text(f"Asunto: {email.subject}\n\n{email.body}", encoding="utf-8")

        console.print(f"[green]{len(emails)} emails generados en:[/] {email_dir}")

    def revenue_dashboard(self) -> None:
        """Muestra dashboard de revenue."""
        table = Table(
            title=f"[bold cyan]Revenue Dashboard: {self.project.slug}[/]",
            header_style="bold bright_white",
            border_style="bright_blue",
            box=box.ROUNDED,
        )
        table.add_column("Metrica", style="cyan")
        table.add_column("Valor", style="bold")
        table.add_column("Nota", style="dim")

        total_leads = len(self.leads)
        hot_plus = sum(1 for l in self.leads if l.priority.value in ("ULTRA HOT", "HOT"))
        table.add_row("Leads totales", str(total_leads), "")
        table.add_row("Leads HOT+", str(hot_plus), f"{hot_plus/total_leads*100:.0f}% del total")
        table.add_row("Revenue bajo", f"${self.project.total_estimated_revenue_loss_low:,.0f}", "Escenario conservador")
        table.add_row("Revenue alto", f"${self.project.total_estimated_revenue_loss_high:,.0f}", "Escenario optimista")

        avg_rev = (self.project.total_estimated_revenue_loss_low + self.project.total_estimated_revenue_loss_high) / 2
        table.add_row("Revenue medio", f"${avg_rev:,.0f}", "Promedio ponderado")

        console.print()
        console.print(table)
        console.print()

        # Proyeccion si se cierra 1 lead
        close_rate = 0.05  # 5% close rate
        projected = avg_rev * close_rate
        console.print(f"[dim]Proyeccion (5% close rate):[/] [bold green]${projected:,.0f}[/] USD/mes potencial")

    def _signals_for_lead(self, lead: Lead) -> list:
        """Extrae signals acionables de un lead para email."""
        signals = []
        if lead.website_status.value == "none":
            signals.append("Sin sitio web detectado")
        elif lead.website_status.value == "http_only":
            signals.append("Sitio web sin HTTPS")
        if lead.audit and not getattr(lead.audit, "ssl_valid", True):
            signals.append("Certificado SSL invalido")
        if not any([getattr(lead.audit, "has_meta_pixel", False),
                    getattr(lead.audit, "has_gtm", False),
                    getattr(lead.audit, "has_analytics", False)]):
            signals.append("Sin tracking de conversiones")
        if lead.review_count and lead.review_count > 20:
            signals.append(f"{lead.review_count} reviews en Google")
        if lead.rating and lead.rating >= 4.0:
            signals.append(f"Excelente reputacion ({lead.rating}/5)")
        return signals or ["Presencia digital optimizable"]
