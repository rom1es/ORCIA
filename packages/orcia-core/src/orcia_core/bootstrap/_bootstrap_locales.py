"""Bilingual locale bundles for bootstrap accostage, wizards, emails, and seeds (`Story 27.7`)."""

from __future__ import annotations

from dataclasses import dataclass

from orcia_kernel.enums import DEFAULT_LOCALE, SupportedLocale

SINGLE_FAMILY_AMBER_WARNING_LOCALES: dict[SupportedLocale, str] = {
    "fr": (
        "⚠️ 1 seule famille de modèles configurée — Ajoutez une 2e famille dans "
        "Administration › Modèles IA pour activer les contrôles croisés de qualité"
    ),
    "en": (
        "⚠️ Only 1 model family configured — Add a 2nd family in "
        "Administration › AI Models to enable cross-model quality gates"
    ),
}

ACCOSTAGE_MILESTONE_TITLES: dict[SupportedLocale, dict[str, str]] = {
    "fr": {
        "first-admin": "1. Compte Admin",
        "first-llm-model": "2. Modèles IA",
        "first-org-unit": "3. Organisation",
        "first-space": "4. Premier Espace d'équipe",
        "first-datasource": "5. Première Source",
        "pilot-workflow-run": "6. Premier Processus",
    },
    "en": {
        "first-admin": "1. Admin Account",
        "first-llm-model": "2. AI Models",
        "first-org-unit": "3. Organization",
        "first-space": "4. First Team Space",
        "first-datasource": "5. First Source",
        "pilot-workflow-run": "6. First Process",
    },
}

WIZARD_STEP_TITLES_LOCALES: dict[SupportedLocale, dict[str, tuple[str, ...]]] = {
    "fr": {
        "sdlc_tech_lead": (
            "Identité du Workspace",
            "Sources Code & Tickets",
            "Tiers Cognitifs IA",
            "Pack SDLC & Gates",
            "Vérification RAG Finale",
        ),
        "ops_manager": (
            "Périmètre Équipe & BU",
            "Sources Documentaires",
            "Plafonds FinOps",
            "Politiques de Revue",
            "Vérification RAG Finale",
        ),
        "secops_admin": (
            "Authentification Bi-Mode",
            "Matrice RBAC 6 Verbes",
            "Coffre-fort & SecretRef",
            "Garde-fous C0-C3 & PII",
            "Audit & Réciprocité Finale",
        ),
    },
    "en": {
        "sdlc_tech_lead": (
            "Workspace Identity",
            "Code & Issue Sources",
            "AI Cognitive Tiers",
            "SDLC Pack & Gates",
            "Final RAG Reciprocity",
        ),
        "ops_manager": (
            "Team & BU Scope",
            "Knowledge Sources",
            "FinOps Budgets",
            "Review Policies",
            "Final RAG Reciprocity",
        ),
        "secops_admin": (
            "Bi-Mode Authentication",
            "6-Verb RBAC Matrix",
            "Secret Vault & KMS",
            "C0-C3 & PII Guards",
            "Final Audit & RAG",
        ),
    },
}

DEMO_WORKSPACE_NAME_LOCALES: dict[SupportedLocale, str] = {
    "fr": "Espace de Démonstration Pré-rempli (Zero Empty-State)",
    "en": "Pre-filled Demo Space (Zero Empty-State)",
}

HUMAN_PROFILE_ARCHETYPE_LABELS: dict[SupportedLocale, dict[str, str]] = {
    "fr": {
        "PM_BUSINESS": "PM / Métier",
        "ARCHITECT": "Architecte",
        "TECH_LEAD": "Tech Lead",
        "DEVELOPER": "Développeur",
        "SECOPS": "SecOps / IAM",
        "EXECUTIVE": "Direction",
    },
    "en": {
        "PM_BUSINESS": "Product Manager / Business",
        "ARCHITECT": "System Architect",
        "TECH_LEAD": "Tech Lead",
        "DEVELOPER": "Software Engineer",
        "SECOPS": "SecOps / IAM",
        "EXECUTIVE": "Executive Leadership",
    },
}

ORG_ROLE_UNIT_LABELS: dict[SupportedLocale, dict[str, str]] = {
    "fr": {"BU": "Direction/Pôle (BU)", "TEAM": "Équipe (TEAM)"},
    "en": {"BU": "Business Unit (BU)", "TEAM": "Team (TEAM)"},
}

OTP_EMAIL_LOCALES: dict[SupportedLocale, tuple[str, str]] = {
    "fr": (
        "[ORCIA] Votre code de vérification à 6 chiffres : {otp_code}",
        "Bonjour,\n\nVotre code de vérification ORCIA est : {otp_code}\n\n"
        "Ce code est valable pendant {ttl_minutes} minutes. "
        "Si vous n'êtes pas à l'origine de cette connexion, ignorez ce message.\n",
    ),
    "en": (
        "[ORCIA] Your 6-digit verification code: {otp_code}",
        "Hello,\n\nYour ORCIA verification code is: {otp_code}\n\n"
        "This code expires in {ttl_minutes} minutes. "
        "If you did not initiate this login, ignore this message.\n",
    ),
}


@dataclass(frozen=True, slots=True)
class RagSeedCopy:
    """Localized RAG fixture texts."""

    confluence_title: str
    confluence_path: str
    section_1: str
    section_2: str
    jira_title: str
    jira_body: str
    traceability_text: str


