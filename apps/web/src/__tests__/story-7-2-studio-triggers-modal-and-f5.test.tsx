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

describe("Story 7.2 — Studio V2 WorkflowTriggersModal, Opt-In Help, Write-Only Secret & F5", () => {
  beforeEach(() => {
    resetPersistedWorkflowsV2();
    seedVitestPlatformSetupState({});
  });

  afterEach(() => {
    cleanup();
  });

  it("manages triggers without jargon, keeps opt-in unchecked by default, and survives F5", async () => {
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

    // 1. Sign autonomy contract first
    fireEvent.click(await screen.findByTestId("studio-autonomy-contract-btn"));
    await waitFor(() => {
      const spSelect = screen.getByTestId("autonomy-contract-sp-select") as HTMLSelectElement;
      expect(spSelect.options.length).toBeGreaterThan(0);
    });
    fireEvent.click(screen.getByTestId("autonomy-contract-sign-btn"));
    await waitFor(() => {
      expect(screen.getByTestId("studio-autonomy-contract-active-badge")).toBeDefined();
    });

    // 2. Open Triggers modal
    fireEvent.click(screen.getByTestId("studio-triggers-btn"));
    const modal = await screen.findByTestId("workflow-triggers-modal");
    expect(modal).toBeDefined();

    // Zero internal technical jargon
    const modalText = modal.textContent ?? "";
    expect(modalText).not.toContain("Service Principal");
    expect(modalText).not.toContain("CIRCUIT_OPEN");
    expect(modalText).not.toContain("OUTBOX_EVENT");
    expect(modalText).not.toContain("LOG_SINK_ALERT");
    expect(modalText).not.toContain("MANUAL_AUTONOMOUS");
    expect(modalText).not.toContain("DBOS");

    // 3. Opt-in auto-help checkbox on OUTBOX_EVENT must be UNCHECKED by default
    const typeSelect = screen.getByTestId("trigger-create-type-select") as HTMLSelectElement;
    fireEvent.change(typeSelect, { target: { value: "OUTBOX_EVENT" } });
    const autoHelpCheckbox = screen.getByTestId(
      "trigger-create-auto-help-checkbox",
    ) as HTMLInputElement;
    expect(autoHelpCheckbox.checked).toBe(false);

    // 4. Create WEBHOOK trigger with Write-Only SecretField
    fireEvent.change(typeSelect, { target: { value: "WEBHOOK" } });
    fireEvent.click(screen.getByTestId("secret-field-replace-toggle-btn"));
    const secretValue = "whsec-studio-canary-7-2"; // pragma: allowlist secret
    fireEvent.change(screen.getByTestId("secret-field-write-only-input"), {
      target: { value: secretValue },
    });
    fireEvent.click(screen.getByTestId("secret-field-commit-set-btn"));
    fireEvent.click(screen.getByTestId("trigger-create-submit-btn"));

    await waitFor(() => {
      expect(screen.getByTestId("workflow-triggers-list")).toBeDefined();
    });
    // Raw secret never rendered in DOM
    expect(screen.getByTestId("workflow-triggers-modal").textContent).not.toContain(secretValue);

    // 5. Simulate F5 reload (unmount -> render)
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

    render(
      <I18nProvider initialLocale="fr">
        <QueryClientProvider client={secondQueryClient}>
          <RouterProvider router={secondRouter} />
        </QueryClientProvider>
      </I18nProvider>,
    );

    await waitFor(() => {
      expect(screen.getByTestId("studio-triggers-btn").textContent).toContain("(1)");
    });
    fireEvent.click(screen.getByTestId("studio-triggers-btn"));
    await waitFor(() => {
      expect(screen.getByTestId("workflow-triggers-list")).toBeDefined();
    });

    // Fire and delete trigger
    const fireBtn = screen.getByText("Déclencher maintenant").closest("button");
    expect(fireBtn).not.toBeNull();
    fireEvent.click(fireBtn!);
    await waitFor(() => {
      expect(screen.getByTestId("studio-status-banner").textContent).toContain("déclenchée");
    });

    const delBtn = screen.getByText("Supprimer").closest("button");
    expect(delBtn).not.toBeNull();
    fireEvent.click(delBtn!);
    await waitFor(() => {
      expect(screen.getByTestId("workflow-triggers-empty")).toBeDefined();
    });
  });
});
