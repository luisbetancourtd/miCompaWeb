"""Tests for Phase 4 Revenue+Email."""

import pytest

from micompaweb.application.services.cost_guardian import CostGuardian
from micompaweb.application.services.email_generator import EmailGenerator
from micompaweb.application.services.market_health import MarketHealthAnalyzer


class TestCostGuardian:
    """Test CostGuardian budget control."""

    def test_initial_state(self):
        cg = CostGuardian()
        assert cg.spent == 0.0
        assert cg.remaining() == 2.00

    def test_charge_affordable(self):
        cg = CostGuardian()
        assert cg.charge("google_places", 10) is True
        assert cg.spent > 0
        assert cg.counters["google_places"] == 10

    def test_charge_exceeds_budget(self):
        cg = CostGuardian()
        # Intentar gastar más de $2.00
        assert cg.charge("llm_api", 1000) is False  # 1000 * 0.003 = $3.00 > $2.00

    def test_can_afford(self):
        cg = CostGuardian()
        assert cg.can_afford("google_places", 100) is True  # $1.7 < $2.0
        assert cg.can_afford("llm_api", 1000) is False  # $3.0 > $2.0

    def test_summary_contains_fields(self):
        cg = CostGuardian()
        cg.charge("google_places", 10)
        cg.charge("serp_api", 50)
        summary = cg.summary()
        assert summary["total_spent"] > 0
        assert "remaining" in summary
        assert "breakdown" in summary
        assert summary["usage_counts"]["google_places"] == 10


class TestEmailGenerator:
    """Test EmailGenerator outreach."""

    def test_generate_spanish(self):
        gen = EmailGenerator()
        email = gen.generate(
            business_name="Plomria Express",
            niche="plomeros",
            signals=["Sin SSL", "Sin tracking", "No mobile-friendly"],
            language="es",
            tone="data",
        )
        assert "Plomria Express" in email.subject
        # Template per-niche usa "fontaneria" o "marketing digital para fontaneria"
        assert "fontaner" in email.body.lower() or "plomero" in email.body.lower()
        assert "Sin SSL" in email.body
        assert email.language == "es"
        assert email.tone == "data"

    def test_generate_english(self):
        gen = EmailGenerator()
        email = gen.generate(
            business_name="Quick Fix",
            niche="plumbers",
            signals=["No SSL", "Missing tracking"],
            language="en",
            tone="casual",
        )
        assert "Quick Fix" in email.subject
        assert email.language == "en"

    def test_generate_batch(self):
        gen = EmailGenerator()
        leads = [
            {"name": "A", "signals": ["x"], "owner_name": "Juan"},
            {"name": "B", "signals": ["y"]},
        ]
        emails = gen.generate_batch(leads, niche="plomeros")
        assert len(emails) == 2
        assert emails[0].personalization["owner_name"] == "Juan"


class TestMarketHealth:
    """Test MarketHealthAnalyzer."""

    def test_calculate_empty(self):
        ana = MarketHealthAnalyzer()
        idx = ana.calculate([])
        assert idx.overall_score == 0.5
        assert idx.risks == ["Sin datos suficientes"]

    def test_calculate_with_data(self):
        ana = MarketHealthAnalyzer()
        leads = [
            {"has_ssl": True, "has_tracking": False, "content_fresh": 0, "website": True, "review_count": 10},
            {"has_ssl": False, "has_tracking": False, "content_fresh": 0, "website": False, "review_count": 2},
            {"has_ssl": True, "has_tracking": True, "content_fresh": 0.5, "website": True, "review_count": 30},
        ]
        idx = ana.calculate(leads, sentiment_compound=0.3, avg_competitor_count=5)
        assert 0.0 <= idx.overall_score <= 1.0
        assert idx.digital_penetration == pytest.approx(2 / 3, abs=0.01)
        assert idx.avg_review_count > 0
        assert len(idx.risks) > 0

    def test_calculate_high_ssl_failure(self):
        ana = MarketHealthAnalyzer()
        leads = [{"has_ssl": False, "has_tracking": False, "content_fresh": 0, "website": True, "review_count": 1}]
        idx = ana.calculate(leads, ssl_failure_rate=0.8, avg_competitor_count=2)
        assert any("SSL" in r for r in idx.risks)

    def test_opportunity_score(self):
        ana = MarketHealthAnalyzer()
        leads = [
            {"has_ssl": False, "has_tracking": False, "content_fresh": 0, "website": False},
        ]
        idx = ana.calculate(leads)
        assert idx.opportunity_score > 0.5  # Baja digital = alta oportunidad

    def test_sentiment_influence(self):
        ana = MarketHealthAnalyzer()
        leads = [{"has_ssl": True, "has_tracking": True, "content_fresh": 0.5, "website": True, "review_count": 10}]
        idx_pos = ana.calculate(leads, sentiment_compound=0.8)
        idx_neg = ana.calculate(leads, sentiment_compound=-0.5)
        assert idx_pos.overall_score > idx_neg.overall_score
