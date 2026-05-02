"""End-to-end integration tests."""

import pytest
from pathlib import Path

from micompaweb.application.services.prospecting_service import ProspectingService
from micompaweb.application.services.doctor import MiCompaWebDoctor
from micompaweb.application.services.market_health import MarketHealthAnalyzer
from micompaweb.application.ui.input_agent import InputAgent
from micompaweb.domain.models import Project, ProjectConfig
from micompaweb.infrastructure.cache.sqlite_cache import SQLiteCache
from micompaweb.infrastructure.adapters import (
    FixtureSource,
    SimpleAuditor,
    HeuristicClient,
)


class TestEndToEndProspecting:
    """End-to-end test with real dependencies (except external APIs)."""

    @pytest.fixture
    async def service(self, tmp_path):
        """Create service with real (non-mock) dependencies."""
        cache_db = tmp_path / "test_cache.db"
        cache = SQLiteCache(cache_db)

        return ProspectingService(
            lead_source=FixtureSource(seed=42),
            web_auditor=SimpleAuditor(timeout_seconds=10),
            llm_client=HeuristicClient(),
            cache=cache,
            exporters=[],
            project_path=tmp_path,
        )

    @pytest.fixture
    def project(self):
        return Project(
            slug="e2e-test",
            config=ProjectConfig(
                niche="plomeros",
                location="Ciudad de México",
                max_leads=5,
            ),
        )

    @pytest.mark.asyncio
    async def test_full_pipeline_executes(self, service, project):
        """Full pipeline should execute successfully."""
        leads = await service.execute(project)

        assert len(leads) == 5
        assert project.is_complete

    @pytest.mark.asyncio
    async def test_leads_have_all_fields_populated(self, service, project):
        """Leads should have all expected fields."""
        leads = await service.execute(project)

        for lead in leads:
            assert lead.pepita_score >= 0
            assert lead.priority is not None
            assert lead.revenue_loss.monthly_mid >= 0
            assert lead.audit is not None

    @pytest.mark.asyncio
    async def test_caching_works(self, tmp_path, project):
        """Cache should persist between calls."""
        cache_db = tmp_path / "cache.db"
        cache = SQLiteCache(cache_db)

        # First service
        service1 = ProspectingService(
            lead_source=FixtureSource(seed=42),
            web_auditor=SimpleAuditor(),
            llm_client=HeuristicClient(),
            cache=cache,
            exporters=[],
            project_path=tmp_path,
        )

        await service1.execute(project)

        # Check cache stats
        stats = await cache.get_stats()
        assert stats["total_entries"] > 0


class TestDoctorIntegration:
    """Doctor integration tests."""

    def test_doctor_runs_on_real_system(self):
        doc = MiCompaWebDoctor()
        report = doc.run()
        assert report.overall == "healthy"
        assert len(report.checks) >= 5
        for c in report.checks:
            assert c.status in ("ok", "warning", "error")


class TestMarketHealthIntegration:
    """Market health with real fixture data."""

    def test_with_fixture_leads(self):
        # Lead fixtures simulados (sin depender de FixtureSource internals)
        leads = [
            {"has_ssl": True, "has_tracking": False, "content_fresh": 0, "website": True, "review_count": 8},
            {"has_ssl": False, "has_tracking": False, "content_fresh": 0, "website": False, "review_count": 2},
            {"has_ssl": True, "has_tracking": True, "content_fresh": 0.5, "website": True, "review_count": 25},
            {"has_ssl": True, "has_tracking": False, "content_fresh": 0, "website": True, "review_count": 5},
            {"has_ssl": False, "has_tracking": False, "content_fresh": 0, "website": False, "review_count": 0},
        ]
        ana = MarketHealthAnalyzer()
        idx = ana.calculate(leads, sentiment_compound=0.2, avg_competitor_count=5)
        assert 0 <= idx.overall_score <= 1
        assert idx.digital_penetration == 0.6  # 3/5 tienen web


class TestInputAgentIntegration:
    """InputAgent with real ProjectConfig."""

    def test_full_sanitize_pipeline(self):
        agent = InputAgent()
        config = ProjectConfig(
            niche="  Plomeros De La  ",
            location="CDMX",
            target_language="es",
            depth="estandar",
            max_leads=10,
        )
        sanitized = agent.sanitize(config)
        assert sanitized.niche == "plomeros"
        assert "cdmx" in sanitized.location or "ciudad de méxico" in sanitized.location
