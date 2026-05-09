"""Tests for SimpleAuditor."""

import pytest
from unittest.mock import AsyncMock
from bs4 import BeautifulSoup

from micompaweb.infrastructure.adapters.audit.simple_auditor import SimpleAuditor
from micompaweb.application.ports.web_auditor import (
    WebAuditError,
    SSLResult,
)


@pytest.fixture
def auditor():
    return SimpleAuditor(timeout_seconds=10)


def make_soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "lxml")


class TestSimpleAuditorProperties:
    def test_auditor_name(self, auditor):
        assert auditor.auditor_name == "simple_httpx_bs4"

    def test_requires_browser_is_false(self, auditor):
        assert auditor.requires_browser is False


class TestCheckTracking:
    @pytest.mark.asyncio
    async def test_detects_meta_pixel_fbq(self, auditor):
        result = await auditor.check_tracking('<script>fbq("init","123");</script>')
        assert result.has_meta_pixel is True

    @pytest.mark.asyncio
    async def test_detects_meta_pixel_facebook_tr(self, auditor):
        result = await auditor.check_tracking('<img src="https://www.facebook.com/tr?id=123">')
        assert result.has_meta_pixel is True

    @pytest.mark.asyncio
    async def test_detects_gtm(self, auditor):
        result = await auditor.check_tracking(
            '<script src="https://www.googletagmanager.com/gtm.js"></script>'
        )
        assert result.has_gtm is True

    @pytest.mark.asyncio
    async def test_detects_google_analytics_gtag(self, auditor):
        result = await auditor.check_tracking('<script>gtag("config","G-XXXX");</script>')
        assert result.has_analytics is True

    @pytest.mark.asyncio
    async def test_detects_google_analytics_ga_create(self, auditor):
        result = await auditor.check_tracking("<script>ga('create','UA-XXXX');</script>")
        assert result.has_analytics is True

    @pytest.mark.asyncio
    async def test_detects_linkedin_pixel(self, auditor):
        result = await auditor.check_tracking(
            "<script>_linkedin_partner_id = '123';</script>"
        )
        assert result.has_linkedin_pixel is True

    @pytest.mark.asyncio
    async def test_detects_tiktok_pixel(self, auditor):
        result = await auditor.check_tracking("<script>ttq.track('PageView');</script>")
        assert result.has_tiktok_pixel is True

    @pytest.mark.asyncio
    async def test_no_tracking_on_plain_html(self, auditor):
        result = await auditor.check_tracking("<html><body><p>Hola mundo</p></body></html>")
        assert result.has_meta_pixel is False
        assert result.has_gtm is False
        assert result.has_analytics is False
        assert result.has_linkedin_pixel is False
        assert result.has_tiktok_pixel is False


class TestDetectTechStack:
    @pytest.mark.asyncio
    async def test_detects_wordpress(self, auditor):
        html = '<link rel="stylesheet" href="/wp-content/themes/my-theme/style.css">'
        result = await auditor.detect_tech_stack(html, make_soup(html))
        assert "WordPress" in result.detected_platforms
        assert result.cms == "WordPress"

    @pytest.mark.asyncio
    async def test_detects_wix(self, auditor):
        html = '<script src="https://static.wix.com/sites/main.js"></script>'
        result = await auditor.detect_tech_stack(html, make_soup(html))
        assert "Wix" in result.detected_platforms
        assert result.cms == "Wix"

    @pytest.mark.asyncio
    async def test_detects_shopify(self, auditor):
        html = '<script src="https://cdn.shopify.com/s/files/shop.js"></script>'
        result = await auditor.detect_tech_stack(html, make_soup(html))
        assert "Shopify" in result.detected_platforms

    @pytest.mark.asyncio
    async def test_detects_squarespace(self, auditor):
        html = '<link href="https://static1.squarespace-cdn.com/main.css">'
        result = await auditor.detect_tech_stack(html, make_soup(html))
        assert "Squarespace" in result.detected_platforms

    @pytest.mark.asyncio
    async def test_detects_webflow(self, auditor):
        html = "<html data-wf-domain='example.webflow.io'>"
        result = await auditor.detect_tech_stack(html, make_soup(html))
        assert "Webflow" in result.detected_platforms

    @pytest.mark.asyncio
    async def test_detects_elementor(self, auditor):
        html = '<link rel="stylesheet" href="/wp-content/plugins/elementor/assets/css/frontend.css">'
        result = await auditor.detect_tech_stack(html, make_soup(html))
        assert "Elementor" in result.detected_platforms

    @pytest.mark.asyncio
    async def test_detects_react(self, auditor):
        html = '<div id="root" data-reactroot=""></div>'
        result = await auditor.detect_tech_stack(html, make_soup(html))
        assert "React" in result.detected_platforms
        assert result.framework == "React"

    @pytest.mark.asyncio
    async def test_detects_nextjs(self, auditor):
        html = '<script id="__NEXT_DATA__" type="application/json">{}</script>'
        result = await auditor.detect_tech_stack(html, make_soup(html))
        assert "Next.js" in result.detected_platforms

    @pytest.mark.asyncio
    async def test_detects_vuejs(self, auditor):
        html = '<div id="app" vue-app></div><script>new Vue();</script>'
        result = await auditor.detect_tech_stack(html, make_soup(html))
        assert "Vue.js" in result.detected_platforms

    @pytest.mark.asyncio
    async def test_detects_cloudflare(self, auditor):
        html = "<!-- cloudflare cdn protection -->"
        result = await auditor.detect_tech_stack(html, make_soup(html))
        assert "Cloudflare" in result.detected_platforms

    @pytest.mark.asyncio
    async def test_detects_aws(self, auditor):
        html = '<img src="https://s3.amazonaws.com/bucket/image.jpg">'
        result = await auditor.detect_tech_stack(html, make_soup(html))
        assert "AWS" in result.detected_platforms

    @pytest.mark.asyncio
    async def test_detects_generator_meta(self, auditor):
        html = '<meta name="generator" content="Ghost 5.0">'
        result = await auditor.detect_tech_stack(html, make_soup(html))
        assert "Ghost 5.0" in result.detected_platforms

    @pytest.mark.asyncio
    async def test_empty_returns_empty_platforms(self, auditor):
        html = "<html><body><p>Sin tech detectable</p></body></html>"
        result = await auditor.detect_tech_stack(html, make_soup(html))
        assert result.detected_platforms == []
        assert result.cms is None
        assert result.framework is None


