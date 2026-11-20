import { QueryClientProvider } from "@tanstack/react-query";
import { createMemoryHistory, RouterProvider } from "@tanstack/react-router";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import React from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { mapApiVsmToUiSpec } from "../features/processes/vsm/mapApiVsmToUiSpec";
import { INITIAL_VSM_SPEC } from "../features/processes/processStudioV2Data";
import { I18nProvider } from "../i18n";
import { createOrciaQueryClient, createOrciaRouter } from "../router";
import { useAuthSessionStore } from "../stores/authSessionStore";
import { seedVitestPlatformSetupState } from "./vitest.setup";

const WS_ID = "0192c4e0-0000-7000-8000-000000000201";

function seedAuthenticatedUser() {
  useAuthSessionStore.setState({
    isAuthenticated: true,
    isHydrating: false,
    accessToken: "mock-token-lead",
    email: "lead@orcia.local",
    displayName: "Lead Architecture",
    roles: ["TEAM_LEAD", "PLATFORM_ADMIN"],
    activeHat: "Tech Lead",
    readOnlyObserver: false,
    mustChangePassword: false,
  });
  seedVitestPlatformSetupState({
    org_units: [
      { id: "org-root", name: "Entreprise", slug: "entreprise", level_kind: "BU", parent_id: null },
    ],
    rbac_grants: [],
    llm_tiers: [],
    workspaces: [
      {
        workspaceId: WS_ID,
        name: "Espace Gates & VSM",
        visibilityMode: "STANDARD",
        ownerOrgUnitName: "Equipe Architecture",
        lifecyclePhase: "BUILD",
        suggestedWorkflows: [],
        accessMode: "CONTRIBUTOR_ACTION_REQUIRED",
        finopsCostUsd: 0.0,
      },
    ],
    datasources: [],
    packs: [],
    workflows: [],
    runs: [],
    catalog_items: [],
    ontology_concepts: [],
    audit_events: [],
  });
}

function jsonRes(payload: unknown, status = 200): Response {
  return new Response(JSON.stringify(payload), {
    status,
    headers: {
      "Content-Type": status >= 400 ? "application/problem+json" : "application/json",
    },
  });
}

