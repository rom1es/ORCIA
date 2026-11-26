// @vitest-environment jsdom
import { createOrciaApiClient } from "@orcia/api-client";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import React from "react";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import {
  readCachedAgentsAndSkills,
  writeCachedAgentsAndSkills,
} from "../components/agentsAndSkillsBridgeStore";
import {
  clearPlatformSetupStorage,
  type ConfiguredPackItem,
} from "../components/platformSetupStore";
import { ShellContainer } from "../components/ShellContainer";
import { CatalogFeaturePanel } from "../features/catalog";
import { buildAgentUpsertPayload } from "../features/catalog/managedAgentsHelpers";
import { buildAssistantAutocompleteSuggestions } from "../features/inbox/assistantAutocompleteHelpers";
import { getDelegateAgents } from "../features/processes/studio/studioCatalogLabels";
import { I18nProvider } from "../i18n";
import { useAuthSessionStore } from "../stores/authSessionStore";
import { resetVitestApiBackend, seedVitestPlatformSetupState } from "./vitest.setup";

function seedAdmin(): void {
  seedVitestPlatformSetupState(
    {
      workspaces: [
        {
          workspaceId: "0192c4e0-0000-7000-8000-000000000201",
          name: "Workspace Story 30.5",
          visibilityMode: "STANDARD",
          ownerOrgUnitName: "Équipe Plateforme",
          lifecyclePhase: "BUILD",
          suggestedWorkflows: [],
          accessMode: "CONTRIBUTOR_ACTION_REQUIRED",
          finopsCostUsd: 0,
        },
      ],
    },
    {
      email: "marc.lead@orcia.io",
      displayName: "Marc Lead",
      roles: ["PLATFORM_ADMIN"],
    },
  );
  useAuthSessionStore.getState().setAuthSession({
    isAuthenticated: true,
    email: "marc.lead@orcia.io",
    displayName: "Marc Lead",
    roles: ["PLATFORM_ADMIN"],
    activeHat: "TEAM_LEAD",
    readOnlyObserver: false,
  });
}

beforeEach(() => {
  resetVitestApiBackend();
  clearPlatformSetupStorage();
  seedAdmin();
});

afterEach(() => {
  cleanup();
});

