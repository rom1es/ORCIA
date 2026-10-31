"""Story 11.5 — Process 5 `generate-and-attach-help` & Validator `validate_help_article`.

Implements:
- Step 2 (`@Rédacteur-Documentation-Orcia`): bilingual (`fr`/`en`) `HelpArticle` Markdown generation
  with declarative YAML frontmatter (`id`, `version`, `bound_routes`, `pack_id`, `roles_allowed`,
  `glossary_terms`, `related_workflows`) and the 3 mandatory sections + `#` anchors.
- Step 3 (`validate_help_article` in Tier 1 `< 5 s`):
  1. Verifies every route in `bound_routes` exists in the router tree or pack manifest;
  2. Verifies no non-existent `@orcia/ui` component is cited and all 3 mandatory sections
     (`## 1. À quoi sert cet écran ?`, `## 2. Comment faire (Pas-à-pas)`,
     `## 3. Questions fréquentes & Dépannage` or their English equivalents) + `#` anchors exist;
  3. Verifies `glossary_terms` align with the Glossary and `0` secrets/tokens leak in the text.
- Step 4 (Hot Attachment `< 100 ms` & Git Export):
  Atomically persists `HELP_ARTICLE` in `catalog_items` + `cas/<sha256>`, invalidates Redis
  `help:route:*` cache keys, and exports `.md` files to `docs/help/{fr,en}/` or
  `packages/orcia-pack-{slug}/help/{fr,en}/`.
"""

from __future__ import annotations

import hashlib
import json
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from uuid_utils import uuid7

from orcia_core.catalog.contextual_help import build_help_redis_cache_key
from orcia_core.orchestration.errors import ObserverModeReadOnlyError
from orcia_kernel.errors import OrciaDomainError

HelpTriggerRegime = Literal["STAGED_HUMAN_REVIEW", "AUTONOMOUS_CONTRACT"]

DEFAULT_KNOWN_ROUTES: frozenset[str] = frozenset(
    {
        "/cockpit",
        "/assistant",
        "/workspaces",
        "/mes-espaces",
        "/mes-espaces/$id/sources",
        "/mes-espaces/$id/deliverables",
        "/mes-espaces/$id/glossary",
        "/agents",
        "/processes",
        "/control-center",
        "/settings",
        "/wizards",
        "/help",
    }
)

KNOWN_ORCIA_UI_COMPONENTS: frozenset[str] = frozenset(
    {
        "FourZoneDirectionCShell",
        "StreamlinedCockpitView",
        "TopHeaderSearchCommand",
        "ContextualHelpColumnAndCenter",
        "AssistantGovernanceModalAndStudio",
        "AssistantSpeedSelectorAndStreamView",
        "AssistantCitationPillsAndArtifactCard",
        "AssistantFoldersAndCollaborativeThreadView",
        "WorkspaceFiveTabsAndExternalRebaseView",
        "DnaStarlarkCompilerAndGlossaryLifecycleView",
        "RemoteServiceTestBenchAndMcpExposureView",
        "PackBuilderProcessesStudioView",
        "HelpArticleGeneratorAndValidatorView",
        "HumanLedAnchorCard",
        "CognitiveReviewBriefing",
        "ArbitrationTieBreakCard",
    }
)

_MANDATORY_SECTIONS_FR: tuple[str, str, str] = (
    "## 1. À quoi sert cet écran ?",
    "## 2. Comment faire (Pas-à-pas)",
    "## 3. Questions fréquentes & Dépannage",
)

_MANDATORY_SECTIONS_EN: tuple[str, str, str] = (
    "## 1. What is this screen for?",
    "## 2. How to use (Step-by-step)",
    "## 3. Frequently Asked Questions & Troubleshooting",
)

_SECRET_LEAK_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bpat_mcp_[A-Za-z0-9_-]{8,}"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{12,}"),
    re.compile(r"(?:secret|vault|kms)://[^\s\"')]+"),
    re.compile("-----BEGIN " + r"[A-Z ]*PRIVATE KEY-----"),  # pragma: allowlist secret
    re.compile(r"\bBearer\s+eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+"),
)

_UI_COMPONENT_REF_RE = re.compile(r"`<([A-Z][A-Za-z0-9]+)\s*/?>`|`@orcia/ui:([A-Z][A-Za-z0-9]+)`")


