"""Models and Markdown renderer for Process 5 (`generate-and-attach-help`) & Process 6."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Literal

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
        "AutonomyContractModal",
    }
)


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


@dataclass(frozen=True, slots=True)
class OrciaDocumentationWorkflowStepResult:
    """Single step outcome of Process 6 (`generate-orcia-documentation`)."""

    step_number: int
    step_key: str
    title_fr: str
    title_en: str
    lead_agent_handle: str
    status: Literal["COMPLETED", "FAILED"]
    summary_fr: str
    summary_en: str
    elapsed_ms: float


@dataclass(frozen=True, slots=True)
class OrciaDocumentationWorkflowReport:
    """Full 4-step execution report for Process 6 (`generate-orcia-documentation`)."""

    workflow_slug: str
    workflow_uri: str
    lead_agent_handle: str
    routes_inventoried_count: int
    ui_components_inventoried_count: int
    help_files_inventoried_count: int
    faq_architecture_present: bool
    tech_lead_reports_count: int
    steps: tuple[OrciaDocumentationWorkflowStepResult, ...]
    generated_markdown_fr: str
    generated_markdown_en: str
    validation_fr: HelpArticleValidationReport
    validation_en: HelpArticleValidationReport
    published_targets: tuple[str, ...]
    total_elapsed_ms: float


def render_bilingual_help_markdown_text(
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
