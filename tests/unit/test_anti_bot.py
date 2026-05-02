"""Tests for Anti-Bot Infrastructure."""

import pytest

from micompaweb.infrastructure.browser import (
    BrowserEmulator,
    RateLimiter,
    FetchOrchestrator,
    Strategy,
    FetchResult,
)


class TestBrowserEmulator:
    """Test BrowserEmulator profiles."""

    def test_get_random_profile_returns_valid(self):
        emu = BrowserEmulator()
        profile = emu.get_random_profile()
        assert profile.user_agent.startswith("Mozilla/5.0")
        assert len(profile.viewport) == 2

    def test_get_headers_includes_user_agent(self):
        emu = BrowserEmulator()
        # Usar perfil que SI tenga sec_ch_ua (Chrome)
        chrome_profile = [p for p in emu.PROFILES if "Chrome" in p.user_agent and "Mobile" not in p.user_agent][0]
        headers = emu.get_headers(chrome_profile)
        assert "User-Agent" in headers
        assert "Accept-Language" in headers
        assert "sec-ch-ua" in headers

    def test_get_headers_firefox_no_sec_ch(self):
        emu = BrowserEmulator()
        # Buscar perfil firefox
        ff_profile = [p for p in emu.PROFILES if "Firefox" in p.user_agent][0]
        headers = emu.get_headers(ff_profile)
        assert "sec-ch-ua" not in headers or headers.get("sec-ch-ua") is None


class TestRateLimiter:
    """Test RateLimiter backoff."""

    def test_initial_delay(self):
        rl = RateLimiter(base_delay=1.0)
        assert rl.current_delay == 1.0

    def test_backoff_increases(self):
        rl = RateLimiter(base_delay=1.0)
        rl.wait()  # attempt 0
        assert rl.current_delay == 2.0
        rl.wait()  # attempt 1
        assert rl.current_delay == 4.0

    def test_max_delay_capped(self):
        rl = RateLimiter(base_delay=1.0, max_delay=8.0)
        for _ in range(5):
            rl.wait()
        assert rl.current_delay == 8.0

    def test_reset(self):
        rl = RateLimiter(base_delay=1.0)
        rl.wait()
        rl.reset()
        assert rl.attempt == 0
        assert rl.current_delay == 1.0


class TestFetchOrchestrator:
    """Test domain classification and strategy."""

    def test_classify_instagram_heavy(self):
        orch = FetchOrchestrator()
        assert orch.classify_domain("https://instagram.com/p/abc") == Strategy.HEAVY

    def test_classify_local_fast(self):
        orch = FetchOrchestrator()
        assert orch.classify_domain("https://plomeria-los-amigos.com") == Strategy.FAST

    def test_classify_cloudflare_strong(self):
        orch = FetchOrchestrator()
        assert orch.classify_domain("https://someshop.cloudflare.com") == Strategy.STRONG

    def test_analyze_response_403_cloudflare(self):
        orch = FetchOrchestrator()
        sig = orch.analyze_response(403, {}, "cf-browser-verification")
        assert sig.known_bot_defense is True
        assert sig.requires_js is True

    def test_analyze_response_rate_limited(self):
        orch = FetchOrchestrator()
        sig = orch.analyze_response(429, {})
        assert sig.rate_limited is True

    def test_adapt_escalates_fast_to_strong(self):
        orch = FetchOrchestrator()
        sig = orch.analyze_response(403, {}, "enable javascript")
        strategy = orch.adapt_strategy("https://example.com", sig)
        assert strategy == Strategy.STRONG

    def test_adapt_escalates_strong_to_heavy(self):
        orch = FetchOrchestrator()
        sig = orch.analyze_response(403, {}, "captcha")
        strategy = orch.adapt_strategy("https://someshop.cloudflare.com/login", sig)
        assert strategy == Strategy.HEAVY

    def test_get_request_config_fast(self):
        orch = FetchOrchestrator()
        config = orch.get_request_config(Strategy.FAST)
        assert "User-Agent" in config["headers"]
        assert config["strategy"] == "fast"

    def test_get_request_config_heavy_deterministic(self):
        orch = FetchOrchestrator()
        config1 = orch.get_request_config(Strategy.HEAVY, profile_seed="abc.com")
        config2 = orch.get_request_config(Strategy.HEAVY, profile_seed="abc.com")
        assert config1["headers"]["User-Agent"] == config2["headers"]["User-Agent"]
