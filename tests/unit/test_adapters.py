"""Tests for infrastructure adapters."""

import pytest

from micompaweb.infrastructure.adapters.lead_sources import (
    FixtureSource,
    CachedSource,
    LeadSourceManager,
)
from micompaweb.infrastructure.adapters.llm import HeuristicClient
from micompaweb.domain.models import WebsiteStatus


class TestFixtureSource:
    """Test cases for FixtureSource."""

    @pytest.fixture
    def source(self):
        return FixtureSource(seed=42)

    @pytest.mark.asyncio
    async def test_search_returns_leads(self, source):
        """Should return fixture leads."""
        leads = await source.search("plomeros", "CDMX", max_results=10)

        assert len(leads) == 10
        assert all(l.source == "fixture" for l in leads)

    @pytest.mark.asyncio
    async def test_leads_have_varied_website_status(self, source):
        """Should have mix of website statuses."""
        leads = await source.search("test", "City", max_results=100)

        statuses = {l.website_status for l in leads}
        assert len(statuses) > 1  # Should have variety

    @pytest.mark.asyncio
    async def test_leads_are_deterministic_with_seed(self):
        """Same seed should give same results."""
        source1 = FixtureSource(seed=123)
        source2 = FixtureSource(seed=123)

        leads1 = await source1.search("plomeros", "CDMX", max_results=5)
        leads2 = await source2.search("plomeros", "CDMX", max_results=5)

        assert [l.business_name for l in leads1] == [l.business_name for l in leads2]

    def test_estimate_cost_is_zero(self, source):
        """Fixture source should be free."""
        cost = source.estimate_cost(100)
        assert cost.usd_amount == 0.0


class TestCachedSource:
    """Test cases for CachedSource."""

    @pytest.fixture
    def mock_underlying(self):
        """Create mock underlying source."""
        from tests.conftest import MockLeadSource
        from micompaweb.domain.models import Lead

        return MockLeadSource([
            Lead(id="1", business_name="Test 1", niche="test"),
            Lead(id="2", business_name="Test 2", niche="test"),
        ])

    @pytest.fixture
    def mock_cache(self):
        """Create mock cache."""
        from tests.conftest import MockCache
        return MockCache()

    @pytest.mark.asyncio
    async def test_uses_cache_when_available(self, mock_underlying, mock_cache):
        """Should return cached results if available."""
        from micompaweb.domain.models import Lead

        # Pre-populate cache (key format: search_<source_name>_<niche>_<location>_<radius>_<max_results>_<language>)
        cached_lead = Lead(id="cached", business_name="Cached", niche="test")
        await mock_cache.set("search_mock_test_location_10000_10_es", [cached_lead])

        cached_source = CachedSource(mock_underlying, mock_cache)

        leads = await cached_source.search("test", "location", max_results=10)

        # Should get cached result
        assert any(l.id == "cached" for l in leads)

    @pytest.mark.asyncio
    async def test_saves_to_cache_when_not_cached(self, mock_underlying, mock_cache):
        """Should save results to cache."""
        cached_source = CachedSource(mock_underlying, mock_cache)

        await cached_source.search("test", "new location", max_results=10)

        # Should have called set on cache
        assert len(mock_cache.set_calls) > 0


class TestLeadSourceManager:
    """Test cases for LeadSourceManager."""

    @pytest.fixture
    def manager(self):
        return LeadSourceManager(max_cost_per_operation=2.00)

    @pytest.mark.asyncio
    async def test_tries_sources_in_priority_order(self, manager):
        """Should try sources by priority."""
        from tests.conftest import MockLeadSource
        from micompaweb.domain.models import Lead

        source1 = MockLeadSource([])  # Empty, will fail
        source2 = MockLeadSource([Lead(id="1", business_name="Test", niche="test")])

        manager.add_source(source1, priority=1)
        manager.add_source(source2, priority=2)

        leads = await manager.search("test", "location", max_results=10)

        assert len(leads) > 0

    @pytest.mark.asyncio
    async def test_raises_when_no_source_available(self, manager):
        """Should raise NoSourceAvailable when all fail."""
        from tests.conftest import MockLeadSource

        manager.add_source(MockLeadSource([]), priority=1)

        from micompaweb.application.ports import NoSourceAvailable
        with pytest.raises(NoSourceAvailable):
            await manager.search("test", "location", max_results=10)


class TestHeuristicClient:
    """Test cases for HeuristicClient."""

    @pytest.fixture
    def client(self):
        return HeuristicClient()

    @pytest.mark.asyncio
    async def test_analyzes_old_copyright_as_outdated(self, client):
        """Old copyright should be detected as outdated."""
        result = await client.analyze_vigency(
            content="Some content",
            website_url="https://example.com",
            copyright_year=2020,  # Old
        )

        assert result.is_outdated is True
        assert result.confidence > 0.5
        assert "2020" in result.reason

    @pytest.mark.asyncio
    async def test_analyzes_recent_copyright_as_fresh(self, client):
        """Recent copyright should not be outdated."""
        from datetime import datetime

        result = await client.analyze_vigency(
            content="Some content",
            website_url="https://example.com",
            copyright_year=datetime.now().year,
        )

        assert result.is_outdated is False

    def test_is_always_available(self, client):
        """Heuristic client should always be available."""
        assert client.is_available() is True

    def test_is_local(self, client):
        """Heuristic client should be considered local."""
        assert client.is_local is True

    def test_estimate_cost_is_zero(self, client):
        """Heuristic should be free."""
        assert client.estimate_cost(1000, 500) == 0.0


