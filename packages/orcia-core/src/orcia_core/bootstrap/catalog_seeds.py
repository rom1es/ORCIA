"""Idempotent Federated Catalog, Workflow Definitions & 4-Layer Override seeds (AD-16)."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _j(payload: dict[str, object]) -> str:
    return json.dumps(payload, sort_keys=True)


@dataclass(frozen=True, slots=True)
class CatalogItemSeed:
    """Reference catalog item seed across federated schemes (`git`, `nexus`, `db`, etc.)."""

    id: str
    resource_id: str
    uri: str
    title: str
    description: str
    resource_type: str
    source_format: str
    version: str
    sha256: str
    cas_key: str
    visibility_scope: str
    owner_org_unit_id: str
    owner_workspace_id: str | None = None
    content_payload: str = ""


@dataclass(frozen=True, slots=True)
class WorkflowDefinitionSeed:
    """Reference workflow definition seed (`ORCIA` native or `BMAD_PACK`)."""

    id: str
    workspace_id: str | None
    uri: str
    version: str
    source_format: str
    steps_schema_json: str
    adaptive_gate_policy: str
    sha256: str


@dataclass(frozen=True, slots=True)
class CustomizationOverrideSeed:
    """Reference 4-layer declarative override seed (`TEAM`, `WORKSPACE`, `USER`)."""

    id: str
    override_key: str
    org_unit_id: str | None
    workspace_id: str | None
    user_id: str | None
    target_uri: str
    override_layer: str
    override_manifest_json: str
    sha256: str


_SECOPS_AGENT_PAYLOAD = _j(
    {
        "id": "res-blackbox-security-agent",
        "kind": "agent",
        "version": "v2.1.0",
        "rules": ["OWASP-TOP-10", "PCI-DSS-4.0"],
    }
)
_SECOPS_SHA = _sha256_text(_SECOPS_AGENT_PAYLOAD)

_CHECKOUT_SKILL_PAYLOAD = _j(
    {
        "id": "res-open-checkout-skill",
        "kind": "skill",
        "version": "v1.0.0",
        "steps": ["validate-cart", "authorize-payment", "emit-ledger-event"],
    }
)
_CHECKOUT_SHA = _sha256_text(_CHECKOUT_SKILL_PAYLOAD)

_NEXUS_BMAD_PAYLOAD = _j(
    {
        "id": "res-nexus-bmad-architecture-pack",
        "kind": "skill",
        "source_format": "BMAD_PACK",
        "archive": "bmad-architecture-pack-1.4.0.tar.gz",
    }
)
_NEXUS_SHA = _sha256_text(_NEXUS_BMAD_PAYLOAD)

_CONFLUENCE_ADR_PAYLOAD = _j(
    {
        "id": "res-confluence-adr-template",
        "kind": "template",
        "space": "PAYADR",
        "page": "adr-hexagonal-spine",
        "version": "v12",
    }
)
_CONFLUENCE_SHA = _sha256_text(_CONFLUENCE_ADR_PAYLOAD)

_JIRA_SEC_PAYLOAD = _j(
    {
        "id": "res-jira-secops-playbook",
        "kind": "workflow",
        "project": "PAYSEC",
        "issue": "PAYSEC-101",
    }
)
_JIRA_SHA = _sha256_text(_JIRA_SEC_PAYLOAD)

_DB_WORKFLOW_SCHEMA = _j(
    {
        "title": "Workflow Delivery Solution Paiement",
        "description": "Pipeline gouverné de livraison multi-sources Paiement",
        "scalars": {
            "default_model": "claude-sonnet-4",
            "evaluator_model": "gpt-4.1",
            "timeout_seconds": 600,
            "human_greeting": "Bonjour Architecte",
        },
        "datasources": ["db://orcia/catalog/payment-delivery-workflow@v1.2.0"],
        "rules": ["RULE-BASE-HEXAGONAL", "RULE-BASE-ZERO-DIFF"],
        "facts": ["FACT-ORG-ORCIA-GROUP"],
        "lenses": [
            {"code": "security", "weight": 0.4, "threshold": 0.8},
            {"code": "architecture", "weight": 0.6, "threshold": 0.75},
        ],
        "steps": [
            {
                "step_key": "step-01-intent",
                "title": "Ancrage d'intention humaine",
                "instructions": "Rédiger et signer les hypothèses structurantes.",
                "human_authored_required": True,
            },
            {
                "step_key": "step-02-execution",
                "title": "Génération et vérification multi-sources",
                "instructions": "Exécuter les contrôles sur les dépôts git et projets Jira.",
                "human_authored_required": False,
            },
        ],
    }
)
_DB_WORKFLOW_SHA = _sha256_text(_DB_WORKFLOW_SCHEMA)

DEFAULT_CATALOG_ITEM_SEEDS: tuple[CatalogItemSeed, ...] = (
    CatalogItemSeed(
        "0192c4e0-0000-7000-8000-000000000701", "res-blackbox-security-agent",
        "git://gitlab.entreprise.io/archi/security-audit-agent@v2.1.0",
        "Agent d'Audit SecOps Boîte Noire (Équipe Parente)",
        "Agent SecOps d'audit OWASP & PCI-DSS exécutable sans exposer son prompt.",
        "agent", "ORCIA", "v2.1.0", _SECOPS_SHA, f"cas/{_SECOPS_SHA}", "SHARED_TEAM",
        "0192c4e0-0000-7000-8000-000000000103", None, _SECOPS_AGENT_PAYLOAD,
    ),
    CatalogItemSeed(
        "0192c4e0-0000-7000-8000-000000000702", "res-open-checkout-skill",
        "git://gitlab.entreprise.io/payments/checkout-web/skills/payment-flow@v1.0.0",
        "Skill Validation Checkout (Source Ouverte Équipe)",
        "Skill de validation du tunnel de paiement Checkout avec source inspectable.",
        "skill", "ORCIA", "v1.0.0", _CHECKOUT_SHA, f"cas/{_CHECKOUT_SHA}", "SHARED_WORKSPACE",
        "0192c4e0-0000-7000-8000-000000000104", "0192c4e0-0000-7000-8000-000000000201",
        _CHECKOUT_SKILL_PAYLOAD,
    ),
    CatalogItemSeed(
        "0192c4e0-0000-7000-8000-000000000703", "res-nexus-bmad-architecture-pack",
        "nexus://nexus.entreprise.io/bmad-skills/bmad-architecture-pack-1.4.0.tar.gz",
        "Pack BMAD Architecture Spine v1.4.0 (Nexus)",
        "Archive immuable BMAD (SKILL.md + customize.toml + steps/*.md) publiée.",
        "skill", "BMAD_PACK", "1.4.0", _NEXUS_SHA, f"cas/{_NEXUS_SHA}", "PUBLISHED_ORG",
        "0192c4e0-0000-7000-8000-000000000101", None, _NEXUS_BMAD_PAYLOAD,
    ),
    CatalogItemSeed(
        "0192c4e0-0000-7000-8000-000000000704", "res-payment-delivery-workflow",
        "db://orcia/catalog/payment-delivery-workflow@v1.2.0",
        "Workflow Delivery Solution Paiement (Base DB)",
        "Workflow déclaratif supportant les surcharges à 4 niveaux et run-lock.json.",
        "workflow", "ORCIA", "v1.2.0", _DB_WORKFLOW_SHA, f"cas/{_DB_WORKFLOW_SHA}", "SHARED_BU",
        "0192c4e0-0000-7000-8000-000000000102", "0192c4e0-0000-7000-8000-000000000201",
        _DB_WORKFLOW_SCHEMA,
    ),
    CatalogItemSeed(
        "0192c4e0-0000-7000-8000-000000000705", "res-confluence-adr-template",
        "confluence://PAYADR/adr-hexagonal-spine@v12",
        "Gabarit ADR Hexagonal Spine (Confluence @v12)",
        "Template de décision d'architecture versionné depuis Confluence.",
        "template", "ORCIA", "v12", _CONFLUENCE_SHA, f"cas/{_CONFLUENCE_SHA}", "PENDING_APPROVAL",
        "0192c4e0-0000-7000-8000-000000000103", "0192c4e0-0000-7000-8000-000000000201",
        _CONFLUENCE_ADR_PAYLOAD,
    ),
    CatalogItemSeed(
        "0192c4e0-0000-7000-8000-000000000706", "res-jira-secops-playbook",
        "jira://PAYSEC/PAYSEC-101", "Playbook SecOps Incident Paiement (Brouillon)",
        "Brouillon d'automatisation de remédiation d'incident SecOps.",
        "workflow", "ORCIA", "v0.1.0", _JIRA_SHA, f"cas/{_JIRA_SHA}", "DRAFT",
        "0192c4e0-0000-7000-8000-000000000104", "0192c4e0-0000-7000-8000-000000000201",
        _JIRA_SEC_PAYLOAD,
    ),
)  # fmt: skip

DEFAULT_WORKFLOW_DEFINITION_SEEDS: tuple[WorkflowDefinitionSeed, ...] = (
    WorkflowDefinitionSeed(
        "0192c4e0-0000-7000-8000-000000000801", "0192c4e0-0000-7000-8000-000000000201",
        "db://orcia/catalog/payment-delivery-workflow@v1.2.0", "v1.2.0", "ORCIA",
        _DB_WORKFLOW_SCHEMA, "STRICT", _DB_WORKFLOW_SHA,
    ),
)  # fmt: skip

_OVERRIDE_PARENT_TEAM = _j(
    {
        "scalars": {"timeout_seconds": 900, "compliance_regime": "PCI-DSS-L1"},
        "rules": ["RULE-TEAM-PARENT-SECOPS-AUDIT"],
        "facts": ["FACT-TEAM-PARENT-ARCHITECTURE-BOARD"],
        "lenses": [{"code": "security", "weight": 0.5, "threshold": 0.85}],
    }
)
_OVERRIDE_SUBTEAM = _j(
    {
        "scalars": {"squad_channel": "#checkout-core"},
        "rules": ["RULE-SUBTEAM-CHECKOUT-IDEMPOTENCY"],
        "facts": ["FACT-SUBTEAM-STRIPE-ADYEN-ROUTING"],
        "lenses": [{"code": "finops", "weight": 0.2, "threshold": 0.8}],
    }
)
_OVERRIDE_WORKSPACE = _j(
    {
        "scalars": {"solution_slug": "ws-solution-paiement"},
        "datasources": [
            "git://gitlab.entreprise.io/payments/checkout-web",
            "git://gitlab.entreprise.io/payments/ledger-api",
            "git://gitlab.entreprise.io/payments/infra-terraform",
            "jira://jira.entreprise.io/projects/PAYBUILD",
            "jira://jira.entreprise.io/projects/PAYSEC",
            "confluence://wiki.entreprise.io/spaces/PAYPROD",
            "confluence://wiki.entreprise.io/spaces/PAYADR",
        ],
        "rules": ["RULE-WS-PAYMENT-MULTI-REPO-SYNC"],
        "facts": ["FACT-WS-PAYMENT-3GIT-2JIRA-2CONFLUENCE"],
        "lenses": [{"code": "architecture", "weight": 0.65, "threshold": 0.82}],
    }
)
_OVERRIDE_USER = _j(
    {
        "scalars": {"human_greeting": "Bonjour Marc (Tech Lead Checkout)", "verbosity": "concise"},
        "rules": ["RULE-USER-FRENCH-TYPOGRAPHY"],
        "facts": [],
        "lenses": [],
    }
)

DEFAULT_CUSTOMIZATION_OVERRIDE_SEEDS: tuple[CustomizationOverrideSeed, ...] = (
    CustomizationOverrideSeed(
        "0192c4e0-0000-7000-8000-000000000901", "ovr-team-parent-archi-payment-wf",
        "0192c4e0-0000-7000-8000-000000000103", None, None,
        "db://orcia/catalog/payment-delivery-workflow@v1.2.0", "TEAM",
        _OVERRIDE_PARENT_TEAM, _sha256_text(_OVERRIDE_PARENT_TEAM),
    ),
    CustomizationOverrideSeed(
        "0192c4e0-0000-7000-8000-000000000902", "ovr-subteam-checkout-payment-wf",
        "0192c4e0-0000-7000-8000-000000000104", None, None,
        "db://orcia/catalog/payment-delivery-workflow@v1.2.0", "TEAM",
        _OVERRIDE_SUBTEAM, _sha256_text(_OVERRIDE_SUBTEAM),
    ),
    CustomizationOverrideSeed(
        "0192c4e0-0000-7000-8000-000000000903", "ovr-workspace-payment-wf",
        None, "0192c4e0-0000-7000-8000-000000000201", None,
        "db://orcia/catalog/payment-delivery-workflow@v1.2.0", "WORKSPACE",
        _OVERRIDE_WORKSPACE, _sha256_text(_OVERRIDE_WORKSPACE),
    ),
    CustomizationOverrideSeed(
        "0192c4e0-0000-7000-8000-000000000904", "ovr-user-marc-payment-wf",
        None, None, "0192c4e0-0000-7000-8000-000000000603",
        "db://orcia/catalog/payment-delivery-workflow@v1.2.0", "USER",
        _OVERRIDE_USER, _sha256_text(_OVERRIDE_USER),
    ),
)  # fmt: skip
