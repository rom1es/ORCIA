import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import React, { useState } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import {
  AgentDetailAndSandboxModal,
  FinopsGovernanceDashboardView,
  SidebarAccountPopover,
  UserSettingsMcpTokensTab,
  UserSettingsModalDialog,
  type AgentsAndSkillsManagerLabels,
  type FinopsDashboardLabels,
} from "../index";
import { TEST_AGENT_STUDIO_LABELS } from "./agentsAndSkillsLabelsFixture";
import { TEST_USER_SETTINGS_LABELS } from "./userSettingsLabelsFixture";

const FINOPS_LABELS = {
  pageTitle: "Coûts & Budgets",
  pageSubtitle: "Suivi FinOps",
  infoButtonAriaLabel: "Aide",
  scopeSelector: {
    currentWorkspace: "Espace courant",
    currentTeam: "Équipe",
    entirePlatform: "Plateforme",
  },
  configureBudgetButton: "Configurer le budget",
  kpis: {
    consolidatedCostTitle: "Coût consolidé",
    verifiedInternalSubtitle: "interne",
    reportedExternalSubtitle: "externe",
    tokensTitle: "Tokens LLM",
    internalTokensSubtitle: "internes",
    remoteTokensSubtitle: "distants",
    externalCallsTitle: "Appels externes",
    externalUnitsSubtitle: "unités",
    savingsTitle: "Économies",
    activeBreakersBadge: "disjoncteurs",
    pausedRunsBadge: "en pause",
  },
  emptyStateText: "Aucune dépense",
  tabs: {
    processes: "Processus",
    tiers: "Niveaux",
    externalServices: "Services externes",
    cognitiveGovernance: "Gouvernance",
  },
  processesTable: {
    title: "Processus",
    workflowCol: "Processus",
    runsCol: "Exécutions",
    setupCostCol: "Setup",
    runCostCol: "Coût",
    humanTimeCol: "Temps humain",
    totalCostCol: "Total",
    ttmCol: "Gain TTM",
    statusCol: "Statut",
    actionsCol: "Action",
    pausedBadgeBudget: "En pause",
    pausedBadgeRetries: "En pause",
    activeBadge: "Opérationnel",
    overrideButton: "Débloquer",
    emptyProcessesText: "Aucun processus",
  },
  tiersTable: {
    title: "Niveaux",
    tierCol: "Niveau",
    effortCol: "Effort",
    invocationsCol: "Appels",
    inputTokensCol: "Entrée",
    outputTokensCol: "Sortie",
    totalTokensCol: "Total",
    costCol: "Coût",
    emptyTiersText: "Vide",
    tierLabels: {},
    effortLabels: {},
  },
  modals: {
    budgetTitle: "Budget",
    budgetDescription: "Desc",
    monthlyLimitLabel: "Mensuel",
    warningThresholdLabel: "Alerte",
    hardStopLabel: "Plafond",
    scopeLabel: "Périmètre",
    scopeGlobalLabel: "Global",
    scopeBuLabel: "Direction",
    scopeTeamLabel: "Équipe",
    scopeWorkspaceLabel: "Espace",
    saveButton: "Enregistrer",
    cancelButton: "Annuler",
    overrideTitle: "Déblocage",
    overrideDescription: "Desc",
    overrideAmountLabel: "Montant",
    overrideReasonLabel: "Motif",
    overrideSubmitButton: "Valider",
  },
} as unknown as FinopsDashboardLabels;

const AGENT_LABELS = {
  heading: "Mes Agents",
  subtitle: "Sous-titre",
  tabAgents: "Agents",
  tabSkills: "Compétences",
  tabConnections: "Connecteurs",
  emptyAgentsTitle: "Vide",
  emptyAgentsDescription: "Vide",
  emptySkillsTitle: "Vide",
  emptySkillsDescription: "Vide",
  createAgentSectionTitle: "Créer",
  agentNameLabel: "Nom",
  agentNamePlaceholder: "Nom",
  agentRoleLabel: "Rôle",
  agentRolePlaceholder: "Rôle",
  agentInstructionsLabel: "Instructions",
  agentInstructionsPlaceholder: "Instructions",
  agentThinkingLevelLabel: "Réflexion",
  thinkingLevels: { simple: "Simple", medium: "Moyen", complex: "Complexe", auto: "Auto" },
  attachedSkillsLabel: "Compétences",
  noSkillsAvailableHint: "Aucune",
  createAgentButtonLabel: "Créer",
  testAgentInputPlaceholder: "Prompt...",
  runAgentButtonLabel: "Exécuter",
  deleteAgentButtonLabel: "Supprimer",
  mobilizedSkillsLabel: "Compétences",
  createSkillSectionTitle: "Créer",
  skillUsageBanner: "Banner",
  skillNameLabel: "Nom",
  skillNamePlaceholder: "Nom",
  skillObjectiveLabel: "Objectif",
  skillObjectivePlaceholder: "Objectif",
  skillParamsLabel: "Paramètres",
  skillParamsPlaceholder: "Paramètres",
  skillInstructionsLabel: "Instructions",
  skillInstructionsPlaceholder: "Instructions",
  skillOutputFormatLabel: "Format",
  skillOutputFormatPlaceholder: "Format",
  createSkillButtonLabel: "Créer",
  testSkillInputPlaceholder: "Test",
  runSkillButtonLabel: "Tester",
  deleteSkillButtonLabel: "Supprimer",
  studio: TEST_AGENT_STUDIO_LABELS,
};

