"""Idempotent Federated Catalog, Workflow Definitions & 4-Layer Override seeds (AD-16)."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


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


_SECOPS_AGENT_PAYLOAD = json.dumps(
    {
        "id": "res-blackbox-security-agent",
        "kind": "agent",
        "version": "v2.1.0",
        "rules": ["OWASP-TOP-10", "PCI-DSS-4.0"],
    },
    sort_keys=True,
)
_SECOPS_SHA = _sha256_text(_SECOPS_AGENT_PAYLOAD)

_CHECKOUT_SKILL_PAYLOAD = json.dumps(
    {
        "id": "res-open-checkout-skill",
        "kind": "skill",
        "version": "v1.0.0",
        "steps": ["validate-cart", "authorize-payment", "emit-ledger-event"],
    },
    sort_keys=True,
)
_CHECKOUT_SHA = _sha256_text(_CHECKOUT_SKILL_PAYLOAD)

_NEXUS_BMAD_PAYLOAD = json.dumps(
    {
        "id": "res-nexus-bmad-architecture-pack",
        "kind": "skill",
        "source_format": "BMAD_PACK",
        "archive": "bmad-architecture-pack-1.4.0.tar.gz",
    },
    sort_keys=True,
)
_NEXUS_SHA = _sha256_text(_NEXUS_BMAD_PAYLOAD)

_CONFLUENCE_ADR_PAYLOAD = json.dumps(
    {
        "id": "res-confluence-adr-template",
        "kind": "template",
        "space": "PAYADR",
        "page": "adr-hexagonal-spine",
        "version": "v12",
    },
    sort_keys=True,
)
_CONFLUENCE_SHA = _sha256_text(_CONFLUENCE_ADR_PAYLOAD)

_JIRA_SEC_PAYLOAD = json.dumps(
    {
        "id": "res-jira-secops-playbook",
        "kind": "workflow",
        "project": "PAYSEC",
        "issue": "PAYSEC-101",
    },
    sort_keys=True,
)
_JIRA_SHA = _sha256_text(_JIRA_SEC_PAYLOAD)

_DB_WORKFLOW_SCHEMA = json.dumps(
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
    },
    sort_keys=True,
)
_DB_WORKFLOW_SHA = _sha256_text(_DB_WORKFLOW_SCHEMA)

DEFAULT_CATALOG_ITEM_SEEDS: tuple[CatalogItemSeed, ...] = (
    CatalogItemSeed(
        id="0192c4e0-0000-7000-8000-000000000701",
        resource_id="res-blackbox-security-agent",
        uri="git://gitlab.entreprise.io/archi/security-audit-agent@v2.1.0",
        title="Agent d'Audit SecOps Boîte Noire (Équipe Parente)",
        description="Agent SecOps d'audit OWASP & PCI-DSS exécutable sans exposer son prompt.",
        resource_type="agent",
        source_format="ORCIA",
        version="v2.1.0",
        sha256=_SECOPS_SHA,
        cas_key=f"cas/{_SECOPS_SHA}",
        visibility_scope="SHARED_TEAM",
        owner_org_unit_id="0192c4e0-0000-7000-8000-000000000103",
        owner_workspace_id=None,
        content_payload=_SECOPS_AGENT_PAYLOAD,
    ),
    CatalogItemSeed(
        id="0192c4e0-0000-7000-8000-000000000702",
        resource_id="res-open-checkout-skill",
        uri="git://gitlab.entreprise.io/payments/checkout-web/skills/payment-flow@v1.0.0",
        title="Skill Validation Checkout (Source Ouverte Équipe)",
        description="Skill de validation du tunnel de paiement Checkout avec source inspectable.",
        resource_type="skill",
        source_format="ORCIA",
        version="v1.0.0",
        sha256=_CHECKOUT_SHA,
        cas_key=f"cas/{_CHECKOUT_SHA}",
        visibility_scope="SHARED_WORKSPACE",
        owner_org_unit_id="0192c4e0-0000-7000-8000-000000000104",
        owner_workspace_id="0192c4e0-0000-7000-8000-000000000201",
        content_payload=_CHECKOUT_SKILL_PAYLOAD,
    ),
    CatalogItemSeed(
        id="0192c4e0-0000-7000-8000-000000000703",
        resource_id="res-nexus-bmad-architecture-pack",
        uri="nexus://nexus.entreprise.io/bmad-skills/bmad-architecture-pack-1.4.0.tar.gz",
        title="Pack BMAD Architecture Spine v1.4.0 (Nexus)",
        description="Archive immuable BMAD (SKILL.md + customize.toml + steps/*.md) publiée.",
        resource_type="skill",
        source_format="BMAD_PACK",
        version="1.4.0",
        sha256=_NEXUS_SHA,
        cas_key=f"cas/{_NEXUS_SHA}",
        visibility_scope="PUBLISHED_ORG",
        owner_org_unit_id="0192c4e0-0000-7000-8000-000000000101",
        owner_workspace_id=None,
        content_payload=_NEXUS_BMAD_PAYLOAD,
    ),
    CatalogItemSeed(
        id="0192c4e0-0000-7000-8000-000000000704",
        resource_id="res-payment-delivery-workflow",
        uri="db://orcia/catalog/payment-delivery-workflow@v1.2.0",
        title="Workflow Delivery Solution Paiement (Base DB)",
        description="Workflow déclaratif supportant les surcharges à 4 niveaux et run-lock.json.",
        resource_type="workflow",
        source_format="ORCIA",
        version="v1.2.0",
        sha256=_DB_WORKFLOW_SHA,
        cas_key=f"cas/{_DB_WORKFLOW_SHA}",
        visibility_scope="SHARED_BU",
        owner_org_unit_id="0192c4e0-0000-7000-8000-000000000102",
        owner_workspace_id="0192c4e0-0000-7000-8000-000000000201",
        content_payload=_DB_WORKFLOW_SCHEMA,
    ),
    CatalogItemSeed(
        id="0192c4e0-0000-7000-8000-000000000705",
        resource_id="res-confluence-adr-template",
        uri="confluence://PAYADR/adr-hexagonal-spine@v12",
        title="Gabarit ADR Hexagonal Spine (Confluence @v12)",
        description="Template de décision d'architecture versionné depuis Confluence.",
        resource_type="template",
        source_format="ORCIA",
        version="v12",
        sha256=_CONFLUENCE_SHA,
        cas_key=f"cas/{_CONFLUENCE_SHA}",
        visibility_scope="PENDING_APPROVAL",
        owner_org_unit_id="0192c4e0-0000-7000-8000-000000000103",
        owner_workspace_id="0192c4e0-0000-7000-8000-000000000201",
        content_payload=_CONFLUENCE_ADR_PAYLOAD,
    ),
    CatalogItemSeed(
        id="0192c4e0-0000-7000-8000-000000000706",
        resource_id="res-jira-secops-playbook",
        uri="jira://PAYSEC/PAYSEC-101",
        title="Playbook SecOps Incident Paiement (Brouillon)",
        description="Brouillon d'automatisation de remédiation d'incident SecOps.",
        resource_type="workflow",
        source_format="ORCIA",
        version="v0.1.0",
        sha256=_JIRA_SHA,
        cas_key=f"cas/{_JIRA_SHA}",
        visibility_scope="DRAFT",
        owner_org_unit_id="0192c4e0-0000-7000-8000-000000000104",
        owner_workspace_id="0192c4e0-0000-7000-8000-000000000201",
        content_payload=_JIRA_SEC_PAYLOAD,
    ),
)

DEFAULT_WORKFLOW_DEFINITION_SEEDS: tuple[WorkflowDefinitionSeed, ...] = (
    WorkflowDefinitionSeed(
        id="0192c4e0-0000-7000-8000-000000000801",
        workspace_id="0192c4e0-0000-7000-8000-000000000201",
        uri="db://orcia/catalog/payment-delivery-workflow@v1.2.0",
        version="v1.2.0",
        source_format="ORCIA",
        steps_schema_json=_DB_WORKFLOW_SCHEMA,
        adaptive_gate_policy="STRICT",
        sha256=_DB_WORKFLOW_SHA,
    ),
)

_OVERRIDE_PARENT_TEAM = json.dumps(
    {
        "scalars": {"timeout_seconds": 900, "compliance_regime": "PCI-DSS-L1"},
        "rules": ["RULE-TEAM-PARENT-SECOPS-AUDIT"],
        "facts": ["FACT-TEAM-PARENT-ARCHITECTURE-BOARD"],
        "lenses": [{"code": "security", "weight": 0.5, "threshold": 0.85}],
    },
    sort_keys=True,
)
_OVERRIDE_SUBTEAM = json.dumps(
    {
        "scalars": {"squad_channel": "#checkout-core"},
        "rules": ["RULE-SUBTEAM-CHECKOUT-IDEMPOTENCY"],
        "facts": ["FACT-SUBTEAM-STRIPE-ADYEN-ROUTING"],
        "lenses": [{"code": "finops", "weight": 0.2, "threshold": 0.8}],
    },
    sort_keys=True,
)
_OVERRIDE_WORKSPACE = json.dumps(
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
    },
    sort_keys=True,
)
_OVERRIDE_USER = json.dumps(
    {
        "scalars": {"human_greeting": "Bonjour Marc (Tech Lead Checkout)", "verbosity": "concise"},
        "rules": ["RULE-USER-FRENCH-TYPOGRAPHY"],
        "facts": [],
        "lenses": [],
    },
    sort_keys=True,
)

DEFAULT_CUSTOMIZATION_OVERRIDE_SEEDS: tuple[CustomizationOverrideSeed, ...] = (
    CustomizationOverrideSeed(
        id="0192c4e0-0000-7000-8000-000000000901",
        override_key="ovr-team-parent-archi-payment-wf",
        org_unit_id="0192c4e0-0000-7000-8000-000000000103",
        workspace_id=None,
        user_id=None,
        target_uri="db://orcia/catalog/payment-delivery-workflow@v1.2.0",
        override_layer="TEAM",
        override_manifest_json=_OVERRIDE_PARENT_TEAM,
        sha256=_sha256_text(_OVERRIDE_PARENT_TEAM),
    ),
    CustomizationOverrideSeed(
        id="0192c4e0-0000-7000-8000-000000000902",
        override_key="ovr-subteam-checkout-payment-wf",
        org_unit_id="0192c4e0-0000-7000-8000-000000000104",
        workspace_id=None,
        user_id=None,
        target_uri="db://orcia/catalog/payment-delivery-workflow@v1.2.0",
        override_layer="TEAM",
        override_manifest_json=_OVERRIDE_SUBTEAM,
        sha256=_sha256_text(_OVERRIDE_SUBTEAM),
    ),
    CustomizationOverrideSeed(
        id="0192c4e0-0000-7000-8000-000000000903",
        override_key="ovr-workspace-payment-wf",
        org_unit_id=None,
        workspace_id="0192c4e0-0000-7000-8000-000000000201",
        user_id=None,
        target_uri="db://orcia/catalog/payment-delivery-workflow@v1.2.0",
        override_layer="WORKSPACE",
        override_manifest_json=_OVERRIDE_WORKSPACE,
        sha256=_sha256_text(_OVERRIDE_WORKSPACE),
    ),
    CustomizationOverrideSeed(
        id="0192c4e0-0000-7000-8000-000000000904",
        override_key="ovr-user-marc-payment-wf",
        org_unit_id=None,
        workspace_id=None,
        user_id="0192c4e0-0000-7000-8000-000000000603",
        target_uri="db://orcia/catalog/payment-delivery-workflow@v1.2.0",
        override_layer="USER",
        override_manifest_json=_OVERRIDE_USER,
        sha256=_sha256_text(_OVERRIDE_USER),
    ),
)
