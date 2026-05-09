"""Cached auditor wrapper - evita re-auditar URLs ya vistas en el mismo proyecto."""

import dataclasses
import hashlib
from datetime import datetime

from micompaweb.application.ports.web_auditor import (
    TechnicalAudit,
    SSLResult,
    TrackingResult,
    TechStackResult,
    ContactResult,
)
from micompaweb.application.ports.cache import Cache


class CachedAuditor:
    """Wrapper que añade caché SQLite a cualquier auditor web.

    TTL por defecto: 7 días. Una URL auditada no se re-audita en el mismo
    proyecto durante ese período, reduciendo latencia y carga de red.
    """

    TTL_SECONDS = 7 * 24 * 3600

    def __init__(self, auditor, cache: Cache) -> None:
        self._auditor = auditor
        self._cache = cache

    async def audit(self, url: str) -> TechnicalAudit:
        key = f"audit_{hashlib.md5(url.encode()).hexdigest()}"
        cached = await self._cache.get(key)
        if cached is not None:
            return _audit_from_dict(cached)

        result = await self._auditor.audit(url)
        await self._cache.set(key, _audit_to_dict(result), ttl_seconds=self.TTL_SECONDS)
        return result

    async def check_ssl(self, url: str) -> SSLResult:
        return await self._auditor.check_ssl(url)

    @property
    def auditor_name(self) -> str:
        return f"cached_{self._auditor.auditor_name}"

    @property
    def requires_browser(self) -> bool:
        return self._auditor.requires_browser


def _audit_to_dict(audit: TechnicalAudit) -> dict:
    d = dataclasses.asdict(audit)
    ssl = d.get("ssl") or {}
    if ssl.get("expiry_date") is not None:
        ssl["expiry_date"] = ssl["expiry_date"].isoformat()
    return d


def _audit_from_dict(d: dict) -> TechnicalAudit:
    ssl_d = d.get("ssl") or {}
    expiry = ssl_d.get("expiry_date")
    if expiry and isinstance(expiry, str):
        expiry = datetime.fromisoformat(expiry)

    tracking_d = d.get("tracking") or {}
    tech_d = d.get("tech_stack") or {}
    contacts_d = d.get("contacts") or {}

    return TechnicalAudit(
        ssl=SSLResult(
            is_valid=ssl_d.get("is_valid", False),
            expiry_date=expiry,
            issuer=ssl_d.get("issuer"),
            error_message=ssl_d.get("error_message"),
        ),
        tracking=TrackingResult(
            has_meta_pixel=tracking_d.get("has_meta_pixel", False),
            has_gtm=tracking_d.get("has_gtm", False),
            has_analytics=tracking_d.get("has_analytics", False),
            has_linkedin_pixel=tracking_d.get("has_linkedin_pixel", False),
            has_tiktok_pixel=tracking_d.get("has_tiktok_pixel", False),
        ),
        tech_stack=TechStackResult(
            detected_platforms=tech_d.get("detected_platforms", []),
            cms=tech_d.get("cms"),
            framework=tech_d.get("framework"),
            hosting=tech_d.get("hosting"),
        ),
        contacts=ContactResult(
            emails=contacts_d.get("emails", []),
            phones=contacts_d.get("phones", []),
            social_links=contacts_d.get("social_links", {}),
            has_contact_form=contacts_d.get("has_contact_form", False),
            has_whatsapp=contacts_d.get("has_whatsapp", False),
        ),
        mobile_friendly=d.get("mobile_friendly", False),
        load_time_ms=d.get("load_time_ms"),
        copyright_year=d.get("copyright_year"),
        page_title=d.get("page_title"),
        meta_description=d.get("meta_description"),
    )
