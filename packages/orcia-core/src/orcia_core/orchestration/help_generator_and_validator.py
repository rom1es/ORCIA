"""Story 11.5 — Process 5 `generate-and-attach-help` & Validator `validate_help_article`."""

from __future__ import annotations

import hashlib
import inspect
import time
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from orcia_core.catalog.contextual_help import build_help_redis_cache_key
from orcia_core.orchestration._help_article_models import (
    DEFAULT_KNOWN_ROUTES,
    KNOWN_ORCIA_UI_COMPONENTS,
    GeneratedAndAttachedHelpResult,
    HelpArticleValidationError,
    HelpArticleValidationReport,
    HelpTriggerRegime,
    OrciaDocumentationWorkflowReport,
    OrciaDocumentationWorkflowStepResult,
    render_bilingual_help_markdown_text,
)
from orcia_core.orchestration._help_article_validator import HelpArticleDeterministicValidator
from orcia_core.orchestration._help_orcia_docs_workflow import (
    execute_orcia_documentation_workflow,
)
from orcia_core.orchestration._internal._sql_help_catalog import persist_help_catalog_items_sql
from orcia_core.orchestration.errors import ObserverModeReadOnlyError


class HelpGenerationAndHotAttachmentService:
    """Process 5 (`generate-and-attach-help`) service with `< 100 ms` hot attachment."""

    def __init__(
        self,
        *,
        session_factory: async_sessionmaker[AsyncSession] | None = None,
        redis_client: Any | None = None,
        validator: HelpArticleDeterministicValidator | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._redis = redis_client
        self._validator = validator or HelpArticleDeterministicValidator()
        self._attached_articles: dict[str, GeneratedAndAttachedHelpResult] = {}

    @property
    def validator(self) -> HelpArticleDeterministicValidator:
        """Return the underlying `HelpArticleDeterministicValidator`."""
        return self._validator

    def render_bilingual_help_markdown(
        self,
        *,
        article_id: str,
        version: str,
        pack_id: str,
        title_fr: str,
        title_en: str,
        bound_routes: list[str],
        roles_allowed: list[str],
        glossary_terms: list[str],
        related_workflows: list[str],
        purpose_fr: str,
        purpose_en: str,
        steps_fr: list[str],
        steps_en: list[str],
        faq_fr: list[str],
        faq_en: list[str],
        ui_component_name: str = "ContextualHelpColumnAndCenter",
    ) -> tuple[str, str]:
        """Generate bilingual (`fr`, `en`) Markdown help articles with YAML frontmatter."""
        return render_bilingual_help_markdown_text(
            article_id=article_id,
            version=version,
            pack_id=pack_id,
            title_fr=title_fr,
            title_en=title_en,
            bound_routes=bound_routes,
            roles_allowed=roles_allowed,
            glossary_terms=glossary_terms,
            related_workflows=related_workflows,
            purpose_fr=purpose_fr,
            purpose_en=purpose_en,
            steps_fr=steps_fr,
            steps_en=steps_en,
            faq_fr=faq_fr,
            faq_en=faq_en,
            ui_component_name=ui_component_name,
        )

    async def generate_and_attach_help(
        self,
        *,
        article_id: str,
        article_slug: str,
        version: str,
        pack_slug: str,
        title_fr: str,
        title_en: str,
        bound_routes: list[str],
        roles_allowed: list[str],
        glossary_terms: list[str],
        related_workflows: list[str],
        purpose_fr: str,
        purpose_en: str,
        steps_fr: list[str],
        steps_en: list[str],
        faq_fr: list[str],
        faq_en: list[str],
        ui_component_name: str = "ContextualHelpColumnAndCenter",
        trigger_regime: HelpTriggerRegime = "AUTONOMOUS_CONTRACT",
        known_glossary_terms: list[str] | None = None,
        actor_role: str = "ARCHITECT",
        export_root_dir: Path | None = None,
        autonomous_run_id: str | None = None,
        contract_label: str | None = None,
        trigger_label: str | None = None,
    ) -> GeneratedAndAttachedHelpResult:
        """Execute Process 5 (`generate-and-attach-help`): generate, validate, hot-attach."""
        if actor_role.upper() == "READ_ONLY_OBSERVER":
            raise ObserverModeReadOnlyError(detail_override="generate_and_attach_help")

        pack_id = "core" if pack_slug in ("", "core") else f"orcia://packs/orcia-pack-{pack_slug}"
        md_fr, md_en = self.render_bilingual_help_markdown(
            article_id=article_id,
            version=version,
            pack_id=pack_id,
            title_fr=title_fr,
            title_en=title_en,
            bound_routes=bound_routes,
            roles_allowed=roles_allowed,
            glossary_terms=glossary_terms,
            related_workflows=related_workflows,
            purpose_fr=purpose_fr,
            purpose_en=purpose_en,
            steps_fr=steps_fr,
            steps_en=steps_en,
            faq_fr=faq_fr,
            faq_en=faq_en,
            ui_component_name=ui_component_name,
        )

        extra_routes = bound_routes if all(r.startswith("/") for r in bound_routes) else None
        val_fr = self._validator.validate_help_article(
            markdown_text=md_fr,
            lang="fr",
            extra_allowed_routes=extra_routes,
            known_glossary_terms=known_glossary_terms,
        )
        val_en = self._validator.validate_help_article(
            markdown_text=md_en,
            lang="en",
            extra_allowed_routes=extra_routes,
            known_glossary_terms=known_glossary_terms,
        )
        if not val_fr.passed or not val_en.passed:
            all_violations = list(val_fr.violations) + list(val_en.violations)
            raise HelpArticleValidationError("; ".join(all_violations))

        t_attach = time.perf_counter()
        fr_sha = hashlib.sha256(md_fr.encode("utf-8")).hexdigest()
        en_sha = hashlib.sha256(md_en.encode("utf-8")).hexdigest()
        norm_pack = pack_slug if pack_slug and pack_slug != "core" else "core"
        invalidated_keys: list[str] = []
        for route in bound_routes:
            for lang_code in ("fr", "en"):
                rkey = build_help_redis_cache_key(route, norm_pack, lang_code)
                invalidated_keys.append(rkey)
                if self._redis is not None:
                    del_res = self._redis.delete(rkey)
                    if inspect.isawaitable(del_res):
                        await del_res

        if norm_pack == "core":
            rel_fr = f"docs/help/fr/{article_slug}.md"
            rel_en = f"docs/help/en/{article_slug}.md"
        else:
            rel_fr = f"packages/orcia-pack-{norm_pack}/help/fr/{article_slug}.md"
            rel_en = f"packages/orcia-pack-{norm_pack}/help/en/{article_slug}.md"

        if export_root_dir is not None:
            for rel_path, content in ((rel_fr, md_fr), (rel_en, md_en)):
                target_file = (export_root_dir / rel_path).resolve()
                target_file.parent.mkdir(parents=True, exist_ok=True)
                target_file.write_text(content, encoding="utf-8")

        if self._session_factory is not None:
            await persist_help_catalog_items_sql(
                self._session_factory,
                article_id=article_id,
                version=version,
                pack_slug=norm_pack,
                title_fr=title_fr,
                title_en=title_en,
                bound_routes=bound_routes,
                glossary_terms=glossary_terms,
                fr_sha=fr_sha,
                en_sha=en_sha,
                summary_fr=purpose_fr,
                summary_en=purpose_en,
                fr_markdown=md_fr,
                en_markdown=md_en,
                autonomous_run_id=autonomous_run_id,
                contract_label=contract_label,
                trigger_label=trigger_label,
            )

        hot_attach_ms = round((time.perf_counter() - t_attach) * 1000.0, 3)
        result = GeneratedAndAttachedHelpResult(
            article_id=article_id,
            version=version,
            pack_id=pack_id,
            trigger_regime=trigger_regime,
            bound_routes=tuple(bound_routes),
            fr_cas_key=f"cas/{fr_sha}",
            en_cas_key=f"cas/{en_sha}",
            fr_sha256=fr_sha,
            en_sha256=en_sha,
            fr_markdown=md_fr,
            en_markdown=md_en,
            validation_fr=val_fr,
            validation_en=val_en,
            invalidated_redis_keys=tuple(invalidated_keys),
            exported_git_paths=(rel_fr, rel_en),
            hot_attach_elapsed_ms=hot_attach_ms,
            authority_role="REFERENCE",
        )
        self._attached_articles[article_id] = result
        return result

    async def run_generate_orcia_documentation_workflow(
        self,
        *,
        repo_root: Path | None = None,
        actor_role: str = "ARCHITECT",
        export_root_dir: Path | None = None,
    ) -> OrciaDocumentationWorkflowReport:
        """Execute Process 6 (`generate-orcia-documentation`) in 4 governed steps."""
        return await execute_orcia_documentation_workflow(
            self,
            repo_root=repo_root,
            actor_role=actor_role,
            export_root_dir=export_root_dir,
        )


async def run_generate_orcia_documentation_workflow(
    *,
    service: HelpGenerationAndHotAttachmentService | None = None,
    repo_root: Path | None = None,
    actor_role: str = "ARCHITECT",
    export_root_dir: Path | None = None,
) -> OrciaDocumentationWorkflowReport:
    """Convenience runner for Process 6 (`generate-orcia-documentation`)."""
    svc = service or HelpGenerationAndHotAttachmentService()
    return await svc.run_generate_orcia_documentation_workflow(
        repo_root=repo_root,
        actor_role=actor_role,
        export_root_dir=export_root_dir,
    )


__all__ = [
    "DEFAULT_KNOWN_ROUTES",
    "GeneratedAndAttachedHelpResult",
    "HelpArticleDeterministicValidator",
    "HelpArticleValidationError",
    "HelpArticleValidationReport",
    "HelpGenerationAndHotAttachmentService",
    "HelpTriggerRegime",
    "KNOWN_ORCIA_UI_COMPONENTS",
    "OrciaDocumentationWorkflowReport",
    "OrciaDocumentationWorkflowStepResult",
    "run_generate_orcia_documentation_workflow",
]
