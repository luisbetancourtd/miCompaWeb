"""Pytest configuration and shared fixtures."""

import pytest
from datetime import datetime
from pathlib import Path

from micompaweb.domain.models import (
    Lead,
    WebsiteStatus,
    PriorityTier,
    Project,
    ProjectConfig,
    TechnicalAudit,
    VigencyResult,
    ScoreBreakdown,
    ScoreCategory,
)
from micompaweb.application.ports.web_auditor import SSLResult
from micompaweb.application.ports import (
    LeadSource,
    WebAuditor,
    LLMClient,
    Cache,
    Exporter,
)


# =============================================================================
# Domain Model Fixtures
# =============================================================================

@pytest.fixture
def sample_lead():
    """Sample lead for testing."""
    return Lead(
        id="test_lead_001",
        external_id="google_place_123",
        source="google_places",
        business_name="Test Business",
        category="plumber",
        niche="plomeros",
        phone="+52 55 1234 5678",
        email="test@example.com",
        website_url="https://example.com",
        website_status=WebsiteStatus.EXISTS,
        address="Calle Test 123",
        city="Ciudad de México",
        country="Mexico",
        rating=4.5,
        review_count=50,
        has_recent_reviews=True,
        competitor_count=15,
    )


@pytest.fixture
def sample_lead_no_website():
    """Sample lead without website."""
    return Lead(
        id="test_lead_002",
        external_id="google_place_456",
        source="google_places",
        business_name="No Web Business",
        category="dentist",
        niche="dentistas",
        phone="+52 55 8765 4321",
        website_status=WebsiteStatus.NONE,
        city="Guadalajara",
        rating=4.8,
        review_count=120,
        has_recent_reviews=True,
    )


@pytest.fixture
def sample_project():
    """Sample project for testing."""
    config = ProjectConfig(
        niche="plomeros",
        location="Ciudad de México",
        depth="estandar",
        max_leads=50,
        target_language="es",
    )
    return Project(
        slug="plomeros-cdmx-20240101",
        config=config,
    )


@pytest.fixture
def sample_audit():
    """Sample technical audit."""
    return TechnicalAudit(
        ssl=SSLResult(is_valid=True),
        has_meta_pixel=False,
        has_gtm=True,
        has_analytics=True,
        mobile_friendly=True,
        technology_stack=["WordPress", "PHP"],
        emails_found=["contact@example.com"],
        copyright_year=2024,
    )


@pytest.fixture
def sample_vigency_outdated():
    """Sample vigency result - outdated."""
    return VigencyResult(
        is_outdated=True,
        outdated_confidence=0.85,
        outdated_reason="Copyright year 2021 indicates old content",
        outdated_snippet="© 2021 All rights reserved",
        evidence=["Old copyright", "Stale content"],
        provider_used="groq",
    )


@pytest.fixture
def sample_vigency_fresh():
    """Sample vigency result - not outdated."""
    return VigencyResult(
        is_outdated=False,
        outdated_confidence=0.90,
        outdated_reason="Recent content detected",
        evidence=["Copyright 2024", "Fresh posts"],
        provider_used="groq",
    )


@pytest.fixture
def sample_score_breakdowns():
    """Sample score breakdowns."""
    return [
        ScoreBreakdown(
            criterion="no_website",
            category=ScoreCategory.DIGITAL_NEGLECT,
            points=50,
            max_points=50,
            evidence="Sin presencia web",
            confidence=1.0,
        ),
        ScoreBreakdown(
            criterion="review_volume",
            category=ScoreCategory.AUTHORITY,
            points=30,
            max_points=30,
            evidence="50 reviews",
            confidence=1.0,
        ),
    ]


# =============================================================================
# Port Mock Fixtures
# =============================================================================

class MockLeadSource:
    """Mock lead source for testing."""

    def __init__(self, leads=None):
        self._leads = leads or []
        self.search_calls = []

    async def search(self, niche, location, radius_meters=10000, max_results=100, language="es"):
        self.search_calls.append({
            "niche": niche,
            "location": location,
            "radius_meters": radius_meters,
            "max_results": max_results,
        })
        return self._leads[:max_results]

    async def get_details(self, external_id, language="es"):
        for lead in self._leads:
            if lead.external_id == external_id:
                return lead
        return None

    def health_check(self):
        from micompaweb.application.ports.lead_source import SourceHealth
        return SourceHealth(is_healthy=True, message="Mock source healthy")

    def estimate_cost(self, num_results):
        from micompaweb.application.ports.lead_source import CostEstimate
        return CostEstimate(usd_amount=0.0, requests_count=0, source_name="mock")

    @property
    def source_name(self):
        return "mock"

    @property
    def supports_caching(self):
        return True


