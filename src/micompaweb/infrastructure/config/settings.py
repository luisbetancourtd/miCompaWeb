"""Application settings - Pydantic Settings with env vars."""

from typing import Optional
from pathlib import Path

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Configuración de la aplicación vía variables de entorno.

    Todas las APIs son opcionales - la app funciona con --fixture
    o con datos cacheados sin configurar nada.
    """

    # API Keys (all optional)
    google_places_api_key: Optional[str] = Field(
        default=None,
        alias="GOOGLE_PLACES_API_KEY",
    )
    groq_api_key: Optional[str] = Field(
        default=None,
        alias="GROQ_API_KEY",
    )
    openrouter_api_key: Optional[str] = Field(
        default=None,
        alias="OPENROUTER_API_KEY",
    )

    # LLM Configuration
    ollama_base_url: str = Field(
        default="http://localhost:11434",
        alias="OLLAMA_BASE_URL",
    )
    default_llm_provider: str = Field(
        default="heuristic",
        alias="DEFAULT_LLM_PROVIDER",
    )

    # NocoDB Integration
    nocodb_url: Optional[str] = Field(
        default=None,
        alias="NOCODB_URL",
    )
    nocodb_api_token: Optional[str] = Field(
        default=None,
        alias="NOCODB_API_TOKEN",
    )
    nocodb_database_id: Optional[str] = Field(
        default=None,
        alias="NOCODB_DATABASE_ID",
    )

    # Cache & Storage
    cache_dir: Path = Field(
        default=Path("./projects/.cache"),
        alias="CACHE_DIR",
    )
    projects_dir: Path = Field(
        default=Path("./projects"),
        alias="PROJECTS_DIR",
    )

    # Cost Control
    max_daily_cost_usd: float = Field(
        default=2.00,
        alias="MAX_DAILY_COST_USD",
    )
    enable_cost_tracking: bool = Field(
        default=True,
        alias="ENABLE_COST_TRACKING",
    )

    # Feature Flags
    enable_vigency_check: bool = Field(
        default=True,
        alias="ENABLE_VIGENCY_CHECK",
    )
    enable_nocodb_sync: bool = Field(
        default=True,
        alias="ENABLE_NOCODB_SYNC",
    )

    class Config:
        """Pydantic config."""
        env_file = ".env"
        env_file_encoding = "utf-8"

    @property
    def has_places_api(self) -> bool:
        """Check if Google Places API is configured."""
        return bool(self.google_places_api_key)

    @property
    def has_llm_cloud(self) -> bool:
        """Check if any cloud LLM is configured."""
        return bool(self.groq_api_key) or bool(self.openrouter_api_key)

    @property
    def has_nocodb(self) -> bool:
        """Check if NocoDB is configured."""
        return bool(self.nocodb_url and self.nocodb_api_token)

    def ensure_directories(self) -> None:
        """Create necessary directories."""
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.projects_dir.mkdir(parents=True, exist_ok=True)