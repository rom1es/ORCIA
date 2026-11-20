import { fireEvent, render, screen } from "@testing-library/react";
import React, { useState } from "react";
import { describe, expect, it, vi } from "vitest";
import {
  WorkflowTriggersModal,
  type WorkflowTriggersModalLabels,
} from "../primitives/WorkflowTriggersModal";
import {
  WorkspaceFiveTabsAndExternalRebaseView,
  type WorkspaceFiveTabsLabels,
  type WorkspaceSubTabKey,
} from "../primitives/WorkspaceFiveTabsAndExternalRebaseView";

const FIVE_TABS_LABELS_FR: WorkspaceFiveTabsLabels = {
  heading: "Gouvernance & Livrables de l'Espace",
  tabOverview: "1. Vue d'ensemble",
  tabDocumentsSources: "2. Documents & Sources",
  tabDeliverablesArtifacts: "3. Livrables & Artefacts produits",
  tabGlossaryRules: "4. Glossaire & Règles métiers",
  tabMembersTeam: "5. Membres & Équipe",
  defaultDestinationTitle: "Destination par défaut",
  roleReferenceBadge: "Référence métier",
  roleActiveBadge: "Périmètre actif",
  modeReadOnlyBadge: "Lecture seule",
  modeReadWriteBadge: "Lecture + Écriture",
  waiverSectionTitle: "Dérogations d'exception",
  inviolableEnterpriseLockNotice: "Directives 1_ENTERPRISE verrouillées.",
  externalRebaseTitle: "Rebase externe",
  humanAmendedBadge: "HUMAN_AMENDED_EXTERNAL",
  supersededMemlogNotice: "[SUPERSEDED_BY_HUMAN_COMMIT]",
  registerWaiverCta: "Acquitter l'écart",
};

const TRIGGERS_LABELS_FR: WorkflowTriggersModalLabels = {
  title: "Déclencheurs autonomes",
  description: "Configurer les automatisations",
  helpButtonLabel: "Aide",
  missingContractNotice: "Contrat requis",
  emptyListHint: "Aucun déclencheur configuré.",
  typeLabel: "Type",
  triggerKeyLabel: "Clé unique (optionnelle)",
  triggerKeyPlaceholder: "Ex : alert-api-prod",
  typeOptions: {
    MANUAL_AUTONOMOUS: "Lancement autonome",
    WEBHOOK: "Webhook entrant",
    CRON: "Planification",
    LOG_SINK_ALERT: "Alerte journaux",
    OUTBOX_EVENT: "Événement métier",
  },
  statusLabels: {
    ACTIVE: "Actif",
    PAUSED: "En pause",
    CIRCUIT_OPEN: "Suspendu",
  },
  cronLabel: "Expression",
  cronPlaceholder: "0 * * * *",
  logServiceLabel: "Service supervisé",
  logServicePlaceholder: "orcia-api",
  cooldownLabel: "Délai (s)",
  maxRunsPerHourLabel: "Max / heure",
  maxDailyCostLabel: "Plafond / jour",
  autoHelpCheckboxLabel: "Aide auto",
  webhookSecretFieldLabel: "Secret webhook", // pragma: allowlist secret
  secretConfiguredBadge: "Configuré", // pragma: allowlist secret
  secretUnconfiguredBadge: "Non configuré", // pragma: allowlist secret
  secretFingerprintPrefix: "Empreinte", // pragma: allowlist secret
  secretReplaceCta: "Remplacer", // pragma: allowlist secret
  secretCancelCta: "Annuler", // pragma: allowlist secret
  secretClearCta: "Effacer", // pragma: allowlist secret
  secretSaveCta: "Enregistrer", // pragma: allowlist secret
  secretInputPlaceholder: "Secret", // pragma: allowlist secret
  createButton: "Créer le déclencheur",
  creatingButton: "Création...",
  fireNowButton: "Déclencher",
  resetCircuitButton: "Réactiver",
  pauseButton: "Mettre en pause",
  activateButton: "Activer",
  deleteButton: "Supprimer",
  closeButton: "Fermer",
  failuresPrefix: "Échecs :",
};

