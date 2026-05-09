"""Application ports (interfaces/contracts)."""

from .lead_source import LeadSource, LeadSourceError, NoSourceAvailable
from .web_auditor import WebAuditor, WebAuditError
from .llm_client import LLMClient, LLMError, VigencyResult
from .cache import Cache, CacheError
from .exporter import Exporter, ExportError, ExportConfig

__all__ = [
    "LeadSource",
    "LeadSourceError",
    "NoSourceAvailable",
    "WebAuditor",
    "WebAuditError",
    "LLMClient",
    "LLMError",
    "VigencyResult",
    "Cache",
    "CacheError",
    "Exporter",
    "ExportError",
    "ExportConfig",
]