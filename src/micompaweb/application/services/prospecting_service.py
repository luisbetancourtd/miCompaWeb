"""Prospecting service - orquestador del pipeline M1."""

import asyncio
from typing import List, Optional, Callable
from datetime import datetime
from pathlib import Path

from micompaweb.domain.models import (
    Lead, Project, ProjectStatus, ProjectConfig,
    PriorityTier, WebsiteStatus, CompetitorComparison,
)
from micompaweb.application.ports import (
    LeadSource,
    WebAuditor,
    LLMClient,
    Cache,
    Exporter,
)
from micompaweb.application.services.scoring_service import ScoringService
from micompaweb.application.services.revenue_service import RevenueService
from micompaweb.domain.rules.guardian import InputGuardian


class ProspectingError(Exception):
    """Error en pipeline de prospección."""
    pass


class ProspectingService:
    """Orquestador del pipeline M1 - reemplaza a LeadProcessor God Object.

    Este servicio:
    - No conoce implementaciones concretas (usa protocolos)
    - Es testeable (dependencias inyectables)
    - Soporta modo offline (vía cache)
    - Reporta progreso (callbacks)
    """

    def __init__(
        self,
        lead_source: LeadSource,
        web_auditor: WebAuditor,
        llm_client: LLMClient,
        cache: Cache,
        exporters: List[Exporter],
        project_path: Path,
        competitor_service=None,
        sentiment_adapter=None,
        input_guardian: Optional[InputGuardian] = None,
        cost_guardian=None,
    ):
        self.lead_source = lead_source
        self.web_auditor = web_auditor
        self.llm_client = llm_client
        self.cache = cache
        self.exporters = exporters
        self.project_path = project_path

        # Servicios internos
        self.scoring_service = ScoringService()
        self.revenue_service = RevenueService()

        # Servicios opcionales (Phase 3+ wiring)
        self.competitor_service = competitor_service
        self.sentiment_adapter = sentiment_adapter
        self.input_guardian = input_guardian
        self.cost_guardian = cost_guardian

        # Callbacks de progreso
        self._progress_callbacks: List[Callable[[str, int, int], None]] = []

    def on_progress(self, callback: Callable[[str, int, int], None]) -> None:
        """Registra callback de progreso: (stage, current, total)."""
        self._progress_callbacks.append(callback)

    def _notify_progress(self, stage: str, current: int, total: int) -> None:
        """Notifica a todos los callbacks."""
        for callback in self._progress_callbacks:
            try:
                callback(stage, current, total)
            except Exception:
                pass  # No dejar que un callback falle rompa el pipeline

    async def execute(
        self,
        project: Project,
        skip_cache: bool = False,
        max_concurrent_audits: int = 5,
    ) -> List[Lead]:
        """Ejecuta el pipeline completo M1.

        Args:
            project: Proyecto configurado
            skip_cache: Si True, ignora caché y fuerza búsqueda nueva
            max_concurrent_audits: Máximo de auditorías web simultáneas

        Returns:
            Lista de leads procesados y puntuados

        Raises:
            ProspectingError: Si falla el pipeline
        """
        project.status = ProjectStatus.RUNNING
        project.started_at = datetime.now()

        try:
            # === STAGE 0: Input Validation ===
            self._validate_inputs(project)

            # === STAGE 1: Discovery ===
            cache_key = self.cache.make_key(
                "search",
                project.config.niche,
                project.config.location,
                project.config.depth,
            )

            leads: List[Lead] = []

            if not skip_cache:
                cached = await self.cache.get(cache_key)
                if cached:
                    leads = cached
                    print(f"[Cache] {len(leads)} leads desde caché")

            if not leads:
                leads = await self._discover_leads(project)
                await self.cache.set(cache_key, leads, ttl_seconds=86400 * 30)  # 30 días

            project.stats.total_scanned = len(leads)

            # === STAGE 1.5: Chain Filter ===
            leads = self._filter_chains(leads)

            # === STAGE 2: Web Audit ===
            leads_with_websites = [l for l in leads if l.website_url]
            await self._audit_websites(leads_with_websites, max_concurrent_audits)

            # === STAGE 3: Vigency Check ===
            await self._check_vigency(leads_with_websites, max_concurrent_audits)

            # === STAGE 3.5: Competitor Analysis ===
            self._analyze_competitors(leads)

            # === STAGE 4: Scoring ===
            self._score_leads(leads)

            # === STAGE 4.5: Sentiment Analysis ===
            self._analyze_sentiment(leads)

            # === STAGE 5: Revenue Estimation ===
            self._estimate_revenue(leads, project)

            # === STAGE 6: Export ===
            await self._export_results(leads, project)

            # === COMPLETE ===
            project.status = ProjectStatus.COMPLETED
            project.completed_at = datetime.now()
            self._update_stats(project, leads)

            return leads

        except Exception as e:
            project.status = ProjectStatus.FAILED
            project.error_message = str(e)
            raise ProspectingError(f"Pipeline failed: {e}") from e

    async def _discover_leads(self, project: Project) -> List[Lead]:
        """Descubre leads desde la fuente configurada con control de costos."""
        self._notify_progress("discovery", 0, 1)

        # Preview de costo antes de ejecutar
        if self.cost_guardian:
            preview = self.cost_guardian.preview_cost(
                self.lead_source.source_name, project.config.max_leads
            )
            if not self.cost_guardian.can_proceed(
                self.lead_source.source_name, project.config.max_leads
            ):
                raise ProspectingError(
                    f"Presupuesto diario insuficiente: necesita ~${preview:.2f}, "
                    f"restante ${self.cost_guardian.remaining():.2f}"
                )

        depth_radius = {
            "rapida": 5000,
            "estandar": 10000,
            "exhaustiva": 20000,
        }
        radius = depth_radius.get(project.config.depth, 10000)

        leads = await self.lead_source.search(
            niche=project.config.niche,
            location=project.config.location,
            radius_meters=radius,
            max_results=project.config.max_leads,
            language=project.config.target_language,
        )

        self._notify_progress("discovery", 1, 1)
        return leads

    @staticmethod
    def _convert_audit(audit) -> "TechnicalAudit":
        """Convierte auditoría de web_auditor a formato Lead."""
        from micompaweb.domain.models import TechnicalAudit

        # Manejar ambos formatos: web_auditor.TechnicalAudit (con ssl.is_valid)
        # y lead.TechnicalAudit (con ssl_valid directo)
        if hasattr(audit, "ssl"):
            # Formato web_auditor - convertir
            return TechnicalAudit(
                ssl_valid=audit.ssl.is_valid if audit.ssl else False,
                has_meta_pixel=audit.tracking.has_meta_pixel if hasattr(audit, "tracking") else False,
                has_gtm=audit.tracking.has_gtm if hasattr(audit, "tracking") else False,
                has_analytics=audit.tracking.has_analytics if hasattr(audit, "tracking") else False,
                mobile_friendly=getattr(audit, "mobile_friendly", False),
                load_time_ms=getattr(audit, "load_time_ms", None),
                copyright_year=getattr(audit, "copyright_year", None),
                page_title=getattr(audit, "page_title", None),
                meta_description=getattr(audit, "meta_description", None),
            )
        # Ya es el formato correcto (lead.TechnicalAudit)
        return audit

    async def _audit_websites(
        self,
        leads: List[Lead],
        max_concurrent: int,
    ) -> None:
        """Audita sitios web concurrentemente."""
        semaphore = asyncio.Semaphore(max_concurrent)
        total = len(leads)

        async def audit_one(lead: Lead, index: int) -> None:
            async with semaphore:
                try:
                    audit = await self.web_auditor.audit(lead.website_url)
                    lead.audit = self._convert_audit(audit)
                except Exception as e:
                    # Log pero no fallar el pipeline por un lead
                    print(f"Audit failed for {lead.website_url}: {e}")
                finally:
                    self._notify_progress("audit", index + 1, total)

        tasks = [audit_one(lead, i) for i, lead in enumerate(leads)]
        await asyncio.gather(*tasks)

    async def _check_vigency(
        self,
        leads: List[Lead],
        max_concurrent: int,
    ) -> None:
        """Verifica vigencia de contenido concurrentemente."""
        semaphore = asyncio.Semaphore(max_concurrent)
        total = len(leads)

        async def check_one(lead: Lead, index: int) -> None:
            async with semaphore:
                try:
                    # Obtener contenido para análisis
                    content = lead.audit.page_title or ""
                    if lead.audit.meta_description:
                        content += " " + lead.audit.meta_description

                    vigency = await self.llm_client.analyze_vigency(
                        content=content,
                        website_url=lead.website_url or "",
                        copyright_year=lead.audit.copyright_year,
                    )
                    lead.vigency = vigency
                except Exception as e:
                    print(f"Vigency check failed for {lead.business_name}: {e}")
                finally:
                    self._notify_progress("vigency", index + 1, total)

        tasks = [check_one(lead, i) for i, lead in enumerate(leads)]
        await asyncio.gather(*tasks)

    def _score_leads(self, leads: List[Lead]) -> None:
        """Puntúa todos los leads."""
        for i, lead in enumerate(leads):
            scoring_result = self.scoring_service.calculate(lead)
            lead.pepita_score = scoring_result.total_score
            lead.priority = scoring_result.priority_tier
            lead.score_breakdown = scoring_result.breakdowns
            self._notify_progress("scoring", i + 1, len(leads))

    def _estimate_revenue(self, leads: List[Lead], project: Project) -> None:
        """Estima pérdida de ingresos para todos los leads."""
        for lead in leads:
            estimate = self.revenue_service.calculate(lead, project.config.niche)
            lead.revenue_loss = estimate

    async def _export_results(self, leads: List[Lead], project: Project) -> None:
        """Exporta resultados a todos los formatos configurados."""
        from micompaweb.application.ports import ExportConfig

        for exporter in self.exporters:
            try:
                config = ExportConfig(
                    output_dir=self.project_path / "exports",
                    filename_prefix=project.slug,
                    include_disqualified=False,
                    format=exporter.format_name,
                    language=project.config.target_language,
                )
                result = await exporter.export(leads, project, config)
                print(f"[Export] {result.file_path} ({result.file_size_bytes} bytes)")
            except Exception as e:
                print(f"Export failed for {exporter.format_name}: {e}")

        self._notify_progress("export", 1, 1)

    def _update_stats(self, project: Project, leads: List[Lead]) -> None:
        """Actualiza estadísticas del proyecto."""
        project.stats.total_leads = len(leads)
        project.stats.ultra_hot_leads = sum(
            1 for l in leads if l.priority == "ULTRA HOT"
        )
        project.stats.hot_leads = sum(
            1 for l in leads if l.priority == "HOT"
        )
        project.stats.warm_leads = sum(
            1 for l in leads if l.priority == "WARM"
        )
        project.stats.cold_leads = sum(
            1 for l in leads if l.priority == "COLD"
        )
        project.stats.discarded_leads = sum(
            1 for l in leads if l.disqualified
        )

        # Market health score
        if leads:
            no_website_pct = sum(
                1 for l in leads if l.website_status == "none"
            ) / len(leads)
            project.market_health_score = no_website_pct * 100

        # Revenue totals
        total_low = sum(l.revenue_loss.monthly_low for l in leads)
        total_high = sum(l.revenue_loss.monthly_high for l in leads)
        project.total_estimated_revenue_loss_low = total_low
        project.total_estimated_revenue_loss_high = total_high

    def _validate_inputs(self, project: Project) -> None:
        """STAGE 0: Valida inputs con InputGuardian si está disponible."""
        if self.input_guardian is None:
            return
        result = self.input_guardian.validate(
            niche=project.config.niche,
            city=project.config.location,
            language=project.config.target_language,
        )
        if not result.is_valid:
            errors = "; ".join(result.errors)
            raise ProspectingError(f"Validacion fallida: {errors}")
        if result.warnings:
            print(f"[Guardian] Warnings: {result.warnings}")
        if result.suggestions:
            print(f"[Guardian] Sugerencias: {result.suggestions}")

    def _filter_chains(self, leads: List[Lead]) -> List[Lead]:
        """STAGE 1.5a: Filtra cadenas usando InputGuardian."""
        if self.input_guardian is None:
            return leads
        filtered = []
        for lead in leads:
            if self.input_guardian.disqualify_chain(lead.business_name):
                print(f"[Filter] Chain descartado: {lead.business_name}")
                lead.disqualified = True
                lead.disqualification_reason = "Chain detectado por InputGuardian"
                continue
            filtered.append(lead)
        self._notify_progress("filter_chains", len(filtered), len(leads))
        return filtered

    def _analyze_competitors(self, leads: List[Lead]) -> None:
        """STAGE 3.5: Analiza competidores usando datos de auditoría reales."""
        if self.competitor_service is None or not leads:
            return
        # Construir lista de dicts crudos desde los leads (ahora con audit data)
        raw_competitors = []
        for lead in leads:
            raw_competitors.append({
                "name": lead.business_name,
                "website": lead.website_url,
                "has_tracking": any([
                    lead.audit.has_meta_pixel,
                    lead.audit.has_gtm,
                    lead.audit.has_analytics,
                ]),
                "has_photos": lead.gbp_health.has_photos,
                "has_reviews": lead.review_count > 0,
                "review_count": lead.review_count,
                "rating": lead.rating,
                "age_months": getattr(lead, "estimated_business_age_years", 0) or 0,
                # Enriquecimiento digital (disponible post-audit)
                "ssl_valid": lead.audit.ssl_valid,
                "mobile_friendly": lead.audit.mobile_friendly,
                "cms": lead.audit.cms,
                "technology_stack": lead.audit.technology_stack,
            })
        matrix = self.competitor_service.analyze(raw_competitors)
        for lead in leads:
            lead.competitor_count = matrix.total_competitors
            lead.competitor_comparison = [
                CompetitorComparison(
                    competitor_name=c.name,
                    competitor_rating=c.rating,
                    competitor_reviews=c.review_count,
                    has_website=c.has_website,
                    advantage=", ".join(c.signals[:2]) or "N/A",
                )
                for c in matrix.profiles[:3]
            ]
        print(f"[Competitor] {matrix.total_competitors} competidores | Madurez: {matrix.market_maturity}")
        self._notify_progress("competitors", 1, 1)

    def _analyze_sentiment(self, leads: List[Lead]) -> None:
        """STAGE 4.5: Analiza sentimiento de reviews reales o simuladas."""
        if self.sentiment_adapter is None:
            return
        for i, lead in enumerate(leads):
            if not lead.review_count:
                continue
            # Usar reviews reales si existen, fallback a mocks
            reviews = lead.reviews_sample if lead.reviews_sample else self._generate_mock_reviews(lead)
            score = self.sentiment_adapter.analyze(reviews)
            from micompaweb.domain.models import ReviewSentiment
            lead.review_sentiment = ReviewSentiment(
                common_themes=score.themes if score.themes else [self.sentiment_adapter.category(score.compound)],
                average_sentiment=score.compound,
            )
            self._notify_progress("sentiment", i + 1, len(leads))

    @staticmethod
    def _generate_mock_reviews(lead: Lead) -> list:
        """Genera reviews simuladas basadas en rating para fallback."""
        rating = lead.rating
        if rating >= 4.5:
            return ["excelente servicio", "muy profesional", "recomiendo", "genial atencion"]
        elif rating >= 4.0:
            return ["buen servicio", "buena atencion", "recomendable"]
        elif rating >= 3.0:
            return ["regular", "aceptable", "podria mejorar"]
        else:
            return ["malo", "pesimo servicio", "lento"]

    def _update_stats(self, project: Project, leads: List[Lead]) -> None:
        """Actualiza estadísticas del proyecto con MarketHealth robusto (5 factores)."""
        project.stats.total_leads = len(leads)
        project.stats.ultra_hot_leads = sum(
            1 for l in leads if l.priority == PriorityTier.ULTRA_HOT
        )
        project.stats.hot_leads = sum(
            1 for l in leads if l.priority == PriorityTier.HOT
        )
        project.stats.warm_leads = sum(
            1 for l in leads if l.priority == PriorityTier.WARM
        )
        project.stats.cold_leads = sum(
            1 for l in leads if l.priority == PriorityTier.COLD
        )
        project.stats.discarded_leads = sum(
            1 for l in leads if l.disqualified
        )

        # Market health robusto: 5 factores weighted
        if leads:
            n = len(leads)
            no_website_pct = sum(1 for l in leads if l.website_status == WebsiteStatus.NONE) / n
            ssl_fail_pct = sum(1 for l in leads if not l.audit.ssl_valid) / n
            no_tracking_pct = sum(1 for l in leads if not any([
                l.audit.has_meta_pixel, l.audit.has_gtm, l.audit.has_analytics
            ])) / n
            outdated_pct = sum(1 for l in leads if getattr(l.vigency, "is_outdated", False)) / n
            avg_competitors = sum(l.competitor_count for l in leads) / n

            project.stats.ssl_failure_rate = round(ssl_fail_pct * 100, 1)
            project.stats.tracking_adoption_rate = round((1 - no_tracking_pct) * 100, 1)
            project.stats.content_outdated_pct = round(outdated_pct * 100, 1)
            project.stats.avg_competitor_count = round(avg_competitors, 1)

            # Score weighted: digital neglect 45%, authority 30%, sales readiness 25%
            digital_neglect = (no_website_pct * 0.4 + ssl_fail_pct * 0.3 + no_tracking_pct * 0.3)
            authority = 1.0 - min(avg_competitors / 20.0, 1.0)  # menos competidores = más autoridad
            sales_readiness = no_website_pct * 0.5 + outdated_pct * 0.3 + (1 - ssl_fail_pct) * 0.2

            market_health = (
                digital_neglect * 45 +
                authority * 30 +
                sales_readiness * 25
            )
            project.market_health_score = round(market_health, 1)

        # Revenue totals
        total_low = sum(l.revenue_loss.monthly_low for l in leads)
        total_high = sum(l.revenue_loss.monthly_high for l in leads)
        project.total_estimated_revenue_loss_low = total_low
        project.total_estimated_revenue_loss_high = total_high