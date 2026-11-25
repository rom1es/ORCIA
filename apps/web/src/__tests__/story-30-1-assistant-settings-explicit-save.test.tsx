import { QueryClientProvider } from "@tanstack/react-query";
import { createMemoryHistory, RouterProvider } from "@tanstack/react-router";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import React from "react";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { clearPlatformSetupStorage } from "../components/platformSetupStorageHelpers";
import { resetBackgroundAssistantStreamForTests } from "../features/inbox/assistantBackgroundStreamStore";
import { createOrciaQueryClient, createOrciaRouter } from "../router";
import { useAuthSessionStore } from "../stores/authSessionStore";
import { backendState } from "./setup/mockBackendState";
import { resetVitestApiBackend, seedVitestPlatformSetupState } from "./vitest.setup";

const WS_ID = "0195f000-0000-7000-8000-000000000301";
const TEAM_ID = "0192c4e0-0000-7000-8000-000000000103";

function seedAdmin(): void {
  seedVitestPlatformSetupState(
    {
      org_units: [
        { id: "0192c4e0-0000-7000-8000-000000000101", name: "Direction Ops", slug: "dir-ops", level: "BU", parentId: null, billingEnabled: true },
        { id: TEAM_ID, name: "Équipe Socle", slug: "equipe-socle", level: "TEAM", parentId: "0192c4e0-0000-7000-8000-000000000101", billingEnabled: true },
      ],
      workspaces: [
        { workspaceId: WS_ID, name: "Espace Mode A", visibilityMode: "STANDARD", ownerOrgUnitName: "Équipe Socle", lifecyclePhase: "BUILD", suggestedWorkflows: [], accessMode: "CONTRIBUTOR_ACTION_REQUIRED", finopsCostUsd: 0 },
      ],
      ai_model_mappings: [
        { id: "01930000-0000-7000-8000-000000000011", scope_level: "GLOBAL", scope_id: null, inference_tier: "medium", usage: "chat", is_active: true, draining: false, provider: "ollama", model_name: "qwen3:8b", supports_tools: true },
      ],
      datasources: [],
    },
    { email: "admin.30.1@orcia.fr", displayName: "Admin 30.1", roles: ["PLATFORM_ADMIN"] },
  );
  useAuthSessionStore.getState().setAuthSession({
    isAuthenticated: true,
    email: "admin.30.1@orcia.fr",
    displayName: "Admin 30.1",
    roles: ["PLATFORM_ADMIN"],
    activeHat: "PLATFORM_ADMIN",
  });
}

async function mountAssistantApp() {
  const queryClient = createOrciaQueryClient();
  const history = createMemoryHistory({ initialEntries: ["/assistant"] });
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
  resetBackgroundAssistantStreamForTests();
});

afterEach(() => {
  cleanup();
});

describe("Story 30.1 — Explicit Save, Dirty Guard, Inline Modal Errors & Empty Personal Instructions", () => {
  it("prevents keystroke auto-save, persists empty personal instructions on Save, and closes cleanly afterward", async () => {
    seedAdmin();
    await mountAssistantApp();

    fireEvent.click(await screen.findByTestId("assistant-open-governance-btn"));
    const modal = await screen.findByTestId("assistant-governance-container");
    const instrInput = screen.getByTestId("assistant-user-instructions-input") as HTMLTextAreaElement;
    expect(instrInput.value).toBe("");

    // Typing does NOT fire PUT and does NOT flash autosaved badge
    fireEvent.change(instrInput, { target: { value: "Règle temporaire" } });
    fireEvent.change(screen.getByTestId("assistant-gov-tone-select"), { target: { value: "SYNTHETIC" } });
    expect(
      backendState.recordedCalls.filter((c) => c.path.includes("/api/v1/assistant/governance/mode-a/")),
    ).toHaveLength(0);
    expect(screen.queryByTestId("assistant-gov-autosaved-badge")).toBeNull();

    // Explicit Save awaits PUT + GET refresh, then shows saved badge and keeps modal open
    fireEvent.click(screen.getByTestId("assistant-save-user-prefs-btn"));
    await waitFor(() => {
      const putCalls = backendState.recordedCalls.filter(
        (c) => c.path === "/api/v1/assistant/governance/mode-a/user" && c.method === "PUT",
      );
      expect(putCalls).toHaveLength(1);
      expect(within(modal).getByTestId("assistant-gov-autosaved-badge")).toBeDefined();
    });

    // Clear personal instructions back to "" and explicitly save
    fireEvent.change(instrInput, { target: { value: "" } });
    fireEvent.click(screen.getByTestId("assistant-save-user-prefs-btn"));
    await waitFor(() => {
      const putCalls = backendState.recordedCalls.filter(
        (c) => c.path === "/api/v1/assistant/governance/mode-a/user" && c.method === "PUT",
      );
      expect(putCalls).toHaveLength(2);
      expect((putCalls[1]?.body as Record<string, unknown>).personal_instructions).toBe("");
      expect(within(modal).getByTestId("assistant-gov-autosaved-badge")).toBeDefined();
    });

    // Clicking Fermer after Save closes cleanly without unsaved alert
    expect(screen.getByTestId("assistant-gov-cancel-btn").textContent).toBe("Fermer");
    fireEvent.click(screen.getByTestId("assistant-gov-cancel-btn"));
    expect(screen.queryByTestId("assistant-gov-unsaved-changes-alert")).toBeNull();
    expect(screen.queryByTestId("assistant-governance-container")).toBeNull();
  });

  it("renders inline modal alert on PUT failure without saved badge and discards local draft on confirm", async () => {
    seedAdmin();
    await mountAssistantApp();

    fireEvent.click(await screen.findByTestId("assistant-open-governance-btn"));
    const modal = await screen.findByTestId("assistant-governance-container");

    // Switch to Tab 2 and enter invalid (<3 chars) instructions to trigger 422 RFC 9457 error
    fireEvent.click(screen.getByTestId("assistant-gov-tab-WORKSPACE_SETTINGS"));
    fireEvent.change(screen.getByTestId("assistant-workspace-instructions-input"), {
      target: { value: "ab" },
    });
    fireEvent.click(screen.getByTestId("assistant-save-user-prefs-btn"));

    await waitFor(() => {
      const errBanner = within(modal).getByTestId("assistant-gov-error-banner");
      expect(errBanner.getAttribute("role")).toBe("alert");
      expect(errBanner.textContent).toContain("3 caractères");
    });
    expect(within(modal).queryByTestId("assistant-gov-autosaved-badge")).toBeNull();
    expect(screen.getByTestId("assistant-gov-cancel-btn").textContent).toBe("Annuler");

    // Clicking Annuler -> Quitter sans enregistrer discards draft without touching server
    fireEvent.click(screen.getByTestId("assistant-gov-cancel-btn"));
    expect(screen.getByTestId("assistant-gov-unsaved-changes-alert")).toBeDefined();
    fireEvent.click(screen.getByTestId("assistant-gov-unsaved-discard-btn"));
    expect(screen.queryByTestId("assistant-governance-container")).toBeNull();
  });
});
