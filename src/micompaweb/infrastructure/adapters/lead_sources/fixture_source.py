"""Fixture lead source - datos de prueba para desarrollo offline."""

import random
from typing import List, Optional
from datetime import datetime

from micompaweb.domain.models import Lead, WebsiteStatus, GBPHealth, PriorityTier
from micompaweb.application.ports.lead_source import (
    LeadSource,
    SourceHealth,
    CostEstimate,
)


class FixtureSource:
    """Fuente de leads ficticios para desarrollo y testing.

    Genera datos realistas sin costo API, ideal para:
    - Desarrollo offline
    - Testing unitario
    - CI/CD pipelines
    - Demos sin API keys
    """

    FIRST_NAMES = [
        "Express", "Rápido", "Pro", "Master", "Elite", "Premium", "Local",
        "Express", "Total", "Completo", "Solución", "Servicio", "Express",
    ]

    DOMAINS = [
        "example.com", "test.local", "demo.site", "fixture.net", "mock.org",
        "test.com", "demo.local", "example.org", "fixture.com",
    ]

    CITIES = [
        "Ciudad de México", "Guadalajara", "Monterrey", "Puebla", "Tijuana",
        "Cancún", "Mérida", "Querétaro", "León", "Toluca",
    ]

    def __init__(self, seed: Optional[int] = None):
        """Inicializa fuente de fixtures.

        Args:
            seed: Semilla para reproducibilidad
        """
        self._rng = random.Random(seed)

    async def search(
        self,
        niche: str,
        location: str,
        radius_meters: int = 10000,
        max_results: int = 100,
        language: str = "es",
    ) -> List[Lead]:
        """Genera leads ficticios."""
        # Usar semilla basada en nicho+ubicación para consistencia
        seed_str = f"{niche}-{location}-{max_results}"
        self._rng.seed(seed_str)

        leads = []
        for i in range(max_results):
            lead = self._generate_fixture_lead(niche, location, i)
            leads.append(lead)

        return leads

    async def get_details(self, external_id: str, language: str = "es") -> Optional[Lead]:
        """Genera detalles para un ID fixture."""
        # Parsear el external_id
        if not external_id.startswith("fixture_"):
            return None

        # Extraer índice del ID
        try:
            idx = int(external_id.split("_")[1])
            return self._generate_fixture_lead("generic", "Anywhere", idx)
        except (IndexError, ValueError):
            return None

    def health_check(self) -> SourceHealth:
        """Siempre saludable."""
        return SourceHealth(
            is_healthy=True,
            message="Fixture source always available",
        )

    def estimate_cost(self, num_results: int) -> CostEstimate:
        """Gratuito."""
        return CostEstimate(
            usd_amount=0.0,
            requests_count=0,
            source_name=self.source_name,
        )

    @property
    def source_name(self) -> str:
        return "fixture"

    @property
    def supports_caching(self) -> bool:
        return False  # No necesita caché, ya es gratuito

    def _generate_fixture_lead(self, niche: str, location: str, index: int) -> Lead:
        """Genera un lead fixture realista."""
        # Nombre del negocio
        suffix = self._rng.choice(self.FIRST_NAMES)
        business_name = f"{niche.title()} {suffix} {index + 1}"

        # Determinar website status (distribución realista)
        website_roll = self._rng.random()
        if website_roll < 0.40:  # 40% sin web
            website_url = None
            website_status = WebsiteStatus.NONE
        elif website_roll < 0.55:  # 15% HTTP only
            website_url = f"http://{self._rng.choice(self.DOMAINS)}/business{index}"
            website_status = WebsiteStatus.HTTP_ONLY
        else:  # 45% con HTTPS
            website_url = f"https://www.{self._rng.choice(self.DOMAINS)}/business{index}"
            website_status = WebsiteStatus.EXISTS

        # Rating y reviews (distribución realista)
        rating = self._rng.choice([3.5, 4.0, 4.2, 4.5, 4.8, 5.0])
        review_count = self._rng.randint(3, 200)

        # Ciudad basada en location o aleatoria
        if location in self.CITIES:
            city = location
        else:
            city = self._rng.choice(self.CITIES)

        # Teléfono ficticio mexicano
        phone = f"+52 55 {self._rng.randint(1000, 9999)} {self._rng.randint(1000, 9999)}"

        # Email
        email = f"contacto{business_name.lower().replace(' ', '')}@example.com"

        # Fecha de creación aleatoria en los últimos 2 años
        created_at = datetime.fromtimestamp(
            datetime.now().timestamp() - self._rng.randint(0, 63072000)
        )

        return Lead(
            id=f"fixture_{index}_{int(datetime.now().timestamp())}",
            external_id=f"fixture_{index}",
            source=self.source_name,
            business_name=business_name,
            category=niche,
            niche=niche,
            phone=phone,
            email=email,
            website_url=website_url,
            website_status=website_status,
            address=f"Calle {self._rng.randint(1, 200)} #{self._rng.randint(1, 100)}, {city}",
            city=city,
            country="Mexico",
            rating=rating,
            review_count=review_count,
            has_recent_reviews=self._rng.random() > 0.3,
            maps_url=f"https://maps.google.com/?q=fixture_{index}",
            gbp_health=GBPHealth(
                has_photos=self._rng.random() > 0.5,
                has_hours=self._rng.random() > 0.4,
                has_description=self._rng.random() > 0.3,
                is_claimed=self._rng.random() > 0.2,
            ),
            created_at=created_at,
        )