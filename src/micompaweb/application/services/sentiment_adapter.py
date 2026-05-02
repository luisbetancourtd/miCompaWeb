"""Sentiment analysis adapter - local VADER-based."""

from typing import List, Dict
from dataclasses import dataclass


@dataclass
class SentimentScore:
    """Resultado de análisis de sentimiento."""
    compound: float       # -1.0 a 1.0
    positive: float       # 0.0 a 1.0
    negative: float       # 0.0 a 1.0
    neutral: float        # 0.0 a 1.0
    review_count: int = 0
    confidence: str = "medium"  # high, medium, low


class SentimentAdapter:
    """Analizador de sentimiento local (VADER opcional, fallback heuristico)."""

    # Palabras positivas en español/inglés (versión básica sin NLTK)
    POSITIVE_WORDS = {
        "excelente", "excelentes", "fantastico", "fantástico", "increíble", "increible",
        "genial", "bueno", "buena", "buenisimo", "buenísimo",
        "amable", "recomiendo", "profesional", "rápido", "rapido", "eficiente", "calidad",
        "me encanto", "me encantó", "muy bueno", "super", "súper", "gran", "perfecto", "encantado",
        "gracias", "atención", "atencion", "resolvieron", "cumplieron", "buen",
        "excellent", "great", "amazing", "professional", "fast", "quality",
        "best", "good", "love", "friendly", "recommend", "perfect",
    }

    NEGATIVE_WORDS = {
        "pesimo", "pésimo", "terrible", "malo", "mala", "horrible", "deficiente",
        "lento", "caro", "nunca", "jamas", "jamás", "no llegaron", "no respondieron",
        "desastre", "problema", "queja", "decepcionante", "robo", "estafa",
        "desorganizado", "grosero", "irresponsable", "tardaron", "sin",
        "terrible", "bad", "slow", "expensive", "worst", "poor", "never",
        "unprofessional", "rude", "scam", "fraud", "disappointing",
    }

    def _normalize(self, text: str) -> str:
        """Quita tildes para matching más robusto."""
        return text.lower().replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u").replace("ñ", "n")

    def analyze(self, reviews: List[str]) -> SentimentScore:
        """Analiza lista de reviews y retorna score compuesto."""
        if not reviews:
            return SentimentScore(compound=0.0, positive=0.0, negative=0.0, neutral=1.0, review_count=0)

        pos_reviews = 0
        neg_reviews = 0
        neutral_reviews = 0

        for review in reviews:
            normalized = self._normalize(review)
            has_pos = any(pw in normalized for pw in self.POSITIVE_WORDS)
            has_neg = any(nw in normalized for nw in self.NEGATIVE_WORDS)

            if has_neg:
                neg_reviews += 1
            elif has_pos:
                pos_reviews += 1
            else:
                neutral_reviews += 1

        total = len(reviews)
        pos_ratio = pos_reviews / total
        neg_ratio = neg_reviews / total
        neutral_ratio = neutral_reviews / total

        compound = (pos_ratio - neg_ratio) * min(total / 5.0, 1.0)
        compound = max(-1.0, min(1.0, compound))

        confidence = "low" if total < 5 else ("high" if total >= 15 else "medium")

        return SentimentScore(
            compound=compound,
            positive=pos_ratio,
            negative=neg_ratio,
            neutral=neutral_ratio,
            review_count=total,
            confidence=confidence,
        )

    def has_negative_signal(self, reviews: List[str], threshold: float = 0.4) -> bool:
        """True si más del threshold de reviews son negativas."""
        score = self.analyze(reviews)
        return score.negative >= threshold

    def category(self, compound: float) -> str:
        """Categoría textual del compound."""
        if compound >= 0.5:
            return "muy positivo"
        elif compound >= 0.1:
            return "positivo"
        elif compound >= -0.1:
            return "neutral"
        elif compound >= -0.5:
            return "negativo"
        else:
            return "muy negativo"
