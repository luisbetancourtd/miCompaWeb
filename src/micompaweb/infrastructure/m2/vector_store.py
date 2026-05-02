"""M2 local vector store - Qdrant wrapper (in-memory como fallback)."""

from typing import List, Optional, Dict
from dataclasses import dataclass


def _has_qdrant() -> bool:
    try:
        import qdrant_client
        return True
    except ImportError:
        return False


@dataclass
class VectorPoint:
    id: str
    vector: List[float]
    payload: Dict
    score: Optional[float] = None


class LocalVectorStore:
    """Vector store local con Qdrant (in-memory fallback)."""

    def __init__(self, collection_name: str = "micompaweb", dimension: int = 384):
        self.collection_name = collection_name
        self.dimension = dimension
        self._available = _has_qdrant()
        self._client = None
        self._in_memory: Dict[str, VectorPoint] = {}

        if self._available:
            try:
                from qdrant_client import QdrantClient
                self._client = QdrantClient(":memory:")
                self._client.create_collection(
                    collection_name=collection_name,
                    vectors_config={"size": dimension, "distance": "Cosine"},
                )
            except Exception:
                self._available = False

    @property
    def is_available(self) -> bool:
        return self._available

    def upsert(self, points: List[VectorPoint]) -> bool:
        """Inserta/actualiza puntos vectoriales."""
        # Siempre guardar en memoria como backup
        for p in points:
            self._in_memory[p.id] = p

        if not self._available or self._client is None:
            return True

        try:
            from qdrant_client.models import PointStruct
            qdrant_points = [
                PointStruct(id=p.id, vector=p.vector, payload=p.payload)
                for p in points
            ]
            self._client.upsert(
                collection_name=self.collection_name,
                points=qdrant_points,
            )
            return True
        except Exception:
            return True  # in-memory backup asegura disponibilidad

    def search(
        self,
        vector: List[float],
        limit: int = 5,
        filter_payload: Optional[Dict] = None,
    ) -> List[VectorPoint]:
        """Búsqueda semántica por similitud de vectores."""
        if not self._available or self._client is None:
            return self._fallback_search(vector, limit)

        try:
            results = self._client.search(
                collection_name=self.collection_name,
                query_vector=vector,
                limit=limit,
            )
            return [
                VectorPoint(
                    id=str(r.id),
                    vector=r.vector if hasattr(r, "vector") else [],
                    payload=r.payload,
                    score=r.score,
                )
                for r in results
            ]
        except Exception:
            return self._fallback_search(vector, limit)

    def _fallback_search(self, query_vector: List[float], limit: int) -> List[VectorPoint]:
        """Fallback in-memory con similitud coseno."""
        import math
        def cosine(a, b):
            dot = sum(x * y for x, y in zip(a, b))
            norm_a = math.sqrt(sum(x * x for x in a)) or 1
            norm_b = math.sqrt(sum(x * x for x in b)) or 1
            return dot / (norm_a * norm_b)

        scored = []
        for p in self._in_memory.values():
            if p.vector:
                score = cosine(query_vector, p.vector)
                scored.append((score, p))
        scored.sort(reverse=True)
        return [p for _, p in scored[:limit]]

    def count(self) -> int:
        qdrant_count = 0
        if self._available and self._client:
            try:
                result = self._client.count(collection_name=self.collection_name)
                qdrant_count = getattr(result, "count", 0)
            except Exception:
                pass
        return qdrant_count + len(self._in_memory)
