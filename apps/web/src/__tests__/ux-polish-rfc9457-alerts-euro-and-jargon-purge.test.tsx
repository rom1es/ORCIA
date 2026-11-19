import { OrciaProblemError } from "@orcia/api-client";
import {
  AgentExecutionTrace,
  AssistantThinkingSubWindow,
  FinopsKpiStrip,
  OrciaButton,
  TopHeaderSearchCommand,
  UserProfileOverviewPage,
  type AgentExecutionTraceLabels,
  type TopHeaderSearchCommandLabels,
} from "@orcia/ui";
import { QueryClientProvider } from "@tanstack/react-query";
import { createMemoryHistory, RouterProvider } from "@tanstack/react-router";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import React from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { clearPlatformSetupStorage } from "../components/platformSetupStore";
import { WorkflowStudioHeaderBar } from "../features/processes/studio/WorkflowStudioHeaderBar";
import { INITIAL_WORKFLOWS_V2 } from "../features/processes/processStudioV2Data";
import { I18nProvider } from "../i18n";
import { PROFILE_OVERVIEW_FR_LABELS } from "../i18n/locales/profile_overview_labels";
import { formatRfc9457ErrorToBanner } from "../lib/formatRfc9457ErrorToBanner";
import { formatCurrency, formatShortDate, formatShortDateTime } from "../lib/formatters";
import { createOrciaQueryClient, createOrciaRouter } from "../router";
import { useAuthSessionStore } from "../stores/authSessionStore";
import { resetVitestApiBackend, seedVitestPlatformSetupState } from "./vitest.setup";

const TRACE_LABELS: AgentExecutionTraceLabels = {
  heading: "Déroulement de l'investigation",
  defaultGroupTitle: "Analyse et recherche dans vos sources",
  runningStatus: "En cours d'analyse...",
  synthesizingStatus: "Synthèse en cours...",
  completedStatus: "Analyse terminée",
  pausedWriteStatus: "En attente de confirmation",
  cancelledStatus: "Exécution interrompue",
  failedStatus: "Interruption sur anomalie",
  stepsCountLabel: (count) => `${count} action${count > 1 ? "s" : ""}`,
  thoughtSummaryLabel: (seconds) => `Réflexion (${seconds}s)`,
  thoughtInProgressLabel: "Réflexion en cours",
  analyzedPrefix: "Analysé",
  linesRangeShort: (start, end) => `#L${start}-${end}`,
  redactedPillSuffix: "Accès requis",
  delegatedPrefix: (agentHandle) => `Délégation à ${agentHandle}`,
  synthesizeNowButtonLabel: "Synthétiser maintenant",
  synthesizeNowButtonHint: "Conclusion immédiate",
  writePreviewHeading: "Confirmation requise",
  writePreviewTargetPrefix: "Outil cible :",
  approveWriteButtonLabel: "Approuver",
  rejectWriteButtonLabel: "Refuser",
  expandGroupAriaLabel: "Déplier l'étape",
  collapseGroupAriaLabel: "Replier l'étape",
};

const CMDK_LABELS: TopHeaderSearchCommandLabels = {
  modalTitle: "Recherche fédérée",
  inputPlaceholder: "Rechercher...",
  scopeScreenLabel: "Cet écran",
  scopeWorkspaceLabel: "Cet espace",
  scopeAllWorkspacesLabel: "Tous les espaces",
  speed1SectionTitle: "Résultats instantanés",
  speed2SectionTitle: "Correspondances sémantiques",
  semanticCloseMatchBadge: "Passage proche",
  emptyResultsLabel: "Aucun résultat trouvé.",
  previewPaneTitle: "Aperçu",
  deepLinkActionLabel: "Ouvrir",
  openHelpColumnActionLabel: "Aide",
  askAssistantFooterPrefix: "Demander à",
  askAssistantFooterSuffix: "Mon Assistant",
  familyLabels: {
    FOLDERS_DISCUSSIONS: "Dossiers & Discussions",
    PROCESSES_EXECUTIONS: "Processus & Exécutions",
    AGENTS_TOOLS: "Agents & Outils",
    DELIVERABLES_ARTIFACTS: "Livrables",
    SOURCES_SNIPPETS: "Sources",
    ONTOLOGY_GLOSSARY: "Glossaire",
    HELP_ACTIONS: "Aide",
  },
};

beforeEach(() => {
  resetVitestApiBackend();
  clearPlatformSetupStorage();
});

afterEach(() => {
  cleanup();
});

