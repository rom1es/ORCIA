import { QueryClientProvider } from "@tanstack/react-query";
import { createMemoryHistory, RouterProvider } from "@tanstack/react-router";
import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import React from "react";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { clearPlatformSetupStorage } from "../components/platformSetupStore";
import { createOrciaQueryClient, createOrciaRouter } from "../router";
import { useAuthSessionStore } from "../stores/authSessionStore";
import { seedVitestPlatformSetupState } from "./vitest.setup";
import { seedVitestOntologyState } from "./vitestOntologyMockHandlers";

describe("Story 20.2 — Menu Glossaire (/ontology), Séparation /help, ONTOLOGY_LEAD & Promotions L4->L1", () => {
  beforeEach(() => {
    clearPlatformSetupStorage();
    seedVitestPlatformSetupState(
      {
        org_units: [
          {
            id: "bu-fin",
            slug: "bu-fin",
            name: "BU Finance",
            level: "BU",
            parentId: "scope-global",
            ontologyLeadUserIds: ["sophie@orcia.ia"],
          },
          {
            id: "team-compta",
            slug: "team-compta",
            name: "Équipe Compta",
            level: "TEAM",
            parentId: "bu-fin",
            leadUserIds: ["marc@orcia.ia"],
            memberUserIds: ["nadia@orcia.ia"],
          },
        ],
        rbac_grants: [],
        llm_tiers: [],
        workspaces: [
          {
            workspaceId: "ws-compta",
            name: "Espace Compta",
            visibilityMode: "STANDARD",
            ownerOrgUnitId: "team-compta",
            ownerOrgUnitName: "Équipe Compta",
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
      },
      { email: "admin@orcia.ia", displayName: "Admin Plateforme", roles: ["PLATFORM_ADMIN"] },
    );
  });

  afterEach(() => {
    cleanup();
  });

  it("navigates via Mes Espaces -> Glossaire to /ontology (no /showcase banner) while 8-item sidebar Aide opens /help (Showcase + Help Center)", async () => {
    const queryClient = createOrciaQueryClient();
    const history = createMemoryHistory({ initialEntries: ["/cockpit"] });
    const router = createOrciaRouter({ queryClient, history });
    await router.load();

    render(
      <QueryClientProvider client={queryClient}>
        <RouterProvider router={router} />
      </QueryClientProvider>,
    );

    const helpBtn = screen.getByTestId("eight-menu-item-help");
    expect(helpBtn.textContent).toContain("Aide");
    expect(screen.queryByTestId("eight-menu-item-glossary")).toBeNull();

    fireEvent.click(screen.getByTestId("eight-menu-item-spaces"));
    await waitFor(() => {
      expect(router.state.location.pathname).toBe("/spaces");
    });
    const glossaryLink = await screen.findByTestId("spaces-open-glossary-link");
    fireEvent.click(glossaryLink);

    await waitFor(() => {
      expect(screen.getByTestId("ontology-create-concept-card")).toBeDefined();
      expect(screen.getByTestId("ontology-tab-proposals")).toBeDefined();
    });
    expect(screen.queryByTestId("help-showcase-site-banner")).toBeNull();
    expect(screen.queryByTestId("help-menu-center-view")).toBeNull();

    fireEvent.click(helpBtn);
    await waitFor(() => {
      expect(screen.getByTestId("help-menu-center-view")).toBeDefined();
    });
    expect(screen.getByTestId("help-showcase-site-banner")).toBeDefined();
    expect(screen.getByTestId("open-orcia-showcase-site-btn")).toBeDefined();
    expect(screen.getAllByTestId("contextual-help-hybrid-panel").length).toBeGreaterThanOrEqual(1);
  });

  it("persists creation, step-up promotion, collision review by ONTOLOGY_LEAD, and survives F5 reload", async () => {
    seedVitestOntologyState([
      {
        id: "c-l2-existing",
        concept_key: "marge-nette-existing",
        canonical_term: "Marge Nette",
        level: "2_DOMAIN",
        scope_id: "bu-fin",
        definition_text: "Définition existante BU Finance.",
        parent_concept_id: null,
        synonyms: [],
        banned_terms: [],
        profile_translations: {},
        expected_schema: {},
        introduced_in_snapshot_id: null,
        snapshot_branch_status: "ACTIVE",
      },
    ]);

    useAuthSessionStore.getState().setAuthSession({
      isAuthenticated: true,
      email: "admin@orcia.ia",
      displayName: "Admin Plateforme",
      roles: ["PLATFORM_ADMIN"],
      activeHat: "PLATFORM_ADMIN",
    });

    const queryClient1 = createOrciaQueryClient();
    const history1 = createMemoryHistory({ initialEntries: ["/ontology"] });
    const router1 = createOrciaRouter({ queryClient: queryClient1, history: history1 });
    await router1.load();

    const firstView = render(
      <QueryClientProvider client={queryClient1}>
        <RouterProvider router={router1} />
      </QueryClientProvider>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("ontology-level-select")).toBeDefined();
    });

    const levelSelect = screen.getByTestId("ontology-level-select") as HTMLSelectElement;
    const teamOptIdx = Array.from(levelSelect.options).findIndex((o) =>
      o.text.includes("Équipe Compta"),
    );
    expect(teamOptIdx).toBeGreaterThanOrEqual(0);
    fireEvent.change(levelSelect, { target: { value: String(teamOptIdx) } });

    fireEvent.change(screen.getByTestId("ontology-concept-name-input"), {
      target: { value: "Marge Nette" },
    });
    fireEvent.change(screen.getByTestId("ontology-concept-def-input"), {
      target: { value: "Marge nette équipe Compta" },
    });
    fireEvent.click(screen.getByTestId("ontology-create-concept-btn"));

    await waitFor(() => {
      expect(screen.getByTestId("ontology-card-3-team-team-compta-marge-nette")).toBeDefined();
    });

    // Propose step-up promotion (L3 Team -> L2 BU Finance)
    fireEvent.click(screen.getByTestId("promote-btn-3-team-team-compta-marge-nette"));
    await waitFor(() => {
      expect(screen.getByTestId("ontology-tab-proposals").textContent).toContain("(1)");
    });

    // Switch session to ONTOLOGY_LEAD (Sophie) and approve in Propositions à valider
    useAuthSessionStore.getState().setAuthSession({
      isAuthenticated: true,
      email: "sophie@orcia.ia",
      displayName: "Sophie Référente",
      roles: ["ONTOLOGY_LEAD"],
      activeHat: "ONTOLOGY_LEAD",
    });

    firstView.unmount();

    const queryClient2 = createOrciaQueryClient();
    const history2 = createMemoryHistory({ initialEntries: ["/ontology"] });
    const router2 = createOrciaRouter({ queryClient: queryClient2, history: history2 });
    await router2.load();

    render(
      <QueryClientProvider client={queryClient2}>
        <RouterProvider router={router2} />
      </QueryClientProvider>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("ontology-tab-proposals").textContent).toContain("(1)");
    });
    // Sophie (ONTOLOGY_LEAD) only sees 2_DOMAIN / 3_TEAM / 4_WORKSPACE in her writable dropdown, NEVER 1_ENTERPRISE
    const sophieSelect = screen.getByTestId("ontology-level-select") as HTMLSelectElement;
    expect(
      Array.from(sophieSelect.options).some((o) => o.text.includes("Organisation (Global)")),
    ).toBe(false);

    fireEvent.click(screen.getByTestId("ontology-tab-proposals"));
    const propCard = await screen.findByTestId("promotion-proposal-card-prop-1");
    expect(propCard.textContent).toContain("Marge Nette");
    expect(screen.getByTestId("promotion-collision-alert-prop-1").textContent).toContain(
      "Définition existante BU Finance",
    );

    fireEvent.click(screen.getByTestId("approve-promotion-btn-prop-1"));
    await waitFor(() => {
      expect(screen.getByTestId("ontology-tab-proposals").textContent).toContain("(0)");
    });
  });
});
