// @vitest-environment jsdom
import { QueryClientProvider } from "@tanstack/react-query";
import { createMemoryHistory, RouterProvider } from "@tanstack/react-router";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import React from "react";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { resetPersistedWorkflowsV2 } from "../features/processes/processStudioV2Data";
import { I18nProvider } from "../i18n";
import { createOrciaQueryClient, createOrciaRouter } from "../router";
import {
  getRecordedVitestApiCalls,
  seedVitestPlatformSetupState,
} from "./vitest.setup";

const FORBIDDEN_JARGON_REGEX =
  /\b(DBOS|asyncio|SQL|Redis|SSE|Claim-Check|déterministe|non-déterministe|deterministic|non-deterministic)\b/i;

function extractVisibleDomText(container: HTMLElement): string {
  const clone = container.cloneNode(true) as HTMLElement;
  for (const hidden of Array.from(clone.querySelectorAll(".sr-only, [aria-hidden='true']"))) {
    hidden.remove();
  }
  return clone.textContent ?? "";
}

describe("Story 16.3 — Dual-Mode Processes Hub & Studio (Goal-Driven vs Milestone-Driven)", () => {
  beforeEach(() => {
    resetPersistedWorkflowsV2();
    seedVitestPlatformSetupState({});
  });

  afterEach(() => {
    cleanup();
  });

  it("renders ProcessesHubPage (/processes) in FR and EN with Goal-driven & Milestone-driven badges and zero technical jargon", async () => {
    for (const locale of ["fr", "en"] as const) {
      const queryClient = createOrciaQueryClient();
      const history = createMemoryHistory({ initialEntries: ["/processes"] });
      const router = createOrciaRouter({ queryClient, history });
      await router.load();

      const view = render(
        <I18nProvider initialLocale={locale}>
          <QueryClientProvider client={queryClient}>
            <RouterProvider router={router} />
          </QueryClientProvider>
        </I18nProvider>,
      );

      expect(screen.getByTestId("processes-hub-v2-page")).toBeDefined();
      const goalBadge = screen.getByTestId(
        "workflow-card-mode-badge-wf-generate-orcia-documentation",
      );
      const milestoneBadge = screen.getByTestId(
        "workflow-card-mode-badge-wf-01-qualification-prd",
      );

      if (locale === "fr") {
        expect(goalBadge.textContent).toContain("Piloté par l'objectif");
        expect(milestoneBadge.textContent).toContain("Piloté par les jalons");
      } else {
        expect(goalBadge.textContent).toContain("Goal-driven");
        expect(milestoneBadge.textContent).toContain("Milestone-driven");
      }

      const visibleText = extractVisibleDomText(
        screen.getByTestId("processes-hub-v2-page"),
      );
      expect(visibleText).not.toMatch(FORBIDDEN_JARGON_REGEX);

      view.unmount();
    }
  });

  it("switches Studio between Goal-driven and Milestone-driven modes, preserves draft inputs across toggles, persists via @orcia/api-client, and survives F5 reload", async () => {
    const queryClient = createOrciaQueryClient();
    const history = createMemoryHistory({
      initialEntries: ["/processes/studio/wf-01-qualification-prd"],
    });
    const router = createOrciaRouter({ queryClient, history });
    await router.load();

    const firstRender = render(
      <I18nProvider initialLocale="fr">
        <QueryClientProvider client={queryClient}>
          <RouterProvider router={router} />
        </QueryClientProvider>
      </I18nProvider>,
    );

    expect(screen.getByTestId("workflow-orchestration-mode-selector")).toBeDefined();
    expect(
      screen.getByTestId("mode-option-milestone-driven").getAttribute("aria-checked"),
    ).toBe("true");
    expect(screen.getByTestId("studio-block-2-deterministic-substeps")).toBeDefined();

    // 1. Customize a milestone sub-step first (disable 'jira')
    fireEvent.click(screen.getByTestId("toggle-substep-enabled-jira"));

    // 2. Switch to Goal-driven mode -> Block 2 switches to Goal-driven editor
    fireEvent.click(screen.getByTestId("mode-option-goal-driven"));
    expect(
      screen.getByTestId("mode-option-goal-driven").getAttribute("aria-checked"),
    ).toBe("true");
    expect(screen.queryByTestId("studio-block-2-deterministic-substeps")).toBeNull();
    expect(screen.getByTestId("studio-block-2-goal-driven")).toBeDefined();

    // Enter objective & select a specialist delegate agent
    const objectiveTextarea = screen.getByTestId(
      "studio-goal-reflexive-objective-input",
    ) as HTMLTextAreaElement;
    fireEvent.change(objectiveTextarea, {
      target: {
        value:
          "Analyser les retours clients et consolider les priorités métier avec indicateurs de valeur.",
      },
    });
    fireEvent.click(screen.getByTestId("toggle-delegate-agent-orchestrateur-produit"));

    // 3. Toggle back to Milestone-driven -> sub-steps ('jira' skipped) preserved!
    fireEvent.click(screen.getByTestId("mode-option-milestone-driven"));
    expect(screen.getByTestId("studio-block-2-deterministic-substeps")).toBeDefined();
    expect(screen.getByTestId("toggle-substep-enabled-jira").textContent).toContain(
      "Étape ignorée",
    );

    // 4. Toggle back to Goal-driven -> objective & delegate agent draft preserved!
    fireEvent.click(screen.getByTestId("mode-option-goal-driven"));
    expect(
      (screen.getByTestId("studio-goal-reflexive-objective-input") as HTMLTextAreaElement)
        .value,
    ).toContain("Analyser les retours clients");
    expect(
      screen
        .getByTestId("toggle-delegate-agent-orchestrateur-produit")
        .getAttribute("aria-pressed"),
    ).toBe("true");

    // 5. Save draft via @orcia/api-client (PUT /api/v1/workflows/v2/wf-01-qualification-prd)
    fireEvent.click(screen.getByTestId("studio-save-draft-btn"));
    await waitFor(() => {
      const putCalls = getRecordedVitestApiCalls().filter(
        (c) =>
          c.method === "PUT" &&
          c.path === "/api/v1/workflows/v2/wf-01-qualification-prd",
      );
      expect(putCalls.length).toBeGreaterThanOrEqual(1);
    });

    // Zero technical jargon on FR Studio page
    expect(
      extractVisibleDomText(screen.getByTestId("workflow-five-blocks-studio-page")),
    ).not.toMatch(FORBIDDEN_JARGON_REGEX);

    // 6. Gate 3 F5 Reload Survival: clear localStorage cache, unmount, and re-mount from API GET!
    firstRender.unmount();
    resetPersistedWorkflowsV2();

    const secondQueryClient = createOrciaQueryClient();
    const secondHistory = createMemoryHistory({
      initialEntries: ["/processes/studio/wf-01-qualification-prd"],
    });
    const secondRouter = createOrciaRouter({
      queryClient: secondQueryClient,
      history: secondHistory,
    });
    await secondRouter.load();

    const secondRender = render(
      <I18nProvider initialLocale="en">
        <QueryClientProvider client={secondQueryClient}>
          <RouterProvider router={secondRouter} />
        </QueryClientProvider>
      </I18nProvider>,
    );

    await waitFor(() => {
      expect(
        screen.getByTestId("mode-option-goal-driven").getAttribute("aria-checked"),
      ).toBe("true");
      expect(
        (screen.getByTestId("studio-goal-reflexive-objective-input") as HTMLTextAreaElement)
          .value,
      ).toContain("Analyser les retours clients");
    });

    // Zero technical jargon on EN Studio page as well
    expect(
      extractVisibleDomText(screen.getByTestId("workflow-five-blocks-studio-page")),
    ).not.toMatch(FORBIDDEN_JARGON_REGEX);

    secondRender.unmount();
  });
});
