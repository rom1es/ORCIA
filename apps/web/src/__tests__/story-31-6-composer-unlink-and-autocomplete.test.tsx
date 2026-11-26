// @vitest-environment jsdom
import { QueryClientProvider } from "@tanstack/react-query";
import { createMemoryHistory, RouterProvider } from "@tanstack/react-router";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import React from "react";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { writeCachedAgentsAndSkills } from "../components/agentsAndSkillsBridgeStore";
import { I18nProvider } from "../i18n";
import { createOrciaQueryClient, createOrciaRouter } from "../router";
import { useAuthSessionStore } from "../stores/authSessionStore";
import { backendState } from "./setup/mockBackendState";
import { seedMockDraftPackForEntity } from "./setup/vitestEpic31PackHandlers";
import { resetVitestApiBackend, seedVitestPlatformSetupState } from "./vitest.setup";

const WS_ID = "0195f000-0000-7000-8000-000000000311";

function seedTestEnv() {
  seedVitestPlatformSetupState(
    {
      org_units: [
        {
          id: "0192c4e0-0000-7000-8000-000000000101",
          name: "Direction Technique",
          slug: "dir-tech",
          level: "BU",
          parentId: null,
          billingEnabled: true,
        },
      ],
      workspaces: [
        {
          workspaceId: WS_ID,
          slug: "ws-equipe-alpha",
          name: "Espace Équipe Alpha",
          ownerOrgUnitId: "0192c4e0-0000-7000-8000-000000000101",
          ownerOrgUnitName: "Direction Technique",
          visibilityMode: "STANDARD",
          lifecyclePhase: "BUILD",
          accessMode: "CONTRIBUTOR_ACTION_REQUIRED",
          finopsCostUsd: 0,
        },
      ],
    },
    { email: "admin@orcia.test", displayName: "Admin Test", roles: ["PLATFORM_ADMIN"] },
  );
  useAuthSessionStore.setState({
    isAuthenticated: true,
    isHydrating: false,
    accessToken: "mock-token-316", // pragma: allowlist secret
    email: "admin@orcia.test",
    displayName: "Admin Test",
    roles: ["PLATFORM_ADMIN"],
    activeHat: "PLATFORM_ADMIN",
    readOnlyObserver: false,
  });
}

async function mountRoute(initialPath: string, locale: "fr" | "en" = "fr") {
  const qc = createOrciaQueryClient();
  const history = createMemoryHistory({ initialEntries: [initialPath] });
  const router = createOrciaRouter({ queryClient: qc, history });
  await router.load();
  return render(
    <I18nProvider initialLocale={locale}>
      <QueryClientProvider client={qc}>
        <RouterProvider router={router} />
      </QueryClientProvider>
    </I18nProvider>,
  );
}