describe("UX Polish — Actionable RFC 9457 Banners, Euro & FR Dates, Modals & Jargon Purge", () => {
  it("translates RFC 9457 statuses (403, 404, 409, 422, 503) and ERR_* codes into actionable FR/EN messages without raw enum leaks", () => {
    const cases: ReadonlyArray<{
      status: number;
      errorCode?: string;
      detail?: string;
      resourceLabel?: string;
      expectedFr: string;
      expectedEn: string;
    }> = [
      {
        status: 403,
        errorCode: "ERR_OBSERVER_MODE_READ_ONLY",
        detail: "READ_ONLY_OBSERVER blocked",
        resourceLabel: "Espace Finance",
        expectedFr: "Action bloquée (mode lecture seule)",
        expectedEn: "Action blocked (read-only mode)",
      },
      {
        status: 404,
        errorCode: "ERR_RESOURCE_NOT_FOUND",
        resourceLabel: "Modèle Mistral",
        expectedFr: "Ressource introuvable",
        expectedEn: "Resource not found",
      },
      {
        status: 409,
        errorCode: "ERR_ONTOLOGY_CONFLICT",
        expectedFr: "Conflit avec un terme de référence",
        expectedEn: "Conflict with reference term",
      },
      {
        status: 422,
        errorCode: "ERR_VALIDATION_FAILED",
        expectedFr: "Données saisies incomplètes ou invalides",
        expectedEn: "Invalid or incomplete input",
      },
      {
        status: 503,
        resourceLabel: "Indexation",
        expectedFr: "Service temporairement indisponible",
        expectedEn: "Service temporarily unavailable",
      },
    ];

    for (const c of cases) {
      const problem = new OrciaProblemError({
        type: "https://orcia.io/problems/test",
        title: "Error",
        status: c.status,
        detail: c.detail ?? "Detail",
        error_code: c.errorCode ?? "ERR_UPSTREAM_UNAVAILABLE",
        trace_id: "0195f000000070008000000000000001",
      });

      const fr = formatRfc9457ErrorToBanner(problem, "fr", c.resourceLabel);
      const en = formatRfc9457ErrorToBanner(problem, "en", c.resourceLabel);

      expect(fr.title).toBe(c.expectedFr);
      expect(en.title).toBe(c.expectedEn);
      expect(fr.remediation.length).toBeGreaterThan(10);
      expect(en.remediation.length).toBeGreaterThan(10);
      expect(fr.fullText).not.toMatch(/\bERR_[A-Z0-9_]+\b/);
      expect(fr.fullText).not.toContain("READ_ONLY_OBSERVER");
      if (c.resourceLabel) {
        expect(fr.fullText).toContain(c.resourceLabel);
      }
    }
  });

  it("renders a visible OrciaAlertBanner with role='alert' on API failure during workspace creation", async () => {
    seedVitestPlatformSetupState({}, { email: "admin@orcia.fr", displayName: "Admin" });
    useAuthSessionStore.getState().setAuthSession({
      isAuthenticated: true,
      email: "admin@orcia.fr",
      displayName: "Admin",
      roles: ["PLATFORM_ADMIN"],
      activeHat: "PLATFORM_ADMIN",
    });

    const queryClient = createOrciaQueryClient();
    const history = createMemoryHistory({ initialEntries: ["/spaces"] });
    const router = createOrciaRouter({ queryClient, history });
    await router.load();

    render(
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={router} />
      </QueryClientProvider>,
    );

    fireEvent.click(await screen.findByTestId("toggle-create-workspace-form-btn"));
    expect(await screen.findByTestId("create-workspace-modal")).toBeDefined();

    const originalFetch = globalThis.fetch;
    globalThis.fetch = (async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = typeof input === "string" ? input : input.toString();
      if (url.includes("/api/v1/workspaces") && (init?.method ?? "GET").toUpperCase() === "POST") {
        return new Response(
          JSON.stringify({
            type: "https://orcia.io/problems/err-validation-failed",
            title: "Validation",
            status: 422,
            detail: "Slug invalide",
            error_code: "ERR_VALIDATION_FAILED",
          }),
          { status: 422, headers: { "Content-Type": "application/problem+json" } },
        );
      }
      return originalFetch(input, init);
    }) as typeof fetch;

    try {
      fireEvent.change(screen.getByTestId("workspace-name-input"), {
        target: { value: "Espace Invalide" },
      });
      fireEvent.change(screen.getByTestId("workspace-slug-input"), {
        target: { value: "espace-invalide" },
      });
      fireEvent.click(screen.getByTestId("create-workspace-submit-btn"));

      const banner = await screen.findByTestId("workspaces-action-feedback-banner");
      expect(banner.getAttribute("role")).toBe("alert");
      expect(banner.textContent).toContain("Données saisies incomplètes ou invalides");
      expect(banner.textContent).not.toContain("ERR_VALIDATION_FAILED");
    } finally {
      globalThis.fetch = originalFetch;
    }
  });

  it("formats all currency values in Euro (€) with zero $ or USD and formats FR dates as jj/mm/aaaa", () => {
    const frEur = formatCurrency(12.5, "fr");
    const enEur = formatCurrency(12.5, "en");
    expect(frEur).toContain("€");
    expect(frEur).not.toContain("$");
    expect(frEur).not.toContain("USD");
    expect(enEur).toContain("€");
    expect(enEur).not.toContain("$");
    expect(enEur).not.toContain("USD");

    expect(formatShortDate("2026-11-19T14:35:00Z", "fr")).toBe("19/11/2026");
    expect(formatShortDate("2026-11-19T14:35:00Z", "en")).toBe("11/19/2026");
    expect(formatShortDateTime("2026-11-19T14:35:00Z", "fr")).toBe("19/11/2026 14:35:00");
  });

  it("hides zero counters, opens '+ Nouveau processus' and '+ Nouvel espace' in OrciaDialog modals, and hides zero KPIs on Profile", async () => {
    seedVitestPlatformSetupState({}, { email: "admin@orcia.fr", displayName: "Admin" });
    useAuthSessionStore.getState().setAuthSession({
      isAuthenticated: true,
      email: "admin@orcia.fr",
      displayName: "Admin",
      roles: ["PLATFORM_ADMIN"],
      activeHat: "PLATFORM_ADMIN",
    });

    const queryClient = createOrciaQueryClient();
    const history = createMemoryHistory({ initialEntries: ["/processes"] });
    const router = createOrciaRouter({ queryClient, history });
    await router.load();

    render(
      <I18nProvider initialLocale="fr">
        <QueryClientProvider client={queryClient}>
          <RouterProvider router={router} />
        </QueryClientProvider>
      </I18nProvider>,
    );

    const openProcessBtn = await screen.findByTestId("open-create-process-modal-btn");
    expect(screen.queryByTestId("create-process-modal")).toBeNull();
    expect(document.body.textContent).not.toContain("Publiés : 0");
    expect(document.body.textContent).not.toContain("Brouillons : 0");

    fireEvent.click(openProcessBtn);
    expect(await screen.findByTestId("create-process-modal")).toBeDefined();
    expect(screen.getByTestId("create-workflow-form")).toBeDefined();

    cleanup();

    render(
      <UserProfileOverviewPage
        locale="fr"
        profile={{
          userId: "u-0",
          displayName: "Camille",
          handle: "camille",
          email: "camille@orcia.fr",
          primaryRole: "CONTRIBUTOR",
          roles: ["CONTRIBUTOR"],
          ledBusinessUnits: [],
          ontologyBusinessUnits: [],
          ledTeams: [],
          memberTeams: [],
          totalTokens: 0,
          peakDailyTokens: 0,
          longestStreakDays: 0,
          currentStreakDays: 0,
          popularItems: [],
        }}
        labels={PROFILE_OVERVIEW_FR_LABELS}
        onEditAccount={vi.fn()}
        onSelectPopularItem={vi.fn()}
        onExploreAgents={vi.fn()}
      />,
    );

    expect(screen.getByTestId("profile-kpis-empty-state")).toBeDefined();
    expect(screen.queryByTestId("profile-kpi-total-tokens")).toBeNull();
  });

  it("purges internal jargon in AssistantThinkingSubWindow, renders Markdown cleanly without '||' in AgentExecutionTrace, hides empty categories in Cmd+K, removes red '(!)' inside primary blue buttons, balances FinOps grid, and avoids duplicate Studio version badges", () => {
    render(
      <div>
        <AssistantThinkingSubWindow
          isGenerating={true}
          hasStreamedResponse={false}
          stepProgress={[
            {
              stepCode: "NODE_1",
              label: "Nœuds 1–4 déterministes (pgvector + RBAC)",
              status: "COMPLETED",
              durationMs: 420,
              intermediateOutput:
                "SYNTHESIS_READY — TECH_LEAD IMMUTABLE PAUSE_AND_ESCALATE OAUTH2_PASSTHROUGH PENDING",
            },
          ]}
        />
        <AgentExecutionTrace
          status="RUNNING"
          events={[
            {
              eventId: "ev-think",
              sequence: 1,
              kind: "THOUGHT_COMPLETED",
              label: "Réflexion",
              actorSlug: "assistant",
              durationSeconds: 2,
              thoughtContent: "**Point clé**\n\n- Détail vérifié",
            },
            {
              eventId: "ev-synth",
              sequence: 2,
              kind: "SYNTHESIS_READY",
              label: "SYNTHESIS_READY",
              actorSlug: "assistant",
            },
          ]}
          labels={TRACE_LABELS}
          onInspectLines={vi.fn()}
          onSynthesizeNow={vi.fn()}
          onApproveWrite={vi.fn()}
          onRejectWrite={vi.fn()}
        />
        <TopHeaderSearchCommand
          labels={CMDK_LABELS}
          speed1Hits={[]}
          speed2Hits={[]}
          speed2Executed={true}
        />
        <OrciaButton
          data-testid="primary-disabled-action"
          variant="primary"
          disabled={true}
          disabledReason="Champ requis manquant"
        >
          Créer
        </OrciaButton>
        <FinopsKpiStrip
          totalRuns={4}
          totalCostEur={12.4}
          verifiedInternalCostEur={8.2}
          reportedExternalCostEur={4.2}
          totalLlmTokens={2500}
          internalTokens={1500}
          remoteTokens={1000}
          totalExternalCalls={3}
          emptyStateText="Vide"
          labels={{
            consolidatedCostTitle: "Coût consolidé",
            verifiedInternalSubtitle: "Interne",
            reportedExternalSubtitle: "Externe",
            tokensTitle: "Tokens",
            internalTokensSubtitle: "Interne",
            remoteTokensSubtitle: "Distant",
            externalCallsTitle: "Appels",
            externalUnitsSubtitle: "Unités",
            savingsTitle: "Économies",
            activeBreakersBadge: "Actifs",
            pausedRunsBadge: "En pause",
          }}
        />
        <WorkflowStudioHeaderBar
          workflow={INITIAL_WORKFLOWS_V2[0]!}
          viewMode="design"
          isFr={true}
          statusBanner={null}
          hasActiveAutonomyContract={false}
          autonomyButtonLabel="Autonomie"
          autonomyActiveBadgeLabel="Autonomie active"
          triggersButtonLabel="Déclencheurs"
          activeTriggersCount={0}
          onBackToHub={vi.fn()}
          onOpenParentVsm={vi.fn()}
          onSelectViewMode={vi.fn()}
          onSaveAsDraft={vi.fn()}
          onPublishWorkflow={vi.fn()}
          onOpenRunDrawer={vi.fn()}
          onOpenHelpSection={vi.fn()}
          onOpenAutonomyContract={vi.fn()}
          onOpenTriggers={vi.fn()}
        />
      </div>,
    );

    const thinkingText = screen.getByTestId("assistant-thinking-subwindow").textContent ?? "";
    expect(thinkingText).toContain("Synthèse prête");
    expect(thinkingText).toContain("Référent Technique");
    expect(thinkingText).toContain("Verrouillé");
    expect(thinkingText).toContain("Pause et escalade humaine");
    expect(thinkingText).toContain("Connexion déléguée (OAuth2)");
    expect(thinkingText).toContain("En attente");
    for (const raw of [
      "SYNTHESIS_READY",
      "TECH_LEAD",
      "IMMUTABLE",
      "PAUSE_AND_ESCALATE",
      "OAUTH2_PASSTHROUGH",
      "PENDING",
    ]) {
      expect(thinkingText).not.toContain(raw);
    }

    fireEvent.click(screen.getByTestId("trace-thought-toggle-btn"));
    const thoughtEl = screen.getByTestId("trace-thought-content");
    expect(thoughtEl.querySelector("strong")?.textContent).toBe("Point clé");
    expect(thoughtEl.style.borderLeft).toBe("");
    expect(screen.getByTestId("trace-event-check-ev-synth").textContent).toBe("Synthèse prête");

    expect(screen.getByTestId("cmdk-empty-results").textContent).toContain("Aucun résultat trouvé.");
    expect(screen.queryByTestId("cmdk-speed1-locked-group")).toBeNull();
    expect(screen.queryByTestId("cmdk-speed2-appended-group")).toBeNull();

    const alertIcon = screen.getByTestId("disabled-button-alert-icon-primary-disabled-action");
    expect(alertIcon.querySelector("svg")).toBeNull();
    expect(alertIcon.className).toContain("sr-only");

    expect(screen.getByTestId("finops-kpi-strip").className).toContain("xl:grid-cols-4");

    const versionBadges = screen.getAllByTestId("studio-workflow-version-badge");
    expect(versionBadges).toHaveLength(1);
    expect(versionBadges[0]?.textContent).not.toContain("(published)");
    expect(versionBadges[0]?.textContent).toContain("Actif · v");
  });
});
