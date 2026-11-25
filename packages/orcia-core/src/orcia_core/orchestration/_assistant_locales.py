"""Bilingual locale bundles for Assistant nodes, folders & three-speed turns (`Story 27.7`)."""

from __future__ import annotations

from orcia_kernel.enums import DEFAULT_LOCALE, SupportedLocale

ASSISTANT_NODE_LOCALES: dict[SupportedLocale, dict[str, str]] = {
    "fr": {
        "intent_summary": "Intention classifiée : {intent}",
        "fan_out_summary": (
            "Fan-out parallèle : {vec_count} hits RAG + {slice_count} tranches ContextSourcePort"
        ),
        "triage_summary": "Tri critique & vérification d'axiomes ({stale_count} alertes STALE)",
        "synth_summary": "Synthèse profil {archetype} ({ms:.2f} ms < 1500 ms)",
        "unverified_citation": "[Citation non vérifiée]",
        "evidence_footer": (
            "📚 {s_count} sources consultées {s_range} · {g_count} termes du Glossaire {g_range} ▾"
        ),
        "restricted_pill": "[{tag} · 🔒 Source restreinte — Demander l'accès]",
    },
    "en": {
        "intent_summary": "Classified intent: {intent}",
        "fan_out_summary": (
            "Parallel fan-out: {vec_count} RAG hits + {slice_count} ContextSourcePort slices"
        ),
        "triage_summary": "Critical triage & axiom verification ({stale_count} STALE alerts)",
        "synth_summary": "Profile synthesis {archetype} ({ms:.2f} ms < 1500 ms)",
        "unverified_citation": "[Unverified citation]",
        "evidence_footer": (
            "📚 {s_count} sources consulted {s_range} · {g_count} Glossary terms {g_range} ▾"
        ),
        "restricted_pill": "[{tag} · 🔒 Restricted source — Request access]",
    },
}

ASSISTANT_FOLDER_LOCALES: dict[SupportedLocale, dict[str, str]] = {
    "fr": {
        "no_attachment": "Aucune pièce jointe",
        "no_prev_summary": "Aucun résumé précédent",
        "no_pinned_note": "Aucune note épinglée",
        "no_folder": "Sans dossier",
        "block_notes": "📌 Notes du dossier : {notes}",
        "block_deliverables": "📎 Livrables & pièces de travail : {attachments}",
        "block_summaries": "🧵 Résumés consolidés des discussions précédentes : {summaries}",
        "restricted_warning": (
            "⚠️ Ce dossier cite des sources restreintes : leurs extraits seront "
            "automatiquement masqués ([🔒 Source restreinte — Demander l'accès]) "
            "pour les collègues non habilités."
        ),
        "presence_banner": "✍️ {first_name} interroge l'assistant...",
        "collab_reply": (
            "Réponse générée sous identité `{identity}` avec continuité "
            "Couche 5 (`{folder_title}`) [S1]."
        ),
        "team_instructions": (
            "Standards d'équipe : traçabilité systématique des décisions et revues croisées."
        ),
        "user_default_instructions": "",
        "ws_default_instructions": (
            "Respecter le glossaire actif de l'Espace et privilégier les sources RÉFÉRENCE."
        ),
        "ws_suggestions": (
            "Synthétiser les derniers écarts documentaires de l'Espace|"
            "Vérifier la conformité d'un ticket avec l'ontologie N1–N3|"
            "Préparer un dossier de cadrage technique|Analyser l'impact d'une modification d'API"
        ),
    },
    "en": {
        "no_attachment": "No attachments",
        "no_prev_summary": "No previous summary",
        "no_pinned_note": "No pinned notes",
        "no_folder": "No folder",
        "block_notes": "📌 Folder notes: {notes}",
        "block_deliverables": "📎 Deliverables & working files: {attachments}",
        "block_summaries": "🧵 Consolidated previous discussion summaries: {summaries}",
        "restricted_warning": (
            "⚠️ This folder cites restricted sources: their excerpts will be "
            "automatically masked ([🔒 Restricted source — Request access]) "
            "for unauthorized colleagues."
        ),
        "presence_banner": "✍️ {first_name} is querying the assistant...",
        "collab_reply": (
            "Response generated under `{identity}` identity with Layer 5 continuity "
            "(`{folder_title}`) [S1]."
        ),
        "team_instructions": "Team standards: systematic decision traceability and peer reviews.",
        "user_default_instructions": "",
        "ws_default_instructions": (
            "Follow the active Space glossary and prioritize REFERENCE sources."
        ),
        "ws_suggestions": (
            "Summarize recent Space documentary gaps|"
            "Check ticket compliance against L1–L3 ontology|"
            "Prepare a technical framing dossier|Analyze the impact of an API change"
        ),
    },
}

