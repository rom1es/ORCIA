import { QueryClientProvider } from "@tanstack/react-query";
import { createMemoryHistory, RouterProvider } from "@tanstack/react-router";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import React from "react";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { clearPlatformSetupStorage } from "../components/platformSetupStorageHelpers";
import { clearSavedAssistantConversationsStorage } from "../features/inbox/savedConversationsStore";
import { resetBackgroundAssistantStreamForTests } from "../features/inbox/assistantBackgroundStreamStore";
import { createOrciaQueryClient, createOrciaRouter } from "../router";
import { useAuthSessionStore } from "../stores/authSessionStore";
import { backendState } from "./setup/mockBackendState";
import { resetVitestApiBackend, seedVitestPlatformSetupState } from "./vitest.setup";

const WS_ID = "0195f000-0000-7000-8000-000000000301";
const TEAM_ID = "0192c4e0-0000-7000-8000-000000000103";

function seedAdminWithModel(supportsTools: boolean): void {
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
        { id: "01930000-0000-7000-8000-000000000011", scope_level: "GLOBAL", scope_id: null, inference_tier: "medium", usage: "chat", is_active: true, draining: false, provider: "ollama", model_name: "qwen3:8b", supports_tools: supportsTools },
        { id: "01930000-0000-7000-8000-000000000012", scope_level: "GLOBAL", scope_id: null, inference_tier: "light", usage: "embedding", is_active: true, draining: false, provider: "ollama", model_name: "bge-m3:latest" },
      ],
      datasources: [
        { id: "ds-sepa-1", alias: "Contrat SEPA Reference", uri: "orcia://kb/sepa-contract.md", authority_tier: "REFERENCE" },
      ],
    },
    { email: "admin.26.9@orcia.fr", displayName: "Admin 26.9", roles: ["PLATFORM_ADMIN"] },
  );
  useAuthSessionStore.getState().setAuthSession({
    isAuthenticated: true,
    email: "admin.26.9@orcia.fr",
    displayName: "Admin 26.9",
    roles: ["PLATFORM_ADMIN"],
    activeHat: "PLATFORM_ADMIN",
  });
}

async function mountAssistantApp() {
  const queryClient = createOrciaQueryClient();
  const history = createMemoryHistory({ initialEntries: ["/assistant"] });
  const router = createOrciaRouter({ queryClient, history });
  await router.load();
  const rendered = render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );
  return { ...rendered, router, queryClient };
}

beforeEach(() => {
  resetVitestApiBackend();
  clearPlatformSetupStorage();
  resetBackgroundAssistantStreamForTests();
  delete (globalThis as Record<string, unknown>).__ORCIA_TEST_CITATION_MAP__;
  delete (globalThis as Record<string, unknown>).__ORCIA_TEST_EMIT_APPROVAL__;
});

afterEach(() => {
  cleanup();
  delete (globalThis as Record<string, unknown>).__ORCIA_TEST_CITATION_MAP__;
  delete (globalThis as Record<string, unknown>).__ORCIA_TEST_EMIT_APPROVAL__;
});

