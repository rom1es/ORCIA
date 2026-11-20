import { FinopsKpiStrip } from "@orcia/ui";
import { QueryClientProvider } from "@tanstack/react-query";
import { createMemoryHistory, RouterProvider } from "@tanstack/react-router";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import React from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { clearPlatformSetupStorage } from "../components/platformSetupStore";
import { AiModelsMasterTable } from "../features/admin/ai-models/AiModelsMasterTable";
import { IamSecopsExceptionForm } from "../features/admin/iam/IamSecopsExceptionForm";
import { StudioCopilotSidebar } from "../features/processes/studio/StudioCopilotSidebar";
import { PackCardItem } from "../features/settings/packs/PackCardItem";
import {
  formatConnectorDisplayName,
  formatConnectorScopes,
  formatPackAgentDisplayName,
  formatPackCounterLabel,
} from "../features/settings/packs/packDisplayFormatters";
import { WorkspaceStudioCardsAndDetailView } from "../features/workspaces/WorkspaceStudioCardsAndDetailView";
import { AI_MODELS_HUB_EN, AI_MODELS_HUB_FR } from "../i18n/locales/ai_models_hub_labels";
import { FINOPS_FR_LABELS } from "../i18n/locales/finops_labels";
import { IAM_TAB_FR_LABELS } from "../i18n/locales/iam_accounts_labels";
import { formatCurrency } from "../lib/formatters";
import { createOrciaQueryClient, createOrciaRouter } from "../router";
import { seedVitestPlatformSetupState } from "./vitest.setup";
import { seedVitestOntologyState } from "./vitestOntologyMockHandlers";

beforeEach(() => {
  clearPlatformSetupStorage();
});

afterEach(() => {
  cleanup();
});

