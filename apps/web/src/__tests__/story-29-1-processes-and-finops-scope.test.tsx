import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import React from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ShellContainer } from "../components/ShellContainer";
import { clearSavedActiveScopeId } from "../components/useShellContainerState";
import { FinopsFeaturePanel } from "../features/finops";
import { AutonomousRunsSupervisionPanel } from "../features/processes/AutonomousRunsSupervisionPanel";
import { I18nProvider } from "../i18n";
import { formatRfc9457ErrorToBanner } from "../lib/formatRfc9457ErrorToBanner";
import { useAuthSessionStore } from "../stores/authSessionStore";
import { seedVitestPlatformSetupState } from "./vitest.setup";
import { seedVitestAutonomousSupervisionRuns } from "./vitestAutonomousSupervisionMockHandlers";

const BU_ID = "0195f000-0000-7000-8000-00000000a001";
const TEAM_ID = "0195f000-0000-7000-8000-00000000a002";
const WS_ID = "0195f000-0000-7000-8000-00000000a003";
const RUN_ID = "0195f000-0000-7000-8000-00000000a004";
const PERSONAL_WS_ID = "0195f000-0000-7000-8000-00000000a099";

function seedTopology(role: string, workspacesOverride?: Array<Record<string, unknown>>) {
  useAuthSessionStore.setState({
    isAuthenticated: true,
    isHydrating: false,
    accessToken: "mock-token",
    email: "user@orcia.test",
    displayName: "Test User",
    roles: [role],
    activeHat: role,
    readOnlyObserver: false,
    mustChangePassword: false,
  });
  seedVitestPlatformSetupState({
    org_units: [
      { id: BU_ID, name: "Division Produit", slug: "bu-prod", level: "BU", parent_id: null },
      { id: TEAM_ID, name: "Équipe Rouge Gorge", slug: "team-rg", level: "TEAM", parent_id: BU_ID },
    ],
    rbac_grants: [],
    llm_tiers: [],
    workspaces: (workspacesOverride as never) ?? [
      {
        workspaceId: WS_ID,
        name: "Espace Rouge Gorge",
        visibilityMode: "STANDARD",
        ownerOrgUnitId: TEAM_ID,
        ownerOrgUnitName: "Équipe Rouge Gorge",
        lifecyclePhase: "RUN",
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

describe("Story 29.1 — Multi-Workspace Processes Supervision & FinOps RBAC Scope Sync", () => {
  afterEach(() => {
    cleanup();
    clearSavedActiveScopeId();
    vi.restoreAllMocks();
  });

  it("calls multi-workspace GET /api/v1/autonomous-runs under scope-global or synthetic ws-* without 404, and hides empty text on error", async () => {
    seedTopology("TEAM_LEAD", [
      {
        workspaceId: "ws-1",
        name: "Espace Synthétique",
        visibilityMode: "STANDARD",
        ownerOrgUnitId: TEAM_ID,
        lifecyclePhase: "RUN",
        suggestedWorkflows: [],
        accessMode: "CONTRIBUTOR_ACTION_REQUIRED",
        finopsCostUsd: 0,
      },
    ]);
    seedVitestAutonomousSupervisionRuns([
      {
        run_id: RUN_ID,
        workspace_id: WS_ID,
        workflow_id: "orcia://workflows/sync",
        workflow_title: "Synchronisation contrat",
        trigger_id: null,
        trigger_label: "Manuel",
        trigger_type: "MANUAL_AUTONOMOUS",
        trigger_status: "ACTIVE",
        run_status: "RUNNING",
        post_hoc_status: "NONE",
        contract_id: "c-1",
        cost_usd: 0.05,
        created_at_iso: "2026-11-24T10:00:00Z",
      },
    ]);

    const seenUrls: string[] = [];
    const origFetch = globalThis.fetch;
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
      const url = typeof input === "string" ? input : (input as Request).url;
      seenUrls.push(url);
      return origFetch(input, init);
    });

    render(
      <I18nProvider initialLocale="fr">
        <ShellContainer>
          <AutonomousRunsSupervisionPanel />
        </ShellContainer>
      </I18nProvider>,
    );

    await waitFor(() => {
      expect(screen.getByTestId(`autonomous-supervised-run-${RUN_ID}`)).toBeDefined();
    });
    expect(seenUrls.some((u) => u.includes("/api/v1/autonomous-runs"))).toBe(true);
    expect(seenUrls.some((u) => u.includes("/api/v1/workspaces/scope-global/autonomous-runs"))).toBe(false);
    expect(seenUrls.some((u) => u.includes("/api/v1/workspaces/ws-1/autonomous-runs"))).toBe(false);

    cleanup();
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
      const url = typeof input === "string" ? input : (input as Request).url;
      if (url.includes("/api/v1/autonomous-runs")) {
        return new Response(
          JSON.stringify({ error_code: "ERR_SCOPE_ACCESS_DENIED", detail: "Forbidden", status: 403 }),
          { status: 403, headers: { "Content-Type": "application/problem+json" } },
        );
      }
      return origFetch(input, init);
    });

    render(
      <I18nProvider initialLocale="fr">
        <ShellContainer>
          <AutonomousRunsSupervisionPanel />
        </ShellContainer>
      </I18nProvider>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("autonomous-supervision-error-banner")).toBeDefined();
    });
    expect(screen.queryByTestId("processes-autonomous-supervision-empty")).toBeNull();
  });

  it("auto-defaults TEAM_LEAD under scope-global to TEAM, hides Plateforme entière, keeps 1 selected pill, and hides empty notice on error", async () => {
    seedTopology("TEAM_LEAD");
    const finopsUrls: string[] = [];
    const origFetch = globalThis.fetch;
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
      const url = typeof input === "string" ? input : (input as Request).url;
      if (url.includes("/api/v1/finops/")) {
        finopsUrls.push(url);
      }
      return origFetch(input, init);
    });

    render(
      <I18nProvider initialLocale="fr">
        <ShellContainer>
          <FinopsFeaturePanel />
        </ShellContainer>
      </I18nProvider>,
    );

    const selector = await screen.findByTestId("sidebar-workspace-selector");
    finopsUrls.length = 0;
    fireEvent.change(selector, { target: { value: "scope-global" } });

    await waitFor(() => {
      expect(finopsUrls.some((u) => u.includes("scope_type=TEAM"))).toBe(true);
    });
    expect(finopsUrls.some((u) => u.includes("scope_type=GLOBAL"))).toBe(false);
    expect(screen.queryByTestId("finops-scope-global")).toBeNull();
    expect(screen.getByTestId("finops-scope-team").getAttribute("aria-selected")).toBe("true");
    expect(screen.getByTestId("finops-scope-workspace").getAttribute("aria-selected")).toBe("false");

    cleanup();
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
      const url = typeof input === "string" ? input : (input as Request).url;
      if (url.includes("/api/v1/finops/dashboard")) {
        return new Response(
          JSON.stringify({ error_code: "ERR_SCOPE_ACCESS_DENIED", detail: "Denied", status: 403 }),
          { status: 403, headers: { "Content-Type": "application/problem+json" } },
        );
      }
      return origFetch(input, init);
    });

    render(
      <I18nProvider initialLocale="fr">
        <ShellContainer>
          <FinopsFeaturePanel />
        </ShellContainer>
      </I18nProvider>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("finops-error-banner")).toBeDefined();
    });
    expect(screen.queryByTestId("finops-empty-state")).toBeNull();
  });

  it("auto-defaults BU_DIRECTOR under scope-global to BU with Team/Division pill selected and provides accurate FR/EN 403 guidance", async () => {
    seedTopology("BU_DIRECTOR");
    const finopsUrls: string[] = [];
    const origFetch = globalThis.fetch;
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
      const url = typeof input === "string" ? input : (input as Request).url;
      if (url.includes("/api/v1/finops/")) {
        finopsUrls.push(url);
      }
      return origFetch(input, init);
    });

    render(
      <I18nProvider initialLocale="fr">
        <ShellContainer>
          <FinopsFeaturePanel />
        </ShellContainer>
      </I18nProvider>,
    );

    const selector = await screen.findByTestId("sidebar-workspace-selector");
    finopsUrls.length = 0;
    fireEvent.change(selector, { target: { value: "scope-global" } });

    await waitFor(() => {
      expect(finopsUrls.some((u) => u.includes("scope_type=BU"))).toBe(true);
    });
    expect(screen.queryByTestId("finops-scope-global")).toBeNull();
    expect(screen.getByTestId("finops-scope-team").getAttribute("aria-selected")).toBe("true");

    const frBanner = formatRfc9457ErrorToBanner(
      { error_code: "ERR_SCOPE_ACCESS_DENIED", status: 403 },
      "fr",
    );
    const enBanner = formatRfc9457ErrorToBanner(
      { error_code: "ERR_SCOPE_ACCESS_DENIED", status: 403 },
      "en",
    );
    expect(frBanner.remediation).not.toContain("Mon Organisation");
    expect(enBanner.remediation).not.toContain("My Organization");
  });

  it("does not send guessed PRIVATE_USER personal workspace_id on post-hoc review under scope-global", async () => {
    seedTopology("PLATFORM_ADMIN", [
      { workspaceId: PERSONAL_WS_ID, name: "Mon Espace Personnel", visibilityMode: "PRIVATE_USER", ownerUserId: "user@orcia.test", lifecyclePhase: "RUN", suggestedWorkflows: [], accessMode: "CONTRIBUTOR_ACTION_REQUIRED", finopsCostUsd: 0 },
      { workspaceId: WS_ID, name: "Espace Autonome E2E", visibilityMode: "STANDARD", ownerOrgUnitId: TEAM_ID, lifecyclePhase: "RUN", suggestedWorkflows: [], accessMode: "CONTRIBUTOR_ACTION_REQUIRED", finopsCostUsd: 0 },
    ]);
    const postedBodies: Array<Record<string, unknown>> = [];
    const origFetch = globalThis.fetch;
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
      const url = typeof input === "string" ? input : (input as Request).url;
      if (url.includes("/api/v1/finops/cognitive-impact")) {
        return new Response(JSON.stringify({
          scope_type: "GLOBAL", scope_id: null, active_framing_ratio: 0.9, active_framing_target: 0.4, active_framing_alert: false,
          quick_pass_rate: 0.02, quick_pass_threshold: 0.05, quick_pass_alert: false, architecture_deviation_index: 0, architecture_deviation_target: 0,
          architecture_deviation_alert: false, pattern_drift_index: 0, pattern_drift_alert: false, total_human_hours: 2, active_framing_hours: 1.5,
          review_hours: 0.5, uncovered_deviations_count: 0, workflow_breakdowns: [], recommendations: [],
          autonomous_governance: {
            total_autonomous_runs: 1, escalated_runs_count: 0, killed_runs_count: 0, sampled_runs_count: 1, pending_samples_count: 1,
            invalidated_samples_count: 0, autonomous_escalation_rate: 0, post_hoc_invalidation_rate: 0, invalidation_alert: false,
            avg_autonomous_cost_usd: 0.1, avg_ttm_gain_minutes: 10,
            pending_samples: [{ id: "smp-e2e-1", run_id: RUN_ID, workspace_id: WS_ID, workflow_title: "Qualification PRD", trigger_label: "Manuel", review_status: "PENDING_SAMPLE", run_status: "COMMITTED_AUTONOMOUS", sampled_at: "2026-11-24T10:00:00Z" }],
          },
          trace_id: "0195f000000070008000000000002901",
        }), { status: 200, headers: { "Content-Type": "application/json" } });
      }
      if (url.includes(`/api/v1/runs/${RUN_ID}/post-hoc-review`)) {
        postedBodies.push(JSON.parse(String(init?.body ?? "{}")) as Record<string, unknown>);
        return new Response(JSON.stringify({ run_id: RUN_ID, review_status: "INVALIDATED_ROLLED_BACK", run_status: "ROLLED_BACK", restored_version: "1.0.0", trace_id: "0195f000000070008000000000002902" }), { status: 200, headers: { "Content-Type": "application/json" } });
      }
      return origFetch(input, init);
    });
    render(<I18nProvider initialLocale="fr"><ShellContainer><FinopsFeaturePanel /></ShellContainer></I18nProvider>);
    fireEvent.change(await screen.findByTestId("sidebar-workspace-selector"), { target: { value: "scope-global" } });
    fireEvent.click(await screen.findByTestId("finops-tab-cognitive-governance"));
    fireEvent.click(await screen.findByTestId(`finops-sample-restore-btn-${RUN_ID}`));
    await waitFor(() => expect(postedBodies.length).toBe(1));
    expect(postedBodies[0]?.workspace_id).not.toBe(PERSONAL_WS_ID);
    expect(postedBodies[0]?.workspace_id).toBe(WS_ID);
  });
});
