// @vitest-environment jsdom
import { QueryClientProvider } from "@tanstack/react-query";
import { createMemoryHistory, RouterProvider } from "@tanstack/react-router";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import React from "react";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { resetPersistedWorkflowsV2 } from "../features/processes/processStudioV2Data";
import { I18nProvider } from "../i18n";
import { createOrciaQueryClient, createOrciaRouter } from "../router";
import { seedVitestPlatformSetupState } from "./vitest.setup";

describe("Story 7.1 — Studio V2 Autonomy Contract Modal, Zero Jargon & F5 Reload Survival", () => {
  beforeEach(() => {
    resetPersistedWorkflowsV2();
    seedVitestPlatformSetupState({});
  });

  afterEach(() => {
    cleanup();
  });

  it("opens AutonomyContractModal in Process Studio V2, signs without jargon, survives F5 reload, and revokes", async () => {
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

    const openBtn = await screen.findByTestId("studio-autonomy-contract-btn");
    fireEvent.click(openBtn);

    const modal = await screen.findByTestId("autonomy-contract-modal");
    expect(modal).toBeDefined();

    // Zero internal jargon visible in UI
    const modalText = modal.textContent ?? "";
    expect(modalText).not.toContain("Service Principal");
    expect(modalText).not.toContain("SERVICE_PRINCIPAL");
    expect(modalText).not.toContain("Tie-Break");
    expect(modalText).not.toContain("AUTONOMOUS_CONTRACT");
    expect(modalText).not.toContain("SignedApprovalToken");
    expect(modalText).not.toContain("TEAM_LEAD");
    expect(modalText).not.toContain("BU_LEAD");
    expect(modalText).not.toContain("HIGH_CRITICAL");

    // Verify contextual info trigger button exists and works
    const helpBtn = screen.getByTestId("autonomy-contract-help-trigger");
    fireEvent.click(helpBtn);

    // Wait for eligible service account option to hydrate from GET
    await waitFor(() => {
      const spSelect = screen.getByTestId("autonomy-contract-sp-select") as HTMLSelectElement;
      expect(spSelect.options.length).toBeGreaterThan(0);
    });

    // Sign contract
    fireEvent.click(screen.getByTestId("autonomy-contract-sign-btn"));

    await waitFor(() => {
      expect(screen.getByTestId("studio-autonomy-contract-active-badge")).toBeDefined();
    });

    // Simulate F5 reload (unmount -> render)
    firstRender.unmount();

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
      <I18nProvider initialLocale="fr">
        <QueryClientProvider client={secondQueryClient}>
          <RouterProvider router={secondRouter} />
        </QueryClientProvider>
      </I18nProvider>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("studio-autonomy-contract-active-badge")).toBeDefined();
    });

    // Re-open modal and revoke contract
    fireEvent.click(screen.getByTestId("studio-autonomy-contract-btn"));
    const revokeBtn = await screen.findByTestId("autonomy-contract-revoke-btn");
    fireEvent.click(revokeBtn);

    await waitFor(() => {
      expect(screen.queryByTestId("studio-autonomy-contract-active-badge")).toBeNull();
    });

    // F5 reload confirms revocation persists
    secondRender.unmount();
    const thirdQueryClient = createOrciaQueryClient();
    const thirdHistory = createMemoryHistory({
      initialEntries: ["/processes/studio/wf-01-qualification-prd"],
    });
    const thirdRouter = createOrciaRouter({
      queryClient: thirdQueryClient,
      history: thirdHistory,
    });
    await thirdRouter.load();

    render(
      <I18nProvider initialLocale="fr">
        <QueryClientProvider client={thirdQueryClient}>
          <RouterProvider router={thirdRouter} />
        </QueryClientProvider>
      </I18nProvider>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("studio-autonomy-contract-btn")).toBeDefined();
    });
    expect(screen.queryByTestId("studio-autonomy-contract-active-badge")).toBeNull();
  });
});