class TestCachedAuditor:
    """Tests for CachedAuditor wrapper."""

    @pytest.fixture
    def mock_cache(self):
        from tests.conftest import MockCache
        return MockCache()

    @pytest.fixture
    def mock_audit_result(self):
        from micompaweb.application.ports.web_auditor import (
            TechnicalAudit, SSLResult, TrackingResult, TechStackResult, ContactResult
        )
        return TechnicalAudit(
            ssl=SSLResult(is_valid=True),
            tracking=TrackingResult(has_meta_pixel=True, has_gtm=False, has_analytics=False),
            tech_stack=TechStackResult(detected_platforms=["WordPress"], cms="WordPress"),
            contacts=ContactResult(emails=["info@test.com"], phones=[], social_links={}),
            mobile_friendly=True,
            load_time_ms=250,
            copyright_year=2021,
            page_title="Test Site",
        )

    @pytest.mark.asyncio
    async def test_calls_underlying_auditor_on_cache_miss(self, mock_cache, mock_audit_result):
        from unittest.mock import AsyncMock
        from micompaweb.infrastructure.adapters.audit.cached_auditor import CachedAuditor

        mock_auditor = AsyncMock()
        mock_auditor.audit = AsyncMock(return_value=mock_audit_result)
        cached = CachedAuditor(mock_auditor, mock_cache)

        result = await cached.audit("https://example.com")

        mock_auditor.audit.assert_called_once_with("https://example.com")
        assert result.page_title == "Test Site"

    @pytest.mark.asyncio
    async def test_returns_cached_result_on_hit(self, mock_cache, mock_audit_result):
        from unittest.mock import AsyncMock
        from micompaweb.infrastructure.adapters.audit.cached_auditor import (
            CachedAuditor, _audit_to_dict
        )

        url = "https://example.com"
        import hashlib
        key = f"audit_{hashlib.md5(url.encode()).hexdigest()}"
        await mock_cache.set(key, _audit_to_dict(mock_audit_result))

        mock_auditor = AsyncMock()
        cached = CachedAuditor(mock_auditor, mock_cache)

        result = await cached.audit(url)

        mock_auditor.audit.assert_not_called()
        assert result.page_title == "Test Site"
        assert result.tracking.has_meta_pixel is True

    @pytest.mark.asyncio
    async def test_saves_to_cache_after_audit(self, mock_cache, mock_audit_result):
        from unittest.mock import AsyncMock
        from micompaweb.infrastructure.adapters.audit.cached_auditor import CachedAuditor

        mock_auditor = AsyncMock()
        mock_auditor.audit = AsyncMock(return_value=mock_audit_result)
        cached = CachedAuditor(mock_auditor, mock_cache)

        await cached.audit("https://example.com")

        assert len(mock_cache.set_calls) == 1

    def test_auditor_name_prefixed(self, mock_cache):
        from unittest.mock import MagicMock
        from micompaweb.infrastructure.adapters.audit.cached_auditor import CachedAuditor

        inner = MagicMock()
        inner.auditor_name = "simple_httpx_bs4"
        cached = CachedAuditor(inner, mock_cache)

        assert cached.auditor_name == "cached_simple_httpx_bs4"

    def test_requires_browser_delegates(self, mock_cache):
        from unittest.mock import MagicMock
        from micompaweb.infrastructure.adapters.audit.cached_auditor import CachedAuditor

        inner = MagicMock()
        inner.requires_browser = False
        cached = CachedAuditor(inner, mock_cache)

        assert cached.requires_browser is False

    @pytest.mark.asyncio
    async def test_roundtrip_preserves_ssl_expiry(self, mock_cache):
        from datetime import datetime
        from unittest.mock import AsyncMock
        from micompaweb.application.ports.web_auditor import (
            TechnicalAudit, SSLResult
        )
        from micompaweb.infrastructure.adapters.audit.cached_auditor import CachedAuditor

        expiry = datetime(2026, 12, 31, 0, 0, 0)
        audit = TechnicalAudit(ssl=SSLResult(is_valid=True, expiry_date=expiry))

        mock_auditor = AsyncMock()
        mock_auditor.audit = AsyncMock(return_value=audit)
        cached = CachedAuditor(mock_auditor, mock_cache)

        await cached.audit("https://example.com")
        result = await cached.audit("https://example.com")

        assert result.ssl.expiry_date == expiry
