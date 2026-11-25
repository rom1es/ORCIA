import { expect, type Page } from "@playwright/test";
import { getBearerTokenFromSession, openSettingsTabViaUi } from "./authAndOrgHelpers";
import { queryDbRows } from "./dbAssertions";
import { createBuAndTeamViaUi, createWorkspaceViaUi } from "./orgAndWorkspace";
import { apiGet } from "./typedApiRequest";

export interface WorkspaceSetupParams {
  readonly name: string;
  readonly slug: string;
  readonly skipOrgCreation?: boolean;
}

export interface CreatedWorkspaceRef {
  readonly uiWorkspaceId: string;
  readonly pgWorkspaceId: string;
  readonly name: string;
  readonly slug: string;
}

export type OntologyTabKey = "EXPLORER" | "PROPOSALS";
export type CatalogAgentsTabKey = "AGENTS" | "SKILLS" | "CONNECTIONS";

/**
 * Resolve the UI workspace ID (`GET /api/v1/workspaces`) and PostgreSQL 18 UUID for a workspace by name/slug.
 */
export async function resolveWorkspaceIds(
  page: Page,
  name: string,
  slug?: string,
): Promise<{ readonly uiWorkspaceId: string; readonly pgWorkspaceId: string }> {
  const token = await getBearerTokenFromSession(page);
  let uiWorkspaceId = "";
  await expect
    .poll(
      async () => {
        const res = await apiGet<{
          workspaces?: Array<{ id?: string; slug?: string; name?: string }>;
        }>(page, "/api/v1/workspaces", { token });
        if (!res.ok()) return "";
        const body = await res.json();
        const found = (body.workspaces ?? []).find(
          (w) => w.name === name || (slug !== undefined && w.slug === slug),
        );
        uiWorkspaceId = found?.id ?? "";
        return uiWorkspaceId;
      },
      { timeout: 20000 },
    )
    .toBeTruthy();

  const rows = queryDbRows<{ id: string }>(
    "SELECT id::text AS id FROM workspaces WHERE name = :name OR slug = :slug LIMIT 1",
    { name, slug: slug ?? name.toLowerCase().replace(/[^a-z0-9-]+/g, "-") },
  );
  const pgWorkspaceId = rows[0]?.id ?? "";
  expect(pgWorkspaceId, `UUID PG18 introuvable dans workspaces pour name=${name}`).toBeTruthy();
  return { uiWorkspaceId, pgWorkspaceId };
}

/**
 * Crée une Direction + Équipe (sauf `skipOrgCreation`) puis un Espace via l'UI et retourne ses IDs.
 */
export async function createOrgAndWorkspaceWithId(
  page: Page,
  params: WorkspaceSetupParams,
): Promise<CreatedWorkspaceRef> {
  if (!params.skipOrgCreation) {
    await createBuAndTeamViaUi(page);
  }
  await createWorkspaceViaUi(page, params.name, params.slug);
  const { uiWorkspaceId, pgWorkspaceId } = await resolveWorkspaceIds(
    page,
    params.name,
    params.slug,
  );
  return {
    uiWorkspaceId,
    pgWorkspaceId,
    name: params.name,
    slug: params.slug,
  };
}

/** Ouvre `/workspaces/$wsId/sources` et attend le tableau maître des sources. */
export async function openWorkspaceSourcesPage(
  page: Page,
  workspaceId: string,
): Promise<void> {
  await page.goto(`/workspaces/${workspaceId}/sources`);
  await expect(page.getByTestId("workspace-detail-sources-content")).toBeVisible({
    timeout: 30000,
  });
  await expect(page.getByTestId("workspace-sources-master-table-root")).toBeVisible({
    timeout: 15000,
  });
}

/** Bascule sur l'onglet Glossaire & Règles Métiers dans `/spaces` ou `/workspaces/$wsId`. */
export async function openWorkspaceGlossaryTab(page: Page): Promise<void> {
  await page.getByTestId("workspace-tab-GLOSSARY_RULES").click();
  await expect(page.getByTestId("workspace-glossary-and-ontology-tab")).toBeVisible({
    timeout: 15000,
  });
}

