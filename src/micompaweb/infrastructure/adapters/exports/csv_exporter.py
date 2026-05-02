"""CSV exporter - datos planos para análisis."""

import csv
import hashlib
from pathlib import Path
from datetime import datetime
from typing import List
from io import StringIO

from micompaweb.domain.models import Lead, Project
from micompaweb.application.ports.exporter import (
    Exporter,
    ExportResult,
    ExportConfig,
    ExportError,
)


class CSVExporter:
    """Exporta leads a CSV para análisis en Excel/Sheets."""

    async def export(
        self,
        leads: List[Lead],
        project: Project,
        config: ExportConfig,
    ) -> ExportResult:
        """Genera CSV con leads."""
        output = StringIO()
        writer = csv.writer(output)

        # Headers
        headers = [
            "business_name",
            "priority",
            "pepita_score",
            "rating",
            "review_count",
            "website_status",
            "phone",
            "email",
            "address",
            "city",
            "maps_url",
            "revenue_loss_monthly_low",
            "revenue_loss_monthly_mid",
            "revenue_loss_monthly_high",
            "ssl_valid",
            "has_tracking",
            "is_outdated",
            "created_at",
        ]
        writer.writerow(headers)

        # Data rows
        for lead in leads:
            has_tracking = any([
                lead.audit.has_meta_pixel,
                lead.audit.has_gtm,
                lead.audit.has_analytics,
            ])

            row = [
                lead.business_name,
                lead.priority,
                lead.pepita_score,
                lead.rating,
                lead.review_count,
                lead.website_status.value,
                lead.phone or "",
                lead.email or "",
                lead.address or "",
                lead.city or "",
                lead.maps_url,
                round(lead.revenue_loss.monthly_low, 2),
                round(lead.revenue_loss.monthly_mid, 2),
                round(lead.revenue_loss.monthly_high, 2),
                lead.audit.ssl_valid,
                has_tracking,
                lead.vigency.is_outdated or False,
                lead.created_at.isoformat(),
            ]
            writer.writerow(row)

        # Write to file
        output_path = config.output_dir / f"{config.filename_prefix}_leads.csv"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        csv_content = output.getvalue()
        output_path.write_text(csv_content, encoding="utf-8")

        return ExportResult(
            file_path=output_path,
            format="csv",
            records_exported=len(leads),
            file_size_bytes=len(csv_content.encode()),
            duration_ms=0,
            checksum=hashlib.md5(csv_content.encode()).hexdigest(),
        )

    @property
    def format_name(self) -> str:
        return "csv"

    @property
    def file_extension(self) -> str:
        return "csv"

    @property
    def requires_template(self) -> bool:
        return False

    def estimate_size(self, num_leads: int) -> int:
        return num_leads * 500  # ~500 bytes por lead