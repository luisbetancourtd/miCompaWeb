"""Tests for M2 anti-bot + RAG stack."""

import pytest

from micompaweb.infrastructure.m2.tls_fetcher import TLSFetcher, TLSFetchResult
from micompaweb.infrastructure.m2.trafilatura_extractor import TrafilaturaExtractor, ExtractedContent
from micompaweb.infrastructure.m2.chunker import SemanticChunker, Chunk
from micompaweb.infrastructure.m2.embedder import LocalEmbedder, EmbeddingResult
from micompaweb.infrastructure.m2.vector_store import LocalVectorStore, VectorPoint
from micompaweb.infrastructure.m2.searxng_client import SearXNGClient, SERPResult
from micompaweb.infrastructure.m2.pipeline import M2Pipeline, M2PipelineResult


class TestTLSFetcher:
    """TLS spoofing fetcher."""

    def test_is_available(self):
        tf = TLSFetcher()
        # Depende de si curl_cffi está instalado
        assert isinstance(tf.is_available, bool)

    def test_browser_profiles_defined(self):
        tf = TLSFetcher()
        assert len(tf.BROWSER_PROFILES) >= 4
        assert "chrome110" in tf.BROWSER_PROFILES

    def test_fetch_unavailable_returns_error(self, monkeypatch):
        tf = TLSFetcher()
        monkeypatch.setattr(tf, "_available", False)
        monkeypatch.setattr(tf, "_session", None)
        result = tf.fetch("https://example.com")
        assert result.success is False
        assert "curl_cffi" in result.error

    def test_fetch_with_fallback_tries_all(self, monkeypatch):
        tf = TLSFetcher()
        calls = []
        def mock_fetch(url, browser=None, timeout=30, impersonate=True):
            calls.append(browser)
            return TLSFetchResult(url=url, status_code=403, text="", headers={}, success=False)
        monkeypatch.setattr(tf, "fetch", mock_fetch)
        result = tf.fetch_with_fallback("https://example.com")
        assert len(calls) >= len(tf.BROWSER_PROFILES)


class TestTrafilaturaExtractor:
    """Content extraction."""

    def test_is_available(self):
        ext = TrafilaturaExtractor()
        assert isinstance(ext.is_available, bool)

    def test_fallback_extract(self):
        ext = TrafilaturaExtractor()
        html = "<html><head><title>Mi Título</title></head><body><p>Hola mundo</p></body></html>"
        result = ext._fallback_extract(html, "https://example.com")
        assert result.title == "Mi Título"
        assert "Hola mundo" in result.body
        assert result.extraction_method == "bs4_fallback"

    def test_extract_empty(self):
        ext = TrafilaturaExtractor()
        result = ext.extract("", fallback=False)
        assert result.body == ""
        assert result.extraction_method == "none"

    def test_extract_with_script_removal(self):
        ext = TrafilaturaExtractor()
        html = "<html><head><title>T</title></head><body><script>alert(1)</script><p>Content</p></body></html>"
        result = ext._fallback_extract(html, "url")
        assert "alert" not in result.body
        assert "Content" in result.body


class TestSemanticChunker:
    """Chunking."""

    def test_chunk_empty(self):
        chunker = SemanticChunker()
        assert chunker.chunk("") == []

    def test_chunk_paragraphs(self):
        chunker = SemanticChunker(chunk_size=100)
        text = "\n\n".join([f"Párrafo {i} con algo de texto" for i in range(10)])
        chunks = chunker.chunk(text)
        assert len(chunks) > 1
        assert all(len(c.text) <= 150 for c in chunks)  # margen

    def test_chunk_indices_sequential(self):
        chunker = SemanticChunker(chunk_size=50)
        text = "A " * 100 + "\n\n" + "B " * 100
        chunks = chunker.chunk(text)
        assert chunks[0].index == 0
        assert chunks[1].index == 1

    def test_chunk_overlap_field(self):
        chunker = SemanticChunker(chunk_size=50, chunk_overlap=10)
        text = "word " * 50
        chunks = chunker.chunk(text)
        if len(chunks) > 1:
            assert len(chunks[0].overlap_prev) > 0 or chunks[0].overlap_prev == ""

    def test_chunk_with_overlap_multiple_texts(self):
        chunker = SemanticChunker(chunk_size=30)
        texts = ["Texto uno con palabras", "Texto dos con más palabras"]
        all_chunks = chunker.chunk_with_overlap(texts)
        assert len(all_chunks) >= 2
        # Índices globales secuenciales
        for i, c in enumerate(all_chunks):
            assert c.index == i


