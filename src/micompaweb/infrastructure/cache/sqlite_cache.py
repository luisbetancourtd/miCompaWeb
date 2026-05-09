"""SQLite cache implementation - persistencia offline-first."""

import json
import sqlite3
from typing import Optional, Any, List
from datetime import datetime, timedelta
from pathlib import Path

import aiosqlite

from micompaweb.application.ports.cache import Cache, CacheEntry


class SQLiteCache:
    """Caché persistente usando SQLite.

    Ideal para:
    - Modo offline (datos previamente buscados)
    - Reducir costos API (no repetir búsquedas)
    - Testing reproducible
    - Performance (SQLite es muy rápido para lecturas)
    """

    SCHEMA = """
    CREATE TABLE IF NOT EXISTS cache_entries (
        key TEXT PRIMARY KEY,
        data TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        expires_at TIMESTAMP,
        source TEXT DEFAULT 'unknown',
        hit_count INTEGER DEFAULT 0
    );

    CREATE INDEX IF NOT EXISTS idx_expires ON cache_entries(expires_at);
    CREATE INDEX IF NOT EXISTS idx_source ON cache_entries(source);
    """

    def __init__(self, db_path: Path):
        """Inicializa caché.

        Args:
            db_path: Ruta al archivo SQLite
        """
        self.db_path = db_path
        self._initialized = False

    async def _init_db(self) -> None:
        """Inicializa schema si es necesario."""
        if self._initialized:
            return

        async with aiosqlite.connect(self.db_path) as db:
            await db.executescript(self.SCHEMA)
            await db.commit()

        self._initialized = True

    async def get(self, key: str) -> Optional[Any]:
        """Obtiene valor del caché."""
        await self._init_db()

        async with aiosqlite.connect(self.db_path) as db:
            # Verificar si existe y no expiró
            cursor = await db.execute(
                """
                SELECT data FROM cache_entries
                WHERE key = ? AND (expires_at IS NULL OR expires_at > ?)
                """,
                (key, datetime.now()),
            )
            row = await cursor.fetchone()

            if row:
                # Incrementar hit count
                await db.execute(
                    "UPDATE cache_entries SET hit_count = hit_count + 1 WHERE key = ?",
                    (key,),
                )
                await db.commit()

                # Deserializar
                try:
                    return json.loads(row[0])
                except json.JSONDecodeError:
                    return None

        return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: Optional[int] = None,
    ) -> None:
        """Guarda valor en caché."""
        await self._init_db()

        # Serializar
        data = json.dumps(value, default=self._json_encoder)

        # Calcular expiración
        expires_at = None
        if ttl_seconds:
            expires_at = datetime.now() + timedelta(seconds=ttl_seconds)

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT OR REPLACE INTO cache_entries
                (key, data, expires_at, source)
                VALUES (?, ?, ?, ?)
                """,
                (key, data, expires_at, "application"),
            )
            await db.commit()

    async def exists(self, key: str) -> bool:
        """Verifica si clave existe y no expiró."""
        await self._init_db()

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                SELECT 1 FROM cache_entries
                WHERE key = ? AND (expires_at IS NULL OR expires_at > ?)
                """,
                (key, datetime.now()),
            )
            return await cursor.fetchone() is not None

    async def delete(self, key: str) -> bool:
        """Elimina entrada del caché."""
        await self._init_db()

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "DELETE FROM cache_entries WHERE key = ?",
                (key,),
            )
            await db.commit()
            return cursor.rowcount > 0

    async def clear(self) -> None:
        """Limpia todo el caché."""
        await self._init_db()

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM cache_entries")
            await db.commit()

    async def get_stats(self) -> dict:
        """Estadísticas del caché."""
        await self._init_db()

        async with aiosqlite.connect(self.db_path) as db:
            # Total entries
            cursor = await db.execute("SELECT COUNT(*) FROM cache_entries")
            total = (await cursor.fetchone())[0]

            # Expired entries
            cursor = await db.execute(
                "SELECT COUNT(*) FROM cache_entries WHERE expires_at < ?",
                (datetime.now(),),
            )
            expired = (await cursor.fetchone())[0]

            # Total hits
            cursor = await db.execute(
                "SELECT COALESCE(SUM(hit_count), 0) FROM cache_entries"
            )
            total_hits = (await cursor.fetchone())[0]

            return {
                "total_entries": total,
                "expired_entries": expired,
                "active_entries": total - expired,
                "total_hits": total_hits,
                "db_size_bytes": self.db_path.stat().st_size if self.db_path.exists() else 0,
            }

    def make_key(self, *parts: str) -> str:
        """Crea clave consistente."""
        return "_".join(p.lower().replace(" ", "_") for p in parts if p)

    @staticmethod
    def _json_encoder(obj: Any) -> Any:
        """Encoder JSON para tipos especiales."""
        if hasattr(obj, "model_dump"):
            # Pydantic model
            return obj.model_dump()
        if hasattr(obj, "isoformat"):
            # datetime
            return obj.isoformat()
        if hasattr(obj, "value"):
            # Enum
            return obj.value
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
