"""Bilingual locale bundles for supervision, challenge/replay, Starlark & MCP (`Story 27.7`)."""

from __future__ import annotations

from orcia_kernel.enums import DEFAULT_LOCALE, SupportedLocale

SUPERVISION_LOCALES: dict[SupportedLocale, dict[str, str]] = {
    "fr": {
        "audit_title": "Contrôle qualité par échantillonnage : {wf}",
        "audit_summary": "Dossier sélectionné automatiquement ({trigger}).",
        "esc_title": "Escalade requise : {wf}",
        "esc_summary": "L'exécution sous contrat ({trigger}) attend une décision humaine.",
        "default_trigger": "Exécution sous contrat",
    },
    "en": {
        "audit_title": "Sampling quality check: {wf}",
        "audit_summary": "Record automatically selected ({trigger}).",
        "esc_title": "Escalation required: {wf}",
        "esc_summary": "Contract execution ({trigger}) is awaiting a human decision.",
        "default_trigger": "Contract execution",
    },
}

CHALLENGE_REPLAY_LOCALES: dict[SupportedLocale, dict[str, str]] = {
    "fr": {
        "preview_summary": (
            "[Traduction Ontologique -> {arch}] Challenge émis depuis '{challenger}' sur "
            "'{target}.{section}' ({translation}) : {reason} — Impact : {inv_count} étape(s) "
            "à rejouer, {pres_count} étape(s) amont préservées (0 token reconsommé)."
        ),
        "revision_summary": "Révision amont v1.1 suite au challenge de '{challenger}'",
    },
    "en": {
        "preview_summary": (
            "[Ontology Translation -> {arch}] Challenge raised from '{challenger}' on "
            "'{target}.{section}' ({translation}): {reason} — Impact: {inv_count} step(s) "
            "to replay, {pres_count} upstream step(s) preserved (0 tokens re-consumed)."
        ),
        "revision_summary": "Upstream revision v1.1 following challenge from '{challenger}'",
    },
}

STARLARK_COMPILER_LOCALES: dict[SupportedLocale, dict[str, str]] = {
    "fr": {
        "verdict_pass": "Conforme : {norm}",
        "verdict_fail": "Écart : {norm}",
        "breadcrumb": "🛡️ [{directive}] ➔ 📏 [{norm}] ➔ ⚙️ Vérifié par : {script}",
        "explanation": (
            "Vérifie de façon déterministe la norme « {norm} » ({rule}) sur le champ '{field}'."
        ),
        "verified_badge": "✓ Vérifié sur cas de test (PASS/FAIL en < 5 ms)",
    },
    "en": {
        "verdict_pass": "Compliant: {norm}",
        "verdict_fail": "Deviation: {norm}",
        "breadcrumb": "🛡️ [{directive}] ➔ 📏 [{norm}] ➔ ⚙️ Verified by: {script}",
        "explanation": "Deterministically enforces norm « {norm} » ({rule}) on field '{field}'.",
        "verified_badge": "✓ Verified on test cases (PASS/FAIL in < 5 ms)",
    },
}