describe("Story 26.9 — Mode A UI/SDK wiring, server thread history, citations, tool loop & Deepen", () => {
  it("hydrates thread messages from PG18 across cold reload, omits conversation_history, and does not synthesize client [Sn]", async () => {
    seedAdminWithModel(true);
    const { unmount } = await mountAssistantApp();

    const input = (await screen.findByTestId("assistant-three-speed-input")) as HTMLInputElement;
    fireEvent.change(input, { target: { value: "Explique Contrat SEPA Reference sans halluciner." } });
    fireEvent.click(await screen.findByTestId("assistant-three-speed-send-btn"));

    await waitFor(() => {
      const turnCall = backendState.recordedCalls.find((c) => c.path === "/api/v1/assistant/turns" && c.method === "POST");
      expect(turnCall).toBeTruthy();
      const reqBody = (turnCall?.body ?? {}) as Record<string, unknown>;
      expect(reqBody.thread_id).toBeTruthy();
      expect(reqBody.conversation_history).toBeUndefined();
    });

    await screen.findByTestId("assistant-conversation-turn-1");
    expect(screen.queryByTestId("assistant-citations-card-wrapper")).toBeNull();
    expect(backendState.assistantThreads.length).toBeGreaterThanOrEqual(1);
    expect(backendState.assistantThreadMessages.length).toBeGreaterThanOrEqual(2);

    clearSavedAssistantConversationsStorage();
    resetBackgroundAssistantStreamForTests();
    unmount();

    const prevCallCount = backendState.recordedCalls.length;
    await mountAssistantApp();
    await waitFor(
      () => {
        const afterCalls = backendState.recordedCalls.slice(prevCallCount).map((c) => `${c.method} ${c.path}`);
        expect(afterCalls.some((x) => x.includes("/messages"))).toBe(true);
      },
      { timeout: 3000 },
    );
    const rehydratedTurn = await screen.findByTestId(
      "assistant-conversation-turn-1",
      {},
      { timeout: 3000 },
    );
    expect(rehydratedTurn.textContent).toContain("Explique Contrat SEPA Reference sans halluciner.");
  });

  it("renders server citation_map, AssistantToolCallTrace, AssistantApprovalRequiredCard, and Mode A governance", async () => {
    seedAdminWithModel(true);
    (globalThis as Record<string, unknown>).__ORCIA_TEST_CITATION_MAP__ = {
      sources: [
        { tag: "S1", index: 1, uri: "orcia://kb/sepa-contract.md", title: "Contrat SEPA Reference", authority_tier: "REFERENCE", freshness: "FRESH", snippet: "Clause J+1.", line_start: 1, line_end: 10, restricted_access: false, display_pill: "[S1] Contrat SEPA Reference" },
      ],
      footer_summary_line: "1 source(s) vérifiée(s)",
    };
    (globalThis as Record<string, unknown>).__ORCIA_TEST_EMIT_APPROVAL__ = true;

    await mountAssistantApp();
    const input = (await screen.findByTestId("assistant-three-speed-input")) as HTMLInputElement;
    fireEvent.change(input, { target: { value: "@assistant Inspecte la spec et propose la mise à jour" } });
    fireEvent.click(await screen.findByTestId("assistant-three-speed-send-btn"));

    await screen.findByTestId("assistant-tool-call-trace");
    await screen.findByTestId("assistant-approval-required-card");
    const citationsCard = await screen.findByTestId("assistant-citations-card-wrapper");
    expect(citationsCard.textContent).toContain("[S1]");

    fireEvent.change(screen.getByTestId("assistant-approval-anchor-input"), {
      target: { value: "Validation conforme aux règles du socle." },
    });
    fireEvent.click(screen.getByTestId("assistant-approval-approve-btn"));

    await waitFor(() => {
      const approveCall = backendState.recordedCalls.find((c) => /\/api\/v1\/assistant\/turns\/.+\/approve$/.test(c.path));
      expect(approveCall).toBeTruthy();
      const approveBody = (approveCall?.body ?? {}) as Record<string, unknown>;
      expect(approveBody.approved).toBe(true);
      expect(String(approveBody.human_anchor_markdown ?? "")).toContain("Validation conforme");
    });
    await screen.findByTestId("assistant-approval-status-badge");

    fireEvent.click(screen.getByTestId("assistant-open-governance-btn"));
    await screen.findByTestId("assistant-governance-container");
    expect(screen.queryByTestId("assistant-open-studio-mode-b-btn")).toBeNull();
    fireEvent.change(screen.getByTestId("assistant-user-instructions-input"), {
      target: { value: "Concise verified answers only." },
    });
    fireEvent.click(screen.getByTestId("assistant-save-user-prefs-btn"));
    await waitFor(() => {
      const putGov = backendState.recordedCalls.find((c) => c.path === "/api/v1/assistant/governance/mode-a/user" && c.method === "PUT");
      expect(putGov).toBeTruthy();
    });
  });

  it("disables Speed 2/3 when supports_tools=false and sends parent_turn_id on Deepen when tools enabled", async () => {
    seedAdminWithModel(false);
    const { unmount } = await mountAssistantApp();

    fireEvent.click(await screen.findByTestId("assistant-model-and-effort-picker-trigger"));
    await screen.findByTestId("assistant-tools-unsupported-notice");
    expect((screen.getByTestId("assistant-effort-option-deep") as HTMLButtonElement).disabled).toBe(true);
    unmount();

    resetVitestApiBackend();
    resetBackgroundAssistantStreamForTests();
    seedAdminWithModel(true);
    await mountAssistantApp();

    const input = (await screen.findByTestId("assistant-three-speed-input")) as HTMLInputElement;
    fireEvent.change(input, { target: { value: "Question initiale rapide" } });
    fireEvent.click(await screen.findByTestId("assistant-three-speed-send-btn"));

    const deepenBtn = await screen.findByTestId("assistant-deepen-turn-btn");
    fireEvent.click(deepenBtn);

    await waitFor(() => {
      const turnCalls = backendState.recordedCalls.filter((c) => c.path === "/api/v1/assistant/turns" && c.method === "POST");
      expect(turnCalls.length).toBeGreaterThanOrEqual(2);
      const deepenBody = (turnCalls[1]?.body ?? {}) as Record<string, unknown>;
      expect(deepenBody.requested_speed).toBe("SPEED_2_AGENT_TOOLS");
      expect(deepenBody.parent_turn_id).toBeTruthy();
    });
  });
});
