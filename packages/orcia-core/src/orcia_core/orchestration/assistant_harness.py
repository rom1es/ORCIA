"""5-Layer Prompt Harness (`AssistantHarness`) & Profile Adaptation (`Story 3.3`, `AD-15`, `AR-4`).

Implements the 5-layer prompt architecture for `orcia://system/workflows/assistant-agent` with
zero SDLC vocabulary inside `orcia-core` (`AD-20`):
1. Layer 1 — `CONSTITUTIONAL_IMMUTABLE`: Prohibits any write to `human_authored_required: true`
   (*Human-Led Anchor Card*) or any autonomous Gate approval; enforces Socratic coaching.
2. Layer 2 — `ONTOLOGY_AND_AXIOMS_L1_L4`: Injects active ontology concepts & immutable axioms.
3. Layer 3 — `HUMAN_PROFILE_ADAPTATION` (`UX-DR12`, `FR-1`): Adapts register, KPIs, and
   indicators to the user's `HumanProfileArchetype` (`EXECUTIVE`, `PM`, `ARCHITECT`,
   `TECH_LEAD`, `DEVELOPER`, `SECOPS`).
4. Layer 4 — `FEDERATED_CONTEXT_FANOUT` (`DEC-CTX-01`): Injects `ContextSliceRecord` and
   `VectorSearchHitRecord` items from `ContextSourcePort` and `VectorStorePort`.
5. Layer 5 — `CONVERSATIONAL_INTENT_AND_COMPOSER`: Current user turn and optional workflow
   composition / modification instructions.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Literal

from orcia_kernel.context_ports import (
    AssistantWorkflowBlueprint,
    ContextSliceRecord,
    VectorSearchHitRecord,
)

AssistantLayerId = Literal[
    "1_CONSTITUTIONAL_IMMUTABLE",
    "2_ONTOLOGY_AND_AXIOMS_L1_L4",
    "3_HUMAN_PROFILE_ADAPTATION",
    "4_FEDERATED_CONTEXT_FANOUT",
    "5_CONVERSATIONAL_INTENT_AND_COMPOSER",
]

AssistantIntentKind = Literal[
    "QA_COACHING",
    "WORKFLOW_COMPOSE",
    "WORKFLOW_MODIFY",
    "WORKFLOW_LAUNCH",
    "HUMAN_ANCHOR_WRITE_REFUSAL",
]

CONSTITUTIONAL_LAYER_1_TEXT: str = (
    "[CONSTITUTIONAL_IMMUTABLE_LAYER_1]\n"
    "1. [NO_HUMAN_ANCHOR_WRITE]: Interdiction absolue de rédiger, pré-remplir ou modifier toute "
    "section marquée `human_authored_required: true` (Human-Led Anchor Card). En cas de demande "
    "de rédaction à la place de l'humain, refuser poliment et engager un questionnement "
    "socratique.\n"
    "2. [NO_GATE_SELF_APPROVAL]: Interdiction absolue d'approuver ou de contourner une Gate "
    "Déterministe, Agentique ou Humaine.\n"
    "3. [EXPLICIT_PROVENANCE_URI]: Toute affirmation factuelle doit citer son URI canonique "
    "`orcia://` et son condensat `sha256:`."
)


@dataclass(frozen=True, slots=True)
class ProfileAdaptationSpec:
    """Semantic adaptation descriptor for a `HumanProfileArchetype` (`FR-1`, `UX-DR12`)."""

    archetype: str
    register_label: str
    vocabulary_tier: Literal[
        "N1_N2_EXECUTIVE",
        "N2_PRODUCT_RULES",
        "N3_TECHNICAL_LINEAGE",
        "N3_SECOPS_GATES",
    ]
    highlighted_indicators: tuple[str, ...]
    response_prefix_fr: str


PROFILE_ADAPTATION_MAP: dict[str, ProfileAdaptationSpec] = {
    "EXECUTIVE": ProfileAdaptationSpec(
        archetype="EXECUTIVE",
        register_label="Direction / BU — KPIs FinOps, ROI, TTM & Risques N1/N2",
        vocabulary_tier="N1_N2_EXECUTIVE",
        highlighted_indicators=("Coût FinOps ($)", "Gain TTM (%)", "Indice de Risque BU", "ROI"),
        response_prefix_fr="[Synthèse Direction N1/N2 — KPIs FinOps & TTM]",
    ),
    "PM": ProfileAdaptationSpec(
        archetype="PM",
        register_label="Product / Métier — Règles de Gestion & Invariants Fonctionnels",
        vocabulary_tier="N2_PRODUCT_RULES",
        highlighted_indicators=(
            "Règles de Gestion",
            "Parcours Utilisateurs",
            "Critères d'Acceptation",
            "Ancres Humaines",
        ),
        response_prefix_fr="[Synthèse Produit & Règles de Gestion Métier]",
    ),
    "ARCHITECT": ProfileAdaptationSpec(
        archetype="ARCHITECT",
        register_label="Architecte — URIs Canoniques, Contrats OpenAPI & Hashes SHA-256 N3",
        vocabulary_tier="N3_TECHNICAL_LINEAGE",
        highlighted_indicators=(
            "URI Canoniques orcia://",
            "Contrats OpenAPI 3.1",
            "Hashes CAS SHA-256",
            "Axiomes Ontologiques L1..L4",
        ),
        response_prefix_fr="[Synthèse Architecture N3 — URIs, Contrats & SHA-256]",
    ),
    "TECH_LEAD": ProfileAdaptationSpec(
        archetype="TECH_LEAD",
        register_label="Tech Lead — Topologie DAG, Dépendances, Hashes SHA-256 & Exécution N3",
        vocabulary_tier="N3_TECHNICAL_LINEAGE",
        highlighted_indicators=(
            "DAG Steps & Verrous run-lock.json",
            "Hashes CAS SHA-256",
            "Couverture & Dette Technique",
            "URIs orcia://",
        ),
        response_prefix_fr="[Synthèse Tech Lead N3 — Topologie DAG & Hashes SHA-256]",
    ),
    "DEVELOPER": ProfileAdaptationSpec(
        archetype="DEVELOPER",
        register_label="Développeur — Spécifications d'Étape, Entrées/Sorties & Contrats N3",
        vocabulary_tier="N3_TECHNICAL_LINEAGE",
        highlighted_indicators=(
            "Pointeurs JIT d'Artefacts",
            "Schémas d'Entrée/Sortie",
            "Hashes CAS SHA-256",
            "URIs orcia://",
        ),
        response_prefix_fr="[Synthèse Technique N3 — Contrats & Pointeurs d'Étape]",
    ),
    "SECOPS": ProfileAdaptationSpec(
        archetype="SECOPS",
        register_label="SecOps — Preuves de Gates, Isolation Passthrough & Conformité",
        vocabulary_tier="N3_SECOPS_GATES",
        highlighted_indicators=(
            "Preuves de Gates",
            "Isolation Passthrough / Service Principal",
            "Politiques Permission Broker",
            "Intégrité Audit Ledger",
        ),
        response_prefix_fr="[Synthèse SecOps — Preuves de Gates & Isolation Passthrough]",
    ),
}


def resolve_profile_adaptation(archetype: str) -> ProfileAdaptationSpec:
    """Resolve `ProfileAdaptationSpec` for a user's `human_profile_archetype` (`UX-DR12`)."""
    norm = archetype.strip().upper()
    return PROFILE_ADAPTATION_MAP.get(norm, PROFILE_ADAPTATION_MAP["ARCHITECT"])


