"""Bilingual FR/EN locale bundle for Audit & FinOps services (`Story 27.7`)."""

from __future__ import annotations

from dataclasses import dataclass

from orcia_kernel.enums import DEFAULT_LOCALE, SupportedLocale


@dataclass(frozen=True, slots=True)
class AuditFinopsLocaleBundle:
    """Localized strings for Audit Ledger summaries, Provenance exports, and Cognitive Impact."""

    circuit_reset_tpl: str
    budget_override_tpl: str
    post_hoc_contract_trigger: str
    rec_strengthen_title: str
    rec_strengthen_desc_tpl: str
    rec_strengthen_action: str
    rec_sampling_title: str
    rec_sampling_desc_tpl: str
    rec_sampling_action: str
    rec_applied_wf_fallback: str
    rec_applied_title: str
    rec_applied_desc: str
    rec_applied_action: str
    prov_aligned: str
    prov_diverged: str
    prov_none_models: str
    prov_system_actor: str
    prov_title_tpl: str
    prov_attestation: str
    prov_certifies_tpl: str
    prov_exported_at_tpl: str
    prov_sec1_title: str
    prov_lbl_align: str
    prov_lbl_run_lock: str
    prov_lbl_contract: str
    prov_lbl_events: str
    prov_lbl_tokens: str
    prov_lbl_cost: str
    prov_lbl_models: str
    prov_lbl_actors: str
    prov_lbl_period: str
    prov_sec2_title: str
    prov_table_header: str
    prov_sec3_title: str
    prov_no_cas: str
    prov_footer: str