class MockWebAuditor:
    """Mock web auditor for testing."""

    def __init__(self, audit_result=None):
        self._audit_result = audit_result
        self.audit_calls = []

    async def audit(self, url):
        self.audit_calls.append(url)
        return self._audit_result or self._default_audit()

    async def check_ssl(self, url):
        from micompaweb.application.ports.web_auditor import SSLResult
        return SSLResult(is_valid=True)

    async def check_tracking(self, url):
        from micompaweb.application.ports.web_auditor import TrackingResult
        return TrackingResult(False, False, False)

    async def detect_tech_stack(self, url):
        from micompaweb.application.ports.web_auditor import TechStackResult
        return TechStackResult([])

    async def extract_contacts(self, url):
        from micompaweb.application.ports.web_auditor import ContactResult
        return ContactResult([], [], {})

    def _default_audit(self):
        from micompaweb.domain.models import TechnicalAudit
        return TechnicalAudit(ssl_valid=True)

    @property
    def auditor_name(self):
        return "mock_auditor"

    @property
    def requires_browser(self):
        return False


class MockLLMClient:
    """Mock LLM client for testing."""

    def __init__(self, vigency_result=None):
        self._vigency_result = vigency_result
        self.analyze_calls = []

    async def analyze_vigency(self, content, website_url, copyright_year=None):
        self.analyze_calls.append({
            "content": content,
            "website_url": website_url,
            "copyright_year": copyright_year,
        })
        return self._vigency_result or self._default_vigency()

    async def generate_opening_angle(self, lead_name, niche, pain_points):
        return f"Hola {lead_name}, vi que necesitan ayuda con su presencia digital."

    def is_available(self):
        return True

    @property
    def provider_name(self):
        return "mock"

    @property
    def is_local(self):
        return True

    def estimate_cost(self, input_tokens, output_tokens):
        return 0.0

    def _default_vigency(self):
        from micompaweb.application.ports.llm_client import VigencyResult, LLMProvider
        return VigencyResult(
            is_outdated=None,
            confidence=0.0,
            reason="",
            snippet="",
            evidence=[],
            provider_used=LLMProvider.HEURISTIC,
            cost_usd=0.0,
        )


class MockCache:
    """Mock cache for testing."""

    def __init__(self):
        self._data = {}
        self.get_calls = []
        self.set_calls = []

    async def get(self, key):
        self.get_calls.append(key)
        return self._data.get(key)

    async def set(self, key, value, ttl_seconds=None):
        self.set_calls.append({"key": key, "ttl": ttl_seconds})
        self._data[key] = value

    async def exists(self, key):
        return key in self._data

    async def delete(self, key):
        if key in self._data:
            del self._data[key]
            return True
        return False

    async def clear(self):
        self._data.clear()

    async def get_stats(self):
        return {
            "total_entries": len(self._data),
            "expired_entries": 0,
            "active_entries": len(self._data),
            "total_hits": 0,
            "db_size_bytes": 0,
        }

    def make_key(self, *parts):
        return "_".join(parts)


@pytest.fixture
def mock_lead_source():
    """Mock lead source fixture."""
    return MockLeadSource


@pytest.fixture
def mock_web_auditor():
    """Mock web auditor fixture."""
    return MockWebAuditor


@pytest.fixture
def mock_llm_client():
    """Mock LLM client fixture."""
    return MockLLMClient


@pytest.fixture
def mock_cache():
    """Mock cache fixture."""
    return MockCache()


# =============================================================================
# M2 Anti-Bot Stack Fixtures
# =============================================================================

@pytest.fixture(scope="session")
def cached_embedder():
    """Session-scoped FastEmbed model to avoid reloading (~20-30s each)."""
    from micompaweb.infrastructure.m2.embedder import LocalEmbedder
    embedder = LocalEmbedder()
    return embedder


@pytest.fixture
def local_embedder(cached_embedder):
    """Per-test embedder that reuses the cached model."""
    return cached_embedder
