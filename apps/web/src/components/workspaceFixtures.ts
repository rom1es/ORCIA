import type {
  UiCatalogExplorerItemView,
  UiCatalogResourcePermissionView,
  UiPermissionBrokerTicketView,
  UiPersonaKey,
  UiRunLockTripletView,
  UiWorkspaceCardView,
} from "@orcia/ui";

export const WS_PAYMENT: UiWorkspaceCardView = {
  id: "ws-solution-paiement",
  name: "Workspace 1 : Solution Paiement",
  ownerOrgUnitName: "Sous-Équipe Checkout & Core Solutions",
  visibilityMode: "STANDARD",
  effectiveRole: "TEAM_LEAD",
  accessMode: "CONTRIBUTOR_ACTION_REQUIRED",
  accessOrigin: "DIRECT_TEAM",
  finopsCostUsd: 142.5,
  datasources: [
    { id: "ds-1", alias: "git-payment-frontend", scheme: "git", uri: "git://gitlab.entreprise.io/payments/checkout-web", role: "code_frontend" },
    { id: "ds-2", alias: "git-payment-api", scheme: "git", uri: "git://gitlab.entreprise.io/payments/ledger-api", role: "code_backend" },
    { id: "ds-3", alias: "git-payment-infra", scheme: "git", uri: "git://gitlab.entreprise.io/payments/infra-terraform", role: "infra_iac" },
    { id: "ds-4", alias: "jira-pay-build", scheme: "jira", uri: "jira://jira.entreprise.io/projects/PAYBUILD", role: "backlog_build" },
    { id: "ds-5", alias: "jira-pay-run", scheme: "jira", uri: "jira://jira.entreprise.io/projects/PAYSEC", role: "incidents_secops" },
    { id: "ds-6", alias: "confluence-pay-product", scheme: "confluence", uri: "confluence://wiki.entreprise.io/spaces/PAYPROD", role: "kb_product" },
    { id: "ds-7", alias: "confluence-pay-adr", scheme: "confluence", uri: "confluence://wiki.entreprise.io/spaces/PAYADR", role: "kb_architecture" },
  ],
};

export const WS_LOYALTY: UiWorkspaceCardView = {
  id: "ws-solution-fidelite",
  name: "Workspace 2 : Solution Fidélité",
  ownerOrgUnitName: "Sous-Équipe Checkout & Core Solutions",
  visibilityMode: "STANDARD",
  effectiveRole: "TEAM_LEAD",
  accessMode: "CONTRIBUTOR_ACTION_REQUIRED",
  accessOrigin: "DIRECT_TEAM",
  finopsCostUsd: 87.25,
  datasources: [
    { id: "ds-8", alias: "git-loyalty-core", scheme: "git", uri: "git://gitlab.entreprise.io/loyalty/rewards-engine", role: "code_backend" },
    { id: "ds-9", alias: "jira-loyalty-backlog", scheme: "jira", uri: "jira://jira.entreprise.io/projects/LOYALTY", role: "backlog_build" },
    { id: "ds-10", alias: "confluence-loyalty-kb", scheme: "confluence", uri: "confluence://wiki.entreprise.io/spaces/LOYKB", role: "kb_product" },
  ],
};

export const WS_CONFIDENTIAL: UiWorkspaceCardView = {
  id: "ws-projet-confidentiel",
  name: "Workspace 3 : Projet Confidentiel M&A",
  ownerOrgUnitName: "Sous-Équipe Checkout & Core Solutions",
  visibilityMode: "CONFIDENTIAL_RESTRICTED",
  effectiveRole: "TEAM_LEAD",
  accessMode: "CONTRIBUTOR_ACTION_REQUIRED",
  accessOrigin: "DIRECT_TEAM",
  finopsCostUsd: 310.0,
  datasources: [],
};

