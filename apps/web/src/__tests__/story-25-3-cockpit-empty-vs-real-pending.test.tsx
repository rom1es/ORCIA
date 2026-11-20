import { QueryClientProvider } from "@tanstack/react-query";
import { createMemoryHistory, RouterProvider } from "@tanstack/react-router";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import React from "react";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { clearPlatformSetupStorage } from "../components/platformSetupStorageHelpers";
import { createOrciaQueryClient, createOrciaRouter } from "../router";
import { useAuthSessionStore } from "../stores/authSessionStore";
import { backendState } from "./setup/mockBackendState";
import { resetVitestApiBackend, seedVitestPlatformSetupState } from "./vitest.setup";

const WS_ID = "0195f000-0000-7000-8000-000000000401";
const TEAM_ID = "0192c4e0-0000-7000-8000-000000000103";

function seedAdminSession(): void {
  seedVitestPlatformSetupState(
    {
      org_units: [
        {
          id: "0192c4e0-0000-7000-8000-000000000101",
          name: "Direction Produit",
          slug: "dir-produit",
          kind: "BU",
          parent_id: null,
          billing_enabled: true,
        },
        {
          id: TEAM_ID,
          name: "Équipe Socle",
          slug: "equipe-socle",
          kind: "TEAM",
          parent_id: "0192c4e0-0000-7000-8000-000000000101",
          billing_enabled: true,
        },
      ],
      workspaces: [
        {
          workspaceId: WS_ID,
          name: "Espace Sobriété 25.3",
          slug: "espace-sobriete-25-3",
          ownerOrgUnitId: TEAM_ID,
          ownerOrgUnitName: "Équipe Socle",
          visibilityMode: "STANDARD",
          lifecyclePhase: "BUILD",
          suggestedWorkflows: [],
          accessMode: "CONTRIBUTOR_ACTION_REQUIRED",
          finopsCostUsd: 0,
        },
      ],
      runs: [],
    },
    {
      email: "admin253@orcia.test",
      displayName: "Admin 25.3",
      roles: ["PLATFORM_ADMIN"],
    },
  );
  useAuthSessionStore.getState().setAuthSession({
    isAuthenticated: true,
    isHydrating: false,
    email: "admin253@orcia.test",
    displayName: "Admin 25.3",
    roles: ["PLATFORM_ADMIN"],
    activeHat: "PLATFORM_ADMIN",
  });
}

async function mountCockpitWithRealRouter() {
  const queryClient = createOrciaQueryClient();
  const history = createMemoryHistory({ initialEntries: ["/cockpit"] });
  const router = createOrciaRouter({ queryClient, history });
  await router.load();
  return render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  resetVitestApiBackend();
  clearPlatformSetupStorage();
});

afterEach(() => {
  cleanup();
});