ASSISTANT_SYNTHESIS_LOCALES: dict[SupportedLocale, dict[str, str]] = {
    "fr": {
        "anchor_refusal": (
            "{prefix} Refus constitutionnel (`human_authored_required: true`, `FR-4`, `AD-3`) : "
            "Je ne peux pas rédiger ni pré-remplir une Ancre Humaine à votre place afin de "
            "préserver votre maîtrise intellectuelle (*Think*). Question socratique : "
            "quels sont les 2 invariants métier non négociables que vous souhaitez fixer "
            "pour le périmètre `{workspace_id}` ?"
        ),
        "cited_sources": " Sources citées : {uris}.",
        "scope_note": " Périmètre : `orcia://workspaces/{workspace_id}`.",
        "proposal_ready": (
            "{prefix} ({indicators}) — Proposition de workflow `{workflow_uri}` "
            "({count} étapes, régime `{regime}`) prête dans le Canvas `@xyflow/react`."
            "{uris_note} [{sha}]"
        ),
    },
    "en": {
        "anchor_refusal": (
            "{prefix} Constitutional refusal (`human_authored_required: true`, `FR-4`, `AD-3`): "
            "I cannot write or pre-fill a Human Anchor on your behalf so as to preserve your "
            "intellectual mastery (*Think*). Socratic question: what are the 2 non-negotiable "
            "business invariants you wish to set for scope `{workspace_id}`?"
        ),
        "cited_sources": " Cited sources: {uris}.",
        "scope_note": " Scope: `orcia://workspaces/{workspace_id}`.",
        "proposal_ready": (
            "{prefix} ({indicators}) — Workflow proposal `{workflow_uri}` "
            "({count} steps, `{regime}` regime) ready in `@xyflow/react` Canvas.{uris_note} [{sha}]"
        ),
    },
}

