// @vitest-environment jsdom
import { createOrciaApiClient } from "@orcia/api-client";
import { QueryClientProvider } from "@tanstack/react-query";
import { createMemoryHistory, RouterProvider } from "@tanstack/react-router";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import React from "react";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { clearPlatformSetupStorage } from "../components/platformSetupStorageHelpers";
import { clearSavedActiveScopeId } from "../components/useShellContainerState";
import { I18nProvider } from "../i18n";
import { createOrciaQueryClient, createOrciaRouter } from "../router";
import { useAuthSessionStore } from "../stores/authSessionStore";
import { resetVitestApiBackend, seedVitestPlatformSetupState } from "./vitest.setup";
import { seedVitestConnectorsInitialData } from "./vitestConnectorsMockHandlers";
import { seedVitestOntologyState } from "./vitestOntologyMockHandlers";

const PERSONAL_WS_ID = "0195f000-0000-7000-8000-000000000401";
const PERSONAL_WS_SLUG = `personal-${PERSONAL_WS_ID}`;
const TEAM_ID = "0195f000-0000-7000-8000-000000000040";

function seedAuditWorkspace(options: { readonly withPendingCandidates?: boolean } = {}) {
  seedVitestPlatformSetupState(
    {
      org_units: [
        {
          id: TEAM_ID,
          name: "Équipe Audit UX",
          slug: "equipe-audit-ux",
          kind: "TEAM",
          level: "TEAM",
          parentId: null,
          billingEnabled: true,
        },
      ],
      workspaces: [
        {
          workspaceId: PERSONAL_WS_ID,
          slug: PERSONAL_WS_SLUG,
          name: "Mon Espace Sobre",
          ownerUserId: "nadia@orcia.fr",
          ownerOrgUnitId: TEAM_ID,
          ownerOrgUnitName: "Équipe Audit UX",
          visibilityMode: "PRIVATE_USER",
          lifecyclePhase: "BUILD",
          accessMode: "CONTRIBUTOR_ACTION_REQUIRED",
          finopsCostUsd: 0,
        },
      ],
    },
    { email: "nadia@orcia.fr", displayName: "Nadia Onto", roles: ["PLATFORM_ADMIN"] },
  );
  seedVitestConnectorsInitialData({ datasources: [] });
  if (options.withPendingCandidates) {
    seedVitestOntologyState(
      [
        {
          id: "concept-284-1",
          concept_key: "4-workspace-taux-sinistre",
          canonical_term: "Taux de Sinistralité",
          level: "4_WORKSPACE",
          scope_id: PERSONAL_WS_ID,
          definition_text: "Ratio sinistres sur primes acquises.",
          parent_concept_id: null,
          synonyms: [],
          banned_terms: [],
          profile_translations: {},
          expected_schema: {},
          introduced_in_snapshot_id: null,
          snapshot_branch_status: "ACTIVE",
        },
        {
          id: "concept-284-2",
          concept_key: "4-workspace-cout-token",
          canonical_term: "Coût Unitaire Jeton",
          level: "4_WORKSPACE",
          scope_id: PERSONAL_WS_ID,
          definition_text: "Coût consolidé par million de jetons.",
          parent_concept_id: null,
          synonyms: [],
          banned_terms: [],
          profile_translations: {},
          expected_schema: {},
          introduced_in_snapshot_id: null,
          snapshot_branch_status: "ACTIVE",
        },
      ],
      [
        {
          id: "0195f000-0000-7000-8300-000000000001",
          proposal_key: "prop-284-1",
          concept_key: "4-workspace-taux-sinistre",
          canonical_term: "Taux de Sinistralité",
          source_level: "4_RUN_EPHEMERAL",
          target_level: "4_WORKSPACE",
          target_scope_id: PERSONAL_WS_ID,
          proposed_by_user_id: "nadia@orcia.fr",
          status: "PENDING_REVIEW",
          source_concept_id: "concept-284-1",
          source_scope_id: PERSONAL_WS_ID,
          definition_text: "Ratio sinistres sur primes acquises.",
          reviewed_by_user_id: null,
          review_comment: null,
          collision_detected: false,
          colliding_definition: null,
        },
        {
          id: "0195f000-0000-7000-8300-000000000002",
          proposal_key: "prop-284-2",
          concept_key: "4-workspace-cout-token",
          canonical_term: "Coût Unitaire Jeton",
          source_level: "4_RUN_EPHEMERAL",
          target_level: "4_WORKSPACE",
          target_scope_id: PERSONAL_WS_ID,
          proposed_by_user_id: "nadia@orcia.fr",
          status: "PENDING_REVIEW",
          source_concept_id: "concept-284-2",
          source_scope_id: PERSONAL_WS_ID,
          definition_text: "Coût consolidé par million de jetons.",
          reviewed_by_user_id: null,
          review_comment: null,
          collision_detected: false,
          colliding_definition: null,
        },
      ],
    );
  }
  useAuthSessionStore.setState({
    isAuthenticated: true,
    isHydrating: false,
    accessToken: "test-jwt-token",
    displayName: "Nadia Onto",
    email: "nadia@orcia.fr",
    roles: ["PLATFORM_ADMIN"],
    activeHat: "PLATFORM_ADMIN",
  });
}

