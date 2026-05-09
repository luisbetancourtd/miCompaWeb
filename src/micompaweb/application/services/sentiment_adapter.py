"""Sentiment analysis adapter - VADER optional, heuristic fallback."""

from typing import List, Dict, Tuple
from dataclasses import dataclass
from collections import Counter

# Optional VADER dependency
try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    _VADER_AVAILABLE = True
except ImportError:
    _VADER_AVAILABLE = False


@dataclass
class SentimentScore:
    """Resultado de análisis de sentimiento."""
    compound: float       # -1.0 a 1.0
    positive: float       # 0.0 a 1.0
    negative: float       # 0.0 a 1.0
    neutral: float        # 0.0 a 1.0
    review_count: int = 0
    confidence: str = "medium"  # high, medium, low
    themes: List[str] = None  # type: ignore

    def __post_init__(self):
        if self.themes is None:
            self.themes = []


class SentimentAdapter:
    """Analizador de sentimiento: VADER si disponible, fallback heuristico."""

    # Stopwords simples para extracción de themes
    STOP_WORDS = {
        "el", "la", "los", "las", "de", "del", "y", "a", "en", "con", "por", "para",
        "un", "una", "uno", "unos", "ese", "esa", "eso", "esos", "pero", "lo", "le",
        "que", "se", "al", "lo", "su", "sus", "me", "mi", "te", "tu", "nos", "les",
        "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of",
        "with", "by", "from", "is", "was", "are", "were", "be", "been", "being",
    }

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

    def __init__(self):
        self._vader = SentimentIntensityAnalyzer() if _VADER_AVAILABLE else None

    def analyze(self, reviews: List[str]) -> SentimentScore:
        """Analiza lista de reviews: VADER si disponible, heuristico fallback."""
        if not reviews:
            return SentimentScore(
                compound=0.0, positive=0.0, negative=0.0, neutral=1.0, review_count=0,
                themes=[],
            )

        if self._vader:
            return self._analyze_vader(reviews)
        return self._analyze_heuristic(reviews)

    def _analyze_vader(self, reviews: List[str]) -> SentimentScore:
        """Analisis con VADER."""
        compounds = []
        for r in reviews:
            scores = self._vader.polarity_scores(r)
            compounds.append(scores["compound"])

        avg_compound = sum(compounds) / len(compounds)
        pos = sum(1 for c in compounds if c >= 0.05) / len(compounds)
        neg = sum(1 for c in compounds if c <= -0.05) / len(compounds)
        neu = 1.0 - pos - neg

        confidence = "low" if len(reviews) < 5 else ("high" if len(reviews) >= 15 else "medium")
        themes = self._extract_themes(reviews)

        return SentimentScore(
            compound=round(avg_compound, 3),
            positive=round(pos, 3),
            negative=round(neg, 3),
            neutral=round(neu, 3),
            review_count=len(reviews),
            confidence=confidence,
            themes=themes,
        )

    def _analyze_heuristic(self, reviews: List[str]) -> SentimentScore:
        """Analisis heuristico sin dependencias."""
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
        themes = self._extract_themes(reviews)

        return SentimentScore(
            compound=round(compound, 3),
            positive=round(pos_ratio, 3),
            negative=round(neg_ratio, 3),
            neutral=round(neutral_ratio, 3),
            review_count=total,
            confidence=confidence,
            themes=themes,
        )

    def _extract_themes(self, reviews: List[str]) -> List[str]:
        """Extrae palabras clave frecuentes (top 5) de las reviews."""
        words: List[str] = []
        for r in reviews:
            for w in self._normalize(r).split():
                if len(w) > 3 and w not in self.STOP_WORDS:
                    words.append(w)
        if not words:
            return []
        counter = Counter(words)
        return [word for word, _ in counter.most_common(5)]

    @staticmethod
    def _normalize(text: str) -> str:
        """Quita tildes para matching robusto."""
        return (
            text.lower()
            .replace("á", "a").replace("é", "e").replace("í", "i")
            .replace("ó", "o").replace("ú", "u").replace("ñ", "n")
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