describe("Story 30.5 Web Lifecycle, Autocomplete/Process Filtering & Modal Errors", () => {
  it("excludes DRAFT agents from Mon Assistant @autocomplete and Mes Processus delegates", () => {
    const activePack: ConfiguredPackItem = {
      packKey: "orcia-pack-sdlc",
      version: "1.0.0",
      scopePath: "GLOBAL",
      status: "PUBLISHED",
    };
    writeCachedAgentsAndSkills({
      skills: [],
      agents: [
        {
          agentId: "agent-draft-only",
          slug: "draft-only",
          handle: "@draft-only",
          name: "Agent Brouillon Test",
          roleMission: "Draft role",
          instructions: "Wait before prod.",
          thinkingLevel: "medium",
          skillIds: [],
          lastExecutionOutput: null,
          visibilityScope: "TEAM",
          enabledOnWorkspace: true,
          mcpExposed: false,
          lifecycleStatus: "DRAFT",
          testBenchStatus: "UNTESTED",
          testBenchValidated: false,
        },
        {
          agentId: "agent-active-prod",
          slug: "active-prod",
          handle: "@active-prod",
          name: "Agent Actif Validé",
          roleMission: "Active role",
          instructions: "Serve users.",
          thinkingLevel: "medium",
          skillIds: [],
          lastExecutionOutput: null,
          visibilityScope: "TEAM",
          enabledOnWorkspace: true,
          mcpExposed: false,
          lifecycleStatus: "ACTIVE",
          testBenchStatus: "PASSED",
          testBenchValidated: true,
        },
      ],
    });

    const assistantSuggestions = buildAssistantAutocompleteSuggestions([activePack], true);
    const handles = assistantSuggestions.map((s) => s.token);
    expect(handles).toContain("@active-prod");
    expect(handles).not.toContain("@draft-only");

    const delegateSlugs = getDelegateAgents("fr").map((d) => d.slug);
    expect(delegateSlugs).toContain("active-prod");
    expect(delegateSlugs).not.toContain("draft-only");
  });

  it("shows inline modal [role='alert'] and rolls back MCP checkbox on backend 422/500", async () => {
    const client = createOrciaApiClient({ baseUrl: "", locale: "fr" });
    await client.upsertAgent({
      agent_id: "agent-draft-modal-err",
      name: "Agent Draft Modal Err",
      role_mission: "Verify inline error alert",
      instructions: "Check controls carefully.",
      thinking_level: "medium",
      skill_ids: [],
    });
    await client.executeAgent("agent-draft-modal-err", { prompt: "Confirm readiness" });

    render(
      <I18nProvider initialLocale="fr">
        <ShellContainer>
          <CatalogFeaturePanel />
        </ShellContainer>
      </I18nProvider>,
    );

    const openBtn = await screen.findByTestId("open-agent-detail-modal-btn-agent-draft-modal-err");
    const agentId = "agent-draft-modal-err";
    fireEvent.click(openBtn);
    await screen.findByTestId(`agent-detail-modal-${agentId}`);

    const originalFetch = globalThis.fetch;
    globalThis.fetch = (async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = typeof input === "string" ? input : input.toString();
      if (url.includes("/governance") && (init?.method ?? "GET").toUpperCase() === "PATCH") {
        return new Response(
          JSON.stringify({
            type: "https://orcia.io/problems/err-draft-agent-lifecycle-blocked",
            title: "Agent lifecycle blocked",
            status: 422,
            detail: "Agent au statut DRAFT : validez au Banc de Test avant exposition MCP.",
            error_code: "ERR_DRAFT_AGENT_LIFECYCLE_BLOCKED",
          }),
          { status: 422, headers: { "Content-Type": "application/problem+json" } },
        );
      }
      return originalFetch(input, init);
    }) as typeof fetch;

    try {
      const checkbox = screen.getByTestId(
        `agent-mcp-expose-checkbox-${agentId}`,
      ) as HTMLInputElement;
      const before = checkbox.checked;
      fireEvent.click(checkbox);

      await waitFor(() => {
        const alert = screen.getByTestId(`agent-detail-modal-error-${agentId}`);
        expect(alert.getAttribute("role")).toBe("alert");
        expect(alert.textContent).toContain("Agent au statut DRAFT");
        expect(checkbox.checked).toBe(before);
      });
    } finally {
      globalThis.fetch = originalFetch;
    }
  });

  it("duplicates read-only PACK preset directly via POST /agents (never 404 /duplicate)", async () => {
    const calledUrls: string[] = [];
    const originalFetch = globalThis.fetch;
    globalThis.fetch = (async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = typeof input === "string" ? input : input.toString();
      if (url.includes("/api/v1/agents-and-skills/agents")) {
        calledUrls.push(`${(init?.method ?? "GET").toUpperCase()} ${url}`);
      }
      return originalFetch(input, init);
    }) as typeof fetch;

    try {
      seedVitestPlatformSetupState(
        {
          packs: [
            {
              packKey: "orcia-pack-sdlc",
              version: "1.0.0",
              scopePath: "GLOBAL",
              status: "PUBLISHED",
            },
          ],
          workspaces: [
            {
              workspaceId: "0192c4e0-0000-7000-8000-000000000201",
              name: "Workspace Story 30.5",
              visibilityMode: "STANDARD",
              ownerOrgUnitName: "Équipe Plateforme",
              lifecyclePhase: "BUILD",
              suggestedWorkflows: [],
              accessMode: "CONTRIBUTOR_ACTION_REQUIRED",
              finopsCostUsd: 0,
            },
          ],
        },
        {
          email: "marc.lead@orcia.io",
          displayName: "Marc Lead",
          roles: ["PLATFORM_ADMIN"],
        },
      );
      render(
        <I18nProvider initialLocale="fr">
          <ShellContainer>
            <CatalogFeaturePanel />
          </ShellContainer>
        </I18nProvider>,
      );

      const dupPackBtn = await screen.findByTestId(
        "duplicate-agent-btn-agent-architecte-solution",
      );
      const packThinkingSelect = screen.getByTestId(
        "agent-card-thinking-select-agent-architecte-solution",
      ) as HTMLSelectElement;
      const packEnableBtn = screen.getByTestId(
        "toggle-agent-enabled-btn-agent-architecte-solution",
      ) as HTMLButtonElement;
      expect(packThinkingSelect.disabled).toBe(true);
      expect(packEnableBtn.disabled).toBe(true);

      fireEvent.click(dupPackBtn);
      await waitFor(() => {
        expect(calledUrls.some((c) => c.endsWith("/api/v1/agents-and-skills/agents"))).toBe(true);
      });
      expect(calledUrls.some((c) => c.includes("/duplicate"))).toBe(false);
      // P1: PACK preset must NOT leak into cached client workspace agents
      expect(
        readCachedAgentsAndSkills().agents.some((a) => a.agentId === "agent-architecte-solution"),
      ).toBe(false);

      // P0: buildAgentUpsertPayload must be strictly typed to UpsertAgentRequest & omit test_bench_*
      const strictPayload = buildAgentUpsertPayload("agent-strict-check", {
        name: "Agent Strict",
        roleMission: "Verify schema",
        instructions: "Check fields.",
        thinkingLevel: "medium",
        testBenchValidated: true,
        testBenchStatus: "PASSED",
        lifecycleStatus: "ACTIVE",
      });
      expect("test_bench_status" in strictPayload).toBe(false);
      expect("test_bench_validated" in strictPayload).toBe(false);
    } finally {
      globalThis.fetch = originalFetch;
    }
  });
});