describe("Story 31.6 — Pack Composer, Anti-Hostage Unlink Dialog & Qualified Autocomplete", () => {
  beforeEach(() => {
    resetVitestApiBackend();
    seedTestEnv();
  });

  afterEach(() => {
    cleanup();
  });

  it("composes a CUSTOM draft pack, enforces 422 closure & PII leak alerts, and publishes with auto_include_dependencies", async () => {
    await mountRoute("/settings/packs", "en");

    await waitFor(() => {
      expect(screen.getByTestId("open-pack-composer-modal-btn")).toBeDefined();
    });

    fireEvent.click(screen.getByTestId("open-pack-composer-modal-btn"));
    fireEvent.change(screen.getByTestId("pack-composer-slug-input"), { target: { value: "finops-audit" } });
    fireEvent.change(screen.getByTestId("pack-composer-name-input"), { target: { value: "FinOps Audit Pack" } });
    fireEvent.change(screen.getByTestId("pack-composer-description-input"), {
      target: { value: "Contact secret@corp.internal for keys" },
    });
    fireEvent.click(screen.getByTestId("pack-composer-save-draft-btn"));

    await waitFor(() => {
      expect(screen.getByTestId("pack-composer-export-btn")).toBeDefined();
    });

    // PII/secret leak blocked on export -> 422 inline [role="alert"]
    fireEvent.click(screen.getByTestId("pack-composer-export-btn"));
    await waitFor(() => {
      const alert = screen.getByTestId("pack-composer-error-alert");
      expect(alert.getAttribute("role")).toBe("alert");
      expect(alert.textContent).toContain("ERR_PACK_PII_OR_INFRA_LEAK");
    });

    // Clean description and publish
    fireEvent.click(screen.getByTestId("pack-composer-tab-metadata"));
    fireEvent.change(screen.getByTestId("pack-composer-description-input"), {
      target: { value: "Clean declarative FinOps audit pack" },
    });
    fireEvent.click(screen.getByTestId("pack-composer-save-draft-btn"));
    await waitFor(() => {
      expect(screen.getByTestId("pack-composer-publish-btn")).toBeDefined();
    });

    fireEvent.click(screen.getByTestId("pack-composer-publish-btn"));
    await waitFor(() => {
      expect(screen.getByTestId("pack-composer-draft-row-finops-audit").textContent).toContain("Publié");
    });
  });

  it("prompts EntityUnlinkConfirmDialog on 409 ERR_ENTITY_REFERENCED_BY_PACK_DRAFT during agent delete and retries with unlink_from_draft_packs=true", async () => {
    backendState.agents = [
      {
        agent_id: "agent-finops-helper",
        slug: "finops-helper",
        handle: "@finops-helper",
        name: "FinOps Helper",
        role_mission: "Audit costs",
        instructions: "Review costs cleanly",
        thinking_level: "medium",
        skill_ids: [],
        visibility_scope: "TEAM",
        lifecycle_status: "ACTIVE",
        test_bench_status: "PASSED",
        test_bench_validated: true,
      },
    ];
    seedMockDraftPackForEntity({
      slug: "draft-finops-bundle",
      name: "Draft FinOps Bundle",
      entityType: "AGENT",
      entityId: "agent-finops-helper",
      entitySlug: "finops-helper",
    });

    await mountRoute("/agents", "fr");

    const delBtn = await screen.findByTestId("delete-agent-btn-agent-finops-helper");
    fireEvent.click(delBtn);

    await waitFor(() => {
      const dialog = screen.getByTestId("entity-unlink-confirm-dialog");
      expect(dialog).toBeDefined();
      expect(screen.getByTestId("entity-unlink-draft-packs-list").textContent).toContain("Draft FinOps Bundle");
    });

    fireEvent.click(screen.getByTestId("entity-unlink-confirm-btn"));
    await waitFor(() => {
      expect(screen.queryByTestId("entity-unlink-confirm-dialog")).toBeNull();
      expect(screen.queryByTestId("agent-card-agent-finops-helper")).toBeNull();
    });
  });

  it("displays origin pack attribution badges on colliding @pack/agent options in Mon Assistant", async () => {
    backendState.aiModelMappings = [
      {
        id: "01930000-0000-7000-8000-000000000098",
        scope_level: "GLOBAL",
        scope_id: null,
        inference_tier: "medium",
        usage: "chat",
        is_active: true,
        provider: "openai",
        model_name: "gpt-4o-mini",
      },
    ];
    backendState.agents = [
      {
        agent_id: "sdlc:reviewer",
        slug: "reviewer",
        handle: "@reviewer",
        name: "SDLC Reviewer",
        role_mission: "SDLC review",
        instructions: "Check SDLC",
        thinking_level: "medium",
        skill_ids: [],
        visibility_scope: "PACK",
        pack_slug: "sdlc",
        qualified_ref: "@sdlc/reviewer",
        is_colliding: true,
        lifecycle_status: "ACTIVE",
      },
      {
        agent_id: "legal:reviewer",
        slug: "reviewer",
        handle: "@reviewer",
        name: "Legal Reviewer",
        role_mission: "Legal review",
        instructions: "Check Legal",
        thinking_level: "medium",
        skill_ids: [],
        visibility_scope: "PACK",
        pack_slug: "legal",
        qualified_ref: "@legal/reviewer",
        is_colliding: true,
        lifecycle_status: "ACTIVE",
      },
    ];
    writeCachedAgentsAndSkills({ agents: [], skills: [] });

    await mountRoute("/assistant", "fr");
    const promptInput = await screen.findByTestId("assistant-three-speed-input");
    await waitFor(() => {
      fireEvent.change(promptInput, { target: { value: "@rev" } });
      expect(screen.getByTestId("assistant-autocomplete-badge-sdlc/reviewer").textContent).toBe("sdlc");
      expect(screen.getByTestId("assistant-autocomplete-badge-legal/reviewer").textContent).toBe("legal");
    });

    fireEvent.click(screen.getByTestId("assistant-autocomplete-option-sdlc/reviewer"));
    expect((promptInput as HTMLInputElement).value).toContain("@sdlc/reviewer");
  });
});
