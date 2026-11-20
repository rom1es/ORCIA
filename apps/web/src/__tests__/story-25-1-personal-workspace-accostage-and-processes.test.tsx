import { ProgressiveDay0AccostageBanner } from "@orcia/ui";
import { QueryClientProvider } from "@tanstack/react-query";
import { createMemoryHistory, RouterProvider } from "@tanstack/react-router";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import React from "react";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import {
  buildUnifiedAccostageMilestones,
  computeAccostageProgressSummary,
} from "../components/platformSetupAccostage";
import { buildPlatformSetupPutPayload } from "../components/platformSetupHydration";
import { clearPlatformSetupStorage } from "../components/platformSetupStore";
import { I18nProvider } from "../i18n";
import { enDictionary } from "../i18n/locales/en";
import { createOrciaQueryClient, createOrciaRouter } from "../router";
import { resetAuthSessionStore, useAuthSessionStore } from "../stores/authSessionStore";
import { backendState } from "./setup/mockBackendState";
import { resetVitestApiBackend, seedVitestPlatformSetupState } from "./vitest.setup";

async function renderCockpitWithRouter(initialLocale: "fr" | "en" = "fr") {
  const queryClient = createOrciaQueryClient();
  const history = createMemoryHistory({ initialEntries: ["/cockpit"] });
  const router = createOrciaRouter({ queryClient, history });
  await router.load();
  const view = render(
    <QueryClientProvider client={queryClient}>
      <I18nProvider initialLocale={initialLocale}>
        <RouterProvider router={router} />
      </I18nProvider>
    </QueryClientProvider>,
  );
  return { ...view, router };
}

