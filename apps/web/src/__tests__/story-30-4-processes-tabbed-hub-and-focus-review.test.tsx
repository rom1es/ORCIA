// @vitest-environment jsdom
import { QueryClientProvider } from "@tanstack/react-query";
import { createMemoryHistory, RouterProvider } from "@tanstack/react-router";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import React from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { clearSavedActiveScopeId } from "../components/useShellContainerState";
import { I18nProvider } from "../i18n";
import { createOrciaQueryClient, createOrciaRouter } from "../router";
import { useAuthSessionStore } from "../stores/authSessionStore";
import { backendState } from "./setup/mockBackendState";
import { resetVitestApiBackend, seedVitestPlatformSetupState } from "./vitest.setup";

const WS_ID = "0195f000-0000-7000-8000-000000003041";

function seedAdminWorkspace() {
  useAuthSessionStore.setState({
    isAuthenticated: true,
    isHydrating: false,
    accessToken: "mock-token",
    email: "admin@orcia.test",
    displayName: "Admin User",
    roles: ["PLATFORM_ADMIN"],
    activeHat: "ARCHITECT",
    readOnlyObserver: false,
    mustChangePassword: false,
  });
  seedVitestPlatformSetupState({
    org_units: [],
    rbac_grants: [],
    llm_tiers: [{ id: "llm-1", provider: "openai", model_id: "gpt-4o-mini", tier: "standard", enabled: true }],
    workspaces: [
      {
        workspaceId: WS_ID,
        name: "Espace Produit",
        visibilityMode: "STANDARD",
        ownerOrgUnitName: "Produit",
        lifecyclePhase: "BUILD",
        suggestedWorkflows: [],
        accessMode: "CONTRIBUTOR_ACTION_REQUIRED",
        finopsCostUsd: 0,
      },
    ],
    datasources: [],
    packs: [],
    workflows: [],
    runs: [],
    catalog_items: [],
    ontology_concepts: [],
  });
}

async function mountAt(path: string, locale: "fr" | "en" = "fr", widthPx = 1440) {
  Object.defineProperty(window, "innerWidth", { configurable: true, writable: true, value: widthPx });
  const queryClient = createOrciaQueryClient();
  const history = createMemoryHistory({ initialEntries: [path] });
  const router = createOrciaRouter({ queryClient, history });
  await router.load();
  const rendered = render(
    <I18nProvider initialLocale={locale}>
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={router} />
      </QueryClientProvider>
    </I18nProvider>,
  );
  return { ...rendered, router, history };
}

