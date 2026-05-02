"""Groq Cloud LLM client - rápido y económico."""

import json
import httpx
from typing import Optional

from micompaweb.application.ports.llm_client import (
    LLMClient,
    LLMError,
    VigencyResult,
    LLMProvider,
)


class GroqClient:
    """Cliente para Groq Cloud API.

    Ventajas:
    - Muy rápido (inferencia optimizada)
    - Económico (~$0.0001 por llamada)
    - Modelos de alta calidad (Llama, Mixtral)

    Docs: https://console.groq.com/docs
    """

    BASE_URL = "https://api.groq.com/openai/v1"
    DEFAULT_MODEL = "llama-3.3-70b-versatile"

    def __init__(self, api_key: str, model: str = DEFAULT_MODEL):
        self.api_key = api_key
        self.model = model
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Obtiene cliente HTTP."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.BASE_URL,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                timeout=30.0,
            )
        return self._client

    async def analyze_vigency(
        self,
        content: str,
        website_url: str,
        copyright_year: Optional[int] = None,
    ) -> VigencyResult:
        """Analiza vigencia de contenido via Groq."""
        client = await self._get_client()

        # Construir prompt
        prompt = self._build_vigency_prompt(content, website_url, copyright_year)

        try:
            response = await client.post(
                "/chat/completions",
                json={
                    "model": self.model,
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "Eres un analista de contenido web. "
                                "Analiza si el contenido está desactualizado. "
                                "Responde SOLO en JSON válido."
                            ),
                        },
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0.1,
                    "max_tokens": 500,
                    "response_format": {"type": "json_object"},
                },
            )
            response.raise_for_status()
            data = response.json()

            # Parsear respuesta
            result_text = data["choices"][0]["message"]["content"]
            result = json.loads(result_text)

            return VigencyResult(
                is_outdated=result.get("is_outdated"),
                confidence=result.get("confidence", 0.5),
                reason=result.get("reason", ""),
                snippet=result.get("snippet", ""),
                evidence=result.get("evidence", []),
                provider_used=LLMProvider.GROQ,
                cost_usd=self._estimate_cost(data.get("usage", {})),
            )

        except json.JSONDecodeError as e:
            raise LLMError(f"Invalid JSON response: {e}")
        except httpx.HTTPError as e:
            raise LLMError(f"Groq API error: {e}")
        except Exception as e:
            raise LLMError(f"Unexpected error: {e}")

    def _build_vigency_prompt(
        self,
        content: str,
        website_url: str,
        copyright_year: Optional[int],
    ) -> str:
        """Construye prompt para análisis de vigencia."""
        prompt = f"""Analiza si el siguiente contenido web está desactualizado:

URL: {website_url}
{"Copyright Year: " + str(copyright_year) if copyright_year else ""}

Contenido:
```
{content[:2000]}  # Limitar a 2000 chars
```

Responde en JSON con este formato exacto:
{{
    "is_outdated": true/false/null (null si no puedes determinar),
    "confidence": 0.0-1.0 (tu confianza en la respuesta),
    "reason": "explicación breve",
    "snippet": "texto específico que indicó desactualización",
    "evidence": ["lista", "de", "señales"]
}}

Señales de desactualización:
- Año de copyright viejo (>2 años)
- Promociones expiradas (fechas pasadas)
- Precios obviamente desactualizados
- Eventos pasados mencionados como futuros
- Diseño muy antiguo mencionado explícitamente"""

        return prompt

    def _estimate_cost(self, usage: dict) -> float:
        """Estima costo en USD.

        Groq pricing (aprox):
        - Input: $0.0001 / 1K tokens
        - Output: $0.0001 / 1K tokens
        """
        input_tokens = usage.get("prompt_tokens", 0)
        output_tokens = usage.get("completion_tokens", 0)

        rate = 0.0001 / 1000  # $0.0001 por 1K tokens
        return (input_tokens + output_tokens) * rate

    async def generate_opening_angle(
        self,
        lead_name: str,
        niche: str,
        pain_points: list[str],
    ) -> str:
        """Genera ángulo de apertura."""
        prompt = f"""Genera un mensaje de apertura comercial para:

Negocio: {lead_name}
Nicho: {niche}
Pain points detectados: {', '.join(pain_points)}

El mensaje debe:
1. Ser corto (2-3 oraciones)
2. Personalizado al negocio
3. Mencionar un pain point específico
4. Ofrecer valor inmediato
5. No sonar genérico ni como spam

Responde solo con el mensaje, sin explicaciones."""

        client = await self._get_client()
        response = await client.post(
            "/chat/completions",
            json={
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "Eres un vendedor experto de servicios web. "
                            "Escribes mensajes de apertura personalizados."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.7,
                "max_tokens": 200,
            },
        )
        response.raise_for_status()
        data = response.json()

        return data["choices"][0]["message"]["content"].strip()

    def is_available(self) -> bool:
        """Verifica disponibilidad."""
        return bool(self.api_key)

    @property
    def provider_name(self) -> str:
        return "groq"

    @property
    def is_local(self) -> bool:
        return False

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Estima costo."""
        rate = 0.0001 / 1000
        return (input_tokens + output_tokens) * rate
