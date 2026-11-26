/** @uj UJ-9, UJ-17, UJ-19 | @cap CAP-055, CAP-056, CAP-070, CAP-082, CAP-140, CAP-160 */
import { expect, test } from "./support/e2eCaptureFixture";
import { watchUnexpectedPageAndApiErrors } from "./support/apiErrors";
import { getBearerTokenFromSession } from "./support/authAndOrgHelpers";
import { resetDay0 } from "./support/day0";
import { expectDbRowCount, expectDbRowExists } from "./support/dbAssertions";
import { configureActiveChatModelViaApi, configureActiveEmbeddingModelViaApi } from "./support/embeddingModel";
import { seedSkillAndActiveAgentForComposer } from "./support/epic31PackHelpers";
import { createFirstAdminViaUi } from "./support/firstAdmin";
import { openAgentsPage, openAssistantPage } from "./support/processAndAssistantHelpers";
import { apiPost, reloadColdFromPg } from "./support/typedApiRequest";
import { createOrgAndWorkspaceWithId, openSettingsPacksTab, selectWorkspaceInSidebar } from "./support/workspaceAndCatalogHelpers";
import { switchUiLocaleViaUserSettings } from "./helpers/bilingualI18nHelpers";

test.describe("Epic 31 — Declarative APM Packs Round-Trip, Slots, Anti-Hostage & Bilingual E2E", () => {
  test.beforeEach(() => {
    resetDay0();
  });

  test("FR round-trip: Day-0 packs, Compose->Publish->Export .zip->Import fresh WS->Slot Bind->@/# autocomplete->F5->409 Unlink", async ({
    page,
  }, testInfo) => {
    test.setTimeout(180_000);
    const apiErrors = watchUnexpectedPageAndApiErrors(page, {
      allowedApiStatuses: [
        { pathIncludes: "/api/v1/packs/composer/", status: 422 },
        { pathIncludes: "/api/v1/workspaces/", status: 422 },
        { pathIncludes: "/api/v1/agents-and-skills/agents/", status: 409 },
      ],
    });
    await createFirstAdminViaUi(page);
    await configureActiveChatModelViaApi(page);
    await configureActiveEmbeddingModelViaApi(page);

    const wsA = await createOrgAndWorkspaceWithId(page, {
      name: "Espace Source Pack",
      slug: "ws-source-pack",
    });
    const wsB = await createOrgAndWorkspaceWithId(page, {
      name: "Espace Cible Pack",
      slug: "ws-cible-pack",
      skipOrgCreation: true,
    });
    const token = await getBearerTokenFromSession(page);

    const dsSeeds = [
      { slot: "git-repo", alias: "repo-cible-git", scheme: "git", uri: "https://git.internal.orcia/cible/core.git", source_nature: "SOURCE_CODE", target_scope: "main", target_ref: "refs/heads/main" },
      { slot: "jira-tracker", alias: "jira-cible", scheme: "jira", uri: "https://jira.internal.orcia/projects/CIBLE", source_nature: "WORK_TRACKER", target_scope: "CIBLE", target_ref: "CIBLE" },
      { slot: "confluence-kb", alias: "confluence-cible", scheme: "confluence", uri: "https://wiki.internal.orcia/spaces/CIBLE", source_nature: "DOCUMENT_KB", target_scope: "CIBLE", target_ref: "CIBLE" },
    ] as const;
    const dsBySlot: Record<string, string> = {};
    for (const s of dsSeeds) {
      const dsRes = await apiPost<{ id: string }>(page, `/api/v1/workspaces/${wsB.pgWorkspaceId}/datasources`, {
        token,
        data: { alias: s.alias, scheme: s.scheme, uri: s.uri, source_nature: s.source_nature, target_scope: s.target_scope, target_ref: s.target_ref, sync_mode: "WEBHOOK_PUSH" },
      });
      expect([200, 201]).toContain(dsRes.status());
      dsBySlot[s.slot] = (await dsRes.json()).id;
    }
    await reloadColdFromPg(page);

    const { agentId, agentSlug } = await seedSkillAndActiveAgentForComposer(
      page,
      token,
      wsA.pgWorkspaceId,
    );

    // 1. Verify Day-0 seeded packs (sdlc & orcia-docs) and open Pack Composer on wsA
    await openSettingsPacksTab(page);
    await expect(page.getByTestId("declarative-pack-card-sdlc")).toBeVisible({ timeout: 15000 });
    await expect(page.getByTestId("declarative-pack-card-orcia-docs")).toBeVisible({ timeout: 15000 });
    await page.getByTestId("packs-unified-workspace-select").selectOption(wsA.uiWorkspaceId);

    await page.getByTestId("open-pack-composer-modal-btn").click();
    await expect(page.getByTestId("pack-composer-modal")).toBeVisible({ timeout: 10000 });
    await page.getByTestId("pack-composer-slug-input").fill("custom-qa-pack");
    await page.getByTestId("pack-composer-name-input").fill("Custom QA Pack");
    await page.getByTestId("pack-composer-description-input").fill("Portable QA bundle");
    await page.getByTestId("pack-composer-tab-members").click();
    await expect(page.getByTestId(`pack-composer-member-checkbox-${agentSlug}`)).toBeVisible({ timeout: 15000 });
    await page.getByTestId(`pack-composer-member-checkbox-${agentSlug}`).check();
    await page.getByTestId("pack-composer-save-draft-btn").click();
    await expect(page.getByTestId("pack-composer-closure-gaps")).toBeVisible({ timeout: 15000 });

    await page.getByTestId("pack-composer-publish-btn").click();
    const composerAlert = page.getByTestId("pack-composer-error-alert");
    await expect(composerAlert).toBeVisible({ timeout: 10000 });
    await expect(composerAlert).toHaveAttribute("role", "alert");
    await expect(composerAlert).toContainText("ERR_PACK_CLOSURE_INCOMPLETE");

    await page.getByTestId("pack-composer-auto-include-checkbox").check();
    await page.getByTestId("pack-composer-publish-btn").click();
    await expect(page.getByTestId("pack-composer-draft-row-custom-qa-pack")).toContainText("Publié", {
      timeout: 15000,
    });

    const [download] = await Promise.all([
      page.waitForEvent("download", { timeout: 20000 }),
      page.getByTestId("pack-composer-export-btn").click(),
    ]);
    const zipPath = testInfo.outputPath("custom-qa-pack.zip");
    await download.saveAs(zipPath);
    await page.getByTestId("pack-composer-close-btn").click();

    // 2. Fresh workspace wsB: import exported .zip -> activate -> 422 slot guard -> bind -> activate
    await page.getByTestId("packs-unified-workspace-select").selectOption(wsB.uiWorkspaceId);
    await page.getByTestId("open-pack-import-modal-btn").click();
    await page.getByTestId("pack-import-file-input").setInputFiles(zipPath);
    await page.getByTestId("pack-import-scope-type-select").selectOption("WORKSPACE");
    await page.getByTestId("pack-import-scope-id-select").selectOption(wsB.uiWorkspaceId);
    await page.getByTestId("pack-import-submit-btn").click();
    await expect(page.getByTestId("pack-import-modal")).toBeHidden({ timeout: 15000 });
    await expect(page.getByTestId("workspace-pack-row-custom-qa-pack")).toBeVisible({ timeout: 15000 });

    await page.getByTestId("workspace-pack-toggle-custom-qa-pack").click();
    await expect(page.getByTestId("workspace-pack-row-custom-qa-pack")).toContainText("Actif", { timeout: 15000 });

    await page.getByTestId("workspace-pack-toggle-sdlc").click();
    const drawerAlert = page.getByTestId("pack-slot-drawer-error-alert");
    await expect(drawerAlert).toBeVisible({ timeout: 10000 });
    await expect(drawerAlert).toHaveAttribute("role", "alert");
    await expect(drawerAlert).toContainText("ERR_PACK_SLOT_UNBOUND");
    await expect(page.getByTestId("pack-slot-row-git-repo")).toHaveAttribute("data-slot-missing", "true");
    for (const slot of ["jira-tracker", "confluence-kb", "git-repo"] as const) {
      await page.getByTestId(`pack-slot-select-${slot}`).selectOption(`WORKSPACE_DATASOURCE::${dsBySlot[slot]}`);
    }
    await page.getByTestId("save-pack-slot-bindings-btn").click();
    await expect(page.getByTestId("pack-slot-binding-drawer")).toBeHidden({ timeout: 15000 });

    await page.getByTestId("workspace-pack-toggle-sdlc").click();
    await expect(page.getByTestId("workspace-pack-row-sdlc")).toContainText("Actif", { timeout: 15000 });

    // 3. Qualified @ / / autocomplete & turn execution in Mon Assistant on wsB
    await openAssistantPage(page);
    await selectWorkspaceInSidebar(
      page,
      { workspaceId: wsB.uiWorkspaceId, workspaceName: wsB.name },
      { waitForAssistantOverview: true },
    );
    const promptInput = page.getByTestId("assistant-three-speed-input");
    await promptInput.fill("/pack-qa");
    const dropdown = page.getByTestId("assistant-autocomplete-dropdown");
    await expect(dropdown).toBeVisible({ timeout: 10000 });
    await dropdown.locator('[data-testid^="assistant-autocomplete-option-"]').first().click();
    await promptInput.fill("@pack-qa");
    await expect(dropdown).toBeVisible({ timeout: 10000 });
    await dropdown.locator('[data-testid^="assistant-autocomplete-option-"]').first().click();
    const selectedHandle = await promptInput.inputValue();
    await promptInput.fill(`${selectedHandle} Verify release readiness`);
    await Promise.all([
      page.waitForResponse(
        (r) => r.url().includes("/api/v1/assistant/turns") && r.request().method() === "POST" && r.status() === 202,
        { timeout: 25000 },
      ),
      page.getByTestId("assistant-three-speed-send-btn").click(),
    ]);
    await expect(page.getByTestId("assistant-streamed-response-box").first()).not.toBeEmpty({ timeout: 25000 });

    // 4. Cold F5 reload persistence in PG18
    await reloadColdFromPg(page);
    await openSettingsPacksTab(page);
    await page.getByTestId("packs-unified-workspace-select").selectOption(wsB.uiWorkspaceId);
    await expect(page.getByTestId("workspace-pack-row-custom-qa-pack")).toContainText("Actif", { timeout: 15000 });
    await expect(page.getByTestId("workspace-pack-row-sdlc")).toContainText("Actif");
    expectDbRowExists(
      "SELECT pack_slug FROM workspace_pack_activations WHERE workspace_id = :ws AND pack_slug = 'custom-qa-pack' AND is_active = TRUE",
      { ws: wsB.pgWorkspaceId },
      "custom-qa-pack active in PG18 after F5",
    );
    expectDbRowExists(
      "SELECT slot_key FROM workspace_pack_slot_bindings WHERE workspace_id = :ws AND slot_key = 'git-repo'",
      { ws: wsB.pgWorkspaceId },
      "git-repo slot binding persisted in PG18",
    );

    // 5. Anti-hostage 409 unlink dialog on agent referenced by a CUSTOM DRAFT pack
    await page.getByTestId("packs-unified-workspace-select").selectOption(wsA.uiWorkspaceId);
    await expect(page.getByTestId("packs-unified-workspace-select")).toHaveValue(wsA.uiWorkspaceId);
    await page.getByTestId("open-pack-composer-modal-btn").click();
    await expect(page.getByTestId("pack-composer-modal")).toBeVisible({ timeout: 10000 });
    await page.getByTestId("pack-composer-slug-input").fill("hostage-draft");
    await page.getByTestId("pack-composer-name-input").fill("Hostage Draft");
    await page.getByTestId("pack-composer-tab-members").click();
    await expect(page.getByTestId(`pack-composer-member-checkbox-${agentSlug}`)).toBeVisible({ timeout: 15000 });
    await page.getByTestId(`pack-composer-member-checkbox-${agentSlug}`).check();
    await page.getByTestId("pack-composer-save-draft-btn").click();
    await expect(page.getByTestId("pack-composer-publish-btn")).toBeVisible({ timeout: 15000 });
    await page.getByTestId("pack-composer-close-btn").click();
    await expect(page.getByTestId("pack-composer-draft-row-hostage-draft")).toBeVisible({ timeout: 15000 });

    await openAgentsPage(page);
    await page.getByTestId(`delete-agent-btn-${agentId}`).click();
    await expect(page.getByTestId("entity-unlink-confirm-dialog")).toBeVisible({ timeout: 10000 });
    await expect(page.getByTestId("entity-unlink-draft-packs-list")).toContainText("hostage-draft");
    await page.getByTestId("entity-unlink-confirm-btn").click();
    await expect(page.getByTestId("entity-unlink-confirm-dialog")).toBeHidden({ timeout: 15000 });
    expectDbRowCount(
      "SELECT COUNT(*)::int AS count FROM pack_draft_memberships WHERE entity_slug = :slug",
      { slug: agentSlug },
      0,
      "Draft membership cleanly unlinked on confirmed delete",
    );
    expect(apiErrors).toEqual([]);
  });

  test("EN bilingual verification: English Direction C labels, [role='alert'] slot guard & Pack Composer", async ({ page }) => {
    const apiErrors = watchUnexpectedPageAndApiErrors(page, {
      allowedApiStatuses: [{ pathIncludes: "/api/v1/workspaces/", status: 422 }],
    });
    await createFirstAdminViaUi(page);
    await switchUiLocaleViaUserSettings(page, "en");
    await createOrgAndWorkspaceWithId(page, { name: "English Pack WS", slug: "ws-en-pack" });

    await openSettingsPacksTab(page);
    await expect(page.getByTestId("open-pack-import-modal-btn")).toContainText("Import Pack (.zip / YAML)");
    await expect(page.getByTestId("open-pack-composer-modal-btn")).toContainText("Compose Pack");
    await expect(page.getByTestId("workspace-packs-panel")).toContainText("Workspace Active Packs");
    await expect(page.getByTestId("declarative-pack-card-sdlc")).toBeVisible({ timeout: 15000 });

    await page.getByTestId("workspace-pack-toggle-sdlc").click();
    const drawerAlert = page.getByTestId("pack-slot-drawer-error-alert");
    await expect(drawerAlert).toBeVisible({ timeout: 10000 });
    await expect(drawerAlert).toHaveAttribute("role", "alert");
    await expect(drawerAlert).toContainText("ERR_PACK_SLOT_UNBOUND");
    await page.getByTestId("pack-slot-drawer-cancel-btn").click();

    await page.getByTestId("open-pack-composer-modal-btn").click();
    await expect(page.getByTestId("pack-composer-tab-metadata")).toContainText("1. Identity & scope");
    await expect(page.getByTestId("pack-composer-tab-members")).toContainText("2. Members & dependencies");
    await page.getByTestId("pack-composer-close-btn").click();
    expectDbRowExists(
      "SELECT slug FROM declarative_pack_bundles WHERE slug = 'sdlc' AND bundle_kind = 'SYSTEM' AND status = 'PUBLISHED'",
      {},
      "Day-0 SDLC system pack persisted in PG18",
    );
    expect(apiErrors).toEqual([]);
  });
});