function StatefulFiveTabsHarness() {
  const [activeTab, setActiveTab] = useState<WorkspaceSubTabKey>("OVERVIEW");
  return (
    <WorkspaceFiveTabsAndExternalRebaseView
      workspaceSlug="ws-equipe-alpha"
      workspaceName="Espace Équipe Alpha"
      ownerOrgUnitName="Direction Technique"
      visibilityLabel="Collectif d'équipe"
      effectiveRoleLabel="Contributeur"
      lifecyclePhaseLabel="Construction"
      activeTab={activeTab}
      defaultArtifactDestinationUri="orcia://workspaces/ws-equipe-alpha/artifacts"
      pendingGlossaryCandidatesCount={3}
      sources={[
        {
          sourceId: "src-alpha",
          uri: "git://internal/repo",
          title: "Dépôt Core",
          authorityRole: "ACTIVE",
          accessMode: "READ_WRITE_TARGET",
          freshnessStatus: "FRESH",
        },
      ]}
      activeWaivers={[]}
      rebasedChunks={[]}
      labels={FIVE_TABS_LABELS_FR}
      onSelectTab={setActiveTab}
    />
  );
}

describe("Story 24.2 (USER24-BUG-6 & REM24-03) — WorkspaceFiveTabsAndExternalRebaseView & WorkflowTriggersModal", () => {
  it("switches across all 5 tabs and renders workspace-members-panel on tab 5 instead of Documents & Sources", () => {
    render(<StatefulFiveTabsHarness />);

    // 1. OVERVIEW
    expect(screen.getByTestId("workspace-overview-panel")).toBeDefined();
    expect(screen.queryByTestId("workspace-sources-panel")).toBeNull();
    expect(screen.queryByTestId("workspace-members-panel")).toBeNull();

    // 2. DOCUMENTS_SOURCES
    fireEvent.click(screen.getByTestId("workspace-tab-DOCUMENTS_SOURCES"));
    expect(screen.getByTestId("workspace-sources-panel")).toBeDefined();
    expect(screen.queryByTestId("workspace-overview-panel")).toBeNull();

    // 3. DELIVERABLES_ARTIFACTS
    fireEvent.click(screen.getByTestId("workspace-tab-DELIVERABLES_ARTIFACTS")); // pragma: allowlist secret
    expect(screen.getByTestId("workspace-deliverables-panel")).toBeDefined();
    expect(screen.queryByTestId("workspace-sources-panel")).toBeNull();

    // 4. GLOSSARY_RULES
    fireEvent.click(screen.getByTestId("workspace-tab-GLOSSARY_RULES"));
    expect(screen.getByTestId("workspace-glossary-rules-panel")).toBeDefined();
    expect(screen.queryByTestId("workspace-deliverables-panel")).toBeNull();

    // 5. MEMBERS_TEAM (USER24-BUG-6: must show workspace-members-panel and NEVER Documents & Sources)
    fireEvent.click(screen.getByTestId("workspace-tab-MEMBERS_TEAM"));
    const membersPanel = screen.getByTestId("workspace-members-panel");
    expect(membersPanel).toBeDefined();
    expect(membersPanel.textContent).toContain("Direction Technique");
    expect(screen.queryByTestId("workspace-sources-panel")).toBeNull();
    expect(screen.queryByTestId("workspace-overview-panel")).toBeNull();
    expect(screen.queryByTestId("workspace-glossary-rules-panel")).toBeNull();
  });

  it("submits optional trigger_key in WorkflowTriggersModal and renders RFC 9457 409 error in [role=alert]", () => {
    const onCreateTrigger = vi.fn();
    render(
      <WorkflowTriggersModal
        open={true}
        onOpenChange={vi.fn()}
        workflowTitle="Qualification PRD"
        hasActiveContract={true}
        triggers={[]}
        errorMessage="Conflit (ERR_TRIGGER_DUPLICATE_KEY) : la clé existe déjà."
        labels={TRIGGERS_LABELS_FR}
        onCreateTrigger={onCreateTrigger}
        onUpdateTrigger={vi.fn()}
        onDeleteTrigger={vi.fn()}
        onFireTrigger={vi.fn()}
        onResetCircuit={vi.fn()}
        onOpenHelpSection={vi.fn()}
      />,
    );

    const alert = screen.getByTestId("workflow-triggers-error-banner");
    expect(alert.getAttribute("role")).toBe("alert");
    expect(alert.textContent).toContain("ERR_TRIGGER_DUPLICATE_KEY");

    fireEvent.change(screen.getByTestId("trigger-create-type-select"), {
      target: { value: "LOG_SINK_ALERT" },
    });
    fireEvent.change(screen.getByTestId("trigger-create-key-input"), {
      target: { value: "  alert-api-prod  " },
    });
    fireEvent.change(screen.getByTestId("trigger-create-log-service-input"), {
      target: { value: "orcia-api" },
    });
    fireEvent.click(screen.getByTestId("trigger-create-submit-btn"));

    expect(onCreateTrigger).toHaveBeenCalledWith(
      expect.objectContaining({
        triggerType: "LOG_SINK_ALERT",
        triggerKey: "alert-api-prod",
        logSinkService: "orcia-api",
      }),
    );
  });
});
