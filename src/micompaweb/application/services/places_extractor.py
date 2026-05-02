"""GBP Places details extractor - datos de ficha Google."""

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class PlaceDetails:
    """Detalles extraídos de una ficha Google Business Profile."""
    place_id: Optional[str] = None
    name: str = ""
    address: str = ""
    phone: Optional[str] = None
    website: Optional[str] = None
    rating: float = 0.0
    review_count: int = 0
    has_photos: bool = False
    photo_count: int = 0
    has_hours: bool = False
    has_phone: bool = False
    has_website: bool = False
    categories: List[str] = None
    gbp_url: Optional[str] = None
    services: List[str] = None
    is_claimed: bool = False

    def __post_init__(self):
        if self.categories is None:
            self.categories = []
        if self.services is None:
            self.services = []


class PlacesDetailsExtractor:
    """Extrae y normaliza datos de GBP."""

    def extract(self, raw_data: dict) -> PlaceDetails:
        """Extrae PlaceDetails desde dict crudo."""
        photos = raw_data.get("photos", [])
        categories = raw_data.get("categories", [])
        if isinstance(categories, str):
            categories = [categories]

        return PlaceDetails(
            place_id=raw_data.get("place_id"),
            name=raw_data.get("name", ""),
            address=raw_data.get("address", ""),
            phone=raw_data.get("phone"),
            website=raw_data.get("website"),
            rating=raw_data.get("rating", 0.0),
            review_count=raw_data.get("review_count", 0),
            has_photos=len(photos) > 0,
            photo_count=len(photos),
            has_hours=bool(raw_data.get("hours")),
            has_phone=bool(raw_data.get("phone")),
            has_website=bool(raw_data.get("website")),
            categories=categories,
            gbp_url=raw_data.get("gbp_url"),
            services=raw_data.get("services", []),
            is_claimed=raw_data.get("is_claimed", False),
        )

    def enrich(self, details: PlaceDetails, reviews_text: List[str] = None) -> dict:
        """Enriquece PlaceDetails con análisis."""
        result = {
            "basic": {
                "name": details.name,
                "address": details.address,
                "rating": details.rating,
                "reviews": details.review_count,
                "claimed": details.is_claimed,
            },
            "presence": {
                "has_website": details.has_website,
                "has_phone": details.has_phone,
                "has_hours": details.has_hours,
                "has_photos": details.has_photos,
                "photo_count": details.photo_count,
            },
            "categories": details.categories,
        }
        if reviews_text:
            result["reviews_sample"] = reviews_text[:3]  # primeras 3
        return result
