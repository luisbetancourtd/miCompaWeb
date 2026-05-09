"""miCompaWeb v1.1 - AI-powered CLI for web agency prospecting.

This package provides tools for:
- Discovering local businesses with web presence gaps
- Auditing websites for technical issues
- Scoring leads based on opportunity signals
- Generating executive reports

Example:
    >>> from micompaweb.application.services import ProspectingService
    >>> service = ProspectingService(...)
    >>> leads = await service.execute(project)
"""

__version__ = "1.1.0"
__author__ = "El Compa Digital"
__email__ = "contact@micompaweb.dev"
__license__ = "MIT"

from micompaweb.domain.models import Lead, Project, ScoringResult

__all__ = [
    "Lead",
    "Project",
    "ScoringResult",
]