class TestExtractEmails:
    def test_extracts_plain_email(self, auditor):
        emails = auditor._extract_emails("Escríbenos a info@miempresa.mx")
        assert "info@miempresa.mx" in emails

    def test_extracts_multiple_emails(self, auditor):
        html = "info@empresa.com o soporte@empresa.com"
        emails = auditor._extract_emails(html)
        assert len(emails) == 2

    def test_filters_example_domains(self, auditor):
        emails = auditor._extract_emails("usuario@example.com y real@negocio.mx")
        assert "usuario@example.com" not in emails
        assert "real@negocio.mx" in emails

    def test_returns_empty_on_no_emails(self, auditor):
        emails = auditor._extract_emails("<html><body><p>Sin email aquí</p></body></html>")
        assert emails == []


class TestExtractPhones:
    def test_extracts_mexican_phone(self, auditor):
        phones = auditor._extract_phones("+52 55 1234 5678")
        assert len(phones) > 0

    def test_extracts_usa_format(self, auditor):
        phones = auditor._extract_phones("Llama al (555) 123-4567")
        assert len(phones) > 0

    def test_returns_empty_on_no_phones(self, auditor):
        phones = auditor._extract_phones("<p>Sin teléfono</p>")
        assert phones == []


class TestCheckMobileFriendly:
    def test_responsive_viewport(self, auditor):
        soup = make_soup('<meta name="viewport" content="width=device-width, initial-scale=1">')
        assert auditor._check_mobile_friendly(soup) is True

    def test_no_viewport_meta(self, auditor):
        soup = make_soup("<html><body></body></html>")
        assert auditor._check_mobile_friendly(soup) is False

    def test_viewport_without_device_width(self, auditor):
        soup = make_soup('<meta name="viewport" content="width=1024">')
        assert auditor._check_mobile_friendly(soup) is False


class TestExtractCopyrightYear:
    def test_extracts_from_footer(self, auditor):
        soup = make_soup("<footer>© 2019 Mi Empresa</footer>")
        assert auditor._extract_copyright_year(soup) == 2019

    def test_extracts_copyright_keyword(self, auditor):
        soup = make_soup("<p>Copyright 2021 All rights reserved</p>")
        assert auditor._extract_copyright_year(soup) == 2021

    def test_copyright_symbol_in_body(self, auditor):
        soup = make_soup("<body><p>©2018 Empresa</p></body>")
        assert auditor._extract_copyright_year(soup) == 2018

    def test_returns_none_when_no_year(self, auditor):
        soup = make_soup("<html><body><p>Sin fechas aquí</p></body></html>")
        assert auditor._extract_copyright_year(soup) is None


class TestExtractTitle:
    def test_extracts_title_tag(self, auditor):
        soup = make_soup("<title>Mi Negocio | Servicios</title>")
        assert auditor._extract_title(soup) == "Mi Negocio | Servicios"

    def test_returns_none_without_title(self, auditor):
        soup = make_soup("<html><body></body></html>")
        assert auditor._extract_title(soup) is None


class TestExtractMetaDescription:
    def test_extracts_description(self, auditor):
        soup = make_soup('<meta name="description" content="Mejor plomero en CDMX">')
        assert auditor._extract_meta_description(soup) == "Mejor plomero en CDMX"

    def test_extracts_og_description_fallback(self, auditor):
        soup = make_soup('<meta property="og:description" content="Descripción OG">')
        assert auditor._extract_meta_description(soup) == "Descripción OG"

    def test_returns_none_without_description(self, auditor):
        soup = make_soup("<html><body></body></html>")
        assert auditor._extract_meta_description(soup) is None


