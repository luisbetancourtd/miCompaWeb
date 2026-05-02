"""Ollama local LLM client - gratuito y privado."""

import json
from typing import Optional, List

import httpx

from micompaweb.application.ports.llm_client import (
    LLMClient,
    LLMError,
    VigencyResult,
    LLMProvider,
)


class OllamaClient:
    """Cliente para Ollama (LLM local).

    Ventajas:
    - Gratuito (sin costo API)
    - Privado (datos no salen de tu infraestructura)
    - Funciona offline
    - Sin rate limits

    Requisitos:
    - Ollama instalado: https://ollama.com/download
    - Modelo descargado: `ollama pull llama3.2`

    Docker Compose incluye servicio Ollama opcional.
    """

    DEFAULT_MODELS = ["llama3.2", "phi3", "gemma:2b", "qwen:7b"]

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "llama3.2",
        fallback_models: Optional[List[str]] = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.fallback_models = fallback_models or []
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Obtiene cliente HTTP."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=f"{self.base_url}/api",
                timeout=60.0,  # Modelos locales pueden ser lentos
            )
        return self._client

    async def _try_models(self, content: str, website_url: str, copyright_year) -> VigencyResult:
        """Intenta con modelos en orden hasta que uno funcione."""
        models_to_try = [self.model] + self.fallback_models

        for model in models_to_try:
            try:
                return await self._analyze_with_model(
                    model, content, website_url, copyright_year
                )
            except Exception as e:
                print(f"Ollama model {model} failed: {e}")
                continue

        raise LLMError("All Ollama models failed")

    async def _analyze_with_model(
        self,
        model: str,
        content: str,
        website_url: str,
        copyright_year,
    ) -> VigencyResult:
        """Analiza con un modelo específico."""
        client = await self._get_client()

        prompt = self._build_vigency_prompt(content, website_url, copyright_year)

        response = await client.post(
            "/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "format": "json",
                "options": {
                    "temperature": 0.1,
                    "num_predict": 500,
                },
            },
        )
        response.raise_for_status()
        data = response.json()

        result_text = data.get("response", "")
        result = json.loads(result_text)

        return VigencyResult(
            is_outdated=result.get("is_outdated"),
            confidence=result.get("confidence", 0.5),
            reason=result.get("reason", ""),
            snippet=result.get("snippet", ""),
            evidence=result.get("evidence", []),
            provider_used=LLMProvider.OLLAMA,
            cost_usd=0.0,  # Gratuito
        )

    async def analyze_vigency(
        self,
        content: str,
        website_url: str,
        copyright_year: Optional[int] = None,
    ) -> VigencyResult:
        """Analiza vigencia usando Ollama."""
        return await self._try_models(content, website_url, copyright_year)

    def _build_vigency_prompt(
        self,
        content: str,
        website_url: str,
        copyright_year: Optional[int],
    ) -> str:
        """Construye prompt para Ollama."""
        return f"""Analyze if this website content is outdated:

URL: {website_url}
Copyright: {copyright_year or "unknown"}

Content:
```
{content[:1500]}
```

Respond ONLY with valid JSON:
{{
    "is_outdated": true/false/null,
    "confidence": 0.0-1.0,
    "reason": "brief explanation",
    "snippet": "specific outdated text if any",
    "evidence": ["signal1", "signal2"]
}}

Outdated signals:
- Old copyright year (>2 years)
- Past dates mentioned as future
- Obviously old prices
- Expired promotions"""

    async def generate_opening_angle(
        self,
        lead_name: str,
        niche: str,
        pain_points: list[str],
    ) -> str:
        """Genera ángulo de apertura."""
        prompt = f"""Write a short sales opening message for:

Business: {lead_name}
Industry: {niche}
Pain points: {', '.join(pain_points)}

Requirements:
- 2-3 sentences
- Personalized
- Mention specific pain point
- Offer immediate value
- Sound human, not spammy

Respond with the message only."""

        client = await self._get_client()
        response = await client.post(
            "/generate",
            json={
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.7, "num_predict": 200},
            },
        )
        response.raise_for_status()
        data = response.json()

        return data.get("response", "").strip()

    async def is_available(self) -> bool:
        """Verifica si Ollama está corriendo."""
        try:
            client = await self._get_client()
            response = await client.get("/tags", timeout=5.0)
            return response.status_code == 200
        except Exception:
            return False

    @property
    def provider_name(self) -> str:
        return f"ollama_{self.model}"

    @property
    def is_local(self) -> bool:
        return True

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Siempre gratuito."""
        return 0.0
