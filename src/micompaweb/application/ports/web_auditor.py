"""Web auditor protocol - contrato para auditores de sitios web."""

from typing import Protocol
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Dict


class WebAuditError(Exception):
    """Error durante auditoría web."""
    pass


@dataclass
class SSLResult:
    """Resultado de auditoría SSL."""
    is_valid: bool
    expiry_date: Optional[datetime] = None
    issuer: Optional[str] = None
    error_message: Optional[str] = None


@dataclass
class TrackingResult:
    """Resultado de detección de tracking."""
    has_meta_pixel: bool
    has_gtm: bool
    has_analytics: bool
    has_linkedin_pixel: bool = False
    has_tiktok_pixel: bool = False


@dataclass
class TechStackResult:
    """Resultado de detección de tech stack."""
    detected_platforms: List[str]
    cms: Optional[str] = None
    framework: Optional[str] = None
    hosting: Optional[str] = None


@dataclass
class ContactResult:
    """Resultado de extracción de contactos."""
    emails: List[str]
    phones: List[str]
    social_links: Dict[str, str]
    has_contact_form: bool = False
    has_whatsapp: bool = False


@dataclass
class TechnicalAudit:
    """Resultado completo de auditoría técnica."""
    ssl: SSLResult = None  # type: ignore
    tracking: TrackingResult = None  # type: ignore
    tech_stack: TechStackResult = None  # type: ignore
    contacts: ContactResult = None  # type: ignore
    mobile_friendly: bool = False
    load_time_ms: Optional[int] = None
    copyright_year: Optional[int] = None
    page_title: Optional[str] = None
    meta_description: Optional[str] = None

    def __post_init__(self):
        """Set default values for complex fields."""
        if self.ssl is None:
            self.ssl = SSLResult(is_valid=False)
        if self.tracking is None:
            self.tracking = TrackingResult(False, False, False)
        if self.tech_stack is None:
            self.tech_stack = TechStackResult([])
        if self.contacts is None:
            self.contacts = ContactResult([], [], {})


class WebAuditor(Protocol):
    """Contrato para auditores de sitios web.

    Permite múltiples implementaciones:
    - SimpleAuditor: httpx + BeautifulSoup (ligero)
    - Crawl4Auditor: crawl4ai (completo pero pesado)
    - MockAuditor: para testing
    """

    async def audit(self, url: str) -> TechnicalAudit:
        """Audita un sitio web completo.

        Args:
            url: URL del sitio a auditar

        Returns:
            Resultado completo de auditoría

        Raises:
            WebAuditError: Si la auditoría falla
        """
        ...

    async def check_ssl(self, url: str) -> SSLResult:
        """Verifica certificado SSL."""
        ...

    async def check_tracking(self, url: str) -> TrackingResult:
        """Detecta scripts de tracking."""
        ...

    async def detect_tech_stack(self, url: str) -> TechStackResult:
        """Detecta tecnologías utilizadas."""
        ...

    async def extract_contacts(self, url: str) -> ContactResult:
        """Extrae información de contacto."""
        ...

    @property
    def auditor_name(self) -> str:
        """Nombre del implementador."""
        ...

    @property
    def requires_browser(self) -> bool:
        """Si requiere Chrome/Chromium."""
        ...