describe("Story 25.3 — Sobriété Cockpit Jour 0 & Montage strictement conditionnel sur actions réelles PG18", () => {
  it("at 0 runs / 0 pending decisions, hides all waiting blocks, quick assistant box, and Human-Led Governance cards", async () => {
    seedAdminSession();
    const view = await mountCockpitWithRealRouter();

    expect(await screen.findByTestId("cockpit-block-accostage")).toBeTruthy();
    expect(screen.getByTestId("cockpit-block-decisions")).toBeTruthy();
    expect(screen.getByTestId("cockpit-calm-orientation-panel")).toBeTruthy();

    expect(screen.queryByTestId("cockpit-zero-decisions-banner")).toBeNull();
    expect(screen.queryByTestId("cockpit-quick-assistant-box")).toBeNull();
    expect(screen.queryByTestId("cockpit-human-led-governance-section")).toBeNull();
    expect(screen.queryByTestId("cockpit-human-led-anchor-card")).toBeNull();
    expect(screen.queryByTestId("cockpit-arbitration-tiebreak-card")).toBeNull();

    const text = view.container.textContent ?? "";
    expect(text).not.toContain("No pending decisions");
    expect(text).not.toContain("Aucune décision en attente");
    expect(text).not.toContain("Quick access to My Assistant");
    expect(text).not.toContain("Accès rapide à Mon Assistant");
    expect(text).not.toContain("Human-Led Governance");
    expect(text).not.toContain("Gouvernance Human-Led");
    expect(text).not.toContain("DECISION REQUIRED");
    expect(text).not.toContain("Taux Spot 15 min");
    expect(text).not.toContain("Taux Bloqué 48h");
  });

  it("mounts ONLY HumanLedAnchorCard when a real run requires an unsigned anchor, then hides it upon signing", async () => {
    seedAdminSession();
    const runId = "0195f000-0000-7000-8000-000000002531";
    backendState.orchestrationRuns = [
      {
        id: runId,
        workspace_id: WS_ID,
        workflow_uri: "orcia://workflows/claims-engineering-delivery",
        status: "RUNNING",
        step_status: "WAITING_FOR_HUMAN_ANCHOR",
        draft_artifact: {},
        committed_snapshot_id: null,
        human_anchors: [],
        pending_arbitrations: [],
      },
    ];

    await mountCockpitWithRealRouter();

    expect(await screen.findByTestId("cockpit-human-led-governance-section")).toBeTruthy();
    expect(screen.getByTestId("cockpit-human-led-anchor-card")).toBeTruthy();
    expect(screen.queryByTestId("cockpit-arbitration-tiebreak-card")).toBeNull();

    fireEvent.change(screen.getByTestId("cockpit-human-anchor-textarea"), {
      target: {
        value: "Invariants architecturaux validés par le Tech Lead sur le domaine Paiement.",
      },
    });
    fireEvent.click(screen.getByTestId("human-anchor-submit-human_architecture_intent"));

    await waitFor(() => {
      expect(screen.queryByTestId("cockpit-human-led-anchor-card")).toBeNull();
      expect(screen.queryByTestId("cockpit-human-led-governance-section")).toBeNull();
    });
  });

  it("mounts ArbitrationTieBreakCard with ONLY real API options (never Taux Spot 15 min / Taux Bloqué 48h) and disappears once resolved", async () => {
    seedAdminSession();
    const runId = "0195f000-0000-7000-8000-000000002532";
    const arbId = "0195f000-0000-7000-8000-00000000a532";
    backendState.orchestrationRuns = [
      {
        id: runId,
        workspace_id: WS_ID,
        workflow_uri: "orcia://workflows/claims-engineering-delivery",
        status: "WAITING_FOR_HUMAN_ARBITRATION",
        step_status: "WAITING_FOR_HUMAN_ARBITRATION",
        draft_artifact: {
          human_anchors: {
            human_architecture_intent: {
              content_sha256: "a".repeat(64),
            },
          },
        },
        committed_snapshot_id: null,
        human_anchors: [
          {
            id: "sig-2532",
            signature_key: "anchor-human_architecture_intent",
            workspace_id: WS_ID,
            run_id: runId,
            step_execution_id: `step-${runId}`,
            step_key: "frame-architecture-intent",
            section_key: "human_architecture_intent",
            content_text: "Intention d'architecture déjà signée.",
            content_sha256: "a".repeat(64),
            char_length: 38,
            authored_by_user_id: "0195f000-0000-7000-8000-000000000001",
            author_display_name: "Admin 25.3",
            signature_hash: "b".repeat(64),
          },
        ],
        pending_arbitrations: [
          {
            id: arbId,
            arbitration_key: arbId,
            workspace_id: WS_ID,
            run_id: runId,
            step_execution_id: `step-${runId}`,
            step_key: "frame-architecture-intent",
            tie_break_policy: "PAUSE_AND_ESCALATE",
            status: "PENDING",
            question_title: "Choix du moteur d'indexation PG18",
            context_summary: "Deux index candidats évalués.",
            options_matrix: [
              {
                option_key: "OPT_HNSW_COSINE",
                title: "Index HNSW pgvector",
                pros: ["Rappel élevé"],
                cons: ["Mémoire"],
                si_impact: "PostgreSQL 18",
                finops_impact: "0 €/mois",
                recommended: true,
              },
              {
                option_key: "OPT_IVFFLAT",
                title: "Index IVFFlat",
                pros: ["Construction rapide"],
                cons: ["Rappel moindre"],
                si_impact: "PostgreSQL 18",
                finops_impact: "0 €/mois",
                recommended: false,
              },
            ],
            selected_option_key: null,
            human_justification: null,
            resolved_by_user_id: null,
            resolved_by_axiom_key: null,
            outbox_event_id: "evt-arb-2532",
          },
        ],
      },
    ];

    const view = await mountCockpitWithRealRouter();

    const arbCard = await screen.findByTestId("cockpit-arbitration-tiebreak-card");
    expect(arbCard).toBeTruthy();
    expect(screen.queryByTestId("cockpit-human-led-anchor-card")).toBeNull();
    expect(arbCard.textContent).toContain("Index HNSW pgvector");
    expect(arbCard.textContent).toContain("Index IVFFlat");
    expect(view.container.textContent).not.toContain("Taux Spot 15 min");
    expect(view.container.textContent).not.toContain("Taux Bloqué 48h");

    fireEvent.change(arbCard.querySelector('input[type="text"]') as HTMLInputElement, {
      target: { value: "HNSW retenu pour la précision sémantique." },
    });
    fireEvent.click(screen.getByTestId("arbitration-select-OPT_HNSW_COSINE"));

    await waitFor(() => {
      expect(screen.queryByTestId("cockpit-arbitration-tiebreak-card")).toBeNull();
      expect(screen.queryByTestId("cockpit-human-led-governance-section")).toBeNull();
    });
  });
});