export const DEFAULT_CATALOG_RESOURCES: UiCatalogResourcePermissionView[] = [
  {
    resourceId: "res-blackbox-security-agent",
    resourceUri: "git://gitlab.entreprise.io/archi/security-audit-agent@v2.1.0",
    title: "Agent d'Audit SecOps Boîte Noire (Équipe Parente)",
    visibilityScope: "SHARED_TEAM",
    grantedPermissions: ["DISCOVER", "EXECUTE"],
    sourceMasked: true,
  },
  {
    resourceId: "res-open-checkout-skill",
    resourceUri: "git://gitlab.entreprise.io/payments/checkout-web/skills/payment-flow@v1.0.0",
    title: "Skill Validation Checkout (Source Ouverte Équipe)",
    visibilityScope: "SHARED_WORKSPACE",
    grantedPermissions: ["DISCOVER", "EXECUTE", "READ_SOURCE", "EDIT", "ADMIN"],
    sourceMasked: false,
  },
];

export const DEFAULT_CATALOG_EXPLORER_ITEMS: UiCatalogExplorerItemView[] = [
  {
    resourceId: "res-blackbox-security-agent",
    uri: "git://gitlab.entreprise.io/archi/security-audit-agent@v2.1.0",
    scheme: "git",
    title: "Agent d'Audit SecOps Boîte Noire (Équipe Parente)",
    description: "Agent SecOps d'audit OWASP & PCI-DSS exécutable sans exposer son prompt.",
    resourceType: "agent",
    sourceFormat: "ORCIA",
    version: "v2.1.0",
    sha256Short: "8a91c4e2f01b",
    casKey: "cas/8a91c4e2f01b",
    visibilityScope: "SHARED_TEAM",
    grantedPermissions: ["DISCOVER", "EXECUTE"],
    sourceMasked: true,
  },
  {
    resourceId: "res-open-checkout-skill",
    uri: "git://gitlab.entreprise.io/payments/checkout-web/skills/payment-flow@v1.0.0",
    scheme: "git",
    title: "Skill Validation Checkout (Source Ouverte Équipe)",
    description: "Skill de validation du tunnel de paiement Checkout avec source inspectable.",
    resourceType: "skill",
    sourceFormat: "ORCIA",
    version: "v1.0.0",
    sha256Short: "4b72d9a1c30e",
    casKey: "cas/4b72d9a1c30e",
    visibilityScope: "SHARED_WORKSPACE",
    grantedPermissions: ["DISCOVER", "EXECUTE", "READ_SOURCE", "EDIT", "ADMIN"],
    sourceMasked: false,
  },
  {
    resourceId: "res-nexus-bmad-architecture-pack",
    uri: "nexus://nexus.entreprise.io/bmad-skills/bmad-architecture-pack-1.4.0.tar.gz",
    scheme: "nexus",
    title: "Pack BMAD Architecture Spine v1.4.0 (Nexus)",
    description: "Archive immuable BMAD (SKILL.md + customize.toml + steps/*.md) publiée.",
    resourceType: "skill",
    sourceFormat: "BMAD_PACK",
    version: "1.4.0",
    sha256Short: "9f30e1c4a82d",
    casKey: "cas/9f30e1c4a82d",
    visibilityScope: "PUBLISHED_ORG",
    grantedPermissions: ["DISCOVER", "EXECUTE", "READ_SOURCE"],
    sourceMasked: false,
  },
  {
    resourceId: "res-payment-delivery-workflow",
    uri: "db://orcia/catalog/payment-delivery-workflow@v1.2.0",
    scheme: "db",
    title: "Workflow Delivery Solution Paiement (Base DB)",
    description: "Workflow déclaratif supportant les surcharges à 4 niveaux et run-lock.json.",
    resourceType: "workflow",
    sourceFormat: "ORCIA",
    version: "v1.2.0",
    sha256Short: "3c18b7e9d04a",
    casKey: "cas/3c18b7e9d04a",
    visibilityScope: "SHARED_BU",
    grantedPermissions: ["DISCOVER", "EXECUTE", "READ_SOURCE", "EDIT", "ADMIN"],
    sourceMasked: false,
  },
  {
    resourceId: "res-confluence-adr-template",
    uri: "confluence://PAYADR/adr-hexagonal-spine@v12",
    scheme: "confluence",
    title: "Gabarit ADR Hexagonal Spine (Confluence @v12)",
    description: "Template de décision d'architecture versionné depuis Confluence.",
    resourceType: "template",
    sourceFormat: "ORCIA",
    version: "v12",
    sha256Short: "7e54a2c1b90f",
    casKey: "cas/7e54a2c1b90f",
    visibilityScope: "PENDING_APPROVAL",
    grantedPermissions: ["DISCOVER", "EXECUTE", "READ_SOURCE", "EDIT", "ADMIN"],
    sourceMasked: false,
  },
  {
    resourceId: "res-jira-secops-playbook",
    uri: "jira://PAYSEC/PAYSEC-101",
    scheme: "jira",
    title: "Playbook SecOps Incident Paiement (Brouillon)",
    description: "Brouillon d'automatisation de remédiation d'incident SecOps.",
    resourceType: "workflow",
    sourceFormat: "ORCIA",
    version: "v0.1.0",
    sha256Short: "1d83f5a0e72c",
    casKey: "cas/1d83f5a0e72c",
    visibilityScope: "DRAFT",
    grantedPermissions: ["DISCOVER", "EXECUTE", "READ_SOURCE", "EDIT", "ADMIN"],
    sourceMasked: false,
  },
];

