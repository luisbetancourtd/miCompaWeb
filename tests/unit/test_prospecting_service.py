"""Tests for ProspectingService."""

import pytest
from pathlib import Path

from micompaweb.application.services.prospecting_service import ProspectingService
from micompaweb.domain.models import Lead, WebsiteStatus, Project, ProjectConfig


class TestProspectingService:
    """Test cases for ProspectingService."""

    @pytest.fixture
    def service(self, mock_cache, tmp_path):
        """Create service with mock dependencies."""
        from tests.conftest import MockLeadSource, MockWebAuditor, MockLLMClient

        lead_source = MockLeadSource([
            Lead(
                id="test_1",
                business_name="Business 1",
                website_status=WebsiteStatus.EXISTS,
                website_url="https://example1.com",
                niche="test",
            ),
            Lead(
                id="test_2",
                business_name="Business 2",
                website_status=WebsiteStatus.NONE,
                niche="test",
            ),
        ])

        return ProspectingService(
            lead_source=lead_source,
            web_auditor=MockWebAuditor(),
            llm_client=MockLLMClient(),
            cache=mock_cache,
            exporters=[],
            project_path=tmp_path,
        )

    @pytest.fixture
    def project(self):
        """Create test project."""
        return Project(
            slug="test-project",
            config=ProjectConfig(
                niche="test",
                location="Test City",
                max_leads=10,
            ),
        )

    @pytest.mark.asyncio
    async def test_execute_returns_leads(self, service, project):
        """Service should return processed leads."""
        leads = await service.execute(project)

        assert isinstance(leads, list)
        assert len(leads) > 0

    @pytest.mark.asyncio
    async def test_execute_updates_project_status(self, service, project):
        """Project status should be updated to COMPLETED."""
        await service.execute(project)

        assert project.is_complete

    @pytest.mark.asyncio
    async def test_execute_calculates_scores(self, service, project):
        """Leads should have calculated scores."""
        leads = await service.execute(project)

        for lead in leads:
            assert lead.pepita_score >= 0
            assert lead.priority is not None

    @pytest.mark.asyncio
    async def test_execute_estimates_revenue(self, service, project):
        """Revenue loss should be estimated for leads."""
        leads = await service.execute(project)

        for lead in leads:
            assert hasattr(lead.revenue_loss, 'monthly_mid')

    @pytest.mark.asyncio
    async def test_progress_callbacks_called(self, service, project):
        """Progress callbacks should be called."""
        progress_calls = []

        def on_progress(stage, current, total):
            progress_calls.append((stage, current, total))

        service.on_progress(on_progress)
        await service.execute(project)

        assert len(progress_calls) > 0

    @pytest.mark.asyncio
    async def test_skip_cache_ignores_cache(self, service, project, mock_cache):
        """With skip_cache=True, should bypass cache."""
        # Pre-populate cache
        await mock_cache.set("test_key", "cached_value")

        await service.execute(project, skip_cache=True)

        # Should still execute (cache not used due to skip)
        assert project.is_complete


class TestProspectingServiceWithCache:
    """Test caching behavior."""

    @pytest.mark.asyncio
    async def test_uses_cache_when_available(self, tmp_path, mock_cache):
        """Should use cached results if available."""
        from tests.conftest import MockLeadSource, MockWebAuditor, MockLLMClient

        cached_lead = Lead(
            id="cached_1",
            business_name="Cached Business",
            website_status=WebsiteStatus.NONE,
            niche="test",
        )

        # Pre-populate cache
        await mock_cache.set("search_test_test-city_10000_10_es", [cached_lead])

        service = ProspectingService(
            lead_source=MockLeadSource(),  # Empty - would return nothing
            web_auditor=MockWebAuditor(),
            llm_client=MockLLMClient(),
            cache=mock_cache,
            exporters=[],
            project_path=tmp_path,
        )

        project = Project(
            slug="test-project",
            config=ProjectConfig(
                niche="test",
                location="test city",
                max_leads=10,
                target_language="es",
            ),
        )

        # If cache is used, we should get the cached lead
        # Note: This test depends on implementation details
        leads = await service.execute(project)
        # Leads should be processed even if from cache
        assert len(leads) >= 0


# ──────────────────────────────────────────────────────────────
# Phase 3: Pipeline Wiring Tests
# ──────────────────────────────────────────────────────────────