AUDIT_FINOPS_LOCALES: dict[SupportedLocale, AuditFinopsLocaleBundle] = {
    "fr": AuditFinopsLocaleBundle(
        circuit_reset_tpl="Réarmement du coupe-circuit connecteur {key} -> {state}",
        budget_override_tpl="Dérogation budgétaire approuvée (+{amount:.2f} USD) : {reason}",
        post_hoc_contract_trigger="Exécution sous contrat",
        rec_strengthen_title="Renforcement des saisies expertes préalables",
        rec_strengthen_desc_tpl=(
            "Le processus '{wf_title}' hautement critique est validé à 100 % sans "
            "observation. Pour garantir une maîtrise active, renforcez les ancrages "
            "humains obligatoires en amont de l'étape."
        ),
        rec_strengthen_action="Renforcer les saisies expertes",
        rec_sampling_title="Politique ciblée par risque ou par échantillonnage",
        rec_sampling_desc_tpl=(
            "Le processus '{wf_title}' présente un taux de validation unanime avec des "
            "délais de lecture courts. Basculez la vérification en échantillonnage (20 %) "
            "pour préserver l'attention critique."
        ),
        rec_sampling_action="Passer en échantillonnage (20 %)",
        rec_applied_wf_fallback="Processus appliqué",
        rec_applied_title="Politique de validation ajustée",
        rec_applied_desc="Politique ajustée avec succès.",
        rec_applied_action="Appliquée",
        prov_aligned="CONFORME (100 % ALIGNÉ)",
        prov_diverged="ALERTE : DIVERGENCE DÉTECTÉE",
        prov_none_models="Aucun",
        prov_system_actor="Système",
        prov_title_tpl="# Dossier de Provenance & d'Audit Immuable — Exécution `{run_id}`",
        prov_attestation="> **Attestation de Conformité Réglementaire (AI Act, DORA, NIS 2)**",
        prov_certifies_tpl=(
            "> Ce dossier certifie l'historique complet, inaltérable et vérifié "
            "de l'exécution `{run_id}`."
        ),
        prov_exported_at_tpl="> Horodatage de l'export : `{exported_at}`",
        prov_sec1_title="## 1. Synthèse Exécutive & Empreintes Cryptographiques",
        prov_lbl_align="- **Statut d'alignement Run Lock** : `{aligned_label}`",
        prov_lbl_run_lock="- **Condensat Run Lock (`run-lock.json`)** : `{sha}`",
        prov_lbl_contract="- **Condensat Contrat de Workflow** : `{sha}`",
        prov_lbl_events="- **Nombre total d'événements audités** : `{count}`",
        prov_lbl_tokens="- **Consommation globale de tokens** : `{tokens}`",
        prov_lbl_cost="- **Coût complet consolidé** : `${cost:.6f} USD`",
        prov_lbl_models="- **Modèles d'intelligence artificielle invoqués** : `{models}`",
        prov_lbl_actors="- **Intervenants & Acteurs** : `{actors}`",
        prov_lbl_period="- **Période d'exécution** : `{period}`",
        prov_sec2_title="## 2. Chronologie Inaltérable des Événements (`audit_ledger`)",
        prov_table_header=(
            "| Horodatage (UTC) | Type | Acteur | Modèle | Coût USD | Résumé / Action |"
        ),
        prov_sec3_title="## 3. Références Documentaires & CAS SeaweedFS",
        prov_no_cas="*Aucune référence de fragment externe CAS injectée.*",
        prov_footer=(
            "*Rapport scellé produit par ORCIA Audit & FinOps Ledger Engine. "
            "Stockage PostgreSQL 18 append-only protégé par déclencheur d'intégrité.*"
        ),
    ),
    "en": AuditFinopsLocaleBundle(
        circuit_reset_tpl="Connector circuit breaker reset {key} -> {state}",
        budget_override_tpl="Budget override approved (+{amount:.2f} USD): {reason}",
        post_hoc_contract_trigger="Execution under contract",
        rec_strengthen_title="Strengthen upstream expert anchors",
        rec_strengthen_desc_tpl=(
            "The high-criticality workflow '{wf_title}' is approved 100% without "
            "observations. To ensure active oversight, strengthen mandatory upstream "
            "human anchors."
        ),
        rec_strengthen_action="Strengthen expert inputs",
        rec_sampling_title="Risk-based or sampling validation policy",
        rec_sampling_desc_tpl=(
            "The workflow '{wf_title}' shows a unanimous approval rate with short "
            "review durations. Switch verification to sampling (20%) to preserve critical focus."
        ),
        rec_sampling_action="Switch to sampling (20%)",
        rec_applied_wf_fallback="Applied workflow",
        rec_applied_title="Validation policy adjusted",
        rec_applied_desc="Policy adjusted successfully.",
        rec_applied_action="Applied",
        prov_aligned="COMPLIANT (100% ALIGNED)",
        prov_diverged="ALERT: DIVERGENCE DETECTED",
        prov_none_models="None",
        prov_system_actor="System",
        prov_title_tpl="# Immutable Provenance & Audit Dossier — Run `{run_id}`",
        prov_attestation="> **Regulatory Compliance Attestation (AI Act, DORA, NIS 2)**",
        prov_certifies_tpl=(
            "> This dossier certifies the complete, immutable, and verified history "
            "of run `{run_id}`."
        ),
        prov_exported_at_tpl="> Export timestamp: `{exported_at}`",
        prov_sec1_title="## 1. Executive Summary & Cryptographic Digests",
        prov_lbl_align="- **Run Lock alignment status**: `{aligned_label}`",
        prov_lbl_run_lock="- **Run Lock digest (`run-lock.json`)**: `{sha}`",
        prov_lbl_contract="- **Workflow Contract digest**: `{sha}`",
        prov_lbl_events="- **Total audited events**: `{count}`",
        prov_lbl_tokens="- **Total token usage**: `{tokens}`",
        prov_lbl_cost="- **Consolidated total cost**: `${cost:.6f} USD`",
        prov_lbl_models="- **AI models invoked**: `{models}`",
        prov_lbl_actors="- **Participants & Actors**: `{actors}`",
        prov_lbl_period="- **Execution period**: `{period}`",
        prov_sec2_title="## 2. Immutable Event Timeline (`audit_ledger`)",
        prov_table_header=(
            "| Timestamp (UTC) | Type | Actor | Model | Cost USD | Summary / Action |"
        ),
        prov_sec3_title="## 3. Document References & SeaweedFS CAS",
        prov_no_cas="*No external CAS fragment reference injected.*",
        prov_footer=(
            "*Sealed report generated by ORCIA Audit & FinOps Ledger Engine. "
            "Append-only PostgreSQL 18 storage protected by integrity trigger.*"
        ),
    ),
}


def get_audit_finops_locale_bundle(locale: str = DEFAULT_LOCALE) -> AuditFinopsLocaleBundle:
    """Return the localized `AuditFinopsLocaleBundle` (`en` or `fr`, defaulting to `fr`)."""
    norm = (locale or DEFAULT_LOCALE).strip().lower()
    return AUDIT_FINOPS_LOCALES["en"] if norm.startswith("en") else AUDIT_FINOPS_LOCALES["fr"]
