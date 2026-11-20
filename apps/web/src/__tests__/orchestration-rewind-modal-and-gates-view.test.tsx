import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createMemoryHistory, RouterProvider } from "@tanstack/react-router";
import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import React from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ShellContainer } from "../components/ShellContainer";
import { CockpitFeaturePanel } from "../features/cockpit";
import { GatesFeaturePanel } from "../features/gates";
import { I18nProvider } from "../i18n";
import { createOrciaRouter } from "../router";
import { useAuthSessionStore } from "../stores/authSessionStore";
import { seedVitestPlatformSetupState } from "./vitest.setup";

const WS_ID = "0192c4e0-0000-7000-8000-000000000201";

function seedAuthenticatedWorkspace() {
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
    llm_tiers: [{ tier: "fast", model_name: "qwen", endpoint_url: "http://127.0.0.1:11434" }],
    workspaces: [
      {
        workspaceId: WS_ID,
        name: "Espace Orchestration",
        visibilityMode: "STANDARD",
        ownerOrgUnitName: "Equipe Architecture",
        lifecyclePhase: "BUILD",
        suggestedWorkflows: [],
        accessMode: "CONTRIBUTOR_ACTION_REQUIRED",
        finopsCostUsd: 0.05,
      },
    ],
    datasources: [],
    packs: [],
    workflows: [],
    runs: [
      {
        runId: "0195f000-0000-7000-8000-000000000701",
        workspaceId: WS_ID,
        workspaceName: "Espace Orchestration",
        title: "Run Orchestration Test",
        workflowKey: "assistant-agent",
        status: "RUNNING",
        currentStepKey: "frame-architecture-intent",
        createdAtIso: "2026-11-20T01:00:00Z",
      },
    ],
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

describe("Upstream challenge rewind modal, dedicated Gates review view, and RFC 9457 error banners", () => {
  let restoreFetch: (() => void) | null = null;

  afterEach(() => {
    restoreFetch?.();
    restoreFetch = null;
    cleanup();
  });

  it("mounts UpstreamChallengeRewindModal via Radix Portal, submits challenge/replay, and rehydrates stale warning after F5", async () => {
    seedAuthenticatedWorkspace();
    const originalFetch = globalThis.fetch;
    const challengesByRun = new Map<string, Array<{ reason: string }>>();
    const replayedRuns = new Set<string>();

    const spy = vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
      const url = typeof input === "string" ? input : input instanceof Request ? input.url : String(input);
      const path = new URL(url, "http://localhost").pathname;
      const method = (init?.method ?? "GET").toUpperCase();
      const rawBody = typeof init?.body === "string" ? init.body : "{}";
      const body = rawBody ? (JSON.parse(rawBody) as Record<string, unknown>) : {};

      const previewMatch = /^\/api\/v1\/orchestration\/runs\/([^/]+)\/steps\/([^/]+)\/challenge\/preview$/.exec(path);
      if (previewMatch && method === "POST") {
        const runId = decodeURIComponent(previewMatch[1] ?? "");
        const challengerStep = decodeURIComponent(previewMatch[2] ?? "");
        return jsonRes({
          preview: {
            run_id: runId,
            challenger_step_key: challengerStep,
            target_upstream_step_key: String(body.target_upstream_step_key ?? "frame-architecture-intent"),
            challenged_section_key: String(body.challenged_section_key ?? "human_architecture_intent"),
            challenge_reason: String(body.challenge_reason ?? ""),
            target_profile_archetype: String(body.target_profile_archetype ?? "PM_BUSINESS"),
            translated_summary: "Impact What-If calculé depuis PostgreSQL 18.",
            invalidated_downstream_step_keys: ["frame-architecture-intent", challengerStep],
            invalidated_artifact_sections: ["frame-architecture-intent:human_architecture_intent"],
            invalidated_ontology_axiom_keys: [],
            preserved_upstream_step_keys: [],
            upstream_tokens_saved: 420,
          },
          trace_id: "0195f000000070008000000000000111",
        });
      }

      const submitMatch = /^\/api\/v1\/orchestration\/runs\/([^/]+)\/steps\/([^/]+)\/challenge$/.exec(path);
      if (submitMatch && method === "POST") {
        const runId = decodeURIComponent(submitMatch[1] ?? "");
        const challengerStep = decodeURIComponent(submitMatch[2] ?? "");
        const list = challengesByRun.get(runId) ?? [];
        list.push({ reason: String(body.challenge_reason ?? "") });
        challengesByRun.set(runId, list);
        return jsonRes({
          challenge: {
            id: "0195f000-0000-7000-8000-00000000c111",
            challenge_key: "chal-1",
            workspace_id: WS_ID,
            run_id: runId,
            challenger_step_key: challengerStep,
            target_upstream_step_key: String(body.target_upstream_step_key ?? "frame-architecture-intent"),
            challenged_section_key: String(body.challenged_section_key ?? "human_architecture_intent"),
            challenge_reason: String(body.challenge_reason ?? ""),
            target_profile_archetype: "PM_BUSINESS",
            translated_summary: "Contestation enregistrée.",
            invalidated_downstream_step_keys: ["frame-architecture-intent", challengerStep],
            invalidated_artifact_sections: ["frame-architecture-intent:human_architecture_intent"],
            invalidated_ontology_axiom_keys: [],
            preserved_upstream_step_keys: [],
            status: "OPEN",
            created_by_user_id: "user-lead",
            outbox_event_id: "evt-chal-1",
            revised_artifact_version: null,
          },
          preview: {
            run_id: runId,
            challenger_step_key: challengerStep,
            target_upstream_step_key: String(body.target_upstream_step_key ?? "frame-architecture-intent"),
            challenged_section_key: String(body.challenged_section_key ?? "human_architecture_intent"),
            challenge_reason: String(body.challenge_reason ?? ""),
            target_profile_archetype: "PM_BUSINESS",
            translated_summary: "Contestation enregistrée.",
            invalidated_downstream_step_keys: ["frame-architecture-intent", challengerStep],
            invalidated_artifact_sections: ["frame-architecture-intent:human_architecture_intent"],
            invalidated_ontology_axiom_keys: [],
            preserved_upstream_step_keys: [],
            upstream_tokens_saved: 420,
          },
          trace_id: "0195f000000070008000000000000111",
        });
      }

      const replayMatch = /^\/api\/v1\/orchestration\/runs\/([^/]+)\/steps\/([^/]+)\/replay$/.exec(path);
      if (replayMatch && method === "POST") {
        const runId = decodeURIComponent(replayMatch[1] ?? "");
        const stepKey = decodeURIComponent(replayMatch[2] ?? "");
        replayedRuns.add(runId);
        return jsonRes({
          replay: {
            run_id: runId,
            replayed_from_step_key: stepKey,
            sub_workflow_step_key: null,
            reused_upstream_snapshot_ids: [],
            superseded_snapshot_ids: ["snap-old-1"],
            new_active_snapshot_ids: ["snap-new-2"],
            upstream_steps_reexecuted_count: 0,
            upstream_tokens_consumed: 0,
            run_lock_sha256: "sha256:lock",
          },
          trace_id: "0195f000000070008000000000000111",
        });
      }

      const bbMatch = /^\/api\/v1\/orchestration\/runs\/([^/]+)\/blackboard$/.exec(path);
      if (bbMatch && method === "GET") {
        const res = await originalFetch(input, init);
        const runId = decodeURIComponent(bbMatch[1] ?? "");
        if (replayedRuns.has(runId) && res.ok) {
          const data = (await res.json()) as Record<string, unknown>;
          const steps = Array.isArray(data.step_executions)
            ? (data.step_executions as Array<Record<string, unknown>>)
            : [];
          return jsonRes({
            ...data,
            step_executions: [
              ...steps,
              {
                id: `step-stale-${runId}`,
                step_execution_key: `${runId}:delegate-remediation-subworkflow`,
                run_id: runId,
                step_key: "delegate-remediation-subworkflow",
                step_index: 1,
                step_type: "SUB_WORKFLOW",
                execution_mode: "COACHING",
                status: "STALE_NEEDS_REVIEW",
                attempt_count: 1,
                max_agent_retries: 2,
                draft_artifact: {},
                draft_cas_key: null,
                step_memlog: [],
                hydrated_input_uris: [],
                child_run_id: null,
                committed_snapshot_id: null,
                cost_usd: 0,
              },
            ],
          });
        }
        return res;
      }

      return originalFetch(input, init);
    });
    restoreFetch = () => spy.mockRestore();

    const view1 = render(
      <I18nProvider initialLocale="fr">
        <ShellContainer>
          <CockpitFeaturePanel />
        </ShellContainer>
      </I18nProvider>,
    );

    const anchorTextarea = await screen.findByTestId("cockpit-human-anchor-textarea");
    fireEvent.change(anchorTextarea, {
      target: {
        value:
          "Invariants stricts de séparation hexagonale et contrat OpenAPI 3.1 vérifié en continu.",
      },
    });
    fireEvent.click(screen.getByTestId("human-anchor-submit-human_architecture_intent"));

    await waitFor(() => {
      expect(screen.getByTestId("cockpit-human-anchor-signed-badge")).toBeDefined();
    });

    // Open Radix Portal mode of UpstreamChallengeRewindModal
    fireEvent.click(screen.getByTestId("cockpit-open-upstream-challenge-modal-btn"));
    const reasonInput = await screen.findByTestId("upstream-challenge-reason-input");
    expect(reasonInput.closest('[role="dialog"]')).not.toBeNull();

    fireEvent.change(reasonInput, {
      target: { value: "Mise à jour contractuelle partenaire exigeant un réalignement amont." },
    });
    fireEvent.click(screen.getByTestId("upstream-challenge-submit-btn"));

    await waitFor(() => {
      expect(challengesByRun.size).toBe(1);
    });

    fireEvent.click(screen.getByTestId("upstream-replay-trigger-btn"));
    await waitFor(() => {
      expect(screen.getByTestId("upstream-replay-stale-warning-banner").textContent).toContain(
        "Alerte d'obsolescence :",
      );
    });

    // Simulate F5 full unmount + remount
    view1.unmount();

    render(
      <I18nProvider initialLocale="fr">
        <ShellContainer>
          <CockpitFeaturePanel />
        </ShellContainer>
      </I18nProvider>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("cockpit-human-anchor-signed-badge")).toBeDefined();
      expect(screen.getByTestId("upstream-replay-stale-warning-banner").textContent).toContain(
        "Alerte d'obsolescence :",
      );
    });
  });

  it("enforces strict separation of /gates (Briefing 4 blocks & chunk validation) vs /processes (zero process studio form)", async () => {
    seedAuthenticatedWorkspace();
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
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

    expect(screen.getByTestId("gates-dedicated-review-page")).toBeDefined();
    expect(screen.getByTestId("gates-adaptive-human-review-section")).toBeDefined();
    expect(screen.getByTestId("gates-open-human-review-btn")).toBeDefined();
    expect(screen.queryByTestId("settings-workflows-section")).toBeNull();
    expect(screen.queryByTestId("pack-builder-studio-view")).toBeNull();
    expect(screen.queryByTestId("orcia-doc-generation-process-card")).toBeNull();

    await act(async () => {
      await router.navigate({ to: "/processes" });
    });
    expect(screen.getByTestId("processes-hub-v2-page")).toBeDefined();
    expect(screen.queryByTestId("gates-dedicated-review-page")).toBeNull();
  });

  it("displays a visible RFC 9457 [role='alert'] banner on HTTP >= 400 errors during anchor, challenge, and gate mutations", async () => {
    seedAuthenticatedWorkspace();
    const originalFetch = globalThis.fetch;

    const spy = vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
      const url = typeof input === "string" ? input : input instanceof Request ? input.url : String(input);
      const path = new URL(url, "http://localhost").pathname;
      const method = (init?.method ?? "GET").toUpperCase();

      if (path === "/api/v1/orchestration/runs/anchors/sign" && method === "POST") {
        return jsonRes(
          {
            type: "https://orcia.io/errors/observer-mode-read-only",
            title: "Mode Observateur lecture seule",
            status: 403,
            detail: "Action interdite en mode observateur.",
            error_code: "ERR_OBSERVER_MODE_READ_ONLY",
          },
          403,
        );
      }

      if (path === "/api/v1/gates/human/evaluations" && method === "GET") {
        return jsonRes({ evaluations: [], trace_id: "0195f000000070008000000000000111" });
      }
      if (path === "/api/v1/connectors/jira/staged-actions" && method === "GET") {
        return jsonRes({ actions: [], trace_id: "0195f000000070008000000000000111" });
      }
      if (path === "/api/v1/gates/human/evaluate" && method === "POST") {
        return jsonRes(
          {
            type: "https://orcia.io/errors/rubber-stamping-guard",
            title: "Rejet de validation gate",
            status: 422,
            detail: "Rejet RFC 9457 simulé sur mutation de Gate humaine.",
            error_code: "ERR_RUBBER_STAMPING_GUARD_TRIGGERED",
          },
          422,
        );
      }

      return originalFetch(input, init);
    });
    restoreFetch = () => spy.mockRestore();

    // 1. Cockpit anchor HTTP 403 -> [role="alert"]
    render(
      <I18nProvider initialLocale="fr">
        <ShellContainer>
          <CockpitFeaturePanel />
        </ShellContainer>
      </I18nProvider>,
    );

    fireEvent.change(await screen.findByTestId("cockpit-human-anchor-textarea"), {
      target: {
        value: "Contrainte humaine valide dépassant trente caractères pour déclencher la mutation.",
      },
    });
    fireEvent.click(screen.getByTestId("human-anchor-submit-human_architecture_intent"));

    await waitFor(() => {
      const alertBanner = screen.getByRole("alert");
      expect(alertBanner.textContent).toContain("Action interdite en mode observateur.");
    });

    cleanup();

    // 2. Gates human review HTTP 422 -> [role="alert"]
    render(
      <I18nProvider initialLocale="fr">
        <ShellContainer>
          <GatesFeaturePanel />
        </ShellContainer>
      </I18nProvider>,
    );

    fireEvent.click(screen.getByTestId("gates-open-human-review-btn"));
    await waitFor(() => {
      const gatesAlert = screen.getByRole("alert");
      expect(gatesAlert.textContent).toContain("Rejet RFC 9457 simulé");
    });
  });
});
