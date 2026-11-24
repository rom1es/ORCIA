"""Bilingual locale bundles for reflexive agent runtime & adapter outputs (`Story 27.7`)."""

from __future__ import annotations

from dataclasses import dataclass

from orcia_core.kernel.enums import DEFAULT_LOCALE, SupportedLocale


@dataclass(frozen=True, slots=True)
class AgentRuntimeCopy:
    """Localized runtime status & deterministic turn messages."""

    protected_excerpt: str
    default_write_summary: str
    default_rejection_reason: str
    write_approved_summary: str
    write_rejected_summary: str
    fallback_synthesis_heading: str
    inspect_group_title: str
    inspect_thought_tpl: str
    delegate_group_title: str
    delegate_thought_tpl: str
    delegate_objective_tpl: str
    write_preview_group_title: str
    write_preview_thought: str
    write_preview_default_summary: str
    synthesis_empty_refs: str
    synthesis_writes_heading: str
    synthesis_heading_tpl: str
    synthesis_sources_heading: str
    synthesis_code_note: str
    synthesis_group_title: str
    synthesis_thought: str


AGENTS_RUNTIME_LOCALES: dict[SupportedLocale, AgentRuntimeCopy] = {
    "fr": AgentRuntimeCopy(
        protected_excerpt="[Extrait protégé — permission READ_SOURCE requise]",
        default_write_summary="Action externe soumise à approbation",
        default_rejection_reason="Refusé par le valideur humain.",
        write_approved_summary="Écriture externe approuvée et appliquée sur {uri}.",
        write_rejected_summary="Écriture externe refusée par l'humain : {reason}",
        fallback_synthesis_heading="# Synthèse consolidée\n",
        inspect_group_title="Inspection chirurgicale des sources de l'Espace",
        inspect_thought_tpl=(
            "Analysons un extrait ciblé de `{target_uri}` (`#L1-35`)\n"
            "afin d'ancrer la réponse sur les lignes exactes."
        ),
        delegate_group_title="Vérification croisée par un agent spécialisé",
        delegate_thought_tpl=(
            "Sollicitons @{delegate_slug} pour croiser les constats documentaires\n"
            "avec les exigences métier de l'Espace."
        ),
        delegate_objective_tpl="Vérifier la cohérence métier pour : {objective}",
        write_preview_group_title="Préparation de l'aperçu d'écriture gouvernée",
        write_preview_thought=(
            "Préparons la carte d'aperçu avant toute écriture externe\n"
            "pour soumettre la modification à validation humaine."
        ),
        write_preview_default_summary="Valider la publication du livrable",
        synthesis_empty_refs="- Aucune source additionnelle.",
        synthesis_writes_heading="\n\n### Gouvernance d'écriture\n",
        synthesis_heading_tpl="## Synthèse — {objective}\n\n",
        synthesis_sources_heading="### Sources inspectées\n",
        synthesis_code_note="  Livrable structuré vérifié par lecture chirurgicale.\n",
        synthesis_group_title="Consolidation du livrable final",
        synthesis_thought="Synthèse finale prête à partir des observations collectées.",
    ),
    "en": AgentRuntimeCopy(
        protected_excerpt="[Protected excerpt — READ_SOURCE permission required]",
        default_write_summary="External action pending approval",
        default_rejection_reason="Rejected by human reviewer.",
        write_approved_summary="External write approved and applied to {uri}.",
        write_rejected_summary="External write rejected by human: {reason}",
        fallback_synthesis_heading="# Consolidated Synthesis\n",
        inspect_group_title="Surgical inspection of Space sources",
        inspect_thought_tpl=(
            "Let us inspect a targeted excerpt of `{target_uri}` (`#L1-35`)\n"
            "to anchor the answer on exact lines."
        ),
        delegate_group_title="Cross-check by a specialized agent",
        delegate_thought_tpl=(
            "Let us consult @{delegate_slug} to cross-check documentary findings\n"
            "with the Space business requirements."
        ),
        delegate_objective_tpl="Verify business consistency for: {objective}",
        write_preview_group_title="Preparing governed write preview",
        write_preview_thought=(
            "Let us prepare the preview card before any external write\n"
            "to submit the change for human validation."
        ),
        write_preview_default_summary="Approve deliverable publication",
        synthesis_empty_refs="- No additional sources.",
        synthesis_writes_heading="\n\n### Write governance\n",
        synthesis_heading_tpl="## Synthesis — {objective}\n\n",
        synthesis_sources_heading="### Inspected sources\n",
        synthesis_code_note="  Structured deliverable verified via surgical inspection.\n",
        synthesis_group_title="Final deliverable consolidation",
        synthesis_thought="Final synthesis ready from collected observations.",
    ),
}


def get_agent_runtime_copy(locale: SupportedLocale = DEFAULT_LOCALE) -> AgentRuntimeCopy:
    """Return localized agent runtime messages."""
    return AGENTS_RUNTIME_LOCALES.get(locale, AGENTS_RUNTIME_LOCALES[DEFAULT_LOCALE])


__all__ = ["AGENTS_RUNTIME_LOCALES", "AgentRuntimeCopy", "get_agent_runtime_copy"]