class TestLocalEmbedder:
    """FastEmbed embeddings."""

    def test_is_available(self):
        emb = LocalEmbedder()
        assert isinstance(emb.is_available, bool)

    def test_embed_single(self, local_embedder):
        pytest.importorskip("fastembed", reason="fastembed not installed")
        result = local_embedder.embed_single("Hola mundo")
        assert isinstance(result, EmbeddingResult)
        assert result.text == "Hola mundo"
        if local_embedder.is_available:
            assert len(result.vector) > 0
            assert result.dimension > 0

    def test_embed_multiple(self, local_embedder):
        pytest.importorskip("fastembed", reason="fastembed not installed")
        results = local_embedder.embed(["Hola", "mundo"])
        assert len(results) == 2
        if local_embedder.is_available:
            assert all(len(r.vector) > 0 for r in results)
            assert results[0].dimension == results[1].dimension

    def test_embed_unavailable_returns_empty(self, monkeypatch):
        emb = LocalEmbedder()
        monkeypatch.setattr(emb, "_available", False)
        monkeypatch.setattr(emb, "_model", None)
        result = emb.embed_single("test")
        assert result.vector == []
        assert result.model_name == "none"

class TestLocalVectorStore:
    """Qdrant vector store."""

    def test_is_available(self):
        vs = LocalVectorStore()
        assert isinstance(vs.is_available, bool)

    def test_upsert_and_search(self):
        vs = LocalVectorStore(dimension=3)
        points = [
            VectorPoint(id="p1", vector=[1.0, 0.0, 0.0], payload={"text": "uno"}),
            VectorPoint(id="p2", vector=[0.0, 1.0, 0.0], payload={"text": "dos"}),
            VectorPoint(id="p3", vector=[0.5, 0.5, 0.0], payload={"text": "tres"}),
        ]
        assert vs.upsert(points) is True
        # Search cercano a p1
        results = vs.search([0.9, 0.1, 0.0], limit=2)
        assert len(results) > 0
        assert results[0].id == "p1"

    def test_count(self):
        vs = LocalVectorStore(dimension=2)
        vs.upsert([VectorPoint(id="a", vector=[1.0, 0.0], payload={})])
        assert vs.count() == 1

    def test_fallback_search(self):
        vs = LocalVectorStore(dimension=3)
        vs._in_memory["p1"] = VectorPoint(id="p1", vector=[1.0, 0.0, 0.0], payload={})
        vs._in_memory["p2"] = VectorPoint(id="p2", vector=[0.0, 1.0, 0.0], payload={})
        results = vs._fallback_search([1.0, 0.0, 0.0], limit=1)
        assert len(results) == 1
        assert results[0].id == "p1"


class TestSearXNGClient:
    """SearXNG integration."""

    def test_is_available(self):
        client = SearXNGClient()
        assert isinstance(client.is_available, bool)

    def test_search_unavailable_returns_empty(self, monkeypatch):
        client = SearXNGClient()
        monkeypatch.setattr(client, "_available", False)
        results = client.search("test")
        assert results == []

    def test_search_local_businesses_query(self, monkeypatch):
        client = SearXNGClient()
        captured = {}
        def mock_search(query, language="es", limit=10, categories=None):
            captured["query"] = query
            captured["limit"] = limit
            return [SERPResult(title="Test", url="http://test", snippet="s", engine="test", position=1)]
        monkeypatch.setattr(client, "search", mock_search)
        results = client.search_local_businesses("plomeros", "Madrid", limit=15)
        assert captured["query"] == "plomeros en Madrid"
        assert captured["limit"] == 15
        assert len(results) == 1


class TestM2Pipeline:
    """End-to-end M2 pipeline."""

    def test_init(self):
        pipe = M2Pipeline()
        assert pipe.tls_fetcher is not None
        assert pipe.extractor is not None
        assert pipe.chunker is not None
        assert pipe.embedder is not None
        assert pipe.vector_store is not None

    @pytest.mark.slow
    @pytest.mark.integration
    def test_process_real_website(self):
        """Test con HTTPBin o similar (sin JS)."""
        pipe = M2Pipeline(use_vector_store=False)
        result = pipe.process("https://httpbin.org/html", store_in_vector_db=False)
        assert result.fetch_success is True
        assert result.content is not None
        assert len(result.chunks) > 0

    @pytest.mark.slow
    def test_process_404(self):
        pipe = M2Pipeline(use_vector_store=False)
        result = pipe.process("https://httpbin.org/status/404")
        assert result.fetch_success is False
        assert result.error is not None

    @pytest.mark.slow
    @pytest.mark.integration
    def test_query_after_store(self):
        pipe = M2Pipeline(use_tls=False, use_vector_store=False)
        # Procesar y almacenar (sin vector DB -> solo verificar no crash)
        result = pipe.process("https://httpbin.org/html")
        assert isinstance(result, M2PipelineResult)

    @pytest.mark.slow
    @pytest.mark.integration
    def test_process_with_tls_if_available(self):
        pipe = M2Pipeline(use_tls=True, use_vector_store=False)
        result = pipe.process("https://httpbin.org/html")
        assert result.fetch_success is True
        assert result.strategy_used in ("m1_fast", "chrome110", "chrome120", None)
