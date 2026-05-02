"""Email generation service - outreach templates per-niche."""

from typing import Optional
from dataclasses import dataclass


@dataclass
class OutreachEmail:
    """Email generado para outreach."""
    subject: str
    body: str
    tone: str
    language: str
    personalization: dict


class EmailGenerator:
    """Genera emails de outreach personalizados con templates per-niche."""

    # Templates base por idioma
    BASE_TEMPLATES = {
        "es": {
            "subject": "{business_name} - Tu web podría estar perdiendo clientes",
            "body": """Hola {owner_name},

Soy {agent_name}, especialista en presencia digital para {niche}.

Analicé la web de {business_name} y encontré algunas áreas que podrían estar haciendo que pierdas clientes:

{signals}

{closing}

¿Tienes 15 minutos esta semana para hablar?

Saludos,
{agent_name}
{agent_contact}
""",
        },
        "en": {
            "subject": "{business_name} - Your website could be losing you customers",
            "body": """Hi {owner_name},

I'm {agent_name}, a digital presence specialist for {niche} businesses.

I analyzed {business_name}'s website and found some areas that might be costing you customers:

{signals}

{closing}

Do you have 15 minutes this week for a call?

Best regards,
{agent_name}
{agent_contact}
""",
        },
    }

    # Templates per-niche: anchoes específicos para industrias comunes
    NICHE_TEMPLATES = {
        "plomeros": {
            "es": {
                "subject": "{business_name} - ¿Sabías que tus clientes buscan fontanero online?",
                "body": """Hola {owner_name},

Soy {agent_name}, especialista en marketing digital para fontanería.

Analicé cómo encuentran tus clientes cuando tienen una emergencia de tubería o una fuga. {business_name} tiene potencial, pero esto te está costando llamadas:

{signals}

{closing}

¿Te gustaría que te mostrara cómo captar esas llamadas de urgencia que ahora se lleva la competencia?

Saludos,
{agent_name}
{agent_contact}
""",
            },
            "en": {
                "subject": "{business_name} - Do your customers find you in plumbing emergencies?",
                "body": """Hi {owner_name},

I'm {agent_name}, a digital marketing specialist for plumbing businesses.

I analyzed how customers find plumbers when they have burst pipes or leaks. {business_name} has potential, but here's what's costing you calls:

{signals}

{closing}

Would you like me to show you how to capture those emergency calls your competitors are getting?

Best regards,
{agent_name}
{agent_contact}
""",
            },
        },
        "electricistas": {
            "es": {
                "subject": "{business_name} - ¿Quién aparece cuando buscan 'electricista cerca'?",
                "body": """Hola {owner_name},

Soy {agent_name}, especialista en captación digital para electricistas.

Cuando alguien busca 'electricista urgente' en tu zona, ¿sale {business_name} primero? Analicé tu competencia y encontré esto:

{signals}

{closing}

¿Quieres que te enseñe cómo estar en los primeros resultados cuando alguien necesita un electricista?

Saludos,
{agent_name}
{agent_contact}
""",
            },
        },
        "dentistas": {
            "es": {
                "subject": "{business_name} - Pacientes nuevos que buscan dentista en tu zona",
                "body": """Hola {owner_name},

Soy {agent_name}, consultor de marketing dental.

Cada mes hay personas buscando dentista en tu zona que nunca llegan a {business_name}. Esto es lo que encontré:

{signals}

{closing}

Una clínica dental con buena presencia digital recibe hasta 30% más pacientes nuevos. ¿Te interesa saber cómo?

Saludos,
{agent_name}
{agent_contact}
""",
            },
            "en": {
                "subject": "{business_name} - New patients looking for dentists in your area",
                "body": """Hi {owner_name},

I'm {agent_name}, dental marketing consultant.

Every month people search for dentists in your area who never find {business_name}. Here's what I found:

{signals}

{closing}

A dental practice with good digital presence gets up to 30% more new patients. Interested in knowing how?

Best regards,
{agent_name}
{agent_contact}
""",
            },
        },
        "abogados": {
            "es": {
                "subject": "{business_name} - Clientes potenciales que buscan asesoría legal online",
                "body": """Estimado/a equipo de {business_name},

Soy {agent_name}, especialista en consultoría digital para despachos jurídicos.

El 70% de los clientes potenciales investigan a su abogado online antes de contactar. {business_name} podría estar perdiendo casos por esto:

{signals}

{closing}

Una primera impresión digital profesional aumenta la tasa de conversión de consultas. ¿Podemos hablar 15 minutos?

Saludos,
{agent_name}
{agent_contact}
""",
            },
        },
        "restaurantes": {
            "es": {
                "subject": "{business_name} - ¿Tu restaurante se muestra a quienes buscan comer cerca?",
                "body": """Hola {owner_name},

Soy {agent_name}, especialista en visibilidad digital para restaurantes.

El 80% de los comensales buscan restaurantes en Google Maps antes de decidir. ¿Aparece {business_name}?

{signals}

{closing}

Restaurantes con buena ficha de Google reciben hasta el doble de reservas. ¿Te interesa saber cómo?

Saludos,
{agent_name}
{agent_contact}
""",
            },
        },
        "carpinteros": {
            "es": {
                "subject": "{business_name} - Proyectos de carpintería que no llegan a ti",
                "body": """Hola {owner_name},

Soy {agent_name}, especialista en presencia digital para carpinteros y ebanistas.

Cada día hay personas buscando 'carpintero en {city}' o 'muebles a medida' que nunca ven a {business_name}. Esto es lo que encontré:

{signals}

{closing}

Un taller con buena imagen digital recibe proyectos de mayor valor. ¿Te interesa saber cómo?

Saludos,
{agent_name}
{agent_contact}
""",
            },
        },
    }

    TONE_VARIANTS = {
        "formal": {
            "es": "Me encantaría ayudarte a optimizar tu presencia digital para captar más clientes.",
            "en": "I would love to help you optimize your digital presence to attract more customers.",
        },
        "casual": {
            "es": "La verdad es que hay un par de cositas fáciles de arreglar que podrían cambiar mucho.",
            "en": "Honestly there are a few easy fixes that could make a big difference.",
        },
        "data": {
            "es": "Según nuestros datos, negocios con web optimizada duplican sus consultas. Voy a explicarte cómo.",
            "en": "According to our data, businesses with optimized websites double their inquiries. Let me show you how.",
        },
    }

    def _get_template(self, business_name: str, niche: str, language: str, signals: list[str], tone: str, owner_name: str, agent_name: str, agent_contact: str, city: str = "") -> OutreachEmail:
        """Selecciona template per-niche o fallback a base."""
        niche_slug = niche.lower().strip()
        tpl_lang = self.NICHE_TEMPLATES.get(niche_slug, {}).get(language)
        if not tpl_lang:
            tpl_lang = self.BASE_TEMPLATES.get(language, self.BASE_TEMPLATES["es"])

        tone_text = self.TONE_VARIANTS.get(tone, self.TONE_VARIANTS["data"]).get(language, "")
        signals_text = "\n".join(f"• {s}" for s in signals[:5])

        personalization = {
            "business_name": business_name,
            "niche": niche,
            "owner_name": owner_name or "Equipo de " + business_name,
            "signals_count": len(signals),
            "city": city,
        }

        body = tpl_lang["body"].format(
            business_name=business_name,
            niche=niche,
            owner_name=owner_name or "Equipo de " + business_name,
            signals=signals_text,
            closing=tone_text,
            agent_name=agent_name,
            agent_contact=agent_contact,
            city=city or "tu zona",
        )
        subject = tpl_lang["subject"].format(business_name=business_name)

        return OutreachEmail(
            subject=subject,
            body=body,
            tone=tone,
            language=language,
            personalization=personalization,
        )

    def generate(
        self,
        business_name: str,
        niche: str,
        signals: list[str],
        language: str = "es",
        tone: str = "data",
        owner_name: str = "",
        agent_name: str = "Tu Asistente",
        agent_contact: str = "",
        city: str = "",
    ) -> OutreachEmail:
        """Genera email de outreach personalizado con template per-niche."""
        return self._get_template(
            business_name=business_name,
            niche=niche,
            language=language,
            signals=signals,
            tone=tone,
            owner_name=owner_name,
            agent_name=agent_name,
            agent_contact=agent_contact,
            city=city,
        )

    def generate_batch(
        self,
        leads: list[dict],
        niche: str,
        language: str = "es",
        tone: str = "data",
        agent_name: str = "",
        agent_contact: str = "",
        city: str = "",
    ) -> list[OutreachEmail]:
        """Genera batch de emails para múltiples leads."""
        emails = []
        for lead in leads:
            email = self.generate(
                business_name=lead["name"],
                niche=niche,
                signals=lead.get("signals", []),
                language=language,
                tone=tone,
                owner_name=lead.get("owner_name", ""),
                agent_name=agent_name,
                agent_contact=agent_contact,
                city=city,
            )
            emails.append(email)
        return emails