MCP_BENCH_LOCALES: dict[SupportedLocale, dict[str, str]] = {
    "fr": {
        "restricted_tag": "[S1 · 🔒 Source restreinte]",
        "governed_reply": "Réponse gouvernée ({name}) sur « {prompt} » {tag}",
        "history_badge": "💻 Appelé via MCP (IDE)",
        "exposure_desc": "Exposition MCP gouvernée ({regime})",
        "tool_kb_search": (
            "Recherche hybride RAG (vecteurs + BM25) dans la KB multi-sources du Workspace."
        ),
        "tool_catalog_get": (
            "Consulter les Workflows, Agents et Skills épinglés du Catalogue Fédéré."
        ),
        "tool_blackboard_read": "Lire les snapshots actifs du Blackboard pour un Run donné.",
        "tool_propose_draft": (
            "Proposer un brouillon sur une section non protégée (bloque matériellement toute "
            "section marquée human_authored_required: true)."
        ),
        "wasm_ok": "Sandbox WASM locale isolée vérifiée.",
        "bad_scheme": "Schéma '{scheme}' interdit (HTTPS requis).",
        "missing_host": "Hôte manquant dans l'URL.",
        "ssrf_blocked": "Anti-SSRF : cible ou adresse IP interdite '{host}' bloquée.",
        "net_ok": "Réseau, TLS & Anti-SSRF validés.",
        "auth_skipped": "Ignoré (Étape 1 Réseau/Anti-SSRF en échec).",
        "auth_wait_token": "🟠 En attente de jeton utilisateur (Passthrough)",
        "auth_secret_fail": (  # pragma: allowlist secret
            "Échec de validation du secret via SecretProviderPort."
        ),
        "auth_ok": "Authentification vérifiée avec succès.",
        "write_staged": "✍️ Écriture -> Action Staged obligatoire (AD-3)",
        "read_only": "👁️ Lecture seule",
        "cap_desc": "Capacité découverte : {name}",
        "discovered_count": "{count} outil(s) découvert(s) et qualifié(s).",
        "skipped": "Ignoré.",
        "dry_timeout": "Timeout Dry-Run dépassé (> 5 s).",
        "dry_size": "Taille maximale de réponse Dry-Run dépassée (> 1 Mo).",
        "dry_ok": "Essai rapide à chaud validé (< 5 s, <= 1 Mo).",
        "dry_deferred": "Dry-Run différé (en attente de jeton Passthrough ou étape amont).",
    },
    "en": {
        "restricted_tag": "[S1 · 🔒 Restricted source]",
        "governed_reply": "Governed response ({name}) on « {prompt} » {tag}",
        "history_badge": "💻 Called via MCP (IDE)",
        "exposure_desc": "Governed MCP exposure ({regime})",
        "tool_kb_search": "Hybrid RAG search (vectors + BM25) across Workspace multi-sources KB.",
        "tool_catalog_get": (
            "Query pinned Workflows, Agents, and Skills from the Federated Catalog."
        ),
        "tool_blackboard_read": "Read active Blackboard snapshots for a given Run.",
        "tool_propose_draft": (
            "Propose a draft on an unprotected section (materially blocks any section "
            "marked human_authored_required: true)."
        ),
        "wasm_ok": "Isolated local WASM sandbox verified.",
        "bad_scheme": "Scheme '{scheme}' forbidden (HTTPS required).",
        "missing_host": "Missing host in URL.",
        "ssrf_blocked": "Anti-SSRF: forbidden target or IP address '{host}' blocked.",
        "net_ok": "Network, TLS & Anti-SSRF validated.",
        "auth_skipped": "Skipped (Step 1 Network/Anti-SSRF failed).",
        "auth_wait_token": "🟠 Awaiting user token (Passthrough)",
        "auth_secret_fail": (  # pragma: allowlist secret
            "Secret validation failed via SecretProviderPort."
        ),
        "auth_ok": "Authentication verified successfully.",
        "write_staged": "✍️ Write -> Mandatory Staged Action (AD-3)",
        "read_only": "👁️ Read-only",
        "cap_desc": "Discovered capability: {name}",
        "discovered_count": "{count} tool(s) discovered and qualified.",
        "skipped": "Skipped.",
        "dry_timeout": "Dry-Run timeout exceeded (> 5 s).",
        "dry_size": "Maximum Dry-Run response size exceeded (> 1 MB).",
        "dry_ok": "Hot quick test validated (< 5 s, <= 1 MB).",
        "dry_deferred": "Dry-Run deferred (awaiting Passthrough token or upstream step).",
    },
}

OUTBOX_SSE_LOCALES: dict[SupportedLocale, dict[str, str]] = {
    "fr": {
        "arb_title": "⚖️ Arbitrage Humain requis sur '{step}'",
        "arb_summary": "L'étape '{step}' attend un arbitrage humain entre {opts} options.",
        "gate_title": "🛡️ Escalade Gate ({gate_type}) sur '{step}'",
        "gate_summary": "La Gate {gate_type} a signalé un écart (score={score}).",
        "step_title": "Action humaine requise ({ntype}) sur '{step}'",
        "step_summary": "L'étape '{step}' est en pause ({status}).",
    },
    "en": {
        "arb_title": "⚖️ Human Arbitration required on '{step}'",
        "arb_summary": "Step '{step}' is awaiting human arbitration across {opts} options.",
        "gate_title": "🛡️ Gate Escalation ({gate_type}) on '{step}'",
        "gate_summary": "Gate {gate_type} flagged a deviation (score={score}).",
        "step_title": "Human action required ({ntype}) on '{step}'",
        "step_summary": "Step '{step}' is paused ({status}).",
    },
}


def get_runtime_copy(
    table: dict[SupportedLocale, dict[str, str]],
    locale: SupportedLocale = DEFAULT_LOCALE,
) -> dict[str, str]:
    return table.get(locale, table[DEFAULT_LOCALE])


__all__ = [
    "CHALLENGE_REPLAY_LOCALES",
    "MCP_BENCH_LOCALES",
    "OUTBOX_SSE_LOCALES",
    "STARLARK_COMPILER_LOCALES",
    "SUPERVISION_LOCALES",
    "get_runtime_copy",
]
