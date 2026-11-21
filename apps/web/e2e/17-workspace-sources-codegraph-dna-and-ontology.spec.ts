/** @uj UJ-5, UJ-18 | @cap CAP-010, CAP-011, CAP-080, CAP-081, CAP-084, CAP-180 */
import { captureMilestoneScreenshot, expect, test } from "./support/e2eCaptureFixture";
import { resetDay0 } from "./support/day0";
import { expectDbRowCount, expectDbRowExists } from "./support/dbAssertions";
import { bootstrapAdminSession, getBearerTokenFromSession } from "./support/authAndOrgHelpers";
import {
  createOrgAndWorkspaceWithId,
  openOntologyPage,
  openWorkspaceGlossaryTab,
  openWorkspaceSourcesPage,
} from "./support/workspaceAndCatalogHelpers";
import { apiGet, apiPost, reloadColdFromPg } from "./support/typedApiRequest";

test.describe("Sources d'espace multi-nature, graphe de code, glossaire, ontologie et RAG tripartite", () => {
  test.beforeEach(() => {
    resetDay0();
  });

  test("Rattachement source code, fraîcheur SHA-256, webhook, outils codegraph lecture seule et survie F5", async ({
    page,
  }) => {
    await bootstrapAdminSession(page);
    const ws = await createOrgAndWorkspaceWithId(page, {
      name: "Espace CodeGraph E2E",
      slug: "ws-codegraph-e2e",
    });

    await openWorkspaceSourcesPage(page, ws.uiWorkspaceId);
    const tokenForGuard = await getBearerTokenFromSession(page);
    const blockedRagRes = await apiPost<{ error_code?: string }>(
      page,
      `/api/v1/workspaces/${ws.pgWorkspaceId}/datasources`,
      {
        token: tokenForGuard,
        data: {
          alias: "confluence-interdite-jour0",
          scheme: "confluence",
          uri: "https://confluence.internal.orcia/spaces/ARCH",
          source_nature: "DOCUMENT_KB",
        },
      },
    );
    expect(blockedRagRes.status()).toBe(422);
    expect((await blockedRagRes.json()).error_code).toBe("ERR_NO_ACTIVE_EMBEDDING_MODEL");
    expectDbRowCount(
      "SELECT COUNT(*)::int AS count FROM workspace_datasources WHERE workspace_id = :ws_id",
      { ws_id: ws.pgWorkspaceId },
      0,
      "Aucune source RAG insérée sans modèle d'embedding",
    );

    await page.getByTestId("open-attach-source-modal-btn").click();
    await expect(page.getByTestId("workspace-source-attach-modal")).toBeVisible({ timeout: 10000 });
    await expect(page.getByTestId("datasource-rag-embedding-required-notice")).toBeVisible();
    await expect(page.getByTestId("modal-source-nature-select")).toHaveValue("SOURCE_CODE");
    await expect(
      page.locator('[data-testid="modal-source-nature-select"] option[value="DOCUMENT_KB"]'),
    ).toBeDisabled();

    await page.getByTestId("modal-source-nature-select").selectOption("SOURCE_CODE");
    await page.getByTestId("modal-source-alias-input").fill("core-repo");
    await page.getByTestId("modal-source-scheme-input").fill("git");
    await page.getByTestId("modal-source-uri-input").fill("https://git.internal.orcia/core/app.git");
    await page.getByTestId("modal-source-target-scope-input").fill("main");
    await page.getByTestId("modal-source-target-ref-input").fill("refs/heads/main");
    await page.getByTestId("modal-source-sync-mode-select").selectOption("WEBHOOK_PUSH");

    const cgSwitch = page.getByTestId("modal-gitnexus-enabled-switch");
    await expect(cgSwitch).toBeVisible();
    if ((await cgSwitch.getAttribute("aria-checked")) !== "true") {
      await cgSwitch.click();
    }
    await page.getByTestId("modal-source-save-btn").click();
    await expect(page.getByTestId("workspace-source-attach-modal")).toBeHidden({ timeout: 15000 });

    const dsRow = expectDbRowExists(
      "SELECT id::text AS id, source_nature, sync_mode, codegraph_enabled, freshness_status FROM workspace_datasources WHERE workspace_id = :ws_id AND alias = :alias",
      { ws_id: ws.pgWorkspaceId, alias: "core-repo" },
      "Source SOURCE_CODE persistée dans workspace_datasources",
    );
    const dsId = String(dsRow.id);
    expect(dsRow.source_nature).toBe("SOURCE_CODE");
    expect(dsRow.sync_mode).toBe("WEBHOOK_PUSH");
    expect(dsRow.codegraph_enabled).toBe(true);

    await expect(page.getByTestId(`workspace-detail-source-row-${dsId}`)).toBeVisible({ timeout: 15000 });
    await page.getByTestId(`sync-datasource-btn-${dsId}`).click();
    await page.getByTestId("workspace-sources-reconcile-btn").click();

    const token = await getBearerTokenFromSession(page);
    const webhookRes = await apiPost(page, `/api/v1/webhooks/datasources/${dsId}`, {
      token,
      data: {
        delivery_key: `deliv-${dsId}-01`,
        provider_event: "push",
        remote_fingerprint_sha256: "sha256:e2e000111222333444555666777888999",
        ref: "refs/heads/main",
      },
    });
    expect(webhookRes.status()).toBe(200);

    expectDbRowExists(
      "SELECT id::text AS id, datasource_id::text AS datasource_id, reconcile_outcome FROM datasource_webhook_deliveries WHERE datasource_id = :ds_id",
      { ds_id: dsId },
      "Livraison webhook enregistrée dans datasource_webhook_deliveries",
    );

    const toolsRes = await apiGet<{
      tools: Array<{ name: string; read_only: boolean }>;
      active_repositories: Array<{ alias: string; codegraph_enabled: boolean }>;
    }>(page, `/api/v1/workspaces/${ws.pgWorkspaceId}/codegraph/tools`, { token });
    expect(toolsRes.status()).toBe(200);
    const toolsPayload = await toolsRes.json();
    expect(toolsPayload.tools.every((t) => t.read_only)).toBe(true);
    expect(toolsPayload.active_repositories.some((r) => r.alias === "core-repo")).toBe(true);

    const invokeRes = await apiPost(page, `/api/v1/workspaces/${ws.pgWorkspaceId}/codegraph/invoke`, {
      token,
      data: {
        tool_name: "codegraph_locate_symbol",
        arguments: { repo_alias: "core-repo", query: "OrchestrationEngine" },
      },
    });
    expect(invokeRes.status()).toBe(200);

    await page.goto(`/workspaces/${ws.uiWorkspaceId}/sources`);
    await reloadColdFromPg(page);
    await expect(page.getByTestId(`workspace-detail-source-row-${dsId}`)).toBeVisible({ timeout: 20000 });
  });

  test("Glossaire d'espace, promotion gouvernée L4 vers L3 et approbation dans Ontologie persistent après F5", async ({
    page,
  }) => {
    await bootstrapAdminSession(page);
    const ws = await createOrgAndWorkspaceWithId(page, {
      name: "Espace Glossaire E2E",
      slug: "ws-glossary-e2e",
    });

    await page.goto(`/workspaces/${ws.uiWorkspaceId}`);
    await openWorkspaceGlossaryTab(page);

    const term = "Marge Brute Normalisée";
    await page.getByTestId("workspace-glossary-term-input").fill(term);
    await page
      .getByTestId("workspace-glossary-definition-input")
      .fill("Revenu net diminué des coûts directs de production.");
    await page.getByTestId("workspace-glossary-scope-select").selectOption("WORKSPACE");
    await page.getByTestId("workspace-glossary-submit-btn").click();

    const wsTier = page.getByTestId("workspace-glossary-tier-workspace");
    const conceptCard = wsTier.locator('[data-testid^="glossary-concept-card-"]', { hasText: term });
    await expect(conceptCard).toBeVisible({ timeout: 15000 });

    const conceptRow = expectDbRowExists(
      "SELECT id::text AS id, concept_key, level FROM ontology_concepts WHERE canonical_term = :term",
      { term },
      "Concept glossaire créé dans ontology_concepts",
    );
    expect(["4_WORKSPACE", "3_WORKSPACE"]).toContain(String(conceptRow.level));

    await conceptCard.locator('[data-testid^="promote-glossary-concept-btn-"]').click();
    await expect(conceptCard.locator('[data-testid^="promoted-glossary-badge-"]')).toBeVisible({
      timeout: 15000,
    });

    expectDbRowExists(
      "SELECT id::text AS id, status, target_level FROM ontology_promotion_proposals WHERE source_concept_id = :cid AND status = 'PENDING_REVIEW'",
      { cid: String(conceptRow.id) },
      "Proposition de promotion en attente dans ontology_promotion_proposals",
    );

    await openOntologyPage(page, "PROPOSALS");
    const proposalCard = page
      .locator('[data-testid^="promotion-proposal-card-"]', { hasText: term })
      .first();
    await expect(proposalCard).toBeVisible({ timeout: 15000 });
    await proposalCard
      .locator('[data-testid^="promotion-comment-input-"]')
      .fill("Validation gouvernance ontologie");
    await proposalCard.locator('[data-testid^="approve-promotion-btn-"]').click();
    await expect(page.getByTestId("ontology-feedback-banner")).toBeVisible({ timeout: 15000 });

    expectDbRowExists(
      "SELECT id::text AS id, status FROM ontology_promotion_proposals WHERE source_concept_id = :cid AND status = 'APPROVED'",
      { cid: String(conceptRow.id) },
      "Proposition de promotion approuvée dans ontology_promotion_proposals",
    );
    expectDbRowExists(
      "SELECT id::text AS id, event_type FROM audit_ledger WHERE event_type LIKE 'ONTOLOGY_%'",
      undefined,
      "Audit ontologique enregistré dans audit_ledger",
    );

    await page.getByTestId("ontology-tab-explorer").click();
    await page.getByTestId("ontology-level-select").selectOption("0");
    await page.getByTestId("ontology-concept-name-input").fill("Axiome Qualité Globale");
    await page.getByTestId("ontology-concept-def-input").fill("Règle globale inviolable de traçabilité.");
    await page.getByTestId("ontology-create-concept-btn").click();
    await expect(page.getByTestId("ontology-feedback-banner")).toBeVisible({ timeout: 15000 });

    await page.goto("/ontology");
    await reloadColdFromPg(page);
    await expect(page.getByTestId("ontology-kb-explorer-panel")).toContainText("Axiome Qualité Globale", {
      timeout: 20000,
    });
  });

  test("Chaîne ADN Starlark, dérogations d'espace et graphe tripartite RAG persistent en base après F5", async ({
    page,
  }, testInfo) => {
    await bootstrapAdminSession(page);
    const ws = await createOrgAndWorkspaceWithId(page, {
      name: "Espace ADN Tripartite",
      slug: "ws-dna-tripartite",
    });

    // 1. Rattachement et synchronisation réelle d'une source code -> `kb_documents` PG18 (`AD-24.7`)
    await openWorkspaceSourcesPage(page, ws.uiWorkspaceId);
    await page.getByTestId("open-attach-source-modal-btn").click();
    await expect(page.getByTestId("workspace-source-attach-modal")).toBeVisible({ timeout: 10000 });
    await page.getByTestId("modal-source-nature-select").selectOption("SOURCE_CODE");
    await page.getByTestId("modal-source-alias-input").fill("core-dna-repo");
    await page.getByTestId("modal-source-scheme-input").fill("git");
    await page
      .getByTestId("modal-source-uri-input")
      .fill("https://git.internal.orcia/claims/core.git");
    await page.getByTestId("modal-source-target-scope-input").fill("main");
    await page.getByTestId("modal-source-target-ref-input").fill("refs/heads/main");
    await page.getByTestId("modal-source-save-btn").click();
    await expect(page.getByTestId("workspace-source-attach-modal")).toBeHidden({ timeout: 15000 });

    const kbDsRow = expectDbRowExists(
      "SELECT id::text AS id FROM workspace_datasources WHERE workspace_id = :ws_id AND alias = :alias",
      { ws_id: ws.pgWorkspaceId, alias: "core-dna-repo" },
      "Source SOURCE_CODE persistée dans workspace_datasources",
    );
    const kbDsId = String(kbDsRow.id);
    await expect(page.getByTestId(`workspace-detail-source-row-${kbDsId}`)).toBeVisible({
      timeout: 15000,
    });
    const [syncRes] = await Promise.all([
      page.waitForResponse(
        (res) =>
          res.url().includes(`/datasources/${kbDsId}/sync`) && res.request().method() === "POST",
      ),
      page.getByTestId(`sync-datasource-btn-${kbDsId}`).click(),
    ]);
    expect(syncRes.status()).toBe(200);

    // 2. Chaîne ADN Starlark + dérogation d'espace + survie F5 PG18
    await page.goto(`/workspaces/${ws.uiWorkspaceId}`);
    await expect(page.getByTestId("dna-starlark-glossary-view")).toBeVisible({ timeout: 10000 });
    await page.getByTestId("compile-starlark-btn").click();
    await expect(page.getByTestId("starlark-compiler-panel")).toBeVisible({ timeout: 10000 });

    await expect(page.getByTestId("workspace-five-tabs-view")).toBeVisible({ timeout: 10000 });
    await page.locator('[data-testid^="register-waiver-btn-"]').first().click();
    await expect(page.locator('[data-testid^="waiver-item-"]').first()).toBeVisible({
      timeout: 15000,
    });

    await reloadColdFromPg(page);
    await expect(page.getByTestId("starlark-compiler-panel")).toBeVisible({ timeout: 15000 });
    await expect(page.locator('[data-testid^="waiver-item-"]').first()).toBeVisible({
      timeout: 15000,
    });

    expectDbRowExists(
      "SELECT waiver_id::text AS waiver_id, workspace_id::text AS workspace_id, source_uri, status FROM workspace_exception_waivers WHERE workspace_id = :ws_id",
      { ws_id: ws.pgWorkspaceId },
      "Dérogation persistée dans workspace_exception_waivers",
    );
    expectDbRowCount(
      "SELECT COUNT(*)::int AS count FROM workspace_dna_mechanisms WHERE workspace_id = :ws_id",
      { ws_id: ws.pgWorkspaceId },
      1,
      "Mécanisme ADN Starlark persisté dans workspace_dna_mechanisms",
    );

    // 3. Audit tripartite Doc vs Code depuis /ontology -> `tripartite_trace_edges` + survie F5
    await openOntologyPage(page, "EXPLORER");
    await expect(page.getByTestId("tripartite-graph-section")).toBeVisible({ timeout: 15000 });
    await expect(page.getByTestId("tripartite-audit-form")).toBeVisible({ timeout: 10000 });
    await page
      .getByTestId("tripartite-confluence-uri-input")
      .fill("confluence://CLAIMS/SPEC-24-2");
    await page
      .getByTestId("tripartite-git-uri-input")
      .fill("https://git.internal.orcia/claims/core.git");
    await page.getByTestId("tripartite-jira-key-input").fill("PAY-242");
    await page.getByTestId("tripartite-audit-submit-btn").click();
    await expect(page.locator('[data-testid^="tripartite-edge-"]').first()).toBeVisible({
      timeout: 15000,
    });

    await reloadColdFromPg(page);
    await expect(page.getByTestId("tripartite-graph-section")).toBeVisible({ timeout: 15000 });
    await expect(page.locator('[data-testid^="tripartite-edge-"]').first()).toBeVisible({
      timeout: 15000,
    });
    await page.getByTestId("tripartite-graph-section").scrollIntoViewIfNeeded();
    await captureMilestoneScreenshot(page, testInfo, "ontology-tripartite-waivers");

    expectDbRowCount(
      "SELECT COUNT(*)::int AS count FROM kb_documents WHERE workspace_id = :ws_id",
      { ws_id: ws.pgWorkspaceId },
      1,
      "Documents indexés présents dans kb_documents",
    );
    expectDbRowCount(
      "SELECT COUNT(*)::int AS count FROM tripartite_trace_edges WHERE workspace_id = :ws_id",
      { ws_id: ws.pgWorkspaceId },
      1,
      "Arêtes tripartites présentes dans tripartite_trace_edges",
    );
  });
});