describe("Story 24.1 — GatesAdaptiveHumanReviewSection & ValueStreamMapView PG18 hydration", () => {
  let restoreFetch: (() => void) | null = null;

  afterEach(() => {
    restoreFetch?.();
    restoreFetch = null;
    cleanup();
  });

  it("maps ApiValueStreamMapSpec fields cleanly in mapApiVsmToUiSpec", () => {
    const mapped = mapApiVsmToUiSpec(
      {
        id: "vsm-pg18-custom",
        slug: "vsm-pg18-custom",
        title: "Chaîne PG18 Hydratée",
        subtitle: "De l'Idée à la Production PG18",
        source_note: "PG18",
        guiding_principle: "Zero RAM",
        tools_note: "",
        pack_id: "sdlc",
        knowledge_foundation: {
          title: "Socle Confluence PG18",
          summary: "Base documentaire synchronisée",
        },
        phases: [{ num: "01", id: "phase-1", label: "Cadrage PG18", subtitle: "Qualif" }],
        opportunities: {},
        agents_catalog: {},
        nodes: [
          {
            node_type: "step",
            num: "01",
            phase_id: "phase-1",
            title: "Qualification PRD PG18",
            linked_workflow_id: "wf-01-qualification-prd",
            input_actuel: "In",
            input_ia: "In IA",
            output_actuel: "PRD Legacy",
            output_ia: "PRD PG18 Certifié",
            actor_actuel: "PM Humain",
            actor_ia: "PM + Agent Qualif",
            validation_actuel: "Manuelle",
            validation_ia: "Tri-modale",
          },
        ],
      },
      INITIAL_VSM_SPEC,
    );

    expect(mapped.id).toBe("vsm-pg18-custom");
    expect(mapped.title).toBe("Chaîne PG18 Hydratée");
    expect(mapped.knowledge_base.title).toBe("Socle Confluence PG18");
    expect(mapped.phases[0]?.name).toBe("Cadrage PG18");
    expect(mapped.phases[0]?.steps[0]?.title).toBe("Qualification PRD PG18");
    expect(mapped.phases[0]?.steps[0]?.tomorrow.deliverable).toBe("PRD PG18 Certifié");
    // Unmapped step keeps baseline spec
    expect(mapped.phases[0]?.steps[1]?.num).toBe("02");
  });

  it("rehydrates GatesAdaptiveHumanReviewSection via GET with PASS & EXECUTED badges on /gates", async () => {
    seedAuthenticatedUser();
    const originalFetch = globalThis.fetch;
    const spy = vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
      const url = typeof input === "string" ? input : input instanceof Request ? input.url : String(input);
      const path = new URL(url, "http://localhost").pathname;
      const method = (init?.method ?? "GET").toUpperCase();

      if (path === "/api/v1/gates/human/evaluations" && method === "GET") {
        return jsonRes({
          evaluations: [
            {
              id: "0195f000-0000-7000-8000-00000000e101",
              workspace_id: WS_ID,
              run_id: "0195f000-0000-7000-8000-000000000701",
              step_execution_id: "0195f000-0000-7000-8000-000000000801",
              step_key: "step-architecture-gate",
              gate_type: "HUMAN",
              status: "PASS",
              policy: "mandatory_full",
              total_word_count: 1450,
              review_duration_ms: 19200,
              hypotheses_block_inspected: true,
              explicit_hypotheses_confirmation: true,
              ontology_conflicts: 0,
              stale_warnings: 0,
              briefing_4blocks_jsonb: {
                block_1_executive_summary: { summary: "Synthèse rechargée depuis PG18." },
                block_3_decisions_taken: { decisions: ["Décision D1 PG18"] },
                block_4_retained_hypotheses: { hypotheses: ["Hypothèse H1 PG18"] },
              },
              chunks: [],
            },
          ],
          trace_id: "0195f000000070008000000000000111",
        });
      }
      if (path === "/api/v1/jira/actions/staged" && method === "GET") {
        return jsonRes({
          actions: [
            {
              staged_action_id: "0195f000-0000-7000-8000-00000000a101",
              workspace_id: WS_ID,
              run_id: "0195f000-0000-7000-8000-000000000701",
              step_execution_id: "0195f000-0000-7000-8000-000000000801",
              project_alias: "jira:product",
              project_key: "PAYBUILD",
              action_type: "transition_issue",
              issue_key: "PAYBUILD-101",
              summary: "Transition exécutée après PASS",
              target_transition: "IN_REVIEW",
              fields_payload: {},
              status: "EXECUTED",
              idempotency_key: "idem-1",
              provenance_run_lock_uri: "orcia://runs/01/run-lock.json",
              provenance_run_lock_sha256: "sha256:abc",
              executed_issue_key: "PAYBUILD-101",
              replayed_from_cache: false,
            },
          ],
          trace_id: "0195f000000070008000000000000111",
        });
      }
      return originalFetch(input, init);
    });
    restoreFetch = () => spy.mockRestore();

    const queryClient = createOrciaQueryClient();
    const history = createMemoryHistory({ initialEntries: ["/gates"] });
    const router = createOrciaRouter({ queryClient, history });
    await router.load();

    render(
      <I18nProvider initialLocale="fr">
        <QueryClientProvider client={queryClient}>
          <RouterProvider router={router} />
        </QueryClientProvider>
      </I18nProvider>,
    );

    await waitFor(() => {
      const evalBadge = screen.getByTestId("gates-human-evaluation-status-badge");
      expect(evalBadge.getAttribute("data-status")).toBe("PASS");
      expect(evalBadge.textContent).toContain("Validé");

      const jiraBadge = screen.getByTestId("gates-staged-jira-status-badge");
      expect(jiraBadge.getAttribute("data-status")).toBe("EXECUTED");
      expect(jiraBadge.textContent).toContain("Exécutée");
      expect(jiraBadge.textContent).toContain("PAYBUILD-101");
    });
  });

  it("displays [role='alert'] when GET /api/v1/jira/actions/staged fails on /gates", async () => {
    seedAuthenticatedUser();
    const originalFetch = globalThis.fetch;
    const spy = vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
      const url = typeof input === "string" ? input : input instanceof Request ? input.url : String(input);
      const path = new URL(url, "http://localhost").pathname;
      const method = (init?.method ?? "GET").toUpperCase();

      if (path === "/api/v1/gates/human/evaluations" && method === "GET") {
        return jsonRes({ evaluations: [], trace_id: "0195f000000070008000000000000111" });
      }
      if (path === "/api/v1/jira/actions/staged" && method === "GET") {
        return jsonRes(
          {
            type: "https://orcia.io/errors/internal",
            title: "Erreur PostgreSQL 18",
            status: 500,
            detail: "Lecture jira_staged_actions impossible.",
            error_code: "ERR_PG_UNAVAILABLE",
          },
          500,
        );
      }
      return originalFetch(input, init);
    });
    restoreFetch = () => spy.mockRestore();

    const queryClient = createOrciaQueryClient();
    const history = createMemoryHistory({ initialEntries: ["/gates"] });
    const router = createOrciaRouter({ queryClient, history });
    await router.load();

    render(
      <I18nProvider initialLocale="fr">
        <QueryClientProvider client={queryClient}>
          <RouterProvider router={router} />
        </QueryClientProvider>
      </I18nProvider>,
    );

    await waitFor(() => {
      const alertBanner = screen.getByTestId("gates-action-feedback-banner");
      expect(alertBanner.getAttribute("role")).toBe("alert");
      expect(alertBanner.textContent).toContain("Impossible de charger les revues humaines");
    });
  });

  it("loads VSM from GET /api/v1/vsm/{id} and renders vsm-error-banner [role='alert'] on HTTP >= 400", async () => {
    seedAuthenticatedUser();
    const originalFetch = globalThis.fetch;
    const spy = vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
      const url = typeof input === "string" ? input : input instanceof Request ? input.url : String(input);
      const path = new URL(url, "http://localhost").pathname;
      const method = (init?.method ?? "GET").toUpperCase();

      if (path === "/api/v1/vsm/vsm-mon-compte-idea-to-prod" && method === "GET") {
        return jsonRes({
          id: "vsm-mon-compte-idea-to-prod",
          slug: "vsm-mon-compte-idea-to-prod",
          title: "Chaîne de Valeur PG18 Vérifiée",
          subtitle: "De l'Idée à la Production",
          source_note: "PG18",
          guiding_principle: "Human in the loop",
          tools_note: "",
          pack_id: "sdlc",
          knowledge_foundation: {
            title: "Socle Confluence PG18",
            summary: "Hydraté depuis vsm_definitions_v2",
          },
          phases: [{ num: "1", id: "phase-1", label: "Phase 1 PG18", subtitle: "Qualifier" }],
          opportunities: {},
          agents_catalog: {},
          nodes: [],
        });
      }
      if (path === "/api/v1/vsm/vsm-inexistant" && method === "GET") {
        return jsonRes(
          {
            type: "https://orcia.io/errors/not-found",
            title: "VSM introuvable",
            status: 404,
            detail: "La chaîne de valeur 'vsm-inexistant' est absente de PG18.",
            error_code: "ERR_RESOURCE_NOT_FOUND",
          },
          404,
        );
      }
      return originalFetch(input, init);
    });
    restoreFetch = () => spy.mockRestore();

    const queryClient1 = createOrciaQueryClient();
    const history1 = createMemoryHistory({
      initialEntries: ["/processes/vsm/vsm-mon-compte-idea-to-prod"],
    });
    const router1 = createOrciaRouter({ queryClient: queryClient1, history: history1 });
    await router1.load();

    render(
      <I18nProvider initialLocale="fr">
        <QueryClientProvider client={queryClient1}>
          <RouterProvider router={router1} />
        </QueryClientProvider>
      </I18nProvider>,
    );

    await waitFor(() => {
      const view = screen.getByTestId("vsm-interactive-view");
      expect(view.textContent).toContain("Chaîne de Valeur PG18 Vérifiée");
      expect(screen.queryByTestId("vsm-error-banner")).toBeNull();
    });

    cleanup();

    const queryClient2 = createOrciaQueryClient();
    const history2 = createMemoryHistory({
      initialEntries: ["/processes/vsm/vsm-inexistant"],
    });
    const router2 = createOrciaRouter({ queryClient: queryClient2, history: history2 });
    await router2.load();

    render(
      <I18nProvider initialLocale="fr">
        <QueryClientProvider client={queryClient2}>
          <RouterProvider router={router2} />
        </QueryClientProvider>
      </I18nProvider>,
    );

    await waitFor(() => {
      const errBanner = screen.getByTestId("vsm-error-banner");
      expect(errBanner.getAttribute("role")).toBe("alert");
      expect(errBanner.textContent).toContain("Ressource introuvable");
    });
  });
});
