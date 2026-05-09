"""Prompts estructurados para generación de outreach vía LLM."""

OUTREACH_PROMPTS = {
    "es": {
        "system": (
            "Eres un especialista en marketing digital para pequeños negocios locales. "
            "Generas emails de outreach cortos, personalizados y persuasivos. "
            "Usas los pain points detectados para crear urgencia. "
            "Máximo 150 palabras."
        ),
        "user_template": (
            "Negocio: {business_name}\n"
            "Nicho: {niche}\n"
            "Pain points detectados: {pain_points}\n"
            "Idioma: Español\n"
            "Tono: {tone}\n\n"
            "Genera un email de outreach profesional con asunto y cuerpo."
        ),
    },
    "en": {
        "system": (
            "You are a digital marketing specialist for local small businesses. "
            "You write short, personalized, persuasive outreach emails. "
            "You use detected pain points to create urgency. "
            "Max 150 words."
        ),
        "user_template": (
            "Business: {business_name}\n"
            "Niche: {niche}\n"
            "Detected pain points: {pain_points}\n"
            "Language: English\n"
            "Tone: {tone}\n\n"
            "Generate a professional outreach email with subject and body."
        ),
    },
    "fr": {
        "system": (
            "Vous êtes un spécialiste du marketing digital pour les petites entreprises locales. "
            "Vous rédigez des emails de prospection courts, personnalisés et persuasifs. "
            "Vous utilisez les points de douleur détectés pour créer de l'urgence. "
            "Maximum 150 mots."
        ),
        "user_template": (
            "Entreprise: {business_name}\n"
            "Niche: {niche}\n"
            "Points de douleur détectés: {pain_points}\n"
            "Langue: Français\n"
            "Ton: {tone}\n\n"
            "Générez un email de prospection professionnel avec sujet et corps."
        ),
    },
}


def build_outreach_prompt(business_name: str, niche: str, pain_points: list[str], language: str, tone: str) -> dict:
    """Construye el prompt completo para generación de outreach."""
    cfg = OUTREACH_PROMPTS.get(language, OUTREACH_PROMPTS["es"])
    pain = "; ".join(pain_points) if pain_points else "Sin datos específicos"
    return {
        "system": cfg["system"],
        "user": cfg["user_template"].format(
            business_name=business_name,
            niche=niche,
            pain_points=pain,
            tone=tone,
        ),
    }
