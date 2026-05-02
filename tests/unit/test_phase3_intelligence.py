"""Tests for Phase 3 Intelligence services."""

import pytest

from micompaweb.application.services.sentiment_adapter import SentimentAdapter
from micompaweb.application.services.competitor_service import CompetitorService
from micompaweb.application.services.places_extractor import PlacesDetailsExtractor


class TestSentimentAdapter:
    """Test SentimentAnalysis."""

    def test_analyze_empty(self):
        adapter = SentimentAdapter()
        score = adapter.analyze([])
        assert score.neutral == 1.0
        assert score.review_count == 0

    def test_analyze_positive(self):
        adapter = SentimentAdapter()
        score = adapter.analyze(["Excelente servicio, muy profesional", "Gran calidad"])
        assert score.positive > score.negative
        assert score.compound > 0

    def test_analyze_negative(self):
        adapter = SentimentAdapter()
        score = adapter.analyze(["Pésimo, terrible servicio", "Malo", "No llegaron"])
        assert score.negative > score.positive
        assert score.compound < 0

    def test_has_negative_signal_true(self):
        adapter = SentimentAdapter()
        assert adapter.has_negative_signal(["Pésimo servicio", "Muy mal", "deficiente"])

    def test_has_negative_signal_false(self):
        adapter = SentimentAdapter()
        assert not adapter.has_negative_signal(["Muy buen servicio", "Recomiendo"])

    def test_category_very_positive(self):
        adapter = SentimentAdapter()
        assert adapter.category(0.7) == "muy positivo"

    def test_category_negative(self):
        adapter = SentimentAdapter()
        assert adapter.category(-0.3) == "negativo"


class TestCompetitorService:
    """Test CompetitorService."""

    def test_analyze_empty(self):
        svc = CompetitorService()
        matrix = svc.analyze([])
        assert matrix.total_competitors == 0

    def test_analyze_basic(self):
        svc = CompetitorService()
        raw = [
            {"name": "Comp1", "website": True, "has_tracking": True, "has_photos": True, "has_reviews": True, "rating": 4.5, "review_count": 20},
            {"name": "Comp2", "website": False, "rating": 0},
        ]
        matrix = svc.analyze(raw)
        assert matrix.total_competitors == 2
        assert matrix.with_website == 1
        assert matrix.with_tracking == 1
        assert matrix.avg_rating == 4.5
        assert matrix.market_maturity == "emergente"
        assert matrix.opportunity_score > 0

    def test_classify_maturity_madura(self):
        svc = CompetitorService()
        raw = [
            {"name": f"C{i}", "website": True, "has_tracking": True, "has_photos": True, "has_reviews": True, "rating": 4.0, "review_count": 30}
            for i in range(12)
        ]
        matrix = svc.analyze(raw)
        assert matrix.market_maturity == "madura"
        assert matrix.opportunity_score < 50


class TestPlacesDetailsExtractor:
    """Test PlacesDetailsExtractor."""

    def test_extract_basic(self):
        ext = PlacesDetailsExtractor()
        data = {
            "place_id": "abc123",
            "name": "Café Central",
            "address": "Calle Mayor 5",
            "phone": "555-1234",
            "website": "https://cafecentral.com",
            "rating": 4.2,
            "review_count": 15,
            "photos": [{"url": "x"}, {"url": "y"}],
            "hours": "Mon-Fri 8-20",
            "categories": ["cafe", "restaurant"],
            "is_claimed": True,
        }
        details = ext.extract(data)
        assert details.name == "Café Central"
        assert details.phone == "555-1234"
        assert details.photo_count == 2
        assert details.has_hours is True
        assert details.categories == ["cafe", "restaurant"]
        assert details.is_claimed is True

    def test_extract_no_photos(self):
        ext = PlacesDetailsExtractor()
        data = {"name": "Bare", "photos": []}
        details = ext.extract(data)
        assert details.has_photos is False
        assert details.photo_count == 0

    def test_enrich_adds_reviews(self):
        ext = PlacesDetailsExtractor()
        details = ext.extract({"name": "Café", "categories": []})
        enriched = ext.enrich(details, reviews_text=["Muy bueno", "Excelente", "Regular", "Malo"])
        assert "reviews_sample" in enriched
        assert len(enriched["reviews_sample"]) == 3
