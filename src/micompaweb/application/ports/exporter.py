"""Exporter protocol - contrato para exportadores de datos."""

from typing import Optional, Protocol, List
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime

from micompaweb.domain.models import Lead, Project


class ExportError(Exception):
    """Error durante exportación."""
    pass


@dataclass
class ExportResult:
    """Resultado de exportación."""
    file_path: Path
    format: str
    records_exported: int
    file_size_bytes: int
    duration_ms: int
    checksum: str


@dataclass
class ExportConfig:
    """Configuración para exportación."""
    output_dir: Path
    filename_prefix: str = ""
    include_disqualified: bool = False
    format: str = "html"  # html, csv, json, xlsx
    language: str = "es"
    template_name: Optional[str] = None


class Exporter(Protocol):
    """Contrato para exportadores de leads/proyectos.

    Implementaciones:
    - HTMLReportExporter: Informe premium HTML
    - CSVExporter: CSV plano
    - JSONExporter: JSON completo
    - ExcelExporter: XLSX (requiere pandas/openpyxl)
    """

    async def export(
        self,
        leads: List[Lead],
        project: Project,
        config: ExportConfig,
    ) -> ExportResult:
        """Exporta leads a formato específico.

        Args:
            leads: Lista de leads a exportar
            project: Metadata del proyecto
            config: Configuración de exportación

        Returns:
            Resultado de la exportación

        Raises:
            ExportError: Si la exportación falla
        """
        ...

    @property
    def format_name(self) -> str:
        """Nombre del formato (html, csv, json, etc.)."""
        ...

    @property
    def file_extension(self) -> str:
        """Extensión de archivo sin punto."""
        ...

    @property
    def requires_template(self) -> bool:
        """Si requiere templates Jinja2."""
        ...

    def estimate_size(self, num_leads: int) -> int:
        """Estima tamaño en bytes."""
        ...