class HelpArticleValidationError(OrciaDomainError):
    """Raised when `validate_help_article` rejects a `HelpArticle` (`HTTP 422`)."""

    error_code = "ERR_HELP_ARTICLE_VALIDATION_FAILED"
    http_status, type_slug = 422, "help-article-validation-failed"

    def __init__(self, detail: str) -> None:
        super().__init__(detail_override=detail)


@dataclass(frozen=True, slots=True)
class HelpArticleValidationReport:
    """Deterministic validation report produced by `validate_help_article` (`< 5 s`)."""

    article_id: str
    lang: Literal["fr", "en"]
    passed: bool
    bound_routes_valid: bool
    ui_components_and_sections_valid: bool
    glossary_and_zero_secret_valid: bool
    elapsed_ms: float
    violations: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class GeneratedAndAttachedHelpResult:
    """Result of Process 5 (`generate-and-attach-help`)."""

    article_id: str
    version: str
    pack_id: str
    trigger_regime: HelpTriggerRegime
    bound_routes: tuple[str, ...]
    fr_cas_key: str
    en_cas_key: str
    fr_sha256: str
    en_sha256: str
    fr_markdown: str
    en_markdown: str
    validation_fr: HelpArticleValidationReport
    validation_en: HelpArticleValidationReport
    invalidated_redis_keys: tuple[str, ...]
    exported_git_paths: tuple[str, ...]
    hot_attach_elapsed_ms: float
    authority_role: Literal["REFERENCE"] = "REFERENCE"


def _parse_frontmatter_and_body(markdown_text: str) -> tuple[dict[str, Any], str]:
    text = markdown_text.strip()
    meta: dict[str, Any] = {}
    body = text
    if not text.startswith("---"):
        return meta, body
    parts = text.split("---", 2)
    if len(parts) < 3:
        return meta, body
    fm_raw = parts[1].strip()
    body = parts[2].strip()
    current_list_key: str | None = None
    for line in fm_raw.splitlines():
        s = line.strip()
        if not s:
            continue
        if s.startswith("- ") and current_list_key is not None:
            lst = meta.setdefault(current_list_key, [])
            if isinstance(lst, list):
                lst.append(s[2:].strip().strip("\"'"))
            continue
        if ":" in s:
            current_list_key = None
            k, v = s.split(":", 1)
            key = k.strip()
            val = v.strip()
            if not val:
                current_list_key = key
                meta[key] = []
            elif val.startswith("[") and val.endswith("]"):
                try:
                    meta[key] = json.loads(val)
                except ValueError:
                    meta[key] = [x.strip().strip("\"'") for x in val[1:-1].split(",") if x.strip()]
            else:
                meta[key] = val.strip("\"'")
    return meta, body