export const DEFAULT_RUN_LOCK_TRIPLETS: UiRunLockTripletView[] = [
  { alias: "workflow-definition", scheme: "db", uri: "db://orcia/catalog/payment-delivery-workflow@v1.2.0", resolvedVersion: "v1.2.0", sha256Short: "3c18b7e9d04a" },
  { alias: "git-payment-frontend", scheme: "git", uri: "git://gitlab.entreprise.io/payments/checkout-web", resolvedVersion: "latest", sha256Short: "a10f9c28e4b1" },
  { alias: "git-payment-api", scheme: "git", uri: "git://gitlab.entreprise.io/payments/ledger-api", resolvedVersion: "latest", sha256Short: "b21e8d39f5c2" },
  { alias: "jira-pay-build", scheme: "jira", uri: "jira://jira.entreprise.io/projects/PAYBUILD", resolvedVersion: "PAYBUILD", sha256Short: "c32f7e40a6d3" },
  { alias: "confluence-pay-adr", scheme: "confluence", uri: "confluence://wiki.entreprise.io/spaces/PAYADR", resolvedVersion: "latest", sha256Short: "d43a6f51b7e4" },
];

export const PERMISSION_BROKER_TICKET_PRESETS: Record<
  "git" | "confluence" | "jira",
  UiPermissionBrokerTicketView
