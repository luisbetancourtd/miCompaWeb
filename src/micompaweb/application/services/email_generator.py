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
        "fr": {
            "subject": "{business_name} - Votre site web pourrait vous faire perdre des clients",
            "body": """Bonjour {owner_name},

Je suis {agent_name}, spécialiste en présence digitale pour {niche}.

J'ai analysé le site de {business_name} et trouvé quelques points qui pourraient vous coûter des clients :

{signals}

{closing}

Avez-vous 15 minutes cette semaine pour en parler ?

Cordialement,
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
            "fr": {
                "subject": "{business_name} - Vos clients vous trouvent-ils en cas d'urgence plomberie ?",
                "body": """Bonjour {owner_name},

Je suis {agent_name}, spécialiste en marketing digital pour plombiers.

J'ai analysé comment les clients trouvent un plombier en urgence. {business_name} a du potentiel, mais cela vous coûte des appels :

{signals}

{closing}

Souhaitez-vous que je vous montre comment capter ces appels d'urgence que vos concurrents reçoivent ?

Cordialement,
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
            "fr": {
                "subject": "{business_name} - Qui apparaît quand on cherche 'électricien près de chez moi' ?",
                "body": """Bonjour {owner_name},

Je suis {agent_name}, spécialiste en acquisition digitale pour électriciens.

Quand quelqu'un cherche 'électricien urgent' dans votre zone, {business_name} apparaît-il en premier ? J'ai analysé votre concurrence et trouvé ceci :

{signals}

{closing}

Voulez-vous que je vous montre comment apparaître en premier quand quelqu'un a besoin d'un électricien ?

Cordialement,
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
            "fr": {
                "subject": "{business_name} - Nouveaux patients cherchant un dentiste dans votre zone",
                "body": """Bonjour {owner_name},

Je suis {agent_name}, consultant en marketing dentaire.

Chaque mois, des personnes recherchent un dentiste dans votre zone sans jamais trouver {business_name}. Voici ce que j'ai trouvé :

{signals}

{closing}

Un cabinet dentaire avec une bonne présence digitale obtient jusqu'à 30% de nouveaux patients. Cela vous intéresse ?

Cordialement,
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
            "fr": {
                "subject": "{business_name} - Clients potentiels recherchant un conseil juridique en ligne",
                "body": """Bonjour équipe de {business_name},

Je suis {agent_name}, spécialiste en conseil digital pour cabinets juridiques.

70% des clients potentiels recherchent leur avocat en ligne avant de contacter. {business_name} pourrait perdre des dossiers à cause de cela :

{signals}

{closing}

Une première impression digitale professionnelle augmente le taux de conversion des consultations. Pouvons-nous parler 15 minutes ?

Cordialement,
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

Restaurantes con buena ficha de Google reciben jusqu'au double de réservations. ¿Te interesa saber cómo?

Saludos,
{agent_name}
{agent_contact}
""",
            },
            "fr": {
                "subject": "{business_name} - Votre restaurant apparaît-il à ceux qui cherchent à manger près de chez eux ?",
                "body": """Bonjour {owner_name},

Je suis {agent_name}, spécialiste en visibilité digitale pour restaurants.

80% des clients recherchent des restaurants sur Google Maps avant de décider. {business_name} apparaît-il ?

{signals}

{closing}

Les restaurants avec une bonne fiche Google reçoivent jusqu'au double de réservations. Cela vous intéresse ?

Cordialement,
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
            "fr": {
                "subject": "{business_name} - Des projets de menuiserie qui ne vous parviennent pas",
                "body": """Bonjour {owner_name},

Je suis {agent_name}, spécialiste en présence digitale pour menuisiers et ébénistes.

Chaque jour, des personnes recherchent 'menuisier à {city}' ou 'meubles sur mesure' sans jamais voir {business_name}. Voici ce que j'ai trouvé :

{signals}

{closing}

Un atelier avec une bonne image digitale reçoit des projets de plus grande valeur. Cela vous intéresse ?

Cordialement,
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
            "fr": "Je serais ravi de vous aider à optimiser votre présence digitale pour attirer plus de clients.",
        },
        "casual": {
            "es": "La verdad es que hay un par de cositas fáciles de arreglar que podrían cambiar mucho.",
            "en": "Honestly there are a few easy fixes that could make a big difference.",
            "fr": "Il y a quelques petits changements simples qui pourraient faire une grande différence.",
        },
        "data": {
            "es": "Según nuestros datos, negocios con web optimizada duplican sus consultas. Voy a explicarte cómo.",
            "en": "According to our data, businesses with optimized websites double their inquiries. Let me show you how.",
            "fr": "Selon nos données, les entreprises avec un site optimisé doublent leurs demandes. Laissez-moi vous montrer comment.",
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

    @staticmethod
    def extract_pain_points(lead) -> list[str]:
        """Extrae pain points desde el score_breakdown de un lead.

        Args:
            lead: Instancia de Lead con score_breakdown poblado.

        Returns:
            Lista de strings descriptivos de los pain points detectados.
        """
        if not hasattr(lead, "score_breakdown") or not lead.score_breakdown:
            return ["Sin datos de scoring disponibles"]

        pain_points: list[str] = []
        for bd in lead.score_breakdown:
            if bd.points > 0:
                pain_points.append(f"{bd.criterion}: {bd.evidence}")
        return pain_points[:5]  # máximo 5 pain points