beforeEach(() => {
  resetVitestApiBackend();
  clearSavedActiveScopeId();
  seedAdminWorkspace();
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe("Story 30.4 — Mes Processus Tabbed Hub (UX30-09) & 3-Zone Focus Review (UX30-10)", () => {
  it("defaults /processes to Processus métiers without (0) badge when N===0 and purges Mon Compte from VSM in FR & EN", async () => {
    for (const locale of ["fr", "en"] as const) {
      const view = await mountAt("/processes", locale);
      await screen.findByTestId("processes-hub-tabs");

      expect(screen.queryByTestId("processes-tab-badge-validations")).toBeNull();
      expect(screen.getByTestId("processes-tab-catalog").getAttribute("aria-selected")).toBe("true");
      expect(screen.getByTestId("processes-tab-panel-catalog")).toBeDefined();
      expect(screen.queryByTestId("interactive-run-hitl-drawer")).toBeNull();

      fireEvent.click(screen.getByTestId("processes-tab-value-stream"));
      const vsmCard = await screen.findByTestId("processes-hub-vsm-hero-card");
      expect(vsmCard.textContent ?? "").not.toContain("Mon Compte");

      fireEvent.click(screen.getByTestId("processes-tab-validations"));
      expect(screen.getByTestId("processes-tab-panel-validations")).toBeDefined();
      expect(screen.queryByTestId("autonomous-supervision-error-banner")).toBeNull();
      view.unmount();
    }
  });

  it("defaults /processes to Validations & Exécutions (N) when N>0 and navigates to /processes/runs/$runId on open or launch", async () => {
    backendState.workflowV2Runs.set("run-304-pending", {
      run_id: "run-304-pending",
      workspace_id: WS_ID,
      workflow_id: "wf-01-qualification-prd",
      workflow_slug: "wf-01-qualification-prd",
      workflow_version: "1.0.0",
      orchestration_type: "deterministic_dbos",
      execution_mode: "native_orcia",
      status: "WAITING_SUBSTEP_HITL",
      iteration: 1,
      reentry_mode: "initial",
      current_sub_step_index: 0,
      inputs: {},
      mcp_context_bundle: null,
      sub_step_records: [],
      gate_report: null,
      final_artifact_pointer: null,
      reflexive_execution_id: null,
      trace_events: [],
      return_loop_target_step_num: null,
      return_loop_remarks: null,
      audit_trail: [],
    });

    const { router } = await mountAt("/processes", "fr");
    const badge = await screen.findByTestId("processes-tab-badge-validations");
    expect(badge.textContent).toBe("1");
    expect(screen.getByTestId("processes-tab-validations").getAttribute("aria-selected")).toBe("true");
    expect(screen.queryByTestId("interactive-run-hitl-drawer")).toBeNull();

    fireEvent.click(screen.getByTestId("resume-featured-dossier-btn"));
    await waitFor(() => {
      expect(router.state.location.pathname).toBe("/processes/runs/run-304-pending");
    });
    expect(await screen.findByTestId("process-run-focus-review-page")).toBeDefined();
  });

  it("renders 3-zone Focus Review on Desktop, single Cobalt CTA, hidden correction popover, defaultCollapsedWhenCompleted trace & F5 survival", async () => {
    backendState.workflowV2Runs.set("run-304-focus", {
      run_id: "run-304-focus",
      workspace_id: WS_ID,
      workflow_id: "wf-01-qualification-prd",
      workflow_slug: "wf-01-qualification-prd",
      workflow_version: "1.0.0",
      orchestration_type: "deterministic_dbos",
      execution_mode: "native_orcia",
      status: "WAITING_SUBSTEP_HITL",
      iteration: 1,
      reentry_mode: "initial",
      current_sub_step_index: 0,
      inputs: {},
      mcp_context_bundle: null,
      sub_step_records: [],
      gate_report: null,
      final_artifact_pointer: null,
      reflexive_execution_id: null,
      trace_events: [
        {
          event_id: "ev-1",
          seq: 1,
          kind: "THOUGHT_DELTA",
          phase: "Analyse",
          label: "Analyse du besoin",
          detail: "Synthèse prête pour revue.",
          actor_slug: "orchestrateur-produit",
          ts_iso: "2026-11-26T08:00:00Z",
        },
      ],
      return_loop_target_step_num: null,
      return_loop_remarks: null,
      audit_trail: [],
    });

    const first = await mountAt("/processes/runs/run-304-focus", "fr", 1440);
    const page = await screen.findByTestId("process-run-focus-review-page");
    await waitFor(() => {
      expect(screen.getByTestId("run-drawer-status-badge").textContent).toBe("WAITING_SUBSTEP_HITL");
    });

    expect(screen.getByTestId("focus-review-split-layout")).toBeDefined();
    expect(screen.getByTestId("focus-review-zone2-artifact")).toBeDefined();
    expect(screen.getByTestId("focus-review-zone3-reasoning")).toBeDefined();

    // Strictly 1 primary Cobalt CTA (substep approval), zero duplicate Bar 2 CTA or Edit button in Zone 1
    expect(page.querySelectorAll(".orcia-ds-btn-primary")).toHaveLength(1);
    expect(screen.getByTestId("approve-substep-checkpoint-btn")).toBeDefined();
    expect(screen.queryByTestId("anchor-action-1-accept-btn")).toBeNull();
    expect(screen.queryByTestId("open-amend-diff-editor-btn")).toBeNull();
    expect(screen.queryByTestId("anchor-action-2-amend-diff-btn")).toBeNull();
    expect(screen.queryByTestId("human-anchor-card-qualification")).toBeNull();

    // Progressive disclosure: correction inputs hidden until clicked
    expect(screen.queryByTestId("request-corrections-popover")).toBeNull();
    fireEvent.click(screen.getByTestId("toggle-request-corrections-popover-btn"));
    expect(screen.getByTestId("request-corrections-popover")).toBeDefined();
    expect(screen.getByTestId("anchor-return-loop-target-select")).toBeDefined();
    expect(screen.getByTestId("anchor-return-loop-remarks-input")).toBeDefined();

    // Single Preview / Edit toggle in Zone 2
    expect(screen.getByTestId("artifact-markdown-preview")).toBeDefined();
    fireEvent.click(screen.getByTestId("artifact-mode-edit-btn"));
    expect(screen.getByTestId("amend-diff-markdown-textarea")).toBeDefined();
    fireEvent.click(screen.getByTestId("cancel-amend-diff-btn"));
    expect(screen.getByTestId("artifact-markdown-preview")).toBeDefined();

    // AgentExecutionTrace collapsed when waiting/completed
    const traceHeaderBtn = await screen.findByTestId("trace-group-header-btn");
    expect(traceHeaderBtn.getAttribute("aria-expanded")).toBe("false");

    // Cold F5 reload survival
    first.unmount();
    const second = await mountAt("/processes/runs/run-304-focus", "en", 1024);
    await screen.findByTestId("focus-review-compact-layout");
    expect(screen.getByTestId("focus-compact-tab-artifact")).toBeDefined();
    expect(screen.getByTestId("focus-compact-tab-reasoning")).toBeDefined();
    fireEvent.click(screen.getByTestId("focus-compact-tab-reasoning"));
    expect(screen.getByTestId("process-run-reasoning-rail")).toBeDefined();
    second.unmount();
  });

  it("auto-expands AgentExecutionTrace when RUNNING and reserves HumanLedAnchorCard strictly for human_authored_required workflows", async () => {
    backendState.workflowV2Runs.set("run-304-running", {
      run_id: "run-304-running",
      workspace_id: WS_ID,
      workflow_id: "wf-01-qualification-prd",
      workflow_slug: "wf-01-qualification-prd",
      workflow_version: "1.0.0",
      orchestration_type: "non_deterministic",
      execution_mode: "native_orcia",
      status: "RUNNING",
      iteration: 1,
      reentry_mode: "initial",
      current_sub_step_index: 0,
      inputs: {},
      mcp_context_bundle: null,
      sub_step_records: [],
      gate_report: null,
      final_artifact_pointer: null,
      reflexive_execution_id: null,
      trace_events: [
        {
          event_id: "ev-live-1",
          seq: 1,
          kind: "THOUGHT_DELTA",
          phase: "Analyse",
          label: "Exploration",
          detail: "Analyse en cours",
          actor_slug: "assistant",
          ts_iso: "2026-11-26T08:05:00Z",
        },
      ],
      return_loop_target_step_num: null,
      return_loop_remarks: null,
      audit_trail: [],
    });

    const runningView = await mountAt("/processes/runs/run-304-running", "fr", 1440);
    const traceBtn = await screen.findByTestId("trace-group-header-btn");
    expect(traceBtn.getAttribute("aria-expanded")).toBe("true");
    expect(screen.queryByTestId("human-anchor-card-wf-01-qualification-prd")).toBeNull();
    runningView.unmount();

    const { ProcessRunActionBanner } = await import(
      "../features/processes/execution/ProcessRunActionBanner"
    );
    const { frDictionary } = await import("../i18n/locales/fr");
    const anchorView = render(
      <ProcessRunActionBanner
        workflow={{
          id: "wf-human-anchor-304",
          slug: "wf-human-anchor-304",
          title: "Décision souveraine",
          pack_id: "sdlc",
          version: "1.0.0",
          status: "published",
          execution_mode: "native_orcia",
          human_authored_required: true,
          agent_ref: "@assistant",
          skills_refs: [],
          knowledge_base_refs: [],
          triggers: [],
          contract: { inputs: [], outputs: [], exit_criteria: [] },
          sub_steps: [],
          controls: { deterministic_gates: [], probabilistic_evaluations: [] },
          guardrails: [],
        }}
        isFr={true}
        status="WAITING_FINAL_ANCHOR"
        statusLabel="Validation finale requise"
        currentSubStep={undefined}
        iteration={1}
        reentryMode="initial"
        signedTokenPreview={null}
        returnLoopTargetStep="02"
        returnLoopRemarks=""
        humanAnchorLabels={frDictionary.humanAnchor}
        onSimulateExternalWebhook={vi.fn()}
        onApproveCurrentSubStep={vi.fn()}
        onAction1AcceptAndSign={vi.fn()}
        onAction3RejectAndLoop={vi.fn()}
        onAction4SuspendSla={vi.fn()}
        onChangeReturnLoopTarget={vi.fn()}
        onChangeReturnLoopRemarks={vi.fn()}
      />,
    );
    expect(screen.getByTestId("human-anchor-card-wf-human-anchor-304")).toBeDefined();
    anchorView.unmount();
  });
});