describe("Story 25.1 — Personal Workspace, Unified 6-Step Accostage & Mes Processus Unlock", () => {
  beforeEach(() => {
    clearPlatformSetupStorage();
    resetAuthSessionStore();
    resetVitestApiBackend();
  });

  afterEach(() => {
    cleanup();
    clearPlatformSetupStorage();
    resetAuthSessionStore();
    resetVitestApiBackend();
  });

  it("excludes PRIVATE_USER personal workspaces from milestone 4 (First Team Space) and PUT /platform-setup-state", () => {
    const personalWs = {
      workspaceId: "0195f000-0000-7000-8000-000000000777",
      slug: "personal-0195f000-0000-7000-8000-000000000001",
      name: "Espace personnel — Alice",
      ownerOrgUnitId: "0192c4e0-0000-7000-8000-000000000001",
      visibilityMode: "PRIVATE_USER" as const,
      lifecyclePhase: "BUILD" as const,
      suggestedWorkflows: [],
      accessMode: "CONTRIBUTOR_ACTION_REQUIRED" as const,
      finopsCostUsd: 0,
    };
    const summaryOnlyPersonal = computeAccostageProgressSummary({
      accostageCounts: null,
      platformAdmin: {
        displayName: "Alice",
        email: "alice@orcia.test",
        role: "PLATFORM_ADMIN",
      },
      orgUnits: [],
      llmTiers: [],
      workspaces: [personalWs],
      datasources: [],
      workflows: [],
      packs: [],
    });

    expect(summaryOnlyPersonal.hasWorkspaces).toBe(false);
    expect(summaryOnlyPersonal.completedCount).toBe(1);

    const frMilestones = buildUnifiedAccostageMilestones({
      isFr: true,
      summary: summaryOnlyPersonal,
      roles: ["PLATFORM_ADMIN"],
    });
    const enMilestones = buildUnifiedAccostageMilestones({
      isFr: false,
      summary: summaryOnlyPersonal,
      roles: ["PLATFORM_ADMIN"],
    });
    expect(frMilestones).toHaveLength(6);
    expect(frMilestones[3]?.title).toBe("4. Premier Espace d'équipe");
    expect(enMilestones[3]?.title).toBe("4. First Team Space");
    expect(frMilestones[3]?.completed).toBe(false);

    const putPayload = buildPlatformSetupPutPayload({
      orgUnits: [],
      rbacGrants: [],
      llmTiers: [],
      workspaces: [
        personalWs,
        {
          workspaceId: "0195f000-0000-7000-8000-000000000888",
          slug: "team-shared-space",
          name: "Espace Équipe",
          ownerOrgUnitId: "0192c4e0-0000-7000-8000-000000000001",
          visibilityMode: "STANDARD",
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
      catalogItems: [],
      ontologyConcepts: [],
      auditEvents: [],
    });
    expect(putPayload.workspaces).toHaveLength(1);
    expect((putPayload.workspaces?.[0] as { slug?: string } | undefined)?.slug).toBe(
      "team-shared-space",
    );

    // Verify EN locale format template ("{completed} of {total} completed") & milestone 4 label
    render(
      <ProgressiveDay0AccostageBanner
        completedCount={2}
        totalCount={6}
        adminCreated={true}
        adminDisplayName="Alice"
        milestones={enMilestones}
        labels={enDictionary.progressiveAccostage}
      />,
    );
    expect(screen.getByTestId("accostage-progress-pill").textContent).toBe("2 of 6 completed");
    expect(screen.getByTestId("accostage-milestone-step-workspaces").textContent).toContain(
      "4. First Team Space",
    );
  });

  it("renders unified 6-milestone banner without Step 1/2/3 cards, greys out Mes Processus at 0 AI model, and unlocks both sidebar & Cockpit card at 1 AI model with Personal Workspace", async () => {
    seedVitestPlatformSetupState(
      {
        org_units: [],
        workspaces: [],
        llm_tiers: [],
        ai_model_mappings: [],
        datasources: [],
        workflows: [],
      },
      { email: "alice.admin@orcia.fr", displayName: "Alice Admin", roles: ["PLATFORM_ADMIN"] },
    );
    backendState.workspaces = [
      {
        id: "0195f000-0000-7000-8000-000000000777",
        slug: "personal-0195f000-0000-7000-8000-000000000001",
        name: "Espace personnel — Alice Admin",
        owner_org_unit_id: "0192c4e0-0000-7000-8000-000000000001",
        owner_org_unit_name: "ORCIA Root Organization",
        visibility_mode: "PRIVATE_USER",
        lifecycle_phase: "BUILD",
        effective_role: "PLATFORM_ADMIN",
        access_mode: "CONTRIBUTOR_ACTION_REQUIRED",
        access_origin: "DIRECT_TEAM",
        is_personal: true,
        finops_cost_usd: 0,
      },
    ];
    useAuthSessionStore.getState().setAuthSession({
      isAuthenticated: true,
      isHydrating: false,
      email: "alice.admin@orcia.fr",
      displayName: "Alice Admin",
      roles: ["PLATFORM_ADMIN"],
    });

    const firstRender = await renderCockpitWithRouter("fr");

    await waitFor(() => {
      expect(screen.getByTestId("accostage-progress-pill").textContent).toBe("1 / 6 complétées");
    });

    // Zero redundant Step 1 / Step 2 / Step 3 cards and zero collapse toggle when < 6/6
    expect(screen.queryByTestId("welcome-setup-3step-wizard")).toBeNull();
    expect(screen.queryByTestId("welcome-setup-step1-card")).toBeNull();
    expect(screen.queryByTestId("welcome-setup-step2-card")).toBeNull();
    expect(screen.queryByTestId("welcome-setup-step3-card")).toBeNull();
    expect(screen.queryByTestId("accostage-compact-toggle-btn")).toBeNull();

    // All 6 milestones present, 4th is "4. Premier Espace d'équipe" & remains incomplete
    const list = screen.getByTestId("accostage-milestones-list");
    expect(list.querySelectorAll("button")).toHaveLength(6);
    const adminBtn = screen.getByTestId("accostage-milestone-first-admin");
    const wsBtn = screen.getByTestId("accostage-milestone-step-workspaces");
    expect(wsBtn.textContent).toContain("4. Premier Espace d'équipe");
    expect(wsBtn.getAttribute("data-completed")).toBe("false");
    expect(adminBtn.getAttribute("data-completed")).toBe("true");
    expect(adminBtn.className).toContain("bg-[var(--color-gate-pass-bg)]");
    expect(adminBtn.className).toContain("border-[var(--color-gate-pass)]");
    expect(adminBtn.className).toContain("text-[var(--color-gate-pass)]");
    expect(adminBtn.className).toContain("grid-cols-");
    expect(adminBtn.querySelector('[data-orcia-icon="check"]')).not.toBeNull();
    expect(wsBtn.querySelector('[data-orcia-icon="arrowRight"]')).not.toBeNull();

    // 0 AI models -> Mes Processus is disabled BOTH in sidebar and in CockpitOrientationCards
    expect((screen.getByTestId("eight-menu-item-processes") as HTMLButtonElement).disabled).toBe(true);
    expect(
      (screen.getByTestId("cockpit-orientation-card-processes") as HTMLButtonElement).disabled,
    ).toBe(true);
    expect(
      (screen.getByTestId("cockpit-orientation-card-assistant") as HTMLButtonElement).disabled,
    ).toBe(true);

    firstRender.unmount();

    // Now configure 1 AI model (without creating any team space) -> 2/6 and Mes Processus UNLOCKS!
    clearPlatformSetupStorage();
    seedVitestPlatformSetupState(
      {
        org_units: [],
        workspaces: [],
        llm_tiers: [
          {
            tier: "medium",
            primaryModel: "qwen2.5-coder:14b",
            secondaryModel: "",
            modelFamily: "ollama",
            defaultEffort: "balanced",
          },
        ],
        ai_model_mappings: [
          {
            id: "01930000-0000-7000-8000-000000000101",
            scope_level: "GLOBAL",
            scope_id: null,
            inference_tier: "medium",
            usage: "reasoning",
            is_active: true,
            provider: "ollama",
            model_name: "qwen2.5-coder:14b",
          },
        ],
        datasources: [],
        workflows: [],
      },
      { email: "alice.admin@orcia.fr", displayName: "Alice Admin", roles: ["PLATFORM_ADMIN"] },
    );
    backendState.workspaces = [
      {
        id: "0195f000-0000-7000-8000-000000000777",
        slug: "personal-0195f000-0000-7000-8000-000000000001",
        name: "Espace personnel — Alice Admin",
        owner_org_unit_id: "0192c4e0-0000-7000-8000-000000000001",
        owner_org_unit_name: "ORCIA Root Organization",
        visibility_mode: "PRIVATE_USER",
        lifecycle_phase: "BUILD",
        effective_role: "PLATFORM_ADMIN",
        access_mode: "CONTRIBUTOR_ACTION_REQUIRED",
        access_origin: "DIRECT_TEAM",
        is_personal: true,
        finops_cost_usd: 0,
      },
    ];
    useAuthSessionStore.getState().setAuthSession({
      isAuthenticated: true,
      isHydrating: false,
      email: "alice.admin@orcia.fr",
      displayName: "Alice Admin",
      roles: ["PLATFORM_ADMIN"],
    });

    const secondRender = await renderCockpitWithRouter("fr");
    await waitFor(() => {
      expect(screen.getByTestId("accostage-progress-pill").textContent).toBe("2 / 6 complétées");
    });

    // Personal workspace still does NOT complete milestone 4 ("4. Premier Espace d'équipe")
    const wsBtn2 = screen.getByTestId("accostage-milestone-step-workspaces");
    expect(wsBtn2.textContent).toContain("4. Premier Espace d'équipe");
    expect(wsBtn2.getAttribute("data-completed")).toBe("false");
    expect(screen.queryByTestId("accostage-compact-toggle-btn")).toBeNull();

    // BOTH sidebar Mes Processus AND Cockpit orientation card Mes Processus are unlocked!
    await waitFor(() => {
      expect(
        (screen.getByTestId("eight-menu-item-processes") as HTMLButtonElement).disabled,
      ).toBe(false);
      expect(
        (screen.getByTestId("cockpit-orientation-card-processes") as HTMLButtonElement).disabled,
      ).toBe(false);
      expect(
        (screen.getByTestId("cockpit-orientation-card-assistant") as HTMLButtonElement).disabled,
      ).toBe(false);
    });

    // Clicking the unlocked Cockpit Processes card navigates to /processes
    fireEvent.click(screen.getByTestId("cockpit-orientation-card-processes"));
    await waitFor(() => {
      expect(secondRender.router.state.location.pathname).toBe("/processes");
    });
  });
});