ASSISTANT_THREE_SPEED_LOCALES: dict[SupportedLocale, dict[str, str]] = {
    "fr": {
        "cadrage_summary": (
            "Demande analysée pour l'espace « {workspace_id} » (rôle : {active_hat}) : "
            "« {prompt_excerpt} »."
        ),
        "s1_step2_label": "💬 Nœud 5 — Appel LLM unique en streaming SSE (TTFT < 1,2 s)",
        "s1_step2_thinking": (
            "Formulation d'une réponse directe et synthétique pour « {prompt_excerpt} »."
        ),
        "s1_det_label": (
            "⚡ Nœuds 1–4 déterministes (Intention, RBAC, RAG SQL/pgvector & Cache 5 couches)"
        ),
        "s1_response": (
            "[⚡ Vitesse 1 · Casquette {active_hat}] Réponse directe générée avec "
            "prompt 5 couches ({cache_state} Redis) : "
            "Synthèse conforme pour « {prompt} » [S1] [G1]."
        ),
        "s2_default_target": "Connecteur",
        "s2_det_label": "⚡ Nœuds 1–4 déterministes & vérification RBAC/Passthrough",
        "s2_conn_label": "🔍 Interrogation de {target_source}...",
        "s2_conn_out": "Mobilisation des compétences et connecteurs : {targets}.",
        "s2_exec_label": "🛠️ Exécution ConnectorInvoker ({targets})",
        "s2_exec_thinking": (
            "Consolidation des éléments retournés par {targets} pour « {prompt_excerpt} »."
        ),
        "s2_response": (
            "[🛠️ Vitesse 2 · {targets}] Résultat d'interrogation outillée "
            "pour « {prompt} » [S1] [O1]."
        ),
        "s3_det_label": "⚡ Nœuds 1–4 déterministes & assemblage 5 couches",
        "s3_plan_label": "📋 Planification LLM intermédiaire & décomposition causale N1–N3...",
        "s3_plan_out": (
            "Décomposition de la problématique « {prompt_excerpt} » en 3 axes : "
            "1) Synthèse exécutive, 2) Risques & conformité, 3) Plan d'action."
        ),
        "s3_lens_label": (
            "🔬 Vérification multi-facettes orthogonale (AD-10 : Architecture, Sécurité, FinOps)..."
        ),
        "s3_lens_out": (
            "Revue croisée des 3 facettes : cohérence fonctionnelle, "
            "sécurité des accès et maîtrise des coûts."
        ),
        "s3_synth_label": "✍️ Synthèse contradictoire consolidée",
        "s3_synth_out": "Rédaction de la synthèse structurée finale.",
        "s3_response": (
            "[🧠 Vitesse 3 Approfondi · Audit multi-facettes AD-10 ({lenses})] "
            "Analyse approfondie vérifiée pour « {prompt} » [S1] [G1]."
        ),
    },
    "en": {
        "cadrage_summary": (
            "Request analyzed for space '{workspace_id}' (hat: {active_hat}): '{prompt_excerpt}'."
        ),
        "s1_step2_label": "💬 Node 5 — Single-shot LLM SSE streaming call (TTFT < 1.2s)",
        "s1_step2_thinking": "Formulating a direct, concise answer for '{prompt_excerpt}'.",
        "s1_det_label": (
            "⚡ Deterministic Nodes 1–4 (Intent, RBAC, SQL/pgvector RAG & 5-Layer Cache)"
        ),
        "s1_response": (
            "[⚡ Speed 1 · Hat {active_hat}] Direct response generated with "
            "5-layer prompt (Redis {cache_state}): "
            "Compliant synthesis for '{prompt}' [S1] [G1]."
        ),
        "s2_default_target": "Connector",
        "s2_det_label": "⚡ Deterministic Nodes 1–4 & RBAC/Passthrough check",
        "s2_conn_label": "🔍 Querying {target_source}...",
        "s2_conn_out": "Invoking skills and connectors: {targets}.",
        "s2_exec_label": "🛠️ ConnectorInvoker execution ({targets})",
        "s2_exec_thinking": "Consolidating items returned by {targets} for '{prompt_excerpt}'.",
        "s2_response": (
            "[🛠️ Speed 2 · {targets}] Tool-assisted query result for '{prompt}' [S1] [O1]."
        ),
        "s3_det_label": "⚡ Deterministic Nodes 1–4 & 5-layer prompt assembly",
        "s3_plan_label": "📋 Intermediate LLM planning & L1–L3 causal decomposition...",
        "s3_plan_out": (
            "Breaking down problem '{prompt_excerpt}' across 3 axes: "
            "1) Executive summary, 2) Risks & compliance, 3) Action plan."
        ),
        "s3_lens_label": (
            "🔬 Orthogonal multi-lens verification (AD-10: Architecture, Security, FinOps)..."
        ),
        "s3_lens_out": (
            "Cross-review of all 3 facets: functional consistency, "
            "access security, and cost control."
        ),
        "s3_synth_label": "✍️ Consolidated adversarial synthesis",
        "s3_synth_out": "Drafting the final structured synthesis.",
        "s3_response": (
            "[🧠 Speed 3 Deep · Multi-Lens Audit AD-10 ({lenses})] "
            "Verified deep analysis for '{prompt}' [S1] [G1]."
        ),
    },
}


def get_assistant_node_copy(locale: SupportedLocale = DEFAULT_LOCALE) -> dict[str, str]:
    return ASSISTANT_NODE_LOCALES.get(locale, ASSISTANT_NODE_LOCALES[DEFAULT_LOCALE])


__all__ = [
    "ASSISTANT_FOLDER_LOCALES",
    "ASSISTANT_NODE_LOCALES",
    "ASSISTANT_SYNTHESIS_LOCALES",
    "ASSISTANT_THREE_SPEED_LOCALES",
    "get_assistant_node_copy",
]
