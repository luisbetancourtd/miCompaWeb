"""Contract tests for LeadSource implementations.

These tests verify that all LeadSource implementations
comply with the LeadSource protocol.
"""

import pytest
from typing import Type, List

from micompaweb.application.ports import LeadSource
from micompaweb.domain.models import Lead
from micompaweb.infrastructure.adapters.lead_sources import FixtureSource


class TestLeadSourceContract:
    """Contract tests for LeadSource protocol."""

    @pytest.fixture
    async def source(self):
        """Create source instance."""
        return FixtureSource()

    @pytest.mark.asyncio
    async def test_search_returns_list_of_leads(self, source):
        """All sources must return List[Lead]."""
        leads = await source.search("test", "location", max_results=10)

        assert isinstance(leads, list)
        assert all(isinstance(l, Lead) for l in leads)

    @pytest.mark.asyncio
    async def test_search_respects_max_results(self, source):
        """Should not return more than max_results."""
        leads = await source.search("test", "location", max_results=5)

        assert len(leads) <= 5

    @pytest.mark.asyncio
    async def test_get_details_returns_lead_or_none(self, source):
        """get_details should return Lead or None."""
        result = await source.get_details("nonexistent_id")

        assert result is None or isinstance(result, Lead)

    def test_health_check_returns_tuple(self, source):
        """health_check should return (bool, str)."""
        health = source.health_check()

        assert hasattr(health, 'is_healthy')
        assert hasattr(health, 'message')
        assert isinstance(health.is_healthy, bool)
        assert isinstance(health.message, str)

    def test_estimate_cost_returns_cost_estimate(self, source):
        """estimate_cost should return CostEstimate."""
        cost = source.estimate_cost(100)

        assert hasattr(cost, 'usd_amount')
        assert hasattr(cost, 'requests_count')
        assert hasattr(cost, 'source_name')
        assert cost.usd_amount >= 0

    def test_has_source_name_property(self, source):
        """Should have source_name property."""
        assert hasattr(source, 'source_name')
        assert isinstance(source.source_name, str)

    def test_has_supports_caching_property(self, source):
        """Should have supports_caching property."""
        assert hasattr(source, 'supports_caching')
        assert isinstance(source.supports_caching, bool)


class TestCachedSourceContract(TestLeadSourceContract):
    """Contract tests for CachedSource."""

    @pytest.fixture
    async def source(self):
        """Create cached source."""
        from micompaweb.infrastructure.adapters.lead_sources import CachedSource
        from tests.conftest import MockLeadSource, MockCache

        return CachedSource(MockLeadSource(), MockCache())


# Example of how to add more source implementations:
# class TestGooglePlacesSourceContract(TestLeadSourceContract):
#     @pytest.fixture
#     async def source(self):
#         from micompaweb.infrastructure.adapters import GooglePlacesSource
#         return GooglePlacesSource(api_key="test_key")
#
#     @pytest.mark.skip(reason="Requires API key")
#     async def test_search_returns_list_of_leads(self, source):
#         await super().test_search_returns_list_of_leads(source)
