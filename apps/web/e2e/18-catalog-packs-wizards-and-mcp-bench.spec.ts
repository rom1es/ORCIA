/** @uj UJ-9, UJ-19 | @cap CAP-002, CAP-055, CAP-056, CAP-057, CAP-082, CAP-150 */
import { expect, test } from "./support/e2eCaptureFixture";
import { resetDay0 } from "./support/day0";
import { expectDbRowCount, expectDbRowExists } from "./support/dbAssertions";
import { bootstrapAdminSession } from "./support/authAndOrgHelpers";
import {
  openCatalogOrAgentsPage,
  openPacksRegistryPage,
  openSettingsPacksTab,
  openWizardsPage,
} from "./support/workspaceAndCatalogHelpers";
import { reloadColdFromPg } from "./support/typedApiRequest";

test.describe("Catalogue fédéré RBAC, packs déclaratifs, parcours guidés et banc MCP-A2A", () => {
  test.beforeEach(() => {
    resetDay0();
  });

  test("Explorateur du catalogue fédéré, droits granulaires et définitions persistent en base après F5", async ({
    page,
  }) => {
    await bootstrapAdminSession(page);
    await openCatalogOrAgentsPage(page, { route: "/catalog" });

    await expect(page.getByTestId("catalog-explorer-panel")).toBeVisible({ timeout: 10000 });
    await page.getByTestId("catalog-scheme-filter-ALL").click();

    await reloadColdFromPg(page);
    await expect(page.getByTestId("catalog-explorer-panel")).toBeVisible({ timeout: 15000 });

    expectDbRowCount(
      "SELECT COUNT(*)::int AS count FROM catalog_items",
      undefined,
      1,
      "Actifs fédérés persistés dans catalog_items",
    );
    expectDbRowCount(
      "SELECT COUNT(*)::int AS count FROM catalog_acl_entries WHERE permission IN ('DISCOVER', 'EXECUTE', 'READ_SOURCE', 'EDIT', 'ADMIN')",
      undefined,
      1,
      "Droits RBAC persistés dans catalog_acl_entries",
    );
    expectDbRowCount(
      "SELECT COUNT(*)::int AS count FROM workflow_definitions",
      undefined,
      1,
      "Définitions de processus persistées dans workflow_definitions",
    );
  });

  test("Activation de pack par périmètre dans Paramètres survit à F5 et persiste dans platform_settings", async ({
    page,
  }) => {
    await bootstrapAdminSession(page);
    await openSettingsPacksTab(page);

    await page.getByTestId("pack-scope-input").selectOption("GLOBAL");
    await page.getByTestId("activate-pack-btn-orcia-pack-sdlc").click();
    await expect(page.getByTestId("pack-card-active-scopes-orcia-pack-sdlc")).toBeVisible({
      timeout: 15000,
    });
    await expect(page.getByTestId("deactivate-pack-btn-orcia-pack-sdlc")).toBeVisible();

    expectDbRowExists(
      "SELECT key, value_jsonb::text AS val FROM platform_settings WHERE key = 'platform_setup_state_v1' AND value_jsonb::text LIKE '%orcia-pack-sdlc%'",
      undefined,
      "Activation du pack orcia-pack-sdlc persistée dans platform_settings",
    );

    await reloadColdFromPg(page);
    await openSettingsPacksTab(page);
    await expect(page.getByTestId("pack-card-active-scopes-orcia-pack-sdlc")).toBeVisible({
      timeout: 15000,
    });
  });

  test("Registre des packs déclaratifs et export ZIP persistent dans declarative_pack_bundles après F5", async ({
    page,
  }) => {
    await bootstrapAdminSession(page);
    await openPacksRegistryPage(page);

    await expect(page.getByTestId("declarative-pack-card-sdlc")).toBeVisible({ timeout: 15000 });
    await expect(page.getByTestId("declarative-pack-card-orcia-docs")).toBeVisible({
      timeout: 15000,
    });

    await page.getByTestId("export-pack-sdlc-zip-btn").click();
    await expect(page.getByTestId("packs-registry-status-banner")).toBeVisible({ timeout: 10000 });
    await expect(page.getByTestId("exported-pack-zip-filename")).toContainText("sdlc-");

    await reloadColdFromPg(page);
    await expect(page.getByTestId("declarative-pack-card-sdlc")).toBeVisible({ timeout: 15000 });

    expectDbRowCount(
      "SELECT COUNT(*)::int AS count FROM declarative_pack_bundles",
      undefined,
      1,
      "Bundles déclaratifs persistés dans declarative_pack_bundles",
    );
  });

  test("Parcours guidé d'initialisation avec retour arrière survit à F5 et persiste dans wizard_sessions", async ({
    page,
  }) => {
    await bootstrapAdminSession(page);
    await openWizardsPage(page);

    await expect(page.getByTestId("wizard-step-form-1")).toBeVisible({ timeout: 15000 });
    await page.getByTestId("wizard-input-org-unit").fill("Équipe Initialisation");
    await page.getByTestId("wizard-complete-step-btn").click();

    await expect(page.getByTestId("wizard-step-form-2")).toBeVisible({ timeout: 10000 });
    await page.getByTestId("wizard-step-back-btn").click();
    await expect(page.getByTestId("wizard-step-form-1")).toBeVisible({ timeout: 10000 });
    await page.getByTestId("wizard-complete-step-btn").click();

    await expect(page.getByTestId("wizard-step-form-2")).toBeVisible({ timeout: 10000 });
    await page.getByTestId("wizard-input-workspace-name").fill("Espace Initialisation");
    await page.getByTestId("wizard-complete-step-btn").click();

    await expect(page.getByTestId("wizard-step-form-3")).toBeVisible({ timeout: 10000 });
    await page.getByTestId("wizard-input-connector-alias").fill("repo-wizard");
    await page.getByTestId("wizard-input-connector-uri").fill("https://git.internal.orcia/wiz.git");
    await page.getByTestId("wizard-complete-step-btn").click();

    await expect(page.getByTestId("wizard-step-form-4")).toBeVisible({ timeout: 10000 });
    await page.getByTestId("wizard-input-primary-model").fill("qwen2.5:14b");
    await page.getByTestId("wizard-complete-step-btn").click();

    await expect(page.getByTestId("wizard-step-form-5")).toBeVisible({ timeout: 10000 });
    await page.getByTestId("wizard-complete-step-btn").click();
    await expect(page.getByTestId("wizard-completed-badge")).toBeVisible({ timeout: 15000 });

    await reloadColdFromPg(page);
    await expect(page.getByTestId("wizard-completed-badge")).toBeVisible({ timeout: 15000 });

    expectDbRowCount(
      "SELECT COUNT(*)::int AS count FROM wizard_sessions",
      undefined,
      1,
      "Sessions wizard persistées dans wizard_sessions",
    );
  });

  test("Banc de test connecteur distant, trace audit_ledger et exposition gouvernée MCP survivent à F5", async ({
    page,
  }) => {
    await bootstrapAdminSession(page);
    await openCatalogOrAgentsPage(page, { route: "/agents", tab: "CONNECTIONS" });

    await page.getByTestId("run-test-bench-btn").click();
    await expect(page.getByTestId("test-bench-status-1")).toHaveText("PASS", { timeout: 15000 });
    await expect(page.getByTestId("test-bench-status-4")).toHaveText("PASS", { timeout: 15000 });
    await expect(page.getByTestId("discovered-tool-search_documents")).toBeVisible();
    await expect(page.getByTestId("discovered-tool-propose_draft_update")).toBeVisible();

    expectDbRowExists(
      "SELECT id::text AS id, event_type FROM audit_ledger WHERE event_type = 'ADMIN_CONNECTION_TEST'",
      undefined,
      "Exécution banc de test auditée dans audit_ledger",
    );

    const mcpCheckbox = page.getByTestId("toggle-mcp-exposure-checkbox");
    await mcpCheckbox.click();
    await expect(mcpCheckbox).toBeChecked({ timeout: 10000 });

    await reloadColdFromPg(page);
    await page.getByTestId("agents-subview-tab-connections").click();
    await expect(page.getByTestId("toggle-mcp-exposure-checkbox")).toBeChecked({ timeout: 15000 });

    expectDbRowCount(
      "SELECT COUNT(*)::int AS count FROM catalog_items",
      undefined,
      1,
      "Actif exposé gouverné persisté dans catalog_items",
    );
  });
});
