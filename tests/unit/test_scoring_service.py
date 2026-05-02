"""Tests for ScoringService 3D Matrix."""

import pytest

from micompaweb.application.services.scoring_service import ScoringService
from micompaweb.domain.models import (
    Lead,
    WebsiteStatus,
    PriorityTier,
    ScoreCategory,
    TechnicalAudit,
    VigencyResult,
    GBPHealth,
)


class TestScoringService3D:
    """Test cases para ScoringService con matriz 3D (RECARGADO)."""

    def setup_method(self):
        self.service = ScoringService()

    # ================================================================
    # Authority Tests
    # ================================================================
    def test_authority_review_volume_max(self):
        lead = Lead(business_name="Test", review_count=50, rating=5.0,
                    website_status=WebsiteStatus.NONE)
        r = self.service.calculate(lead)
        authority = [b for b in r.breakdowns if b.category == ScoreCategory.AUTHORITY]
        review_bd = [b for b in authority if b.criterion == "review_volume"]
        assert review_bd
        assert review_bd[0].points == 40

    def test_authority_rating_max(self):
        lead = Lead(business_name="Test", rating=4.5, review_count=100,
                    website_status=WebsiteStatus.NONE)
        r = self.service.calculate(lead)
        authority = [b for b in r.breakdowns if b.category == ScoreCategory.AUTHORITY]
        rating_bd = [b for b in authority if b.criterion == "review_rating"]
        assert rating_bd
        assert rating_bd[0].points == 30

    def test_local_signals(self):
        gbp = GBPHealth(photos_count=25, has_categories=True, has_phone=True, has_hours=True)
        lead = Lead(business_name="Test", review_count=0, rating=0.0,
                    website_status=WebsiteStatus.NONE, gbp_health=gbp)
        r = self.service.calculate(lead)
        local = [b for b in r.breakdowns if b.criterion == "local_signals"]
        assert local
        assert local[0].points == 30

    # ================================================================
    # Digital Neglect Tests
    # ================================================================
    def test_no_website_50pts(self):
        lead = Lead(business_name="Test", website_status=WebsiteStatus.NONE)
        r = self.service.calculate(lead)
        bd = [b for b in r.breakdowns if b.criterion == "no_website"]
        assert bd
        assert bd[0].points == 50
        assert bd[0].category == ScoreCategory.DIGITAL_NEGLECT

    def test_insecure_http(self):
        lead = Lead(business_name="Test", website_status=WebsiteStatus.HTTP_ONLY)
        r = self.service.calculate(lead)
        bd = [b for b in r.breakdowns if b.criterion == "insecure_http"]
        assert bd
        assert bd[0].points == 20

    def test_ssl_invalid(self):
        lead = Lead(business_name="Test", website_url="http://x.com",
                    website_status=WebsiteStatus.EXISTS,
                    audit=TechnicalAudit(ssl_valid=False))
        r = self.service.calculate(lead)
        bd = [b for b in r.breakdowns if b.criterion == "invalid_ssl"]
        assert bd
        assert bd[0].points == 20

    def test_tech_obsolete(self):
        lead = Lead(business_name="Test", website_url="https://x.com",
                    website_status=WebsiteStatus.EXISTS,
                    audit=TechnicalAudit(cms="Wix", ssl_valid=True,
                                         copyright_year=2018))
        r = self.service.calculate(lead)
        bd = [b for b in r.breakdowns if b.criterion == "tech_obsolete"]
        assert bd
        assert bd[0].points == 15

    def test_no_tracking(self):
        audit = TechnicalAudit(ssl_valid=True, has_meta_pixel=False,
                               has_gtm=False, has_analytics=False)
        lead = Lead(business_name="Test", website_url="https://x.com",
                    website_status=WebsiteStatus.EXISTS, audit=audit)
        r = self.service.calculate(lead)
        bd = [b for b in r.breakdowns if b.criterion == "no_tracking"]
        assert bd
        assert bd[0].points == 10

    def test_mobile_broken(self):
        audit = TechnicalAudit(ssl_valid=True, mobile_friendly=False)
        lead = Lead(business_name="Test", website_url="https://x.com",
                    website_status=WebsiteStatus.EXISTS, audit=audit)
        r = self.service.calculate(lead)
        bd = [b for b in r.breakdowns if b.criterion == "mobile_broken"]
        assert bd
        assert bd[0].points == 15

    def test_contact_missing(self):
        audit = TechnicalAudit(ssl_valid=True, emails_found=[], phones_found=[])
        lead = Lead(business_name="Test", website_url="https://x.com",
                    website_status=WebsiteStatus.EXISTS, audit=audit)
        r = self.service.calculate(lead)
        bd = [b for b in r.breakdowns if b.criterion == "contact_missing"]
        assert bd
        assert bd[0].points == 10

    def test_content_outdated(self):
        vig = VigencyResult(is_outdated=True, outdated_confidence=0.8,
                            outdated_reason="Old copyright")
        audit = TechnicalAudit(ssl_valid=True)
        lead = Lead(business_name="Test", website_url="https://x.com",
                    website_status=WebsiteStatus.EXISTS, audit=audit, vigency=vig)
        r = self.service.calculate(lead)
        bd = [b for b in r.breakdowns if b.criterion == "content_outdated"]
        assert bd
        assert bd[0].points == 20  # 0.8 * 25
        assert bd[0].max_points == 25

    # ================================================================
    # Sales Readiness Tests
    # ================================================================
    def test_active_gbp(self):
        lead = Lead(business_name="Test", website_status=WebsiteStatus.NONE,
                    owner_response_rate=0.5)
        r = self.service.calculate(lead)
        bd = [b for b in r.breakdowns if b.criterion == "active_gbp"]
        assert bd
        assert bd[0].points == 30

    def test_competitor_density(self):
        lead = Lead(business_name="Test", website_status=WebsiteStatus.NONE,
                    competitor_count=10)
        r = self.service.calculate(lead)
        bd = [b for b in r.breakdowns if b.criterion == "competitor_density"]
        assert bd
        assert bd[0].points == 20

    def test_recent_activity(self):
        lead = Lead(business_name="Test", website_status=WebsiteStatus.NONE,
                    has_recent_reviews=True)
        r = self.service.calculate(lead)
        bd = [b for b in r.breakdowns if b.criterion == "recent_activity"]
        assert bd
        assert bd[0].points == 25

    def test_category_value_high(self):
        lead = Lead(business_name="Test", website_status=WebsiteStatus.NONE)
        r = self.service.calculate(lead, niche_avg_ticket=250)
        bd = [b for b in r.breakdowns if b.criterion == "category_value"]
        assert bd
        assert bd[0].points == 25

    def test_category_value_medium(self):
        lead = Lead(business_name="Test", website_status=WebsiteStatus.NONE)
        r = self.service.calculate(lead, niche_avg_ticket=120)
        bd = [b for b in r.breakdowns if b.criterion == "category_value"]
        assert bd
        assert bd[0].points == 15

    # ================================================================
    # Tier & Weighted Score Tests
    # ================================================================
    def test_ultra_hot_threshold(self):
        """Lead perfecto debería alcanzar ULTRA HOT (>=120)."""
        import datetime
        current_year = datetime.datetime.now().year
        gbp = GBPHealth(photos_count=25, has_categories=True, has_phone=True, has_hours=True)
        audit = TechnicalAudit(ssl_valid=False, cms="Wix", copyright_year=current_year-3,
                               has_meta_pixel=False, has_gtm=False, has_analytics=False,
                               mobile_friendly=False)
        vig = VigencyResult(is_outdated=True, outdated_confidence=1.0,
                            outdated_reason="Old copyright")
        lead = Lead(business_name="Test", website_url="https://x.com",
                    website_status=WebsiteStatus.EXISTS, review_count=100, rating=5.0,
                    has_recent_reviews=True, competitor_count=20,
                    owner_response_rate=0.5, gbp_health=gbp, audit=audit, vigency=vig)
        r = self.service.calculate(lead, niche_avg_ticket=250)
        assert r.total_score >= 120, f"Score={r.total_score}"
        assert r.priority_tier == PriorityTier.ULTRA_HOT.value

    def test_hot_threshold(self):
        """Lead fuerte debería ser HOT (80-119)."""
        audit = TechnicalAudit(ssl_valid=True, has_meta_pixel=False, has_gtm=False,
                               has_analytics=False, mobile_friendly=True)
        lead = Lead(business_name="Test", website_status=WebsiteStatus.NONE,
                    review_count=50, rating=4.5, has_recent_reviews=True,
                    competitor_count=10, audit=audit)
        r = self.service.calculate(lead)
        assert r.total_score >= 80, f"Score={r.total_score}"
        assert r.priority_tier == PriorityTier.HOT.value

    def test_depth_adjustment_rapida(self):
        lead = Lead(business_name="Test", website_status=WebsiteStatus.NONE,
                    review_count=100, rating=5.0)
        r1 = self.service.calculate(lead)
        r2 = self.service.calculate(lead, depth="rapida")
        assert r2.total_score == int(round(r1.total_score * 0.90))

    def test_depth_adjustment_estandar(self):
        lead = Lead(business_name="Test", website_status=WebsiteStatus.NONE,
                    review_count=100, rating=5.0)
        r1 = self.service.calculate(lead)
        r2 = self.service.calculate(lead, depth="estandar")
        assert r2.total_score == int(round(r1.total_score * 0.95))

    def test_category_totals_match_breakdowns(self):
        gbp = GBPHealth(photos_count=25, has_categories=True, has_phone=True, has_hours=True)
        lead = Lead(business_name="Test", website_status=WebsiteStatus.NONE,
                    review_count=50, rating=4.5, has_recent_reviews=True,
                    gbp_health=gbp)
        r = self.service.calculate(lead)
        auth_sum = sum(b.points for b in r.breakdowns
                       if b.category == ScoreCategory.AUTHORITY)
        assert r.authority_points == auth_sum
        neglect_sum = sum(b.points for b in r.breakdowns
                          if b.category == ScoreCategory.DIGITAL_NEGLECT)
        assert r.digital_neglect_points == neglect_sum
        ready_sum = sum(b.points for b in r.breakdowns
                        if b.category == ScoreCategory.SALES_READINESS)
        assert r.sales_readiness_points == ready_sum

    def test_score_capped_at_150(self):
        # Impossible lead: all max points in every category
        gbp = GBPHealth(photos_count=25, has_categories=True, has_phone=True, has_hours=True)
        audit = TechnicalAudit(ssl_valid=False, cms="Wix", copyright_year=2018,
                               has_meta_pixel=False, has_gtm=False,
                               has_analytics=False, mobile_friendly=False)
        vig = VigencyResult(is_outdated=True, outdated_confidence=1.0)
        lead = Lead(business_name="Test", website_status=WebsiteStatus.NONE,
                    review_count=100, rating=5.0, has_recent_reviews=True,
                    competitor_count=50, owner_response_rate=1.0,
                    gbp_health=gbp, audit=audit, vigency=vig)
        r = self.service.calculate(lead, niche_avg_ticket=500)
        assert r.total_score <= 150

    def test_breakdown_confidence_valid(self):
        lead = Lead(business_name="Test", website_status=WebsiteStatus.NONE,
                    review_count=50, rating=4.5)
        r = self.service.calculate(lead)
        for b in r.breakdowns:
            assert 0.0 <= b.confidence <= 1.0

    def test_get_top_signals(self):
        lead = Lead(business_name="Test", website_status=WebsiteStatus.NONE,
                    review_count=50)
        r = self.service.calculate(lead)
        top = r.get_top_signals(n=2)
        assert len(top) <= 2
        if len(top) >= 2:
            assert top[0].points >= top[1].points

    def test_to_dict_for_report(self):
        lead = Lead(business_name="Test", website_status=WebsiteStatus.NONE,
                    review_count=50, rating=4.5)
        r = self.service.calculate(lead)
        d = r.to_dict_for_report()
        assert d["total_score"] == r.total_score
        assert "authority" in d["by_category"]
        assert "digital_neglect" in d["by_category"]
        assert "sales_readiness" in d["by_category"]
        assert "readiness" not in d["by_category"]
