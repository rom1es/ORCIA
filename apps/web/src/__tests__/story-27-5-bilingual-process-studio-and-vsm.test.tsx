// @vitest-environment jsdom
import { QueryClientProvider } from "@tanstack/react-query";
import { createMemoryHistory, RouterProvider } from "@tanstack/react-router";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import React from "react";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import {
  getInitialDeclarativePacks,
  getInitialVsmSpec,
  getInitialWorkflowsV2,
  INITIAL_DECLARATIVE_PACKS,
  INITIAL_VSM_SPEC,
  INITIAL_WORKFLOWS_V2,
  resetPersistedWorkflowsV2,
} from "../features/processes/processStudioV2Data";
import { I18nProvider } from "../i18n";
import { createOrciaQueryClient, createOrciaRouter } from "../router";
import { seedVitestPlatformSetupState } from "./vitest.setup";

describe("Story 27.5 — Bilingual FR/EN Process Studio v2, VSM & Catalog Data", () => {
  beforeEach(() => {
    resetPersistedWorkflowsV2();
    seedVitestPlatformSetupState({});
  });

  afterEach(() => {
    cleanup();
  });

  it("provides full French and English localized pack, VSM, and workflow catalog builders", () => {
    const frPacks = getInitialDeclarativePacks("fr");
    const enPacks = getInitialDeclarativePacks("en");
    expect(frPacks).toEqual(INITIAL_DECLARATIVE_PACKS);
    expect(enPacks[0]?.name).toContain("SDLC Pack");
    expect(enPacks[0]?.name).not.toContain("Chaîne");

    const frVsm = getInitialVsmSpec("fr");
    const enVsm = getInitialVsmSpec("en");
    expect(frVsm).toEqual(INITIAL_VSM_SPEC);
    expect(enVsm.title).toBe("Idea to Production");
    expect(enVsm.phases[0]?.name).toBe("Emergence & Framing");
    expect(enVsm.phases[0]?.steps[1]?.title).toBe("In Review");
    expect(enVsm.return_loops).toHaveLength(12);
    expect(enVsm.opportunities).toHaveLength(3);

    const frWfs = getInitialWorkflowsV2("fr");
    const enWfs = getInitialWorkflowsV2("en");
    expect(frWfs).toEqual(INITIAL_WORKFLOWS_V2);
    expect(enWfs[0]?.title).toBe(
      "Need Qualification, PRD Authoring & Jira Feature Creation",
    );
    expect(enWfs[0]?.sub_steps[0]?.name).toBe("Need qualification");
  });

  it("renders Interactive VSM, 6-Tab StepDetailSheet, and Process Studio in English without French leakage", async () => {
    const queryClient = createOrciaQueryClient();
    const history = createMemoryHistory({
      initialEntries: ["/processes/vsm/vsm-mon-compte-idea-to-prod"],
    });
    const router = createOrciaRouter({ queryClient, history });
    await router.load();

    const vsmView = render(
      <I18nProvider initialLocale="en">
        <QueryClientProvider client={queryClient}>
          <RouterProvider router={router} />
        </QueryClientProvider>
      </I18nProvider>,
    );

    expect(screen.getByTestId("vsm-back-to-hub-btn").textContent).toContain(
      "Back to Processes Hub",
    );
    expect(screen.getByTestId("vsm-step-card-02").textContent).toContain("In Review");
    fireEvent.click(screen.getByTestId("open-step-sheet-btn-02"));
    expect(screen.getByTestId("vsm-step-detail-sheet-02").textContent).toContain(
      "1. Overview & Comparison",
    );
    expect(screen.getByTestId("step-sheet-panel-overview").textContent).toContain(
      "TODAY (Current mode)",
    );
    vsmView.unmount();

    const studioQueryClient = createOrciaQueryClient();
    const studioHistory = createMemoryHistory({
      initialEntries: ["/processes/studio/wf-01-qualification-prd"],
    });
    const studioRouter = createOrciaRouter({
      queryClient: studioQueryClient,
      history: studioHistory,
    });
    await studioRouter.load();

    render(
      <I18nProvider initialLocale="en">
        <QueryClientProvider client={studioQueryClient}>
          <RouterProvider router={studioRouter} />
        </QueryClientProvider>
      </I18nProvider>,
    );

    expect(screen.getByTestId("studio-back-to-hub-btn").textContent).toContain(
      "Back to My Processes",
    );
    expect(screen.getByTestId("studio-workflow-version-badge").textContent).toContain(
      "Active · v1.0.0",
    );
    fireEvent.click(screen.getByTestId("studio-launch-interactive-run-btn"));
    expect(screen.getByTestId("interactive-run-hitl-drawer").textContent).toContain(
      "Expected action: your decision",
    );
  });
});
