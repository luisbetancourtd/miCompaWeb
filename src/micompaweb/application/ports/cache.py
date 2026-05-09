"""Cache protocol - contrato para sistemas de caché."""

from typing import Protocol, Optional, Any
from datetime import datetime
from dataclasses import dataclass


class CacheError(Exception):
    """Error en operación de caché."""
    pass


@dataclass
class CacheEntry:
    """Entrada de caché con metadata."""
    key: str
    data: Any
    created_at: datetime
    expires_at: Optional[datetime]
    source: str
    hit_count: int = 0


class Cache(Protocol):
    """Contrato para sistemas de caché.

    Implementaciones:
    - SQLiteCache: Persistente, offline-first
    - MemoryCache: Volátil, rápido
    - RedisCache: Distribuido (futuro)
    """

    async def get(self, key: str) -> Optional[Any]:
        """Obtiene valor del caché.

        Args:
            key: Clave de búsqueda

        Returns:
            Valor o None si no existe/expiró
        """
        ...

    async def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: Optional[int] = None,
    ) -> None:
        """Guarda valor en caché.

        Args:
            key: Clave única
            value: Valor a guardar (debe ser serializable)
            ttl_seconds: Tiempo de vida, None = sin expiración
        """
        ...

    async def exists(self, key: str) -> bool:
        """Verifica si la clave existe y no expiró."""
        ...

    async def delete(self, key: str) -> bool:
        """Elimina entrada del caché.

        Returns:
            True si existía y se eliminó
        """
        ...

    async def clear(self) -> None:
        """Limpia todo el caché."""
        ...

    async def get_stats(self) -> dict:
        """Retorna estadísticas del caché.

        Returns:
            Dict con: size, hits, misses, hit_rate
        """
        ...

    def make_key(self, *parts: str) -> str:
        """Crea clave consistente a partir de partes.

        Args:
            *parts: Partes de la clave

        Returns:
            Clave normalizada (ej: "plomeros_cdmx_es")
        """
        ...