@dataclass(frozen=True, slots=True)
class PromptLayerBlock:
    """Single immutable layer inside the 5-layer `AssistantHarness` (`AD-15`)."""

    layer_id: AssistantLayerId
    layer_order: int
    immutable: bool
    content_sha256: str
    content: str


@dataclass(frozen=True, slots=True)
class AssembledAssistantPrompt:
    """Full 5-layer prompt assembled by `AssistantHarness` (`AD-15`, `AR-4`)."""

    layers: tuple[PromptLayerBlock, ...]
    system_prompt: str
    user_prompt: str
    constitutional_sha256: str
    profile_adaptation: ProfileAdaptationSpec
    cited_uris: tuple[str, ...]
    stale_warnings: tuple[str, ...]


def _sha256_str(text: str) -> str:
    return f"sha256:{hashlib.sha256(text.encode('utf-8')).hexdigest()}"


class AssistantHarness:
    """Assembles the 5-layer prompt for `orcia://system/workflows/assistant-agent` (`AD-15`)."""

    def assemble_prompt(
        self,
        *,
        user_prompt: str,
        human_profile_archetype: str,
        workspace_id: str,
        intent: AssistantIntentKind,
        ontology_concepts: tuple[dict[str, Any], ...] = (),
        ontology_axioms: tuple[dict[str, Any], ...] = (),
        context_slices: tuple[ContextSliceRecord, ...] = (),
        vector_hits: tuple[VectorSearchHitRecord, ...] = (),
        workflow_blueprint: AssistantWorkflowBlueprint | None = None,
    ) -> AssembledAssistantPrompt:
        """Assemble all 5 layers and compute cryptographic provenance hashes."""
        layer_1 = PromptLayerBlock(
            layer_id="1_CONSTITUTIONAL_IMMUTABLE",
            layer_order=1,
            immutable=True,
            content_sha256=_sha256_str(CONSTITUTIONAL_LAYER_1_TEXT),
            content=CONSTITUTIONAL_LAYER_1_TEXT,
        )

        concept_lines = [
            f"- Concept [{c.get('level', 'L3')}] {c.get('canonical_term', c.get('key', ''))}: "
            f"{c.get('definition', '')}"
            for c in ontology_concepts
        ] or ["- Aucun concept ontologique spécifique actif."]
        axiom_lines = [
            f"- Axiome [IMMUTABLE={a.get('immutable', True)}] {a.get('axiom_key', '')}: "
            f"{a.get('formal_rule', '')}"
            for a in ontology_axioms
        ] or ["- Axiome de base : Intégrité des références `orcia://`."]
        layer_2_text = (
            "[ONTOLOGY_AND_AXIOMS_LAYER_2]\n"
            "Concepts Ontologiques Actifs :\n"
            + "\n".join(concept_lines)
            + "\nAxiomes Formels :\n"
            + "\n".join(axiom_lines)
        )
        layer_2 = PromptLayerBlock(
            layer_id="2_ONTOLOGY_AND_AXIOMS_L1_L4",
            layer_order=2,
            immutable=True,
            content_sha256=_sha256_str(layer_2_text),
            content=layer_2_text,
        )

        profile_spec = resolve_profile_adaptation(human_profile_archetype)
        layer_3_text = (
            f"[HUMAN_PROFILE_ADAPTATION_LAYER_3]\n"
            f"Archetype: {profile_spec.archetype}\n"
            f"Registre: {profile_spec.register_label}\n"
            f"Indicateurs prioritaires: {', '.join(profile_spec.highlighted_indicators)}\n"
            f"Préfixe attendu: {profile_spec.response_prefix_fr}"
        )
        layer_3 = PromptLayerBlock(
            layer_id="3_HUMAN_PROFILE_ADAPTATION",
            layer_order=3,
            immutable=False,
            content_sha256=_sha256_str(layer_3_text),
            content=layer_3_text,
        )

        cited_uris: list[str] = []
        stale_warnings: list[str] = []
        fanout_lines: list[str] = []
        for s in context_slices:
            cited_uris.append(s.source_uri)
            if s.is_stale and s.stale_warning_marker:
                stale_warnings.append(f"{s.source_uri}: {s.stale_warning_marker}")
            fanout_lines.append(
                f"- [{s.source_kind}] {s.source_uri} ({s.content_sha256[:19]}): {s.text_excerpt}"
            )
        for h in vector_hits:
            if h.source_uri not in cited_uris:
                cited_uris.append(h.source_uri)
            if h.is_stale and h.stale_warning_marker:
                stale_warnings.append(f"{h.source_uri}: {h.stale_warning_marker}")
            fanout_lines.append(
                f"- [VECTOR_RRF={h.rrf_score:.4f}] {h.source_uri} ({h.chunk_key}): "
                f"{h.injected_content[:180]}"
            )
        if not fanout_lines:
            fanout_lines.append(f"- Périmètre Workspace `{workspace_id}` (aucune tranche externe).")

        layer_4_text = "[FEDERATED_CONTEXT_FANOUT_LAYER_4]\n" + "\n".join(fanout_lines)
        layer_4 = PromptLayerBlock(
            layer_id="4_FEDERATED_CONTEXT_FANOUT",
            layer_order=4,
            immutable=False,
            content_sha256=_sha256_str(layer_4_text),
            content=layer_4_text,
        )

        composer_note = (
            f"Blueprint Workflow: {workflow_blueprint.workflow_uri} ({workflow_blueprint.title})"
            if workflow_blueprint is not None
            else "Aucun blueprint de workflow requis."
        )
        layer_5_text = (
            f"[CONVERSATIONAL_INTENT_AND_COMPOSER_LAYER_5]\n"
            f"Workspace: {workspace_id}\n"
            f"Intention classifiée: {intent}\n"
            f"{composer_note}\n"
            f"Message utilisateur: {user_prompt}"
        )
        layer_5 = PromptLayerBlock(
            layer_id="5_CONVERSATIONAL_INTENT_AND_COMPOSER",
            layer_order=5,
            immutable=False,
            content_sha256=_sha256_str(layer_5_text),
            content=layer_5_text,
        )

        layers = (layer_1, layer_2, layer_3, layer_4, layer_5)
        system_prompt = "\n\n".join(block.content for block in layers[:4])
        return AssembledAssistantPrompt(
            layers=layers,
            system_prompt=system_prompt,
            user_prompt=layer_5_text,
            constitutional_sha256=layer_1.content_sha256,
            profile_adaptation=profile_spec,
            cited_uris=tuple(cited_uris),
            stale_warnings=tuple(stale_warnings),
        )