> = {
  git: {
    id: "0192c4e0-0000-7000-8000-000000001101",
    ticketKey: "tkt-perm-step-02-git-checkout-core",
    stepKey: "step-02-execution",
    stepNumber: 2,
    stepState: "PERMISSION_DENIED_STEP",
    status: "WAITING_FOR_PERMISSION",
    targetUri: "git://github.enterprise/payments/checkout-core.git",
    connectorScheme: "git",
    executionIdentity: "passthrough",
    upstreamHttpStatus: 403,
    requiredRole: "ROLE_GIT_PAYMENTS_MAINTAINER",
    approverTeam: "SecOps & Core Payments IAM",
    slaHours: 4,
    jiraRequestUrl:
      "https://jira.enterprise.internal/secure/CreateIssueDetails!init.jspa?pid=10420&issuetype=10002&summary=%5BORCIA%20Permission%20Broker%5D%20ROLE_GIT_PAYMENTS_MAINTAINER%20sur%20git%3A%2F%2Fgithub.enterprise%2Fpayments%2Fcheckout-core.git",
    permissionBrokerHint:
      "jira://IAM/ROLE_GIT_PAYMENTS_MAINTAINER?target=git%3A%2F%2Fgithub.enterprise%2Fpayments%2Fcheckout-core.git&approver=SecOps%20%26%20Core%20Payments%20IAM&sla_hours=4",
    procedureMarkdown:
      "### Procédure d'habilitation Dépôts Git Paiement\n1. Ouvrir le ticket Jira IAM pré-rempli.\n2. Faire valider `ROLE_GIT_PAYMENTS_MAINTAINER` par `SecOps & Core Payments IAM`.",
  },
  confluence: {
    id: "0192c4e0-0000-7000-8000-000000001102",
    ticketKey: "tkt-perm-step-03-confluence-pci",
    stepKey: "step-03-adr-sync",
    stepNumber: 3,
    stepState: "PERMISSION_DENIED_STEP",
    status: "WAITING_FOR_PERMISSION",
    targetUri: "confluence://PAY/Architecture-PCI@v4",
    connectorScheme: "confluence",
    executionIdentity: "passthrough",
    upstreamHttpStatus: 403,
    requiredRole: "CONFLUENCE_PAY_ADR_READER",
    approverTeam: "Architecture Paiement & Conformité PCI",
    slaHours: 2,
    jiraRequestUrl:
      "https://jira.enterprise.internal/secure/CreateIssueDetails!init.jspa?pid=10421&issuetype=10002&summary=%5BORCIA%20Permission%20Broker%5D%20CONFLUENCE_PAY_ADR_READER%20sur%20confluence%3A%2F%2FPAY%2FArchitecture-PCI%40v4",
    permissionBrokerHint:
      "jira://IAM/CONFLUENCE_PAY_ADR_READER?target=confluence%3A%2F%2FPAY%2FArchitecture-PCI%40v4&approver=Architecture%20Paiement%20%26%20Conformit%C3%A9%20PCI&sla_hours=2",
    procedureMarkdown:
      "### Accès Espace Confluence Architecture PCI\nOctroi du groupe `CONFLUENCE_PAY_ADR_READER` sous 2h ouvrées.",
  },
  jira: {
    id: "0192c4e0-0000-7000-8000-000000001103",
    ticketKey: "tkt-perm-step-04-jira-secops",
    stepKey: "step-04-jira-transition",
    stepNumber: 4,
    stepState: "PERMISSION_DENIED_STEP",
    status: "WAITING_FOR_PERMISSION",
    targetUri: "jira://SECOPS/SEC-108",
    connectorScheme: "jira",
    executionIdentity: "passthrough",
    upstreamHttpStatus: 403,
    requiredRole: "JIRA_SECOPS_TRANSITION_ACTOR",
    approverTeam: "CSIRT & SecOps Governance",
    slaHours: 4,
    jiraRequestUrl:
      "https://jira.enterprise.internal/secure/CreateIssueDetails!init.jspa?pid=10422&issuetype=10002&summary=%5BORCIA%20Permission%20Broker%5D%20JIRA_SECOPS_TRANSITION_ACTOR%20sur%20jira%3A%2F%2FSECOPS%2FSEC-108",
    permissionBrokerHint:
      "jira://IAM/JIRA_SECOPS_TRANSITION_ACTOR?target=jira%3A%2F%2FSECOPS%2FSEC-108&approver=CSIRT%20%26%20SecOps%20Governance&sla_hours=4",
    procedureMarkdown:
      "### Habilitation Transitions Jira SecOps\nRequiert le rôle `JIRA_SECOPS_TRANSITION_ACTOR` validé par CSIRT.",
  },
};

export function computePersonaTopology(persona: UiPersonaKey): {
  workspaces: UiWorkspaceCardView[];
  finopsTotal: number;
} {
  if (persona === "partenaire") {
    return {
      workspaces: [
        {
          ...WS_PAYMENT,
          effectiveRole: "CONTRIBUTOR",
          accessMode: "CONTRIBUTOR_ACTION_REQUIRED",
          accessOrigin: "PARTNER_INVITE",
          finopsCostUsd: null,
        },
      ],
      finopsTotal: 0,
    };
  }
  if (persona === "claire" || persona === "karim") {
    const origin = persona === "karim" ? "GLOBAL_ADMIN" : "ROLLUP_PARENT";
    return {
      workspaces: [
        { ...WS_PAYMENT, effectiveRole: "OBSERVER", accessMode: "READ_ONLY_OBSERVER", accessOrigin: origin },
        { ...WS_LOYALTY, effectiveRole: "OBSERVER", accessMode: "READ_ONLY_OBSERVER", accessOrigin: origin },
      ],
      finopsTotal: 229.75,
    };
  }
  const role = persona === "nadia" ? "CONTRIBUTOR" : "TEAM_LEAD";
  return {
    workspaces: [
      { ...WS_PAYMENT, effectiveRole: role },
      { ...WS_LOYALTY, effectiveRole: role },
      { ...WS_CONFIDENTIAL, effectiveRole: role },
    ],
    finopsTotal: 539.75,
  };
}

export {
  DEFAULT_ONTOLOGY_CONCEPTS,
  DEFAULT_STALE_ALERTS,
  DEFAULT_TRIPARTITE_EDGES,
} from "./ontologyFixtures";