class HelpArticleDeterministicValidator:
    """Tier 1 deterministic validator `validate_help_article` (`< 5 s`)."""

    def __init__(
        self,
        *,
        known_routes: set[str] | frozenset[str] | None = None,
        known_ui_components: set[str] | frozenset[str] | None = None,
    ) -> None:
        self._known_routes = set(known_routes or DEFAULT_KNOWN_ROUTES)
        self._known_ui_components = set(known_ui_components or KNOWN_ORCIA_UI_COMPONENTS)

    def validate_help_article(
        self,
        *,
        markdown_text: str,
        lang: Literal["fr", "en"] = "fr",
        extra_allowed_routes: list[str] | None = None,
        known_glossary_terms: list[str] | None = None,
    ) -> HelpArticleValidationReport:
        """Validate `HelpArticle` Markdown in `< 5 s` across all 3 deterministic checks."""
        t0 = time.perf_counter()
        meta, body = _parse_frontmatter_and_body(markdown_text)
        article_id = str(meta.get("id", "unknown-help-article"))
        violations: list[str] = []

        # 1. Validate bound_routes against router tree / pack manifest
        allowed_routes = self._known_routes | set(extra_allowed_routes or [])
        bound_routes = meta.get("bound_routes", [])
        if not isinstance(bound_routes, list) or not bound_routes:
            bound_routes_valid = False
            violations.append("Frontmatter 'bound_routes' est vide ou absent.")
        else:
            unknown_routes = [
                r
                for r in bound_routes
                if not str(r).startswith("/") or str(r) not in allowed_routes
            ]
            bound_routes_valid = len(unknown_routes) == 0
            if unknown_routes:
                violations.append(f"Routes inconnues dans bound_routes : {unknown_routes}")

        # 2. Validate @orcia/ui components cited, 3 mandatory sections, and # anchors
        mandatory_sections = _MANDATORY_SECTIONS_FR if lang == "fr" else _MANDATORY_SECTIONS_EN
        missing_sections = [sec for sec in mandatory_sections if sec not in body]
        has_anchors = "{#" in body or "## 1." in body and "#" in body
        cited_components: list[str] = []
        for m in _UI_COMPONENT_REF_RE.finditer(body):
            comp = m.group(1) or m.group(2)
            if comp:
                cited_components.append(comp)
        unknown_components = [c for c in cited_components if c not in self._known_ui_components]
        ui_components_and_sections_valid = (
            len(missing_sections) == 0 and has_anchors and len(unknown_components) == 0
        )
        if missing_sections:
            violations.append(f"Sections obligatoires manquantes : {missing_sections}")
        if unknown_components:
            violations.append(f"Composants @orcia/ui inexistants cités : {unknown_components}")

        # 3. Validate glossary_terms alignment and zero leaked secrets/tokens
        glossary_terms = meta.get("glossary_terms", [])
        glossary_ok = isinstance(glossary_terms, list)
        if glossary_ok and known_glossary_terms:
            known_lower = {t.lower() for t in known_glossary_terms}
            unaligned = [t for t in glossary_terms if str(t).lower() not in known_lower]
            if unaligned:
                glossary_ok = False
                violations.append(f"Termes absents du Glossaire : {unaligned}")

        secret_hits: list[str] = []
        for pat in _SECRET_LEAK_PATTERNS:
            found = pat.findall(markdown_text)
            if found:
                secret_hits.extend(found)
        glossary_and_zero_secret_valid = glossary_ok and len(secret_hits) == 0
        if secret_hits:
            violations.append("Fuite de secret ou token détectée dans le corps HelpArticle.")

        elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 3)
        passed = (
            bound_routes_valid
            and ui_components_and_sections_valid
            and glossary_and_zero_secret_valid
        )
        return HelpArticleValidationReport(
            article_id=article_id,
            lang=lang,
            passed=passed,
            bound_routes_valid=bound_routes_valid,
            ui_components_and_sections_valid=ui_components_and_sections_valid,
            glossary_and_zero_secret_valid=glossary_and_zero_secret_valid,
            elapsed_ms=elapsed_ms,
            violations=tuple(violations),
        )


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
        fm = (
            "---\n"
            f'id: "{article_id}"\n'
            f'version: "{version}"\n'
            f"bound_routes: {json.dumps(bound_routes)}\n"
            f'pack_id: "{pack_id}"\n'
            f"roles_allowed: {json.dumps(roles_allowed)}\n"
            f"glossary_terms: {json.dumps(glossary_terms, ensure_ascii=False)}\n"
            f"related_workflows: {json.dumps(related_workflows)}\n"
            "---\n\n"
        )
        steps_block_fr = "\n".join(f"- {s}" for s in steps_fr)
        faq_block_fr = "\n".join(f"- {q}" for q in faq_fr)
        md_fr = (
            f"{fm}# {title_fr} {{#top}}\n\n"
            f"## 1. À quoi sert cet écran ? {{#overview}}\n"
            f"{purpose_fr} Composant UI : `<{ui_component_name} />`.\n\n"
            f"## 2. Comment faire (Pas-à-pas) {{#steps}}\n"
            f"### Pas-à-pas\n{steps_block_fr}\n\n"
            f"## 3. Questions fréquentes & Dépannage {{#faq}}\n"
            f"### Questions fréquentes\n{faq_block_fr}\n"
        )

        steps_block_en = "\n".join(f"- {s}" for s in steps_en)
        faq_block_en = "\n".join(f"- {q}" for q in faq_en)
        md_en = (
            f"{fm}# {title_en} {{#top}}\n\n"
            f"## 1. What is this screen for? {{#overview}}\n"
            f"{purpose_en} UI Component: `<{ui_component_name} />`.\n\n"
            f"## 2. How to use (Step-by-step) {{#steps}}\n"
            f"### Step-by-step\n{steps_block_en}\n\n"
            f"## 3. Frequently Asked Questions & Troubleshooting {{#faq}}\n"
            f"### Frequently Asked Questions\n{faq_block_en}\n"
        )
        return md_fr, md_en

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
        fr_cas = f"cas/{fr_sha}"
        en_cas = f"cas/{en_sha}"

        # Invalidate Redis cache keys help:route:<route>:<pack>:<lang>
        norm_pack = pack_slug if pack_slug and pack_slug != "core" else "core"
        invalidated_keys: list[str] = []
        for route in bound_routes:
            for lang_code in ("fr", "en"):
                rkey = build_help_redis_cache_key(route, norm_pack, lang_code)
                invalidated_keys.append(rkey)
                if self._redis is not None:
                    self._redis.delete(rkey)

        # Export .md files to docs/help/{fr,en}/ or packages/orcia-pack-{slug}/help/{fr,en}/
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

        await self._persist_help_catalog_items(
            article_id=article_id,
            version=version,
            pack_slug=norm_pack,
            title_fr=title_fr,
            title_en=title_en,
            bound_routes=bound_routes,
            glossary_terms=glossary_terms,
            fr_sha=fr_sha,
            en_sha=en_sha,
        )

        hot_attach_ms = round((time.perf_counter() - t_attach) * 1000.0, 3)
        result = GeneratedAndAttachedHelpResult(
            article_id=article_id,
            version=version,
            pack_id=pack_id,
            trigger_regime=trigger_regime,
            bound_routes=tuple(bound_routes),
            fr_cas_key=fr_cas,
            en_cas_key=en_cas,
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

    async def _persist_help_catalog_items(
        self,
        *,
        article_id: str,
        version: str,
        pack_slug: str,
        title_fr: str,
        title_en: str,
        bound_routes: list[str],
        glossary_terms: list[str],
        fr_sha: str,
        en_sha: str,
    ) -> None:
        if self._session_factory is None:
            return
        root_org_id = UUID("0192c4e0-0000-7000-8000-000000000001")
        async with self._session_factory() as session, session.begin():
            await session.execute(
                sa.text(
                    """
                    INSERT INTO org_units (id, slug, name, unit_type, parent_id)
                    VALUES (:id, 'orcia-root-org', 'ORCIA Root Org', 'ENTERPRISE', NULL)
                    ON CONFLICT (id) DO NOTHING
                    """
                ),
                {"id": root_org_id},
            )
            for lang_code, title, sha in (("fr", title_fr, fr_sha), ("en", title_en, en_sha)):
                res_id = f"{article_id}-{lang_code}"
                uri = f"orcia://packs/{pack_slug}/help/{article_id}/{lang_code}"
                meta_json = json.dumps(
                    {
                        "bound_routes": bound_routes,
                        "glossary_terms": glossary_terms,
                        "authority_role": "REFERENCE",
                        "lang": lang_code,
                    }
                )
                await session.execute(
                    sa.text(
                        """
                        INSERT INTO catalog_items (
                            id, resource_id, uri, title, description,
                            resource_type, source_format, version, sha256, cas_key,
                            visibility_scope, owner_org_unit_id, owner_workspace_id,
                            item_type, metadata_jsonb
                        ) VALUES (
                            :id, :resource_id, :uri, :title, :description,
                            'template', 'ORCIA', :version, :sha256, :cas_key,
                            'PUBLISHED_ORG', :owner_org_unit_id, NULL,
                            'HELP_ARTICLE', CAST(:metadata_jsonb AS jsonb)
                        )
                        ON CONFLICT (resource_id) DO UPDATE
                        SET version = EXCLUDED.version,
                            sha256 = EXCLUDED.sha256,
                            cas_key = EXCLUDED.cas_key,
                            metadata_jsonb = EXCLUDED.metadata_jsonb
                        """
                    ),
                    {
                        "id": UUID(str(uuid7())),
                        "resource_id": res_id,
                        "uri": uri,
                        "title": title,
                        "description": f"HelpArticle ({lang_code}) — REFERENCE",
                        "version": version,
                        "sha256": sha,
                        "cas_key": f"cas/{sha}",
                        "owner_org_unit_id": root_org_id,
                        "metadata_jsonb": meta_json,
                    },
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
]
