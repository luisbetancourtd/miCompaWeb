"""M2 pipeline orchestrator - anti-bot + RAG stack completo."""

from typing import List, Optional, Dict
from dataclasses import dataclass, field

from micompaweb.infrastructure.browser.orchestrator import FetchOrchestrator, Strategy
from micompaweb.infrastructure.m2.tls_fetcher import TLSFetcher, TLSFetchResult
from micompaweb.infrastructure.m2.trafilatura_extractor import TrafilaturaExtractor, ExtractedContent
from micompaweb.infrastructure.m2.chunker import SemanticChunker, Chunk
from micompaweb.infrastructure.m2.embedder import LocalEmbedder, EmbeddingResult
from micompaweb.infrastructure.m2.vector_store import LocalVectorStore, VectorPoint


@dataclass
class M2PipelineResult:
    """Resultado del pipeline M2 completo."""
    url: str
    strategy_used: str
    fetch_success: bool
    content: Optional[ExtractedContent] = None
    chunks: List[Chunk] = field(default_factory=list)
    embeddings: List[EmbeddingResult] = field(default_factory=list)
    stored: bool = False
    error: Optional[str] = None


class M2Pipeline:
    """Pipeline M2: anti-bot → extract → chunk → embed → store."""

    def __init__(
        self,
        use_tls: bool = True,
        use_vector_store: bool = True,
        chunk_size: int = 500,
        vector_dimension: int = 384,
    ):
        self.m1_orchestrator = FetchOrchestrator()
        self.tls_fetcher = TLSFetcher() if use_tls else None
        self.extractor = TrafilaturaExtractor()
        self.chunker = SemanticChunker(chunk_size=chunk_size)
        self.embedder = LocalEmbedder()
        self.vector_store = LocalVectorStore(dimension=vector_dimension) if use_vector_store else None

    def process(self, url: str, store_in_vector_db: bool = True) -> M2PipelineResult:
        """Ejecuta el pipeline completo M2 sobre una URL."""
        result = M2PipelineResult(url=url, strategy_used="", fetch_success=False)

        # Paso 1: Fetch con anti-bot
        fetch_result = self._fetch(url)
        if not fetch_result.success:
            result.error = f"Fetch failed: {fetch_result.error}"
            return result
        result.fetch_success = True
        result.strategy_used = fetch_result.tls_fingerprint or "fast"

        # Paso 2: Extract content
        content = self.extractor.extract(fetch_result.text, url=url)
        result.content = content

        # Paso 3: Chunk
        chunks = self.chunker.chunk(content.body)
        result.chunks = chunks

        # Paso 4: Embed (si disponible)
        if self.embedder.is_available and chunks:
            texts = [c.text for c in chunks]
            embeddings = self.embedder.embed(texts)
            result.embeddings = embeddings

            # Paso 5: Store in vector DB
            if store_in_vector_db and self.vector_store and self.vector_store.is_available:
                points = [
                    VectorPoint(
                        id=f"{url}#{i}",
                        vector=e.vector,
                        payload={"url": url, "chunk_index": i, "text": e.text},
                    )
                    for i, e in enumerate(embeddings)
                    if e.vector  # solo si embedding generó vector
                ]
                if points:
                    result.stored = self.vector_store.upsert(points)

        return result

    def _fetch(self, url: str) -> TLSFetchResult:
        """Fetch con la mejor estrategia disponible."""
        strategy = self.m1_orchestrator.classify_domain(url)

        # Si es dominio duro y TLS disponible, usar curl_cffi
        if strategy in (Strategy.STRONG, Strategy.HEAVY) and self.tls_fetcher and self.tls_fetcher.is_available:
            return self.tls_fetcher.fetch_with_fallback(url)

        # Fallback a M1 FAST (httpx + headers rotados)
        profile = self.m1_orchestrator.emulator.get_random_profile()
        headers = self.m1_orchestrator.emulator.get_headers(profile)

        try:
            import httpx
            resp = httpx.get(url, headers=headers, timeout=30, follow_redirects=True)
            return TLSFetchResult(
                url=url,
                status_code=resp.status_code,
                text=resp.text,
                headers=dict(resp.headers),
                success=200 <= resp.status_code < 400,
                tls_fingerprint="m1_fast",
            )
        except Exception as e:
            return TLSFetchResult(
                url=url, status_code=0, text="", headers={},
                success=False, error=str(e),
            )

    def query(
        self,
        query_text: str,
        limit: int = 5,
    ) -> List[VectorPoint]:
        """Query semántica sobre el vector store."""
        if not self.embedder.is_available:
            return []

        embedding = self.embedder.embed_single(query_text)
        if not embedding.vector:
            return []

        return self.vector_store.search(embedding.vector, limit=limit)
