"""JSON exporter - datos completos serializados."""

import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import List

from micompaweb.domain.models import Lead, Project
from micompaweb.application.ports.exporter import (
    Exporter,
    ExportResult,
    ExportConfig,
    ExportError,
)


class JSONExporter:
    """Exporta leads a JSON con todos los datos."""

    def export(
        self,
        leads: List[Lead],
        project: Project,
        config: ExportConfig,
    ) -> ExportResult:
        """Genera JSON completo."""
        data = {
            "export_metadata": {
                "generated_at": datetime.now().isoformat(),
                "format_version": "1.1.0",
                "total_leads": len(leads),
                "project_slug": project.slug,
            },
            "project": project.model_dump(),
            "leads": [lead.model_dump() for lead in leads],
        }

        json_content = json.dumps(data, indent=2, default=str)

        output_path = config.output_dir / f"{config.filename_prefix}_leads.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json_content, encoding="utf-8")

        return ExportResult(
            file_path=output_path,
            format="json",
            records_exported=len(leads),
            file_size_bytes=len(json_content.encode()),
            duration_ms=0,
            checksum=hashlib.md5(json_content.encode()).hexdigest(),
        )

    @property
    def format_name(self) -> str:
        return "json"

    @property
    def file_extension(self) -> str:
        return "json"

    @property
    def requires_template(self) -> bool:
        return False

    def estimate_size(self, num_leads: int) -> int:
        return num_leads * 3000  # ~3KB por lead (JSON completo)