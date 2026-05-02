"""M2 local embeddings - FastEmbed wrapper."""

from typing import List, Optional
from dataclasses import dataclass


def _has_fastembed() -> bool:
    try:
        import fastembed
        return True
    except ImportError:
        return False


@dataclass
class EmbeddingResult:
    text: str
    vector: List[float]
    model_name: str
    dimension: int


class LocalEmbedder:
    """Embeddings locales con FastEmbed (no API keys)."""

    DEFAULT_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    FALLBACK_DIMENSION = 384

    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or self.DEFAULT_MODEL
        self._available = _has_fastembed()
        self._model = None
        if self._available:
            try:
                from fastembed import TextEmbedding
                self._model = TextEmbedding(model_name=self.model_name)
            except Exception:
                self._available = False

    @property
    def is_available(self) -> bool:
        return self._available

    def embed(self, texts: List[str]) -> List[EmbeddingResult]:
        """Genera embeddings para una lista de textos."""
        if not self._available or self._model is None:
            return [EmbeddingResult(text=t, vector=[], model_name="none", dimension=0) for t in texts]

        results = []
        vectors = list(self._model.embed(texts))
        for text, vec in zip(texts, vectors):
            vec_list = list(vec)
            results.append(EmbeddingResult(
                text=text,
                vector=vec_list,
                model_name=self.model_name,
                dimension=len(vec_list),
            ))
        return results

    def embed_single(self, text: str) -> EmbeddingResult:
        """Embedding para un solo texto."""
        results = self.embed([text])
        return results[0] if results else EmbeddingResult(text=text, vector=[], model_name="none", dimension=0)