/** Navigue vers `/ontology` et active optionnellement l'onglet Explorateur ou Propositions. */
export async function openOntologyPage(
  page: Page,
  tab: OntologyTabKey = "EXPLORER",
): Promise<void> {
  await page.goto("/ontology");
  await expect(page.getByTestId("ontology-tab-explorer")).toBeVisible({ timeout: 30000 });
  if (tab === "PROPOSALS") {
    await page.getByTestId("ontology-tab-proposals").click();
    await expect(page.getByTestId("ontology-promotions-proposals-tab")).toBeVisible({
      timeout: 15000,
    });
  }
}

/** Navigue vers `/catalog` ou `/agents` et sélectionne l'onglet demandé (`AGENTS` | `SKILLS` | `CONNECTIONS`). */
export async function openCatalogOrAgentsPage(
  page: Page,
  options: { readonly route?: "/catalog" | "/agents"; readonly tab?: CatalogAgentsTabKey } = {},
): Promise<void> {
  const route = options.route ?? "/catalog";
  await page.goto(route);
  if (route === "/catalog") {
    await expect(page.getByTestId("catalog-explorer-panel")).toBeVisible({
      timeout: 30000,
    });
    return;
  }
  await expect(page.getByTestId("agents-and-skills-manager-view")).toBeVisible({
    timeout: 30000,
  });
  if (options.tab) {
    const tabTestId = `agents-subview-tab-${options.tab.toLowerCase()}`;
    await page.getByTestId(tabTestId).click();
    if (options.tab === "CONNECTIONS") {
      await expect(page.getByTestId("remote-service-test-bench")).toBeVisible({ timeout: 15000 });
    }
  }
}

/** Navigue vers `/settings/packs` (Registre des Packs Déclaratifs `packs/<domaine>/`). */
export async function openPacksRegistryPage(page: Page): Promise<void> {
  await page.goto("/settings/packs");
  await expect(page.getByTestId("packs-registry-v2-page")).toBeVisible({ timeout: 30000 });
}

/** Navigue vers `/settings` puis active l'onglet `packs` (`SettingsPacksSection`). */
export async function openSettingsPacksTab(page: Page): Promise<void> {
  await openSettingsTabViaUi(page, "packs");
  await expect(page.getByTestId("settings-packs-section")).toBeVisible({ timeout: 15000 });
}

/** Navigue vers `/wizards` et attend le runner durable. */
export async function openWizardsPage(page: Page): Promise<void> {
  await page.goto("/wizards");
  await expect(page.getByTestId("wizards-route-page")).toBeVisible({ timeout: 30000 });
  await expect(page.getByTestId("durable-wizard-runner")).toBeVisible({ timeout: 15000 });
}

/**
 * Re-select a workspace via `sidebar-workspace-selector` after a cold reload
 * and optionally wait for the Assistant workspace overview request to complete.
 */
export async function selectWorkspaceInSidebar(
  page: Page,
  workspaceIdentifier: { readonly workspaceId?: string; readonly workspaceName: string },
  options: { readonly waitForAssistantOverview?: boolean } = {},
): Promise<string> {
  const scopeSelect = page.getByTestId("sidebar-workspace-selector");
  await expect(scopeSelect).toBeVisible({ timeout: 30000 });
  await expect(scopeSelect).toContainText(workspaceIdentifier.workspaceName, { timeout: 30000 });

  let optionValue = workspaceIdentifier.workspaceId ?? "";
  if (!optionValue) {
    optionValue =
      (await scopeSelect
        .locator("option")
        .filter({ hasText: workspaceIdentifier.workspaceName })
        .first()
        .getAttribute("value")) ?? "";
  }
  expect(
    optionValue,
    `Missing sidebar option for workspace ${workspaceIdentifier.workspaceName}`,
  ).toBeTruthy();

  await expect(scopeSelect.locator(`option[value="${optionValue}"]`)).toHaveCount(1, {
    timeout: 15000,
  });

  const currentValue = await scopeSelect.inputValue();
  if (currentValue !== optionValue) {
    if (options.waitForAssistantOverview) {
      const [overviewRes] = await Promise.all([
        page.waitForResponse(
          (r) =>
            r.url().includes(`/api/v1/assistant/workspaces/${optionValue}/overview`) &&
            r.request().method() === "GET",
          { timeout: 30000 },
        ),
        scopeSelect.selectOption(optionValue),
      ]);
      expect(overviewRes.status()).toBeLessThan(400);
    } else {
      await scopeSelect.selectOption(optionValue);
    }
  }
  await expect(scopeSelect).toHaveValue(optionValue, { timeout: 15000 });
  return optionValue;
}
