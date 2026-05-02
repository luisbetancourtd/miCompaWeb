"""Google Places API lead source implementation."""

import httpx
from typing import List, Optional, Dict, Any
from urllib.parse import quote

from micompaweb.domain.models import Lead, WebsiteStatus, GBPHealth
from micompaweb.application.ports.lead_source import (
    LeadSource,
    LeadSourceError,
    SourceHealth,
    CostEstimate,
)


class GooglePlacesSource:
    """Fuente de leads usando Google Places API (New).

    Implementa el protocolo LeadSource para descubrimiento
    de negocios locales vía Google Places API v1.
    """

    # New Places API v1
    PLACES_API_URL = "https://places.googleapis.com/v1"
    GEOCODING_URL = "https://maps.googleapis.com/maps/api/geocode/json"
    COST_PER_100_LEADS = 0.50  # USD aproximado

    def __init__(self, api_key: str):
        self.api_key = api_key
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Obtiene cliente HTTP async (lazy initialization)."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    async def search(
        self,
        niche: str,
        location: str,
        radius_meters: int = 10000,
        max_results: int = 100,
        language: str = "es",
    ) -> List[Lead]:
        """Busca negocios usando Google Places API.

        Args:
            niche: Tipo de negocio (ej: "plomeros")
            location: Ubicación (ej: "Ciudad de México")
            radius_meters: Radio de búsqueda
            max_results: Máximo de resultados
            language: Código de idioma

        Returns:
            Lista de leads normalizados
        """
        # 1. Geocodificación
        coords = await self._geocode_location(location)
        if not coords:
            raise LeadSourceError(f"Could not geocode location: {location}")

        # 2. Búsqueda de lugares cercanos
        places = await self._search_nearby(
            coords, niche, radius_meters, max_results, language
        )

        # 3. Normalizar a modelo Lead
        leads: List[Lead] = []
        for place in places[:max_results]:
            try:
                lead = await self._normalize_place(place, niche, language)
                if lead:
                    leads.append(lead)
            except Exception as e:
                # Continuar con el siguiente si uno falla
                continue

        return leads

    async def get_details(self, external_id: str, language: str = "es") -> Optional[Lead]:
        """Obtiene detalles completos de un lugar usando Places API v1.

        Args:
            external_id: Google Place ID
            language: Código de idioma

        Returns:
            Lead completo o None
        """
        url = f"{self.PLACES_API_URL}/places/{external_id}"

        headers = {
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": "id,displayName,formattedAddress,location,types,"
                               "rating,userRatingCount,websiteUri,nationalPhoneNumber,"
                               "plusCode,photos,regularOpeningHours,editorialSummary,"
                               "businessStatus",
        }

        params = {"languageCode": language}

        client = await self._get_client()
        response = await client.get(url, headers=headers, params=params)

        if response.status_code == 404:
            return None

        response.raise_for_status()
        place = response.json()

        # Convertir formato v1 a legacy y crear Lead
        legacy_place = self._convert_place_v1_to_legacy(place)
        return self._place_details_to_lead(legacy_place, "")

    def health_check(self) -> SourceHealth:
        """Verifica salud de la API."""
        if not self.api_key:
            return SourceHealth(
                is_healthy=False,
                message="Google Places API key not configured",
            )

        # Validación básica del formato de la key
        if len(self.api_key) < 20:
            return SourceHealth(
                is_healthy=False,
                message="Google Places API key appears invalid",
            )

        return SourceHealth(
            is_healthy=True,
            message="Google Places API configured",
        )

    def estimate_cost(self, num_results: int) -> CostEstimate:
        """Estima costo de operación."""
        # 1 geocoding + 1 nearby search + N details
        estimated_cost = (2 + num_results) * (self.COST_PER_100_LEADS / 100)
        return CostEstimate(
            usd_amount=estimated_cost,
            requests_count=2 + num_results,
            source_name=self.source_name,
        )

    @property
    def source_name(self) -> str:
        return "google_places"

    @property
    def supports_caching(self) -> bool:
        return True

    async def _geocode_location(self, location: str) -> Optional[tuple[float, float]]:
        """Geocodifica una ubicación a coordenadas."""
        url = "https://maps.googleapis.com/maps/api/geocode/json"
        params = {
            "address": quote(location),
            "key": self.api_key,
        }

        client = await self._get_client()
        response = await client.get(url, params=params)
        response.raise_for_status()

        data = response.json()
        if data.get("status") != "OK" or not data.get("results"):
            return None

        location_data = data["results"][0]["geometry"]["location"]
        return (location_data["lat"], location_data["lng"])

    async def _search_nearby(
        self,
        coords: tuple[float, float],
        keyword: str,
        radius: int,
        max_results: int,
        language: str,
    ) -> List[Dict[str, Any]]:
        """Busca lugares cercanos usando Places API v1."""
        url = f"{self.PLACES_API_URL}/places:searchNearby"

        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": "places.id,places.displayName,places.formattedAddress,"
                               "places.location,places.types,places.rating,"
                               "places.userRatingCount,places.websiteUri,"
                               "places.nationalPhoneNumber,places.plusCode,"
                               "places.photos,places.regularOpeningHours,"
                               "places.editorialSummary,places.businessStatus",
        }

        body = {
            "locationRestriction": {
                "circle": {
                    "center": {"latitude": coords[0], "longitude": coords[1]},
                    "radius": float(min(radius, 50000)),  # Máximo 50km
                }
            },
            "includedTypes": [self._map_keyword_to_type(keyword)],
            "languageCode": language,
            "maxResultCount": min(max_results, 20),  # API v1 max is 20 per call
        }

        client = await self._get_client()
        response = await client.post(url, headers=headers, json=body)
        response.raise_for_status()

        data = response.json()
        places = data.get("places", [])

        # Convertir formato v1 a formato legacy compatible
        return [self._convert_place_v1_to_legacy(p) for p in places]

    def _map_keyword_to_type(self, keyword: str) -> str:
        """Mapea keywords a tipos de Places API v1."""
        # Tipos soportados: https://developers.google.com/maps/documentation/places/web-service/place-types
        # Nota: "establishment" no es válido en la nueva API v1
        type_mapping = {
            "plomeros": "plumber",
            "plumbers": "plumber",
            "plumber": "plumber",
            "dentistas": "dentist",
            "dentists": "dentist",
            "dentist": "dentist",
            "abogados": "lawyer",
            "lawyers": "lawyer",
            "lawyer": "lawyer",
            "restaurantes": "restaurant",
            "restaurants": "restaurant",
            "restaurant": "restaurant",
            "doctores": "doctor",
            "doctors": "doctor",
            "doctor": "doctor",
            "electricistas": "electrician",
            "electricians": "electrician",
            "electrician": "electrician",
            "carpinteros": "carpenter",
            "carpenters": "carpenter",
            "carpenter": "carpenter",
        }
        mapped = type_mapping.get(keyword.lower(), keyword.lower())
        # Si no hay mapeo válido, usar "business" como fallback seguro
        return mapped if mapped in type_mapping.values() else "business"

    def _convert_place_v1_to_legacy(self, place: Dict[str, Any]) -> Dict[str, Any]:
        """Convierte formato Places API v1 a formato legacy."""
        location = place.get("location", {})
        display_name = place.get("displayName", {})

        return {
            "place_id": place.get("id", ""),
            "name": display_name.get("text", ""),
            "formatted_address": place.get("formattedAddress", ""),
            "geometry": {
                "location": {
                    "lat": location.get("latitude"),
                    "lng": location.get("longitude"),
                }
            },
            "types": place.get("types", []),
            "rating": place.get("rating"),
            "user_ratings_total": place.get("userRatingCount"),
            "website": place.get("websiteUri", ""),
            "formatted_phone_number": place.get("nationalPhoneNumber", ""),
            "plus_code": place.get("plusCode", {}),
            "photos": place.get("photos", []),
            "opening_hours": place.get("regularOpeningHours"),
            "editorial_summary": place.get("editorialSummary"),
            "business_status": place.get("businessStatus"),
        }

    async def _normalize_place(
        self,
        place: Dict[str, Any],
        niche: str,
        language: str,
    ) -> Optional[Lead]:
        """Normaliza un lugar de Google a modelo Lead."""
        place_id = place.get("place_id")
        if not place_id:
            return None

        # Obtener detalles completos
        details = await self.get_details(place_id, language)
        if not details:
            return None

        # Combinar datos básicos + detalles
        details.external_id = place_id
        details.source = self.source_name
        details.niche = niche

        return details

    def _place_details_to_lead(
        self,
        result: Dict[str, Any],
        niche: str,
    ) -> Lead:
        """Convierte detalles de Google Place a Lead."""
        # Determinar estado del website
        website = result.get("website", "")
        if website:
            if website.startswith("https://"):
                website_status = WebsiteStatus.EXISTS
            else:
                website_status = WebsiteStatus.HTTP_ONLY
        else:
            website_status = WebsiteStatus.NONE

        # Extraer ciudad del address
        address = result.get("formatted_address", "")
        city = self._extract_city_from_address(address)

        # GBP Health
        gbp_health = GBPHealth(
            has_photos=bool(result.get("photos")),
            has_hours=bool(result.get("opening_hours")),
            has_description=bool(result.get("editorial_summary")),
            has_categories=bool(result.get("types")),
            has_phone=bool(result.get("formatted_phone_number")),
            has_website=bool(website),
            is_claimed=True,  # Asumimos que si tiene datos está verificado
        )

        return Lead(
            external_id=result.get("place_id", ""),
            source=self.source_name,
            business_name=result.get("name", "Unknown"),
            category=",".join(result.get("types", [])),
            niche=niche,
            phone=result.get("formatted_phone_number"),
            website_url=website if website else None,
            website_status=website_status,
            address=address,
            city=city,
            latitude=result.get("geometry", {}).get("location", {}).get("lat"),
            longitude=result.get("geometry", {}).get("location", {}).get("lng"),
            plus_code=result.get("plus_code", {}).get("global_code"),
            rating=result.get("rating", 0),
            review_count=result.get("user_ratings_total", 0),
            maps_url=f"https://www.google.com/maps/place/?q=place_id:{result.get('place_id')}",
            gbp_health=gbp_health,
        )

    def _extract_city_from_address(self, address: str) -> Optional[str]:
        """Extrae ciudad de una dirección."""
        # Simplificación: toma la parte antes de la primera coma
        if "," in address:
            return address.split(",")[1].strip()
        return None