// @vitest-environment jsdom
import { QueryClientProvider } from "@tanstack/react-query";
import { createMemoryHistory, RouterProvider } from "@tanstack/react-router";
import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import React from "react";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { resetPersistedWorkflowsV2 } from "../features/processes/processStudioV2Data";
import { I18nProvider } from "../i18n";
import { createOrciaQueryClient, createOrciaRouter } from "../router";
import { seedVitestPlatformSetupState } from "./vitest.setup";

describe("Epics 14 & 15 — ORCIA Process Studio v2, Interactive VSM & Declarative Packs (TASK-06, TASK-07, TASK-08)", () => {
  beforeEach(() => {
    resetPersistedWorkflowsV2();
    seedVitestPlatformSetupState({});
  });

  afterEach(() => {
    cleanup();
  });

  it("TASK-06: renders PacksRegistryPage (/settings/packs) with connector healthchecks and .zip workspace export", async () => {
    const queryClient = createOrciaQueryClient();
    const history = createMemoryHistory({ initialEntries: ["/settings/packs"] });
    const router = createOrciaRouter({ queryClient, history });
    await router.load();

    render(
      <I18nProvider initialLocale="fr">
        <QueryClientProvider client={queryClient}>
          <RouterProvider router={router} />
        </QueryClientProvider>
      </I18nProvider>,
    );

    expect(screen.getByTestId("packs-registry-v2-page")).toBeDefined();
    expect(screen.getByTestId("declarative-pack-card-sdlc")).toBeDefined();
    expect(screen.getByTestId("declarative-pack-card-orcia-docs")).toBeDefined();

    // Refresh MCP connector healthchecks
    fireEvent.click(screen.getByTestId("refresh-pack-connectors-health-btn"));
    expect(screen.getByTestId("packs-registry-status-banner").textContent).toContain(
      "Diagnostics de santé MCP",
    );

    // Export workspace as .zip declarative pack
    fireEvent.click(screen.getByTestId("export-workspace-pack-zip-btn"));
    expect(screen.getByTestId("exported-pack-zip-filename").textContent).toContain(
      "sdlc-ws-mon-compte.zip",
    );
  });

  it("TASK-06 & TASK-07: navigates from ProcessesHubPage (/processes) to Interactive 11-Step VSM (/processes/vsm/$vsmId) and inspects the 6-tab StepDetailSheet", async () => {
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

    expect(screen.getByTestId("processes-hub-v2-page")).toBeDefined();
    expect(screen.getByTestId("processes-hub-vsm-hero-card")).toBeDefined();
    expect(screen.getByTestId("bounded-workflow-card-wf-01-qualification-prd")).toBeDefined();
    expect(screen.getByTestId("bounded-workflow-card-wf-08-dev-external-gate")).toBeDefined();

    // Filter by External Delegated Gate
    fireEvent.click(screen.getByTestId("workflows-hub-filter-external_delegated"));
    expect(screen.getByTestId("bounded-workflow-card-wf-08-dev-external-gate")).toBeDefined();
    fireEvent.click(screen.getByTestId("workflows-hub-filter-all"));

    // Navigate to Interactive VSM (/processes/vsm/vsm-mon-compte-idea-to-prod)
    await act(async () => {
      fireEvent.click(screen.getByTestId("open-interactive-vsm-btn"));
    });

    expect(screen.getByTestId("vsm-interactive-view")).toBeDefined();
    expect(screen.getByTestId("vsm-knowledge-base-banner")).toBeDefined();
    expect(screen.getByTestId("vsm-return-loops-svg-overlay")).toBeDefined();

    // Verify all 11 steps are rendered
    for (let i = 1; i <= 11; i += 1) {
      const num = String(i).padStart(2, "0");
      expect(screen.getByTestId(`vsm-step-card-${num}`)).toBeDefined();
    }

    // Switch VSM comparison modes: Today -> Tomorrow -> Compare
    fireEvent.click(screen.getByTestId("vsm-mode-today"));
    expect(screen.getByTestId("vsm-step-01-today-box")).toBeDefined();
    fireEvent.click(screen.getByTestId("vsm-mode-tomorrow"));
    expect(screen.getByTestId("vsm-step-01-tomorrow-box")).toBeDefined();
    fireEvent.click(screen.getByTestId("vsm-mode-compare"));

    // Open Opportunities drawer (P1, P2, P3)
    fireEvent.click(screen.getByTestId("vsm-toggle-opportunities-drawer-btn"));
    expect(screen.getByTestId("vsm-opportunities-drawer")).toBeDefined();

    // Open 6-tab detail sheet for Step 02 ("En revue") and cycle through all 6 tabs
    fireEvent.click(screen.getByTestId("open-step-sheet-btn-02"));
    expect(screen.getByTestId("vsm-step-detail-sheet-02")).toBeDefined();
    expect(screen.getByTestId("step-sheet-panel-overview")).toBeDefined();

    fireEvent.click(screen.getByTestId("step-sheet-tab-agent_substeps"));
    expect(screen.getByTestId("step-sheet-panel-agent_substeps")).toBeDefined();

    fireEvent.click(screen.getByTestId("step-sheet-tab-interactions"));
    expect(screen.getByTestId("step-sheet-panel-interactions")).toBeDefined();

    fireEvent.click(screen.getByTestId("step-sheet-tab-controls_gates"));
    expect(screen.getByTestId("step-sheet-panel-controls_gates")).toBeDefined();

    fireEvent.click(screen.getByTestId("step-sheet-tab-return_loops"));
    expect(screen.getByTestId("step-sheet-panel-return_loops")).toBeDefined();

    fireEvent.click(screen.getByTestId("step-sheet-tab-opportunities"));
    expect(screen.getByTestId("step-sheet-panel-opportunities")).toBeDefined();
  });

  it("TASK-08: renders 5-Block Workflow Studio (/processes/studio/$workflowId), auto-forks as -draft on edit, survives F5 reload, and executes 4-action HITL Anchor Card with S3 Claim-Check & cyclic return loop (:iter-2)", async () => {
    const queryClient = createOrciaQueryClient();
    const history = createMemoryHistory({
      initialEntries: ["/processes/studio/wf-01-qualification-prd"],
    });
    const router = createOrciaRouter({ queryClient, history });
    await router.load();

    const firstRender = render(
      <I18nProvider initialLocale="fr">
        <QueryClientProvider client={queryClient}>
          <RouterProvider router={router} />
        </QueryClientProvider>
      </I18nProvider>,
    );

    // Verify all 5 Control-M blocks and Copilot sidebar
    expect(screen.getByTestId("workflow-five-blocks-studio-page")).toBeDefined();
    expect(screen.getByTestId("studio-copilot-sidebar")).toBeDefined();
    expect(screen.getByTestId("studio-block-1-triggers-contract")).toBeDefined();
    expect(screen.getByTestId("studio-block-2-deterministic-substeps")).toBeDefined();
    expect(screen.getByTestId("studio-block-3-mcp-toolboxes")).toBeDefined();
    expect(screen.getByTestId("studio-block-4-skills-knowledge")).toBeDefined();
    expect(screen.getByTestId("studio-block-5-gates-pipeline")).toBeDefined();

    // Initially published v1.0.0
    expect(screen.getByTestId("studio-workflow-version-badge").textContent).toContain(
      "v1.0.0 (published)",
    );

    // Toggle sub-step 'jira' -> auto-forks into v1.0.0-draft (draft)
    fireEvent.click(screen.getByTestId("toggle-substep-enabled-jira"));
    expect(screen.getByTestId("studio-workflow-version-badge").textContent).toContain(
      "v1.0.0-draft (draft)",
    );

    // Gate 3: Unmount and re-render to prove F5 reload survival
    firstRender.unmount();

    const secondQueryClient = createOrciaQueryClient();
    const secondHistory = createMemoryHistory({
      initialEntries: ["/processes/studio/wf-01-qualification-prd"],
    });
    const secondRouter = createOrciaRouter({
      queryClient: secondQueryClient,
      history: secondHistory,
    });
    await secondRouter.load();

    render(
      <I18nProvider initialLocale="fr">
        <QueryClientProvider client={secondQueryClient}>
          <RouterProvider router={secondRouter} />
        </QueryClientProvider>
      </I18nProvider>,
    );

    expect(screen.getByTestId("studio-workflow-version-badge").textContent).toContain(
      "v1.0.0-draft (draft)",
    );

    // Run isolated What-If simulation -> 2 enabled sub-steps evaluated, 0 external writes
    fireEvent.click(screen.getByTestId("studio-view-mode-what_if"));
    expect(screen.getByTestId("studio-what-if-sandbox-panel")).toBeDefined();
    expect(screen.getByTestId("what-if-substeps-count").textContent).toBe("2");
    expect(screen.getByTestId("what-if-external-writes-count").textContent).toContain("0");

    // Launch Interactive DBOS Run & HITL Drawer
    fireEvent.click(screen.getByTestId("studio-launch-interactive-run-btn"));
    expect(screen.getByTestId("interactive-run-hitl-drawer")).toBeDefined();
    expect(screen.getByTestId("run-drawer-idempotency-key").textContent).toContain(
      ":qualification:iter-1",
    );
    const initialSha = screen.getByTestId("claim-check-sha256").textContent;

    // Action 2: Amend Diff in S3 -> recomputes SHA-256
    fireEvent.click(screen.getByTestId("anchor-action-2-amend-diff-btn"));
    fireEvent.change(screen.getByTestId("amend-diff-markdown-textarea"), {
      target: {
        value: "# Qualification & PRD Amendé par le PO\n\nHypothèse de gain WSJF confirmée (+30%).",
      },
    });
    fireEvent.click(screen.getByTestId("confirm-amend-diff-btn"));
    expect(screen.getByTestId("claim-check-sha256").textContent).not.toBe(initialSha);

    // Action 3: Reject & Trigger Return Loop -> re-enters in 'corrections' mode at iter-2
    fireEvent.click(screen.getByTestId("anchor-action-3-reject-loop-btn"));
    expect(screen.getByTestId("run-drawer-reentry-mode").textContent).toContain(
      "mode: corrections (iter-2)",
    );
    expect(screen.getByTestId("run-drawer-idempotency-key").textContent).toContain(":iter-2");

    // Action 1: Accept & Sign Final Anchor Card
    fireEvent.click(screen.getByTestId("anchor-action-1-accept-btn"));
    expect(screen.getByTestId("run-drawer-status-badge").textContent).toBe("COMPLETED_APPROVED");
  });
});
