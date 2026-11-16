import { QueryClientProvider } from "@tanstack/react-query";
import { createMemoryHistory, RouterProvider } from "@tanstack/react-router";
import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import React from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  clearPlatformSetupStorage,
  writeCachedPlatformAdmin,
} from "../components/platformSetupStorageHelpers";
import { createOrciaQueryClient, createOrciaRouter } from "../router";
import { resetAuthSessionStore, useAuthSessionStore } from "../stores/authSessionStore";

async function renderAppAtRoute(initialEntry: string) {
  const queryClient = createOrciaQueryClient();
  const history = createMemoryHistory({ initialEntries: [initialEntry] });
  const router = createOrciaRouter({ queryClient, history });
  await router.load();
  const view = render(
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>,
  );
  return { ...view, router, queryClient };
}

describe("Story 6.1 — Registre d'Activité /activity, Inspection de Provenance & Export Conformité & Survie F5", () => {
  const runId = "01933e7e-3000-7000-8000-000000000001";

  beforeEach(() => {
    clearPlatformSetupStorage();
    resetAuthSessionStore();

    useAuthSessionStore.getState().setAuthSession({
      email: "amelia.admin@orcia.fr",
      roles: ["PLATFORM_ADMIN"],
      activeHat: "PLATFORM_ADMIN",
    });

    writeCachedPlatformAdmin({
      email: "amelia.admin@orcia.fr",
      displayName: "Amelia Dev",
      role: "PLATFORM_ADMIN",
    });

    // Mock global fetch for audit ledger API endpoints
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input: RequestInfo | URL) => {
      const url = String(input);

      if (url.includes("/api/v1/audit/ledger/") && url.includes("/provenance")) {
        return new Response(
          JSON.stringify({
            run_id: runId,
            root_run_id: null,
            total_events: 2,
            total_input_tokens: 1500,
            total_output_tokens: 500,
            total_cost_usd: 0.004,
            models_invoked: ["qwen2.5-coder"],
            actors_involved: ["Amelia Dev"],
            run_lock_sha256: "sha256-verified-lock",
            workflow_contract_sha256: "sha256-contract",
            cas_references: ["seaweedfs://blobs/sha-1"],
            is_run_lock_aligned: true,
            first_event_at: "2026-11-16T10:00:00Z",
            last_event_at: "2026-11-16T10:05:00Z",
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        );
      }

      if (url.includes("/api/v1/audit/ledger/") && url.includes("/export")) {
        const isMd = url.includes("format=md");
        return new Response(
          JSON.stringify({
            run_id: runId,
            format: isMd ? "md" : "json",
            content: isMd ? "# Dossier Certifié" : "{}",
            exported_at: new Date().toISOString(),
            manifest_sha256: "sha256-verified-lock",
            entries_count: 2,
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        );
      }

      if (url.includes("/api/v1/audit/ledger")) {
        return new Response(
          JSON.stringify({
            items: [
              {
                id: "01933e7e-2000-7000-8000-000000000001",
                source_event_id: "01933e7e-2000-7000-8000-000000000002",
                actor_type: "AGENT",
                actor_id: "amelia-dev",
                actor_display_name: "Amelia Dev",
                actor_email: "amelia@orcia.local",
                event_type: "StepCompleted",
                summary: "Compilation Starlark SDLC terminée",
                scope_path: "GLOBAL",
                run_id: runId,
                cost_usd: 0.004,
                input_tokens: 1500,
                output_tokens: 500,
                created_at: new Date().toISOString(),
              },
            ],
            total: 1,
            limit: 500,
            offset: 0,
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        );
      }

      return new Response(JSON.stringify({}), { status: 200 });
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
    cleanup();
  });

  it("renders /activity, inspects run provenance, exports JSON/MD dossiers, and survives F5 unmount/render", async () => {
    // 1. Initial mount
    const { unmount } = await renderAppAtRoute("/activity");

    await waitFor(() => {
      expect(screen.getByTestId("activity-log-explorer-page")).toBeDefined();
    });

    // 2. Verify row exists
    await waitFor(() => {
      expect(
        screen.getByTestId("audit-event-row-01933e7e-2000-7000-8000-000000000001"),
      ).toBeDefined();
    });

    // 3. Click the row to select run_id
    fireEvent.click(screen.getByTestId("audit-event-row-01933e7e-2000-7000-8000-000000000001"));

    // 4. Inspect Provenance Bar should appear
    await waitFor(() => {
      expect(screen.getByTestId("activity-provenance-export-bar")).toBeDefined();
    });
    expect(screen.getByTestId("activity-inspect-provenance-btn")).toBeDefined();
    expect(screen.getByTestId("activity-export-json-btn")).toBeDefined();
    expect(screen.getByTestId("activity-export-md-btn")).toBeDefined();

    // 5. Inspect provenance
    fireEvent.click(screen.getByTestId("activity-inspect-provenance-btn"));

    await waitFor(() => {
      expect(screen.getByTestId("activity-provenance-modal")).toBeDefined();
    });
    expect(screen.getByTestId("activity-provenance-modal").textContent).toContain("100 % aligné");

    // 6. Test JSON & MD export buttons click without unhandled rejection
    fireEvent.click(screen.getByTestId("activity-export-json-btn"));
    fireEvent.click(screen.getByTestId("activity-export-md-btn"));

    // 7. F5 reload survival test: unmount then remount
    unmount();

    const remount = await renderAppAtRoute("/activity");
    await waitFor(() => {
      expect(remount.getByTestId("activity-log-explorer-page")).toBeDefined();
    });
    await waitFor(() => {
      expect(
        remount.getByTestId("audit-event-row-01933e7e-2000-7000-8000-000000000001"),
      ).toBeDefined();
    });
  });
});
