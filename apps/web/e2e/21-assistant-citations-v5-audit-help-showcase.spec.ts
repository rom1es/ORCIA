/** @uj UJ-10, UJ-17, UJ-20 | @cap CAP-022, CAP-064, CAP-066, CAP-068, CAP-072, CAP-076 */
import { expect, test } from "./support/e2eCaptureFixture";
import { watchUnexpectedPageAndApiErrors } from "./support/apiErrors";
import { resetDay0 } from "./support/day0";
import { expectDbRowCount, expectDbRowExists } from "./support/dbAssertions";
import { bootstrapAdminSession, getBearerTokenFromSession } from "./support/authAndOrgHelpers";
import {
  configureActiveChatModelViaApi,
  configureActiveEmbeddingModelViaApi,
} from "./support/embeddingModel";
import { createOrgAndWorkspaceWithId } from "./support/workspaceAndCatalogHelpers";
import {
  openAssistantPage,
  openHelpCenterPage,
  openShowcasePage,
  reloadClearingStorage,
} from "./support/processAndAssistantHelpers";
import { apiPost } from "./support/typedApiRequest";

test.describe("Assistant conversationnel, citations déterministes, centre d'aide et vitrine produit", () => {
  test.beforeEach(() => {
    resetDay0();
  });

  test("Création de dossier, réponse avec citations vérifiées, verrouillage d'écriture directe et audit en tâche de fond survivent à F5", async ({
    page,
  }) => {
    await bootstrapAdminSession(page);
    const ws = await createOrgAndWorkspaceWithId(page, {
      name: "Espace Assistant Citations",
      slug: "ws-assistant-citations",
    });
    await configureActiveChatModelViaApi(page);
    await configureActiveEmbeddingModelViaApi(page);
    const token = await getBearerTokenFromSession(page);
    const authHeaders = { Authorization: `Bearer ${token}` };

    await openAssistantPage(page, { openFolders: true });
    await page.getByTestId("assistant-new-folder-title-input").fill("Dossier Citations Vérifiées");
    const [folderRes] = await Promise.all([
      page.waitForResponse((r) => r.url().includes("/folders") && r.request().method() === "POST"),
      page.getByTestId("assistant-create-folder-btn").click(),
    ]);
    expect(folderRes.status()).toBeLessThan(400);

    const promptInput = page.getByTestId("assistant-three-speed-input");
    await promptInput.fill("@assistant Analyse les capacités et cite les sources vérifiées.");
    const [turnRes] = await Promise.all([
      page.waitForResponse(
        (r) => r.url().includes("/api/v1/assistant/three-speed/") && r.request().method() === "POST",
        { timeout: 30000 },
      ),
      page.getByTestId("assistant-three-speed-send-btn").click(),
    ]);
    expect(turnRes.status()).toBeLessThan(400);
    await expect(page.getByTestId("assistant-streamed-response-box").first()).not.toBeEmpty({
      timeout: 30000,
    });

    const verifyRes = await apiPost<{
      sanitized_text: string;
      valid_tags: string[];
      stripped_phantom_tags: string[];
    }>(page, "/api/v1/assistant/citations/verify-turn", {
      token,
      data: {
        workspace_id: ws.pgWorkspaceId,
        response_text: "Synthèse appuyée sur [S1], [G1], [O1] et bloc suspect [S99].",
        sources: [
          {
            uri: "orcia://kb/architecture-spine.md",
            title: "Architecture Spine",
            authority_tier: "REFERENCE",
            freshness: "FRESH",
            snippet: "Isolation stricte des contextes.",
          },
        ],
        glossary_items: [
          {
            term_or_axiom_id: "L1-HEXAGONAL",
            label: "Hexagonal",
            ontology_level: "N1_DIRECTIVE",
            definition: "Ports et adaptateurs stricts.",
          },
        ],
        tool_outputs: [
          {
            tool_name: "codegraph_locate_symbol",
            connector_uri: "mcp://gitnexus",
            summary: "Symbole vérifié.",
          },
        ],
      },
    });
    expect(verifyRes.status()).toBe(200);
    const verifiedBody = await verifyRes.json();
    expect(verifiedBody.valid_tags).toEqual(["S1", "G1", "O1"]);
    expect(verifiedBody.stripped_phantom_tags).toContain("S99");
    expect(verifiedBody.sanitized_text).toContain("[Citation non vérifiée]");

    const directWriteRes = await apiPost<{ error_code: string }>(
      page,
      "/api/v1/assistant/artifacts/action",
      {
        token,
        data: {
          workspace_id: ws.pgWorkspaceId,
          action_type: "DIRECT_SI_WRITE",
          artifact_title: "Écriture directe interdite",
          artifact_content: "Contenu non validé",
          target_uri: "confluence://space/page-42",
        },
      },
    );
    expect(directWriteRes.status()).toBe(422);
    expect((await directWriteRes.json()).error_code).toBe(
      "ERR_DIRECT_SI_WRITE_REQUIRES_PROCESS_GATE",
    );

    const bgAuditRes = await apiPost(page, "/api/v1/executions/reflexive", {
      token,
      data: {
        workspace_id: ws.pgWorkspaceId,
        actor_slug: "assistant",
        objective: "BACKGROUND_AUDIT: vérifier la fraîcheur documentaire de l'espace.",
        effort_level: "high",
        effort_mode: "approfondi",
        allow_sub_agent_delegation: true,
        available_delegate_agents: ["assistant"],
        initial_resources: ["docs/product/capabilities.yaml"],
      },
    });
    expect([200, 201]).toContain(bgAuditRes.status());

    await expect(page.getByTestId("assistant-citation-pills-and-artifact-card")).toBeVisible({
      timeout: 10000,
    });
    await expect(page.getByTestId("artifact-card-v5-lock-notice")).toBeVisible({ timeout: 10000 });

    await reloadClearingStorage(page);
    await expect(page.getByTestId("assistant-speed-selector-and-stream")).toBeVisible({
      timeout: 30000,
    });

    expectDbRowExists(
      "SELECT folder_id::text AS folder_id, title FROM assistant_folders WHERE title = :title",
      { title: "Dossier Citations Vérifiées" },
      "Dossier assistant persisté dans assistant_folders PG18",
    );
    expectDbRowCount(
      "SELECT COUNT(*)::int AS count FROM assistant_threads",
      undefined,
      1,
      "Fil conversationnel persisté dans assistant_threads PG18",
    );
    expectDbRowCount(
      "SELECT COUNT(*)::int AS count FROM reflexive_execution_sessions",
      undefined,
      1,
      "Audit en tâche de fond persisté dans reflexive_execution_sessions PG18",
    );
    expectDbRowCount(
      "SELECT COUNT(*)::int AS count FROM audit_ledger",
      undefined,
      1,
      "Traces de provenance persistées dans audit_ledger PG18",
    );
  });

  test("Centre d'aide contextuelle, lien organisationnel, colonne latérale et vitrine produit survivent à F5 sans erreur serveur", async ({
    page,
  }) => {
    const errors = watchUnexpectedPageAndApiErrors(page);
    await bootstrapAdminSession(page);

    await openHelpCenterPage(page);
    await expect(page.getByTestId("help-menu-center-view")).toBeVisible({ timeout: 15000 });

    await page.getByTestId("help-accordion-steps-btn").click();
    await expect(page.getByTestId("help-accordion-steps-content")).toBeVisible();
    await page.getByTestId("help-accordion-terms-btn").click();
    await expect(page.getByTestId("help-accordion-terms-content")).toBeVisible();
    await page.getByTestId("help-accordion-faq-btn").click();
    await expect(page.getByTestId("help-accordion-faq-content")).toBeVisible();

    const helpCenterView = page.getByTestId("help-menu-center-view");
    const helpCenterText = (await helpCenterView.textContent()) ?? "";
    expect(helpCenterText, "USER24-BUG-3: zéro ** brut sur /help").not.toContain("**");
    expect(helpCenterText, "USER24-BUG-3: zéro backtick brut sur /help").not.toContain("`");
    const helpCenterFormattedCount = await helpCenterView.locator("strong, code").count();
    expect(helpCenterFormattedCount, "USER24-BUG-3: HTML strong/code attendu sur /help").toBeGreaterThan(0);

    await page.goto("/spaces");
    await expect(page.getByTestId("four-zone-direction-c-shell")).toBeVisible({ timeout: 15000 });
    await expect(page.getByTestId("topbar-contextual-help-toggle")).toBeVisible({ timeout: 15000 });
    await expect(page.getByTestId("contextual-info-trigger-workspace-sources")).toHaveCount(0);
    const zone4Help = page.getByTestId("four-zone-contextual-help-column");
    if (!(await zone4Help.isVisible())) {
      await page.getByTestId("topbar-contextual-help-toggle").click();
    }
    await expect(zone4Help).toBeVisible({
      timeout: 15000,
    });
    await expect(page.getByTestId("contextual-help-hybrid-panel").first()).toContainText(
      /unité d'organisation/i,
    );
    const zone4FaqBtn = zone4Help.getByTestId("help-accordion-faq-btn");
    if ((await zone4FaqBtn.count()) > 0 && (await zone4FaqBtn.getAttribute("aria-expanded")) !== "true") {
      await zone4FaqBtn.click();
    }
    const zone4Text = (await zone4Help.textContent()) ?? "";
    expect(zone4Text, "USER24-BUG-3: zéro ** brut en Zone 4").not.toContain("**");
    expect(zone4Text, "USER24-BUG-3: zéro backtick brut en Zone 4").not.toContain("`");
    const zone4FormattedCount = await zone4Help.locator("strong, code").count();
    expect(zone4FormattedCount, "USER24-BUG-3: HTML strong/code attendu en Zone 4").toBeGreaterThan(0);

    expectDbRowCount(
      "SELECT COUNT(*)::int AS count FROM catalog_items",
      undefined,
      1,
      "Articles d'aide et actifs fédérés présents dans catalog_items PG18",
    );

    await openShowcasePage(page, "macro");
    await expect(page.getByTestId("eight-menu-item-help")).toHaveAttribute("data-active", "true");
    await expect(page.getByTestId("showcase-pillar-macro")).toBeVisible();
    await page.getByTestId("showcase-tab-features").click();
    await expect(page.getByTestId("showcase-pillar-features")).toBeVisible();
    await page.getByTestId("showcase-tab-architecture").click();
    await expect(page.getByTestId("showcase-pillar-architecture")).toBeVisible();
    await page.getByTestId("showcase-tab-changelog").click();
    await expect(page.getByTestId("showcase-pillar-changelog")).toBeVisible();

    await expect(page.getByTestId("showcase-stat-routes")).toBeVisible();
    await expect(page.getByTestId("showcase-stat-primitives")).toBeVisible();
    await expect(page.getByTestId("showcase-stat-migrations")).toBeVisible();
    await expect(page.getByTestId("showcase-stat-reports")).toBeVisible();
    await expect(page.getByTestId("showcase-stat-capabilities")).toBeVisible();

    await page.getByTestId("showcase-changelog-search-input").fill("Story");
    await expect(page.getByTestId("showcase-changelog-reports-list")).toBeVisible();

    await reloadClearingStorage(page);
    await expect(page.getByTestId("orcia-product-showcase-site-view")).toBeVisible({
      timeout: 30000,
    });
    expect(errors, errors.join("\n")).toEqual([]);
  });
});