async function mountWorkspaces(locale: "fr" | "en") {
  const queryClient = createOrciaQueryClient();
  const history = createMemoryHistory({ initialEntries: ["/workspaces"] });
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
  clearPlatformSetupStorage();
  clearSavedActiveScopeId();
});

afterEach(() => {
  cleanup();
});

describe("Story 28.4 — Anti-Stacking & Sobriety Audit (WX-01..WX-06) + Tab 4 PG18 Glossary Encapsulation", () => {
  it("enforces all 6 WX-01..WX-06 invariants on empty workspace in both FR and EN", async () => {
    for (const locale of ["fr", "en"] as const) {
      resetVitestApiBackend();
      clearPlatformSetupStorage();
      clearSavedActiveScopeId();
      seedAuditWorkspace({ withPendingCandidates: false });
      await createOrciaApiClient({ baseUrl: "" }).updateUserPreferences({ locale });

      const view = await mountWorkspaces(locale);
      await screen.findByTestId("workspace-five-tabs-view");

      // WX-01: Strictly 1 [role="tablist"] with 5 canonical tabs and 0 legacy 3-tab duplicate
      expect(screen.getAllByRole("tablist")).toHaveLength(1);
      expect(screen.getAllByRole("tab")).toHaveLength(5);
      expect(screen.queryByTestId("workspace-detail-tabs-panel")).toBeNull();
      expect(screen.queryByTestId("workspace-detail-tab-sources")).toBeNull();

      // WX-02 & WX-06: Strictly 1 compact header, 0 outer bento header or card grid
      expect(screen.getAllByTestId("workspaces-compact-header")).toHaveLength(1);
      expect(screen.queryByTestId("module-uri-badge-admin")).toBeNull();
      expect(screen.queryByTestId("workspaces-summary-cards-grid")).toBeNull();
      expect(screen.queryByTestId("workspaces-header-and-filters-bar")).toBeNull();

      // WX-05: Tab 1 hides KPI cards and external-rebase notice when empty
      expect(screen.getByTestId("workspace-overview-panel")).toBeDefined();
      expect(screen.queryByTestId("workspace-overview-kpi-grid")).toBeNull();
      expect(screen.queryByTestId("workspace-overview-rebase-section")).toBeNull();
      expect(screen.getByTestId("workspace-overview-empty-hint")).toBeDefined();

      // WX-03: dna-starlark-glossary-view MUST be null on Tabs 1, 2, 3, and 5
      expect(screen.queryByTestId("dna-starlark-glossary-view")).toBeNull();
      expect(view.container.textContent ?? "").not.toContain(PERSONAL_WS_SLUG);
      expect(view.container.textContent ?? "").not.toContain(PERSONAL_WS_ID);

      // Tab 2: hides filter pills when total == 0
      fireEvent.click(screen.getByTestId("workspace-tab-DOCUMENTS_SOURCES"));
      await screen.findByTestId("workspace-sources-empty-state");
      expect(screen.queryByTestId("sources-filter-pill-all")).toBeNull();
      expect(screen.queryByTestId("dna-starlark-glossary-view")).toBeNull();

      // Tab 3: sanitized CAS destination, zero personal-<uuid>
      fireEvent.click(screen.getByTestId("workspace-tab-DELIVERABLES_ARTIFACTS")); // pragma: allowlist secret
      const deliv = await screen.findByTestId("workspace-deliverables-panel");
      expect(deliv.textContent ?? "").not.toContain(PERSONAL_WS_SLUG);
      expect(screen.queryByTestId("dna-starlark-glossary-view")).toBeNull();

      // Tab 5: settings & instructions, zero dna-starlark-glossary-view
      fireEvent.click(screen.getByTestId("workspace-tab-MEMBERS_TEAM"));
      await screen.findByTestId("workspace-members-panel");
      expect(screen.queryByTestId("dna-starlark-glossary-view")).toBeNull();

      // Tab 4: mounts dna-starlark-glossary-view strictly inside workspace-glossary-rules-panel
      fireEvent.click(screen.getByTestId("workspace-tab-GLOSSARY_RULES"));
      const glossaryPanel = await screen.findByTestId("workspace-glossary-rules-panel");
      const starlarkView = await screen.findByTestId("dna-starlark-glossary-view");
      expect(glossaryPanel.contains(starlarkView)).toBe(true);
      expect(
        glossaryPanel.querySelector('[data-testid="workspace-glossary-and-ontology-tab"]'),
      ).not.toBeNull();

      if (locale === "fr") {
        expect(screen.getByTestId("workspace-tab-GLOSSARY_RULES").textContent).toContain("Glossaire");
      } else {
        expect(screen.getByTestId("workspace-tab-GLOSSARY_RULES").textContent).toContain("Glossary");
      }

      view.unmount();
      cleanup();
    }
  }, 15_000);

  it("hydrates Tab 4 glossary candidates from PG18, persists Top-3 approval and FIFO rejection across F5 reload", async () => {
    seedAuditWorkspace({ withPendingCandidates: true });
    const first = await mountWorkspaces("fr");

    // Pending candidates hydrated from PG18 drive Tab 4 badge before even opening Tab 4
    await waitFor(() => {
      expect(screen.getByTestId("workspace-tab-badge-GLOSSARY_RULES").textContent).toBe("2");
    });
    expect(screen.queryByTestId("dna-starlark-glossary-view")).toBeNull();

    // Open Tab 4 -> both pending candidates hydrated into Top-3 & FIFO queue
    fireEvent.click(screen.getByTestId("workspace-tab-GLOSSARY_RULES"));
    await screen.findByTestId("dna-starlark-glossary-view");
    expect(
      screen.getByTestId("queue-candidate-0195f000-0000-7000-8300-000000000001").textContent,
    ).toContain("Taux de Sinistralité");
    expect(
      screen.getByTestId("queue-candidate-0195f000-0000-7000-8300-000000000002").textContent,
    ).toContain("Coût Unitaire Jeton");

    // Reject candidate 2 via PG18 endpoint -> removed from queue
    fireEvent.click(
      screen.getByTestId("reject-candidate-btn-0195f000-0000-7000-8300-000000000002"),
    );
    await waitFor(() => {
      expect(
        screen.queryByTestId("queue-candidate-0195f000-0000-7000-8300-000000000002"),
      ).toBeNull();
      expect(screen.getByTestId("workspace-tab-badge-GLOSSARY_RULES").textContent).toBe("1");
    });

    // F5 cold remount survival -> candidate 1 remains pending, candidate 2 stays rejected
    first.unmount();
    cleanup();

    const reloaded = await mountWorkspaces("fr");
    await waitFor(() => {
      expect(screen.getByTestId("workspace-tab-badge-GLOSSARY_RULES").textContent).toBe("1");
    });
    fireEvent.click(screen.getByTestId("workspace-tab-GLOSSARY_RULES"));
    await screen.findByTestId("dna-starlark-glossary-view");
    expect(
      screen.getByTestId("top3-candidate-0195f000-0000-7000-8300-000000000001"),
    ).toBeDefined();
    expect(
      screen.queryByTestId("queue-candidate-0195f000-0000-7000-8300-000000000002"),
    ).toBeNull();

    // Approve remaining Top-3 candidate via PG18 endpoint -> queue becomes empty
    fireEvent.click(screen.getByTestId("promote-in-flow-btn"));
    await waitFor(() => {
      expect(
        screen.queryByTestId("queue-candidate-0195f000-0000-7000-8300-000000000001"),
      ).toBeNull();
      expect(screen.queryByTestId("workspace-tab-badge-GLOSSARY_RULES")).toBeNull();
    });

    reloaded.unmount();
  }, 15_000);
});