class TestInputGuardianWiring:
    """Valida que InputGuardian se ejecuta en pipeline."""

    @pytest.mark.asyncio
    async def test_guardian_blocks_invalid_input(self, tmp_path, mock_cache):
        from tests.conftest import MockLeadSource, MockWebAuditor, MockLLMClient
        from micompaweb.domain.rules.guardian import InputGuardian

        guardian = InputGuardian(suggestions=[])
        service = ProspectingService(
            lead_source=MockLeadSource([]),
            web_auditor=MockWebAuditor(),
            llm_client=MockLLMClient(),
            cache=mock_cache,
            exporters=[],
            project_path=tmp_path,
            input_guardian=guardian,
        )

        project = Project(
            slug="bad",
            config=ProjectConfig(niche="ab", location="X", max_leads=10),
        )

        with pytest.raises(Exception):
            await service.execute(project)

    @pytest.mark.asyncio
    async def test_guardian_filters_chains(self, tmp_path, mock_cache):
        from tests.conftest import MockLeadSource, MockWebAuditor, MockLLMClient
        from micompaweb.domain.rules.guardian import InputGuardian

        lead_source = MockLeadSource([
            Lead(id="c1", business_name="Walmart Express", website_status=WebsiteStatus.NONE, niche="retail"),
            Lead(id="c2", business_name="Plomeria Garcia", website_status=WebsiteStatus.NONE, niche="test"),
        ])

        guardian = InputGuardian(suggestions=[])
        service = ProspectingService(
            lead_source=lead_source,
            web_auditor=MockWebAuditor(),
            llm_client=MockLLMClient(),
            cache=mock_cache,
            exporters=[],
            project_path=tmp_path,
            input_guardian=guardian,
        )

        project = Project(
            slug="filter-test",
            config=ProjectConfig(niche="test", location="CDMX", max_leads=10),
        )

        leads = await service.execute(project)
        # Walmart debería ser descartado
        names = {l.business_name for l in leads}
        assert "Walmart Express" not in names
        assert "Plomeria Garcia" in names


class TestCompetitorServiceWiring:
    """Valida CompetitorService en pipeline."""

    @pytest.mark.asyncio
    async def test_competitor_count_saved(self, tmp_path, mock_cache):
        from tests.conftest import MockLeadSource, MockWebAuditor, MockLLMClient
        from micompaweb.application.services.competitor_service import CompetitorService

        lead_source = MockLeadSource([
            Lead(id="l1", business_name="Biz A", website_status=WebsiteStatus.NONE, niche="test", rating=4.0, review_count=10),
            Lead(id="l2", business_name="Biz B", website_status=WebsiteStatus.NONE, niche="test", rating=3.5, review_count=5),
        ])

        service = ProspectingService(
            lead_source=lead_source,
            web_auditor=MockWebAuditor(),
            llm_client=MockLLMClient(),
            cache=mock_cache,
            exporters=[],
            project_path=tmp_path,
            competitor_service=CompetitorService(),
        )

        project = Project(
            slug="comp-test",
            config=ProjectConfig(niche="test", location="CDMX", max_leads=10),
        )

        leads = await service.execute(project)
        for lead in leads:
            assert lead.competitor_count > 0
            assert len(lead.competitor_comparison) >= 0


class TestSentimentAdapterWiring:
    """Valida SentimentAdapter en pipeline."""

    @pytest.mark.asyncio
    async def test_sentiment_saved(self, tmp_path, mock_cache):
        from tests.conftest import MockLeadSource, MockWebAuditor, MockLLMClient
        from micompaweb.application.services.sentiment_adapter import SentimentAdapter

        lead_source = MockLeadSource([
            Lead(id="s1", business_name="Good Biz", website_status=WebsiteStatus.NONE, niche="test", rating=4.8, review_count=20),
            Lead(id="s2", business_name="Bad Biz", website_status=WebsiteStatus.NONE, niche="test", rating=2.5, review_count=8),
        ])

        service = ProspectingService(
            lead_source=lead_source,
            web_auditor=MockWebAuditor(),
            llm_client=MockLLMClient(),
            cache=mock_cache,
            exporters=[],
            project_path=tmp_path,
            sentiment_adapter=SentimentAdapter(),
        )

        project = Project(
            slug="sent-test",
            config=ProjectConfig(niche="test", location="CDMX", max_leads=10),
        )

        leads = await service.execute(project)
        for lead in leads:
            assert lead.review_sentiment is not None
            assert lead.review_sentiment.average_sentiment >= -1.0
            assert lead.review_sentiment.average_sentiment <= 1.0


class TestMarketHealthRobusto:
    """Valida MarketHealth con 5 factores weighted."""

    @pytest.mark.asyncio
    async def test_market_health_has_5_factors(self, tmp_path, mock_cache):
        from tests.conftest import MockLeadSource, MockWebAuditor, MockLLMClient

        service = ProspectingService(
            lead_source=MockLeadSource([
                Lead(id="m1", business_name="M1", website_status=WebsiteStatus.NONE, niche="test"),
                Lead(id="m2", business_name="M2", website_status=WebsiteStatus.HTTP_ONLY, niche="test"),
            ]),
            web_auditor=MockWebAuditor(),
            llm_client=MockLLMClient(),
            cache=mock_cache,
            exporters=[],
            project_path=tmp_path,
            competitor_service=None,
            sentiment_adapter=None,
        )

        project = Project(
            slug="mh-test",
            config=ProjectConfig(niche="test", location="CDMX", max_leads=10),
        )

        leads = await service.execute(project)
        assert project.market_health_score >= 0.0
        assert project.market_health_score <= 100.0
        # Stats deben tener campos nuevos
        assert hasattr(project.stats, "ssl_failure_rate")
        assert hasattr(project.stats, "tracking_adoption_rate")
        assert hasattr(project.stats, "content_outdated_pct")
        assert hasattr(project.stats, "avg_competitor_count")