afterEach(() => {
  cleanup();
});

describe("Story 24.4 — Modales OrciaDialog, Onglets horizontaux, Menu Compte, Clés MCP & FinOps", () => {
  it("rend UserSettingsModalDialog en onglets horizontaux .orcia-ds-tabs et supprime account-popover-settings-btn (USER24-BUG-4A, 4B)", () => {
    render(
      <>
        <SidebarAccountPopover
          railCollapsed={false}
          userDisplayName="Claire Martin"
          userEmail="claire@orcia.io"
          userRoleLabel="Responsable Sécurité"
          labels={TEST_USER_SETTINGS_LABELS.popover}
          onOpenSettingsTab={vi.fn()}
          onNavigateProfile={vi.fn()}
          onNavigateHelp={vi.fn()}
          onNavigateShowcase={vi.fn()}
          onLogout={vi.fn()}
        />
        <UserSettingsModalDialog
          open={true}
          onOpenChange={vi.fn()}
          activeTab="PERSONALIZATION"
          onSelectTab={vi.fn()}
          userEmail="claire@orcia.io"
          userRole="SECOPS"
          theme="light"
          locale="fr"
          defaultAssistantHat="ANALYST_PM_PO"
          assistantTone="balanced"
          personalInstructions=""
          autoOpenHelp={true}
          notificationsEnabled={true}
          mcpTokens={[]}
          lastIssuedPlaintext={null}
          labels={TEST_USER_SETTINGS_LABELS}
          onUpdatePreferences={vi.fn()}
          onCreateMcpToken={vi.fn()}
          onRevokeMcpToken={vi.fn()}
        />
      </>,
    );

    fireEvent.keyDown(screen.getByTestId("sidebar-open-my-account-btn"), { key: "Enter" });
    const popover = screen.getByTestId("sidebar-account-popover-menu");
    expect(popover.querySelector('[data-testid="account-popover-personalization-btn"]')).not.toBeNull();
    expect(popover.textContent).not.toContain("Paramètres");

    const tabs = screen.getByTestId("user-settings-tabs");
    expect(tabs.getAttribute("role")).toBe("tablist");
    expect(tabs.getAttribute("aria-orientation")).toBe("horizontal");
    expect(tabs.className).toContain("orcia-ds-tabs");

    const tabPersonalization = screen.getByTestId("user-settings-tab-PERSONALIZATION");
    expect(tabPersonalization.className).toContain("orcia-ds-tab");
    expect(tabPersonalization.getAttribute("aria-selected")).toBe("true");
  });

  it("réinitialise copiedPlaintext quand lastIssuedPlaintext devient null et affiche des libellés FR sans 'IDE MCP (SPACE · default)' ni '· 60 RPM' (USER24-BUG-5)", async () => {
    const onCreate = vi.fn();
    function Harness() {
      const [plaintext, setPlaintext] = useState<string | null>("pat_mcp_secret_token_1234");
      return (
        <div>
          <button type="button" data-testid="clear-plaintext" onClick={() => setPlaintext(null)}>
            Clear
          </button>
          <button type="button" data-testid="restore-plaintext" onClick={() => setPlaintext("pat_mcp_secret_token_5678")}>
            Restore
          </button>
          <UserSettingsMcpTokensTab
            mcpTokens={[
              {
                tokenId: "tok-1",
                label: "Clé personnelle d'éditeur",
                tokenPrefix: "pat_mcp_abc123...",
                tokenSha256: "sha256",
                expiresInDays: 30,
                rpmLimit: 60,
                targetKind: "SPACE",
                targetSlug: "espace-finance",
                mcpEndpointUri: "/api/v1/mcp/spaces/espace-finance",
                ideJsonSnippet: "{}",
                revoked: false,
              },
            ]}
            lastIssuedPlaintext={plaintext}
            labels={TEST_USER_SETTINGS_LABELS}
            onCreateMcpToken={onCreate}
            onRevokeMcpToken={vi.fn()}
          />
        </div>
      );
    }

    render(<Harness />);
    fireEvent.click(screen.getByTestId("mcp-copy-plaintext-btn"));
    expect(screen.getByTestId("mcp-copy-plaintext-btn").textContent).toContain("Copié");

    fireEvent.click(screen.getByTestId("clear-plaintext"));
    expect(screen.queryByTestId("mcp-issued-plaintext-banner")).toBeNull();

    fireEvent.click(screen.getByTestId("restore-plaintext"));
    expect(screen.getByTestId("mcp-copy-plaintext-btn").textContent).toContain("Copier");

    // Empty label & slug submit uses readable French fallback without "default"
    fireEvent.click(screen.getByTestId("mcp-generate-token-btn"));
    expect(onCreate).toHaveBeenCalledWith(
      expect.objectContaining({
        label: "Clé personnelle d'éditeur",
      }),
    );

    const rowText = screen.getByTestId("mcp-token-row-tok-1").textContent ?? "";
    expect(rowText).toContain("Clé personnelle d'éditeur");
    expect(rowText).toContain("Identifiant : pat_mcp_abc123...");
    expect(rowText).not.toContain("IDE MCP (SPACE · default)");
    expect(rowText).not.toContain("· 60 RPM");
  });

  it("monte AgentDetailAndSandboxModal sur OrciaDialog (max-h-[82vh], body/footer DS, handle complet) et FinopsScopePills sur aria-selected", () => {
    render(
      <>
        <AgentDetailAndSandboxModal
          agent={{
            agentId: "ag-compliance",
            slug: "agent_analyste_conformite_long_slug",
            name: "Analyste Conformité",
            handle: "@agent_analyste_conformite_long_slug",
            roleMission: "Audit RGPD",
            instructions: "Vérifier la conformité",
            thinkingLevel: "medium",
            visibilityScope: "TEAM",
            skillIds: [],
            mcpExposed: true,
          }}
          skills={[]}
          labels={AGENT_LABELS}
          testInputValue=""
          onChangeTestInput={vi.fn()}
          onToggleAgentSkill={vi.fn()}
          onExecuteAgent={vi.fn()}
          onClose={vi.fn()}
        />
        <FinopsGovernanceDashboardView
          scopeType="TEAM"
          totalRuns={3}
          totalCostEur={12.5}
          verifiedInternalCostEur={10}
          reportedExternalCostEur={2.5}
          totalLlmTokens={5000}
          internalTokens={4000}
          remoteTokens={1000}
          totalExternalCalls={2}
          processes={[]}
          tiers={[]}
          labels={FINOPS_LABELS}
          headerActions={<span data-testid="finops-header-action-slot">Action</span>}
        />
      </>,
    );

    const modal = screen.getByTestId("agent-detail-modal-ag-compliance");
    expect(modal.className).toContain("max-h-[82vh]");
    expect(modal.querySelector(".orcia-ds-dialog-body")).not.toBeNull();
    expect(modal.querySelector(".orcia-ds-dialog-footer")).not.toBeNull();
    const handle = screen.getByTestId("agent-modal-handle-ag-compliance");
    expect(handle.textContent).toBe("@agent_analyste_conformite_long_slug");
    expect(handle.className).toContain("whitespace-nowrap");
    expect(handle.className).not.toContain("truncate");

    const kpiStrip = screen.getByTestId("finops-kpi-strip");
    expect(kpiStrip.className).toContain("sm:grid-cols-2");
    expect(kpiStrip.className).toContain("xl:grid-cols-4");

    const teamPill = screen.getByTestId("finops-scope-team");
    expect(teamPill.getAttribute("role")).toBe("tab");
    expect(teamPill.getAttribute("aria-selected")).toBe("true");
    expect(teamPill.className).toContain("orcia-ds-tab");
    expect(teamPill.className).not.toContain("active");
    expect(screen.getByTestId("finops-scope-workspace").getAttribute("aria-selected")).toBe("false");
    expect(screen.getByTestId("finops-header-action-slot")).toBeDefined();
  });
});