BOOTSTRAP_RAG_SEED_LOCALES: dict[SupportedLocale, RagSeedCopy] = {
    "fr": RagSeedCopy(
        confluence_title="Spécification Seuil Validation Sinistre",
        confluence_path="Espace CLAIMS > Règles Métier",
        section_1="Section 1 — Tout sinistre supérieur au seuil PAY-101 requiert validation.",
        section_2="Section 2 — La règle s'applique au concept LossEvent et à calculate_reserve.",
        jira_title="Relèvement du seuil de validation LossEvent de 5000 EUR à 7500 EUR",
        jira_body=(
            "Suite au comité risques, le ticket PAY-142 relève le seuil de "
            "calculate_reserve pour LossEvent à 7500 EUR (remplace PAY-101)."
        ),
        traceability_text="Spécification initiale liée à PAY-101 et mise à jour par PAY-142.",
    ),
    "en": RagSeedCopy(
        confluence_title="Claim Validation Threshold Specification",
        confluence_path="Space CLAIMS > Business Rules",
        section_1="Section 1 — Every claim exceeding the PAY-101 threshold requires validation.",
        section_2="Section 2 — The rule applies to the LossEvent concept and calculate_reserve.",
        jira_title="Raise LossEvent validation threshold from 5000 EUR to 7500 EUR",
        jira_body=(
            "Following the risk committee review, ticket PAY-142 raises the "
            "calculate_reserve threshold for LossEvent to 7500 EUR (supersedes PAY-101)."
        ),
        traceability_text="Initial specification linked to PAY-101 and updated by PAY-142.",
    ),
}

WORKFLOW_BOOTSTRAP_SEED_LOCALES: dict[SupportedLocale, dict[str, tuple[str, str]]] = {
    "fr": {
        "init-organization": (
            "Amorçage Jour 0 de l'Organisation (init-organization)",
            "Configure OIDC/Local Argon2id, RBAC, >= 2 familles LLM orthogonales et le catalogue.",
        ),
        "init-workspace": (
            "Onboarding Autonome d'Équipe & Multi-Workspaces (init-workspace)",
            "Crée en self-service l'équipe/sous-équipes, 1..N Workspaces solutions et invitations.",
        ),
        "init-datasource": (
            "Rattachement Gouverné Multi-Sources (init-datasource)",
            "Rattache N x git://, confluence:// (CQL), jira:// (JQL), db:// avec Ancre Humaine.",
        ),
        "init-existing-project": (
            "Absorption Brownfield de Projet Existant (init-existing-project)",
            "Analyse un projet existant et génère sa proposition d'ontologie "
            "et de sources fédérées.",
        ),
        "init-skill": (
            "Initialisation Gouvernée de Skill / Agent (init-skill)",
            "Crée un nouveau Skill ou Agent dans le Catalogue Fédéré avec ses 5 permissions.",
        ),
        "init-user": (
            "Onboarding Première Connexion & Liaison Passthrough (init-user)",
            "Confirme le Profil Humain et lie Jira, Confluence et Git en passthrough AES-256-GCM.",
        ),
    },
    "en": {
        "init-organization": (
            "Day-0 Organization Bootstrap (init-organization)",
            "Configures OIDC/Local Argon2id, RBAC, >= 2 orthogonal LLM families, and catalog.",
        ),
        "init-workspace": (
            "Self-Service Team & Multi-Workspace Onboarding (init-workspace)",
            "Self-service provisioning of teams/sub-teams, 1..N solution workspaces, and invites.",
        ),
        "init-datasource": (
            "Governed Multi-Source Binding (init-datasource)",
            "Binds N x git://, confluence:// (CQL), jira:// (JQL), db:// with Human Anchor.",
        ),
        "init-existing-project": (
            "Brownfield Existing Project Absorption (init-existing-project)",
            "Analyzes an existing repository and generates ontology "
            "and federated source proposals.",
        ),
        "init-skill": (
            "Governed Skill / Agent Initialization (init-skill)",
            "Registers a new Skill or Agent in the Federated Catalog with its 5 permissions.",
        ),
        "init-user": (
            "First-Login Onboarding & Passthrough Binding (init-user)",
            "Confirms the Human Profile and links Jira, Confluence, and Git via AES-256-GCM.",
        ),
    },
}


def get_otp_email_copy(locale: str, *, otp_code: str, ttl_minutes: int) -> tuple[str, str]:
    """Return localized `(subject, body)` pair for 6-digit login verification email."""
    loc: SupportedLocale = "en" if locale.lower().startswith("en") else "fr"
    subj_tpl, body_tpl = OTP_EMAIL_LOCALES[loc]
    return subj_tpl.format(otp_code=otp_code), body_tpl.format(
        otp_code=otp_code, ttl_minutes=ttl_minutes
    )


def get_bootstrap_rag_seed_copy(locale: SupportedLocale = DEFAULT_LOCALE) -> RagSeedCopy:
    """Return localized RAG seed strings for the requested locale."""
    return BOOTSTRAP_RAG_SEED_LOCALES.get(locale, BOOTSTRAP_RAG_SEED_LOCALES[DEFAULT_LOCALE])


__all__ = [
    "ACCOSTAGE_MILESTONE_TITLES",
    "BOOTSTRAP_RAG_SEED_LOCALES",
    "DEMO_WORKSPACE_NAME_LOCALES",
    "HUMAN_PROFILE_ARCHETYPE_LABELS",
    "ORG_ROLE_UNIT_LABELS",
    "OTP_EMAIL_LOCALES",
    "RagSeedCopy",
    "SINGLE_FAMILY_AMBER_WARNING_LOCALES",
    "WIZARD_STEP_TITLES_LOCALES",
    "WORKFLOW_BOOTSTRAP_SEED_LOCALES",
    "get_bootstrap_rag_seed_copy",
    "get_otp_email_copy",
]
