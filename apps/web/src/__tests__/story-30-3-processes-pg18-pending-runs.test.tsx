// @vitest-environment jsdom
import { QueryClientProvider } from "@tanstack/react-query";
import { createMemoryHistory, RouterProvider } from "@tanstack/react-router";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import React from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { clearSavedActiveScopeId } from "../components/useShellContainerState";
import { I18nProvider } from "../i18n";
import { createOrciaQueryClient, createOrciaRouter } from "../router";
import { useAuthSessionStore } from "../stores/authSessionStore";
import { backendState } from "./setup/mockBackendState";
import {
  getRecordedVitestApiCalls,
  resetVitestApiBackend,
  seedVitestPlatformSetupState,
} from "./vitest.setup";

const WS_ID = "0195f000-0000-7000-8000-000000003031";

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
    llm_tiers: [
      {
        id: "llm-1",
        provider: "openai",
        model_id: "gpt-4o-mini",
        tier: "standard",
        enabled: true,
      },
    ],
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

async function mountProcessesRoute(locale: "fr" | "en" = "fr") {
  const queryClient = createOrciaQueryClient();
  const history = createMemoryHistory({ initialEntries: ["/processes"] });
  const router = createOrciaRouter({ queryClient, history });
  await router.load();
  return render(
    <I18nProvider initialLocale={locale}>
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={router} />
      </QueryClientProvider>
    </I18nProvider>,
  );
}

beforeEach(() => {
  resetVitestApiBackend();
  clearSavedActiveScopeId();
  seedAdminWorkspace();
});

afterEach(() => {
  cleanup();
  if (typeof window.localStorage?.removeItem === "function") {
    window.localStorage.removeItem("orcia.processes.active_run_workflow_id.v1");
  }
  vi.restoreAllMocks();
});

describe("Story 30.3 — Mes Processus real PG18 pending validations, zero sticky auto-launch & RFC 9457 error handling", () => {
  it("renders empty state on Day-0 (0 pending runs), ignores sticky localStorage auto-launch, and never hardcodes '1 validation en attente'", async () => {
    if (typeof window.localStorage?.setItem === "function") {
      window.localStorage.setItem(
        "orcia.processes.active_run_workflow_id.v1",
        "wf-generate-orcia-documentation",
      );
    }

    await mountProcessesRoute("fr");

    const card = await screen.findByTestId("processes-active-dossiers-card");
    expect(screen.getByTestId("processes-empty-pending-runs")).toBeDefined();
    expect(card.textContent ?? "").toContain("Aucune validation en attente");
    expect(card.textContent ?? "").not.toContain("1 validation en attente de votre décision");
    expect(screen.queryByTestId("resume-featured-dossier-btn")).toBeNull();
    expect(screen.queryByTestId("interactive-run-hitl-drawer")).toBeNull();

    const postRunCalls = getRecordedVitestApiCalls().filter(
      (c) => c.method === "POST" && c.path.includes("/runs"),
    );
    expect(postRunCalls).toHaveLength(0);
  });

  it("hydrates real PG18 pending runs with truthful status and opens drawer without duplicate POST", async () => {
    backendState.workflowV2Runs.set("run-real-303", {
      run_id: "run-real-303",
      workspace_id: WS_ID,
      workflow_id: "wf-01-qualification-prd",
      workflow_slug: "wf-01-qualification-prd",
      workflow_version: "1.0.0",
      orchestration_type: "deterministic_dbos",
      execution_mode: "native_orcia",
      status: "WAITING_FINAL_ANCHOR",
      iteration: 1,
      reentry_mode: "initial",
      current_sub_step_index: 2,
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

    await mountProcessesRoute("fr");

    const card = await screen.findByTestId("processes-active-dossiers-card");
    await waitFor(() => {
      const errBanner = screen.queryByTestId("processes-hub-error-banner");
      if (errBanner) {
        throw new Error(`Hub error banner shown: ${errBanner.textContent}`);
      }
      expect(card.textContent ?? "").not.toContain("Chargement");
      expect(screen.getByTestId("pending-run-row-run-real-303")).toBeDefined();
    });
    expect(screen.getByTestId("pending-run-status-run-real-303").textContent).toBe(
      "Validation finale requise",
    );

    fireEvent.click(screen.getByTestId("resume-featured-dossier-btn"));
    await waitFor(() => {
      expect(screen.getByTestId("interactive-run-hitl-drawer")).toBeDefined();
    });
    expect(screen.getByTestId("run-drawer-status-badge").textContent).toBe(
      "WAITING_FINAL_ANCHOR",
    );

    const postStarts = getRecordedVitestApiCalls().filter(
      (c) => c.method === "POST" && /\/api\/v1\/workflows\/v2\/.+\/runs$/.test(c.path),
    );
    expect(postStarts).toHaveLength(0);
  });

  it("shows localized RFC 9457 error alert when launching a run fails due to missing LLM/datasource", async () => {
    await mountProcessesRoute("fr");
    await screen.findByTestId("processes-active-dossiers-card");

    const origFetch = globalThis.fetch;
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
      const url = typeof input === "string" ? input : (input as Request).url;
      if (url.includes("/api/v1/workflows/v2/") && url.endsWith("/runs") && init?.method === "POST") {
        return new Response(
          JSON.stringify({
            type: "https://orcia.io/problems/process-datasources-required",
            title: "Sources de données requises",
            status: 422,
            detail: "Aucune source de données n'est attachée à cet espace.",
            error_code: "ERR_PROCESS_DATASOURCES_REQUIRED",
            trace_id: "0195f000000070008000000000000303",
          }),
          { status: 422, headers: { "Content-Type": "application/problem+json" } },
        );
      }
      return origFetch(input, init);
    });

    fireEvent.click(screen.getByTestId("execute-workflow-btn-wf-01-qualification-prd"));
    const banner = await screen.findByTestId("run-drawer-feedback-banner");
    expect(banner.getAttribute("role")).toBe("alert");
    expect(banner.textContent ?? "").toContain("Aucune source de données n'est attachée à cet espace.");
  });
});
