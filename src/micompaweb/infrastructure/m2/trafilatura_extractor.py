"""M2 content extraction - trafilatura con fallback a BeautifulSoup."""

from typing import Optional, Dict, List
from dataclasses import dataclass


def _has_trafilatura() -> bool:
    try:
        import trafilatura
        return True
    except ImportError:
        return False


@dataclass
class ExtractedContent:
    title: str
    body: str
    author: Optional[str] = None
    date: Optional[str] = None
    url: str = ""
    images: List[str] = None
    language: Optional[str] = None
    word_count: int = 0
    extraction_method: str = ""

    def __post_init__(self):
        if self.images is None:
            self.images = []


class TrafilaturaExtractor:
    """Extractor de contenido con trafilatura (fallback a BS4)."""

    def __init__(self):
        self._has_traf = _has_trafilatura()

    @property
    def is_available(self) -> bool:
        return self._has_traf

    def extract(self, html: str, url: str = "", fallback: bool = True) -> ExtractedContent:
        """Extrae contenido de HTML."""
        if self._has_traf:
            try:
                import trafilatura
                result = trafilatura.extract(
                    html,
                    url=url,
                    include_images=True,
                    include_tables=False,
                    include_comments=False,
                    with_metadata=True,
                    output_format="json",
                )
                if result:
                    data = trafilatura.utils.load_json(result) if isinstance(result, str) else result
                    # Parse JSON output
                    if isinstance(data, dict):
                        return ExtractedContent(
                            title=data.get("title", ""),
                            body=data.get("raw_text", data.get("text", "")),
                            author=data.get("author"),
                            date=data.get("date"),
                            url=url,
                            images=data.get("images", []),
                            language=data.get("language"),
                            word_count=len(data.get("raw_text", "").split()) if "raw_text" in data else 0,
                            extraction_method="trafilatura",
                        )
            except Exception:
                pass

        if fallback:
            return self._fallback_extract(html, url)

        return ExtractedContent(title="", body="", url=url, extraction_method="none")

    def _fallback_extract(self, html: str, url: str) -> ExtractedContent:
        """Fallback con BeautifulSoup."""
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "lxml")
        title = soup.title.string if soup.title else ""
        # Remove script/style
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        body = soup.get_text(separator="\n", strip=True)
        return ExtractedContent(
            title=title,
            body=body,
            url=url,
            word_count=len(body.split()),
            extraction_method="bs4_fallback",
        )
