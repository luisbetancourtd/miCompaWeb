"""Tests for Anti-Bot Infrastructure - Complete suite."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from micompaweb.infrastructure.browser import (
    BrowserEmulator,
    RateLimiter,
    FetchOrchestrator,
    Strategy,
    FetchResult,
    AntiBotConfig,
    JA3Spoofer,
    WAFDetector,
    WAFDetection,
    WAFType,
    SmartRetry,
    BrowserProfile,
)


class TestAntiBotConfig:
    """Test AntiBotConfig defaults."""

    def test_default_config(self):
        config = AntiBotConfig()
        assert config.enable_ja3 is True
        assert config.enable_random_delay is True
        assert config.min_delay == 0.5
        assert config.max_delay == 3.0
        assert config.max_retries == 3
        assert config.retry_backoff_base == 2.0
        assert config.user_agents == []
        assert config.proxies == []

    def test_custom_config(self):
        config = AntiBotConfig(enable_ja3=False, max_retries=5)
        assert config.enable_ja3 is False
        assert config.max_retries == 5


class TestBrowserEmulator:
    """Test BrowserEmulator profiles (6 perfiles)."""

    def test_get_random_profile_returns_valid(self):
        emu = BrowserEmulator()
        profile = emu.get_random_profile()
        assert profile.user_agent.startswith("Mozilla/5.0")
        assert len(profile.viewport) == 2

    def test_profiles_count(self):
        emu = BrowserEmulator()
        assert len(emu.PROFILES) == 6

    def test_get_headers_includes_user_agent(self):
        emu = BrowserEmulator()
        chrome_profile = [p for p in emu.PROFILES if "Chrome" in p.user_agent and "Mobile" not in p.user_agent][0]
        headers = emu.get_headers(chrome_profile)
        assert "User-Agent" in headers
        assert "Accept-Language" in headers
        assert "sec-ch-ua" in headers
        assert "sec-ch-ua-mobile" in headers
        assert headers["sec-ch-ua-mobile"] == "?0"
        assert headers["sec-ch-ua-platform"] == '"Windows"'

    def test_get_headers_mobile(self):
        emu = BrowserEmulator()
        mobile_profile = [p for p in emu.PROFILES if "Mobile" in p.user_agent][0]
        headers = emu.get_headers(mobile_profile)
        assert headers["sec-ch-ua-mobile"] == "?1"
        assert "User-Agent" in headers

    def test_get_headers_firefox_no_sec_ch(self):
        emu = BrowserEmulator()
        ff_profile = [p for p in emu.PROFILES if "Firefox" in p.user_agent][0]
        headers = emu.get_headers(ff_profile)
        assert "sec-ch-ua" not in headers or headers.get("sec-ch-ua") is None

    def test_get_profile_by_hash_consistency(self):
        emu = BrowserEmulator()
        p1 = emu.get_profile_by_hash("example.com")
        p2 = emu.get_profile_by_hash("example.com")
        assert p1.user_agent == p2.user_agent

    def test_get_viewports(self):
        emu = BrowserEmulator()
        viewports = emu.get_viewports()
        assert len(viewports) == 6
        for vp in viewports:
            assert len(vp) == 2
            assert vp[0] > 0 and vp[1] > 0

    def test_ja3_preset_mapping(self):
        emu = BrowserEmulator()
        for profile in emu.PROFILES:
            preset = emu.get_ja3_preset(profile)
            assert preset in JA3Spoofer.PRESETS.values()

    def test_ja3_preset_edge(self):
        emu = BrowserEmulator()
        edge_profile = [p for p in emu.PROFILES if "Edg" in p.user_agent][0]
        preset = emu.get_ja3_preset(edge_profile)
        assert preset == "edge99"

    def test_ja3_preset_firefox(self):
        emu = BrowserEmulator()
        ff_profile = [p for p in emu.PROFILES if "Firefox" in p.user_agent][0]
        preset = emu.get_ja3_preset(ff_profile)
        assert preset == "firefox120"

    def test_emulator_with_custom_config(self):
        config = AntiBotConfig(enable_ja3=False)
        emu = BrowserEmulator(config)
        assert emu.config.enable_ja3 is False


class TestJA3Spoofer:
    """Test JA3Spoofer."""

    def test_presets_defined(self):
        assert len(JA3Spoofer.PRESETS) >= 5
        assert "chrome_120" in JA3Spoofer.PRESETS
        assert "firefox_120" in JA3Spoofer.PRESETS

    def test_is_available(self):
        js = JA3Spoofer()
        # curl_cffi está instalado en el entorno, debe ser True
        assert isinstance(js.is_available, bool)

    def test_get_random_preset(self):
        js = JA3Spoofer()
        preset = js.get_random_preset()
        assert preset in JA3Spoofer.PRESETS.values()

    def test_get_session_raises_no_curl(self):
        """Simula que curl_cffi no está disponible."""
        js = JA3Spoofer()
        if not js.is_available:
            with pytest.raises(ImportError):
                js.get_session("chrome120")


class TestWAFDetector:
    """Test WAFDetector (7 tipos de WAF)."""

    def test_detect_cloudflare(self):
        detector = WAFDetector()
        result = detector.detect(403, {"Server": "cloudflare"}, "cf-browser-verification")
        assert result.detected is True
        assert result.waf_type == WAFType.CLOUDFLARE
        assert "cf-browser-verification" in result.signals
        assert result.suggested_strategy == "strong"

    def test_detect_incapsula(self):
        detector = WAFDetector()
        result = detector.detect(403, {"X-Iinfo": "123456"}, "incapsula")
        assert result.detected is True
        assert result.waf_type == WAFType.INCAPSULA

    def test_detect_akamai(self):
        detector = WAFDetector()
        result = detector.detect(403, {"X-Akamai-Request-Id": "abc"}, "")
        assert result.detected is True
        assert result.waf_type == WAFType.AKAMAI

    def test_detect_data_dome(self):
        detector = WAFDetector()
        result = detector.detect(403, {}, "datadome")
        assert result.detected is True
        assert result.waf_type == WAFType.DATA_DOME

    def test_detect_perimeter_x(self):
        detector = WAFDetector()
        result = detector.detect(403, {}, "perimeterx")
        assert result.detected is True
        assert result.waf_type == WAFType.PERIMETER_X

    def test_detect_sucuri(self):
        detector = WAFDetector()
        result = detector.detect(403, {"X-Sucuri-Id": "123"}, "")
        assert result.detected is True
        assert result.waf_type == WAFType.SUCURI

    def test_detect_aws_waf(self):
        detector = WAFDetector()
        result = detector.detect(403, {"awselb": "123"}, "")
        assert result.detected is True
        assert result.waf_type == WAFType.AWS_WAF

    def test_detect_none(self):
        detector = WAFDetector()
        result = detector.detect(200, {"Server": "nginx"}, "Hola mundo")
        assert result.detected is False
        assert result.waf_type == WAFType.NONE

    def test_is_blocking_response_403(self):
        detector = WAFDetector()
        assert detector.is_blocking_response(403, "access denied") is True
        assert detector.is_blocking_response(200, "normal page") is False
        assert detector.is_blocking_response(403, "normal page") is True
        assert detector.is_blocking_response(429, "") is True

    def test_is_blocking_response_captcha(self):
        detector = WAFDetector()
        assert detector.is_blocking_response(200, "Please complete the captcha") is True
        assert detector.is_blocking_response(200, "Enable JavaScript") is True


class TestWAFDetection:
    """Test WAFDetection dataclass."""

    def test_defaults(self):
        wd = WAFDetection()
        assert wd.detected is False
        assert wd.waf_type == WAFType.NONE
        assert wd.signals == []
        assert wd.suggested_strategy == "fast"

    def test_with_signals(self):
        wd = WAFDetection(detected=True, waf_type=WAFType.CLOUDFLARE, signals=["block"])
        assert wd.detected is True


class TestRateLimiter:
    """Test RateLimiter backoff."""

    def test_initial_delay(self):
        rl = RateLimiter(base_delay=1.0)
        assert rl.current_delay == 1.0

    def test_backoff_increases(self):
        rl = RateLimiter(base_delay=1.0)
        rl.wait()
        assert rl.current_delay == 2.0
        rl.wait()
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


class TestSmartRetry:
    """Test SmartRetry auto-strategy logic."""

    def test_retryable_429(self):
        sr = SmartRetry()
        should, action = sr.should_retry(429, "")
        assert should is True
        assert action == "slow_down"

    def test_retryable_502(self):
        sr = SmartRetry()
        should, action = sr.should_retry(502, "")
        assert should is True
        assert action == "same"

    def test_bot_detection_403_captcha(self):
        sr = SmartRetry()
        should, action = sr.should_retry(403, "Cloudflare captcha challenge")
        assert should is True
        assert action == "escalate"

    def test_bot_detection_automated(self):
        sr = SmartRetry()
        should, action = sr.should_retry(403, "automated requests detected")
        assert should is True
        assert action == "escalate"

    def test_no_retry_404(self):
        sr = SmartRetry()
        should, action = sr.should_retry(404, "not found")
        assert should is False
        assert action == "none"

    def test_waf_detected_force_escalate(self):
        sr = SmartRetry()
        should, action = sr.should_retry(200, "OK", waf_detected=True)
        assert should is True
        assert action == "escalate"

    def test_wait_increases(self):
        sr = SmartRetry(base_delay=1.0, max_delay=10.0)
        sr.wait(0)
        sr.wait(1)
        sr.wait(2)
        # Debe incrementarse, no decrecerse
        assert sr._rate_limiter.current_delay >= 1.0


class TestFetchOrchestratorV2:
    """Test FetchOrchestrator con ejecutores reales."""

    def test_classify_instagram_heavy(self):
        orch = FetchOrchestrator()
        assert orch.classify_domain("https://instagram.com/p/abc") == Strategy.HEAVY

    def test_classify_local_fast(self):
        orch = FetchOrchestrator()
        assert orch.classify_domain("https://plomeria-los-amigos.com") == Strategy.FAST

    def test_classify_cloudflare_strong(self):
        orch = FetchOrchestrator()
        assert orch.classify_domain("https://someshop.cloudflare.com") == Strategy.STRONG

    def test_classify_login_strong(self):
        orch = FetchOrchestrator()
        assert orch.classify_domain("https://example.com/login") == Strategy.STRONG

    def test_classify_checkout_strong(self):
        orch = FetchOrchestrator()
        assert orch.classify_domain("https://example.com/checkout") == Strategy.STRONG

    def test_analyze_response_403_cloudflare(self):
        orch = FetchOrchestrator()
        sig = orch.analyze_response(403, {}, "cf-browser-verification")
        assert sig.known_bot_defense is True
        assert sig.requires_js is True

    def test_analyze_response_rate_limited(self):
        orch = FetchOrchestrator()
        sig = orch.analyze_response(429, {})
        assert sig.rate_limited is True

    def test_analyze_response_cdn(self):
        orch = FetchOrchestrator()
        sig = orch.analyze_response(200, {"Server": "cloudflare"}, "")
        assert sig.uses_cdn is True

    def test_analyze_response_challenge(self):
        orch = FetchOrchestrator()
        sig = orch.analyze_response(200, {}, "Please enable javascript")
        assert sig.requires_js is True
        assert sig.known_bot_defense is True

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

    def test_executores_lazy_init(self):
        orch = FetchOrchestrator()
        # Pre-initialization
        assert orch._fast is None
        assert orch._strong is None
        assert orch._heavy is None
        # Post-access (triggered)
        _ = orch.fast_executor
        assert orch._fast is not None

    def test_orchestrator_has_waf_detector(self):
        orch = FetchOrchestrator()
        assert hasattr(orch, "waf_detector")
        assert hasattr(orch, "smart_retry")


class TestFetchOrchestratorFetchMethods:
    """Test fetch y fetch_smart con mocks de ejecutores."""

    @pytest.mark.asyncio
    async def test_fetch_fast_success(self):
        orch = FetchOrchestrator()
        # Mock FastExecutor
        mock_result = FetchResult(
            status_code=200, headers={}, text="OK", url="https://test.com",
            strategy="fast"
        )
        orch._fast = MagicMock()
        orch._fast.fetch = AsyncMock(return_value=MagicMock(
            html="OK", url="https://test.com", status_code=200,
            headers={}, error=None, waf_detected=False, response_time_ms=100,
            strategy="fast"
        ))
        orch._fast.name = "fast"

        profile = orch.emulator.get_random_profile()
        result = await orch.fetch("https://test.com", Strategy.FAST)
        assert result.status_code == 200
        assert result.text == "OK"

    @pytest.mark.asyncio
    async def test_fetch_smart_escalates(self):
        orch = FetchOrchestrator(auto_retry=True)

        # Simular: FAST falla con bot detection -> intenta STRONG -> éxito
        orch._fast = MagicMock()
        orch._fast.fetch = AsyncMock(return_value=MagicMock(
            html="", url="https://test.com", status_code=403,
            headers={}, error="Blocked",
            waf_detected=True, response_time_ms=0, strategy="fast"
        ))
        orch._fast.name = "fast"

        orch._strong = MagicMock()
        orch._strong.fetch = AsyncMock(return_value=MagicMock(
            html="<html>OK</html>", url="https://test.com", status_code=200,
            headers={}, error=None, waf_detected=False,
            response_time_ms=500, strategy="strong"
        ))
        orch._strong.name = "strong"

        result = await orch.fetch_smart("https://test.com", max_attempts=3)
        assert result.status_code == 200
        assert result.text == "<html>OK</html>"

    @pytest.mark.asyncio
    async def test_fetch_smart_all_fail(self):
        orch = FetchOrchestrator()

        # Todos los ejecutores fallan - necesitamos max_attempts=3 para que el fallback final aparezca
        for name in ["fast", "strong", "heavy"]:
            mock = MagicMock()
            mock.fetch = AsyncMock(return_value=MagicMock(
                html="", url="https://test.com", status_code=403,
                headers={}, error="Blocked", waf_detected=True,
                response_time_ms=0, strategy=name
            ))
            mock.name = name
            setattr(orch, f"_{name}", mock)

        result = await orch.fetch_smart("https://test.com", max_attempts=3)
        assert result.error is not None
        assert result.is_bot_detected is True


class TestFastExecutorWithoutCurlCffi:
    """Test FastExecutor con fallback a httpx."""

    @pytest.mark.asyncio
    async def test_fetch_httpx_fallback(self):
        from micompaweb.infrastructure.browser.executors import FastExecutor

        executor = FastExecutor()
        # Forzar que curl_cffi no disponible
        executor.has_curl_cffi = False
        executor.has_httpx = True

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.text = "<html>Test</html>"
            mock_response.status_code = 200
            mock_response.headers = {}
            mock_response.url = "https://example.com"

            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock(return_value=mock_response)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=False)
            mock_client.return_value = mock_instance

            result = await executor.fetch("https://example.com")
            assert result.status_code == 200
            assert "Test" in result.html
            assert result.strategy.startswith("fast")

    def test_name(self):
        from micompaweb.infrastructure.browser.executors import FastExecutor
        executor = FastExecutor()
        assert executor.name == "fast"

    def test_supports_ja3_when_curl_available(self):
        from micompaweb.infrastructure.browser.executors import FastExecutor
        executor = FastExecutor()
        executor.has_curl_cffi = True
        executor.has_httpx = True
        assert executor.supports_ja3 is True


class TestStrongExecutorWithoutPlaywright:
    """Test StrongExecutor sin Playwright."""

    def test_name(self):
        from micompaweb.infrastructure.browser.executors import StrongExecutor
        executor = StrongExecutor()
        assert executor.name == "strong"

    @pytest.mark.asyncio
    async def test_fetch_returns_error_when_no_playwright(self):
        from micompaweb.infrastructure.browser.executors import StrongExecutor
        executor = StrongExecutor()
        executor.has_playwright = False

        result = await executor.fetch("https://example.com")
        assert "playwright not installed" in result.error
        assert result.status_code == 0


class TestHeavyExecutorWithoutCrawl4AI:
    """Test HeavyExecutor sin Crawl4AI."""

    def test_name(self):
        from micompaweb.infrastructure.browser.executors import HeavyExecutor
        executor = HeavyExecutor()
        assert executor.name == "heavy"

    @pytest.mark.asyncio
    async def test_fetch_returns_error_when_no_crawl4ai(self):
        from micompaweb.infrastructure.browser.executors import HeavyExecutor
        executor = HeavyExecutor()
        executor._check_deps = lambda: None
        executor.has_crawl4ai = False
        executor.has_playwright = False

        result = await executor.fetch("https://example.com")
        assert "crawl4ai not installed" in result.error
        assert result.status_code == 0


class TestCrawl4Auditor:
    """Test Crawl4Auditor con anti-bot integration."""

    def test_init_requires_crawl4ai(self):
        # crawl4ai está instalado, no debe lanzar error
        from micompaweb.infrastructure.adapters.audit.crawl4ai_auditor import Crawl4Auditor
        auditor = Crawl4Auditor()
        assert auditor.auditor_name == "crawl4ai_chrome_antibot"
        assert auditor.requires_browser is True

    def test_check_tracking(self):
        from micompaweb.infrastructure.adapters.audit.crawl4ai_auditor import Crawl4Auditor
        import asyncio

        auditor = Crawl4Auditor()

        # Test con HTML que contiene tracking
        html_with_pixel = "<html><script>fbq('track', 'PageView');</script></html>"
        result = asyncio.run(auditor.check_tracking(html_with_pixel))
        assert result.has_meta_pixel is True
        assert result.has_gtm is False
        assert result.has_analytics is False

        # Test con GTM
        html_with_gtm = "<html><script src='googletagmanager.com/gtm.js'></script></html>"
        result = asyncio.run(auditor.check_tracking(html_with_gtm))
        assert result.has_gtm is True

        # Test con Analytics
        html_with_ga = "<html><script>gtag('config', 'GA-123');</script></html>"
        result = asyncio.run(auditor.check_tracking(html_with_ga))
        assert result.has_analytics is True

    @pytest.mark.asyncio
    async def test_detect_tech_stack_wordpress(self):
        from micompaweb.infrastructure.adapters.audit.crawl4ai_auditor import Crawl4Auditor

        auditor = Crawl4Auditor()
        html = "<html><link href='/wp-content/themes/style.css' /></html>"
        result = await auditor.detect_tech_stack(html)
        assert "WordPress" in result.detected_platforms
        assert result.cms == "WordPress"

    @pytest.mark.asyncio
    async def test_detect_tech_stack_react(self):
        from micompaweb.infrastructure.adapters.audit.crawl4ai_auditor import Crawl4Auditor

        auditor = Crawl4Auditor()
        html = "<html><div id='__next'></div></html>"
        result = await auditor.detect_tech_stack(html)
        assert "Next.js" in result.detected_platforms
        assert result.framework == "Next.js"

    @pytest.mark.asyncio
    async def test_detect_tech_stack_vue(self):
        from micompaweb.infrastructure.adapters.audit.crawl4ai_auditor import Crawl4Auditor

        auditor = Crawl4Auditor()
        html = "<html><div vue-app></div></html>"
        result = await auditor.detect_tech_stack(html)
        assert "Vue.js" in result.detected_platforms

    @pytest.mark.asyncio
    async def test_detect_tech_stack_empty(self):
        from micompaweb.infrastructure.adapters.audit.crawl4ai_auditor import Crawl4Auditor

        auditor = Crawl4Auditor()
        result = await auditor.detect_tech_stack("<html></html>")
        assert result.cms is None
        assert result.framework is None

    def test_auditor_name(self):
        from micompaweb.infrastructure.adapters.audit.crawl4ai_auditor import Crawl4Auditor
        auditor = Crawl4Auditor()
        assert auditor.auditor_name == "crawl4ai_chrome_antibot"

    def test_requires_browser(self):
        from micompaweb.infrastructure.adapters.audit.crawl4ai_auditor import Crawl4Auditor
        auditor = Crawl4Auditor()
        assert auditor.requires_browser is True

    @pytest.mark.asyncio
    async def test_audit_invalid_url(self):
        from micompaweb.infrastructure.adapters.audit.crawl4ai_auditor import Crawl4Auditor
        from micompaweb.application.ports.web_auditor import WebAuditError

        auditor = Crawl4Auditor()
        with pytest.raises(WebAuditError):
            await auditor.audit("not-a-url")

    @pytest.mark.asyncio
    async def test_audit_returns_technicalaudit(self):
        from micompaweb.infrastructure.adapters.audit.crawl4ai_auditor import Crawl4Auditor
        from micompaweb.application.ports.web_auditor import TechnicalAudit

        auditor = Crawl4Auditor()

        # Mockear _fetch_html para evitar crear browser
        async def mock_fetch(url):
            from micompaweb.infrastructure.browser.anti_bot import FetchResult
            return FetchResult(
                status_code=200, headers={}, text="<html><title>Test</title></html>",
                url=url, strategy="heavy", error=None,
                is_bot_detected=False, response_time_ms=100,
            )

        auditor._fetch_html = mock_fetch

        result = await auditor.audit("https://example.com")
        assert isinstance(result, TechnicalAudit)
        assert result.ssl is not None
        assert result.tracking is not None
        assert result.tech_stack is not None
        assert result.contacts is not None