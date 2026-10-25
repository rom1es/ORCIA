"use client";

import {
  HumanLedAnchorCard,
  StatusBadge,
  type UiCatalogResourcePermissionView,
  type UiModuleKey,
  type UiPersonaKey,
  type UiWorkspaceCardView,
  WorkspaceTopologyPanel,
} from "@orcia/ui";
import React, { useState } from "react";
import { useI18n } from "../i18n";
import { usePersonaContext } from "./ShellContainer";

const WS_PAYMENT: UiWorkspaceCardView = {
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

const WS_LOYALTY: UiWorkspaceCardView = {
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

const WS_CONFIDENTIAL: UiWorkspaceCardView = {
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

const DEFAULT_CATALOG_RESOURCES: UiCatalogResourcePermissionView[] = [
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

function computePersonaTopology(persona: UiPersonaKey): {
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
    // Upward Roll-up: sees STANDARD workspaces (WS 1 & WS 2) in READ_ONLY_OBSERVER, excludes CONFIDENTIAL_RESTRICTED (WS 3)
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

export function ModuleWorkspaceView({ moduleKey }: { moduleKey: UiModuleKey }) {
  const { dictionary } = useI18n();
  const { activePersona, setActivePersona } = usePersonaContext();
  const pageCopy = dictionary.modulePages[moduleKey];
  const [customAnchorText, setCustomAnchorText] = useState<string | null>(null);
  const anchorText = customAnchorText ?? dictionary.humanAnchor.defaultValue;
  const { workspaces, finopsTotal } = computePersonaTopology(activePersona);

  return (
    <div
      data-testid={`module-view-${moduleKey}`}
      style={{
        display: "flex",
        flexDirection: "column",
        gap: "16px",
      }}
    >
      <div
        style={{
          backgroundColor: "var(--color-surface-card)",
          border: "1px solid var(--color-border)",
          borderRadius: "var(--radius-md)",
          padding: "16px",
          display: "flex",
          flexDirection: "column",
          gap: "8px",
        }}
      >
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            gap: "8px",
            flexWrap: "wrap",
          }}
        >
          <strong>{pageCopy.subtitle}</strong>
          <StatusBadge
            testId={`module-uri-badge-${moduleKey}`}
            label={pageCopy.uriBadgeExample}
            tone="cobalt"
            monospace
          />
        </div>
        <p style={{ margin: 0, color: "var(--color-muted-foreground)" }}>{pageCopy.description}</p>
      </div>

      {moduleKey === "cockpit" && (
        <HumanLedAnchorCard
          sectionKey="architecture-intent"
          sectionTitle={dictionary.humanAnchor.defaultSectionTitle}
          authorName={dictionary.humanAnchor.defaultAuthorName}
          value={anchorText}
          labels={dictionary.humanAnchor}
          onChange={setCustomAnchorText}
        />
      )}

      <WorkspaceTopologyPanel
        activePersona={activePersona}
        workspaces={workspaces}
        consolidatedFinopsUsd={finopsTotal}
        catalogResources={DEFAULT_CATALOG_RESOURCES}
        labels={dictionary.workspaceTopology}
        onSelectPersona={setActivePersona}
      />
    </div>
  );
}