class TestDetectContactForm:
    def test_detects_form_with_email_field(self, auditor):
        soup = make_soup('<form><input name="email"><button>Enviar</button></form>')
        assert auditor._detect_contact_form(soup) is True

    def test_detects_form_with_spanish_keywords(self, auditor):
        soup = make_soup('<form><input name="nombre"><input name="mensaje"></form>')
        assert auditor._detect_contact_form(soup) is True

    def test_no_form(self, auditor):
        soup = make_soup("<html><body><p>Sin formularios</p></body></html>")
        assert auditor._detect_contact_form(soup) is False

    def test_form_without_contact_keywords_returns_false(self, auditor):
        # Login form: no contact-related keywords in HTML attributes or text
        soup = make_soup('<form action="/login"><input type="password"><button type="submit">Login</button></form>')
        assert auditor._detect_contact_form(soup) is False


class TestExtractSocialLinks:
    def test_extracts_facebook(self, auditor):
        soup = make_soup('<a href="https://facebook.com/mibusiness">Facebook</a>')
        links = auditor._extract_social_links(soup, "https://example.com")
        assert "facebook" in links

    def test_extracts_instagram(self, auditor):
        soup = make_soup('<a href="https://instagram.com/mibusiness">IG</a>')
        links = auditor._extract_social_links(soup, "https://example.com")
        assert "instagram" in links

    def test_extracts_twitter_x(self, auditor):
        soup = make_soup('<a href="https://x.com/mibusiness">X</a>')
        links = auditor._extract_social_links(soup, "https://example.com")
        assert "twitter" in links

    def test_extracts_linkedin(self, auditor):
        soup = make_soup('<a href="https://linkedin.com/company/mi-empresa">LinkedIn</a>')
        links = auditor._extract_social_links(soup, "https://example.com")
        assert "linkedin" in links

    def test_extracts_youtube(self, auditor):
        soup = make_soup('<a href="https://youtube.com/channel/UCxxx">YouTube</a>')
        links = auditor._extract_social_links(soup, "https://example.com")
        assert "youtube" in links

    def test_extracts_tiktok(self, auditor):
        soup = make_soup('<a href="https://tiktok.com/@mibusiness">TikTok</a>')
        links = auditor._extract_social_links(soup, "https://example.com")
        assert "tiktok" in links

    def test_extracts_whatsapp(self, auditor):
        soup = make_soup('<a href="https://wa.me/521234567890">WhatsApp</a>')
        links = auditor._extract_social_links(soup, "https://example.com")
        assert "whatsapp" in links

    def test_no_social_links(self, auditor):
        soup = make_soup('<a href="/about">Acerca de</a>')
        links = auditor._extract_social_links(soup, "https://example.com")
        assert links == {}


class TestAuditMethod:
    @pytest.mark.asyncio
    async def test_raises_on_invalid_url(self, auditor):
        with pytest.raises(WebAuditError):
            await auditor.audit("no-es-una-url")

    @pytest.mark.asyncio
    async def test_raises_on_empty_url(self, auditor):
        with pytest.raises(WebAuditError):
            await auditor.audit("")

    @pytest.mark.asyncio
    async def test_returns_partial_result_when_fetch_fails(self, auditor):
        auditor.check_ssl = AsyncMock(return_value=SSLResult(is_valid=False))
        auditor._fetch_html = AsyncMock(side_effect=Exception("timeout"))

        result = await auditor.audit("http://unreachable.example.com")

        assert result is not None
        assert result.ssl.is_valid is False

    @pytest.mark.asyncio
    async def test_full_audit_with_mocked_network(self, auditor):
        html = """<html><head>
            <title>Plomero CDMX</title>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <meta name="description" content="Plomero profesional">
            <script>fbq("init","123");</script>
        </head><body>
            <a href="https://facebook.com/plomeroscdmx">FB</a>
            <footer>© 2020 Plomero CDMX</footer>
        </body></html>"""

        auditor.check_ssl = AsyncMock(return_value=SSLResult(is_valid=True))
        auditor._fetch_html = AsyncMock(return_value=html)

        result = await auditor.audit("https://plomero.com")

        assert result.page_title == "Plomero CDMX"
        assert result.mobile_friendly is True
        assert result.tracking.has_meta_pixel is True
        assert result.copyright_year == 2020
        assert result.meta_description == "Plomero profesional"
        assert result.load_time_ms is not None
        assert result.load_time_ms >= 0

    @pytest.mark.asyncio
    async def test_check_ssl_http_only(self, auditor):
        result = await auditor.check_ssl("http://nossl.example.com")
        assert result.is_valid is False
        assert "no SSL" in result.error_message