describe("Story 24.6 — Packs 5 Counters, Singular n <= 1, IAM Split, Microcopy & FinOps 0,002 €", () => {
  it("renders PackCardItem with 5 counters, singular n <= 1 in FR, and humanized connectors & agents", () => {
    expect(formatPackCounterLabel(0, "Chaîne", "Chaînes", "Stream", "Streams", true)).toBe("Chaîne");
    expect(formatPackCounterLabel(1, "Chaîne", "Chaînes", "Stream", "Streams", true)).toBe("Chaîne");
    expect(formatPackCounterLabel(2, "Chaîne", "Chaînes", "Stream", "Streams", true)).toBe("Chaînes");
    expect(formatPackCounterLabel(0, "Chaîne", "Chaînes", "Stream", "Streams", false)).toBe("Streams");
    expect(formatPackCounterLabel(1, "Chaîne", "Chaînes", "Stream", "Streams", false)).toBe("Stream");

    expect(formatConnectorDisplayName("mcp:atlassian-jira", true)).toBe("Atlassian Jira");
    expect(formatConnectorDisplayName("mcp:atlassian-confluence", true)).toBe("Atlassian Confluence");
    expect(formatConnectorScopes(["read", "write_preview"], true)).toBe(
      "Lecture, Écriture sous validation",
    );
    expect(formatPackAgentDisplayName("crl-etude-archi", true)).toBe(
      "Analyste Étude Architecture",
    );

    render(
      <PackCardItem
        isFr={true}
        onExportZip={vi.fn()}
        pack={{
          id: "pack-1",
          slug: "pack-etude-archi",
          name: "Pack Étude Architecture",
          version: "1.0.0",
          description: "Cadrage technique et dossiers d'architecture.",
          rbac_namespace: "architecture",
          bundle_sha256: "packsha246test00",
          agents_count: 1,
          skills_count: 4,
          gates_count: 1,
          vsm_count: 0,
          workflows_count: 1,
          agents_slugs: ["crl-etude-archi"],
          skills_slugs: ["s1", "s2", "s3", "s4"],
          connector_health: [
            {
              connector_type: "mcp:atlassian-jira",
              required_scopes: ["read", "write_preview"],
              used_for: "Suivi des décisions d'architecture",
              health: {
                connector_type: "mcp:atlassian-jira",
                ok: true,
                latency_ms: 14,
                error_message: null,
              },
            },
          ],
        }}
      />,
    );

    const grid = screen.getByTestId("pack-counters-pack-etude-archi");
    expect(grid.children.length).toBe(5);
    expect(grid.textContent).toContain("1Agent");
    expect(grid.textContent).toContain("4Compétences");
    expect(grid.textContent).toContain("1Validation");
    expect(grid.textContent).toContain("0Chaîne");
    expect(grid.textContent).toContain("1Processus");

    const card = screen.getByTestId("declarative-pack-card-pack-etude-archi");
    expect(card.textContent).toContain("Atlassian Jira");
    expect(card.textContent).toContain("Lecture, Écriture sous validation");
    expect(card.textContent).toContain("Analyste Étude Architecture");
    expect(card.textContent).not.toContain("mcp:atlassian-jira");
    expect(card.textContent).not.toContain("crl-etude-archi");
  });

  it("renders WorkspaceStudioCardsAndDetailView with anti-truncation search input & n <= 1 singular labels", () => {
    render(
      <WorkspaceStudioCardsAndDetailView
        isFr={true}
        workspaces={[
          {
            workspaceId: "ws-1",
            name: "Espace Paiements",
            visibilityMode: "STANDARD",
            ownerOrgUnitName: "Équipe Paiements",
            lifecyclePhase: "BUILD",
            suggestedWorkflows: [],
            accessMode: "CONTRIBUTOR_ACTION_REQUIRED",
            finopsCostUsd: 0.002,
          },
        ]}
        datasources={[
          {
            id: "ds-1",
            workspaceName: "Espace Paiements",
            alias: "Dépôt Paiements",
            scheme: "git",
            uri: "git://repo/payments",
            executionIdentity: "passthrough",
            freshnessTtlDays: 7,
            tripartiteStatus: "ALIGNED",
          },
        ]}
        ontologyConcepts={[
          {
            conceptKey: "sepa-rule",
            canonicalTerm: "Règle SEPA",
            level: "4_WORKSPACE",
            scopeId: "ws-1",
            definitionText: "Règle de validation SEPA.",
            immutable: false,
            synonyms: [],
            profileTranslations: {},
            impactedTemplates: [],
            impactedWorkflows: [],
            impactedRuns: [],
          },
        ]}
        workflows={[
          {
            workflowKey: "wf-1",
            title: "Audit SEPA",
            version: "1.0.0",
            status: "PUBLISHED",
            prePrompt: "",
            prePromptSha256: "sha",
            requiredParams: [],
            requiredMarkdownSections: [],
            triggers: [],
            layers: [],
          },
        ]}
        orgUnits={[]}
        isCreateFormExpanded={false}
        onToggleCreateForm={vi.fn()}
        openHelpSection={vi.fn()}
        onNavigateToRoute={vi.fn()}
        onUpdateWorkspacePhase={vi.fn()}
        onUpdateWorkspaceVisibility={vi.fn()}
        onRegisterDatasource={vi.fn()}
        onAddOntologyConcept={vi.fn()}
        onPromoteOntologyConcept={vi.fn()}
        onFeedback={vi.fn()}
      />,
    );

    const searchInput = screen.getByTestId("workspaces-search-input") as HTMLInputElement;
    expect(searchInput.placeholder).toBe("Rechercher un espace…");
    expect(searchInput.style.minWidth).toBe("230px");

    const card = screen.getByTestId("workspace-studio-card-ws-1");
    expect(card.textContent).toContain("1 Source rattachée");
    expect(card.textContent).toContain("1 Terme & Règle actif");
    expect(card.textContent).toContain("1 Processus");
    expect(card.textContent).toContain("0,002");
  });

  it("renders IamSecopsExceptionForm with shortened globalScopeOption and StudioCopilotSidebar compact placeholder", () => {
    render(
      <div>
        <IamSecopsExceptionForm
          isSecopsAuthorized={true}
          isSubmitting={false}
          accounts={[]}
          orgUnits={[]}
          workspaces={[]}
          labels={IAM_TAB_FR_LABELS}
          openHelpSection={vi.fn()}
          onCreateException={vi.fn()}
        />
        <StudioCopilotSidebar
          isFr={true}
          onAttachSkill={vi.fn()}
          onAttachMcpTool={vi.fn()}
          onAttachDeterministicGate={vi.fn()}
        />
      </div>,
    );

    const scopeSelect = screen.getByTestId("rbac-scope-preset-select") as HTMLSelectElement;
    expect(scopeSelect.parentElement?.style.minWidth).toBe("240px");
    expect(scopeSelect.textContent).toContain("Plateforme entière (Global)");
    expect(screen.getByTestId("rbac-verbs-checkbox-group")).toBeDefined();

    const copilotInput = screen.getByTestId("studio-copilot-input") as HTMLInputElement;
    expect(copilotInput.placeholder).toBe("Ex : Ajouter un contrôle…");
    expect(copilotInput.style.flex).toBe("1 1 170px");
  });

  it("deduplicates Organisation (Global) in /ontology mounted via real RouterProvider", async () => {
    seedVitestPlatformSetupState(
      {
        org_units: [],
        rbac_grants: [],
        llm_tiers: [],
        workspaces: [],
        datasources: [],
        packs: [],
        workflows: [],
        runs: [],
        catalog_items: [],
        ontology_concepts: [],
      },
      { email: "admin@orcia.ia", displayName: "Admin", roles: ["PLATFORM_ADMIN"] },
    );
    seedVitestOntologyState([], []);

    const queryClient = createOrciaQueryClient();
    const history = createMemoryHistory({ initialEntries: ["/ontology"] });
    const router = createOrciaRouter({ queryClient, history });
    await router.load();

    render(
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={router} />
      </QueryClientProvider>,
    );

    const select = (await screen.findByTestId("ontology-level-select")) as HTMLSelectElement;
    await waitFor(() => {
      expect(select.options.length).toBeGreaterThan(0);
    });
    expect(select.textContent).toContain("Organisation (Global)");
    expect(select.textContent).not.toContain("Organisation (Global) · Organisation (Global)");
  });

  it("uses 'paliers' across AI Models Hub labels and formats 0.002 € with 3 decimals in FinOps", () => {
    expect(AI_MODELS_HUB_FR.coverageTitle).toBe("Couverture des 4 paliers cognitifs");
    expect(AI_MODELS_HUB_FR.coverageAllConfigured).toBe(
      "Tous les paliers cognitifs sont opérationnels",
    );
    expect(AI_MODELS_HUB_FR.coverageMissingTiers).toBe("Paliers à compléter :");
    expect(AI_MODELS_HUB_FR.colTier).toBe("Palier Cognitif");
    expect(AI_MODELS_HUB_EN.colTier).toBe("Model Tier");

    render(
      <div>
        <AiModelsMasterTable
          isFr={true}
          labels={AI_MODELS_HUB_FR}
          tierLabels={{
            tierLabel: "Palier",
            effortLabel: "Effort",
            simpleBadge: "Rapide",
            mediumBadge: "Équilibré",
            complexBadge: "Approfondi",
            autoBadge: "Automatique",
            effortDefault: "Standard",
            effortFast: "Faible",
            effortBalanced: "Équilibré",
            effortDeep: "Élevé",
          }}
          mappings={[]}
          allowedVerbs={["read", "create", "update", "delete"]}
          testingId={null}
          onOpenCreateModal={vi.fn()}
          onOpenEditModal={vi.fn()}
          onOpenRotateKeyModal={vi.fn()}
          onToggleActive={vi.fn()}
          onOpenDeleteDialog={vi.fn()}
          onTestConnection={vi.fn()}
        />
        <FinopsKpiStrip
          totalRuns={1}
          totalCostEur={0.002}
          verifiedInternalCostEur={0.002}
          reportedExternalCostEur={0}
          totalLlmTokens={240}
          internalTokens={240}
          remoteTokens={0}
          totalExternalCalls={0}
          emptyStateText={FINOPS_FR_LABELS.finops.emptyStateText}
          labels={FINOPS_FR_LABELS.finops.kpis}
        />
      </div>,
    );

    expect(formatCurrency(0.002, "fr").replace(/\s+/g, " ")).toBe("0,002 €");
    expect(formatCurrency(0.002, "en")).toBe("€0.002");
    expect(formatCurrency(12.5, "fr").replace(/\s+/g, " ")).toBe("12,50 €");

    expect(screen.getByTestId("finops-kpi-strip").textContent).toContain("0,002 €");
    expect(screen.getByTestId("ai-models-empty-state").textContent).not.toContain("Tier cognitif");
  });
});
