import { expect, type Page } from "@playwright/test";
import {
  openCatalogOrAgentsPage,
  type CatalogAgentsTabKey,
} from "./workspaceAndCatalogHelpers";

export type FinopsTabSlug =
  | "processes"
  | "tiers"
  | "external-services"
  | "cognitive-governance";

export type StudioViewModeSlug = "design" | "whatif" | "yaml";
export type ShowcaseTabSlug = "macro" | "features" | "architecture" | "changelog";

/** Vide `localStorage` et `sessionStorage` puis recharge la page (`F5` réel). */
export async function reloadClearingStorage(page: Page): Promise<void> {
  await page.evaluate(() => {
    window.localStorage.clear();
    window.sessionStorage.clear();
  });
  await page.reload();
}

/** Navigue vers `/cockpit` et attend l'affichage du Cockpit ou de l'état d'accostage. */
export async function openCockpitPage(page: Page): Promise<void> {
  await page.goto("/cockpit");
  await expect(page.getByTestId("cockpit-active-scope-badge")).toBeVisible({ timeout: 30000 });
}

/** Navigue vers `/gates` et attend la section de revue humaine adaptative. */
export async function openGatesPage(page: Page): Promise<void> {
  await page.goto("/gates");
  await expect(page.getByTestId("gates-active-scope-badge")).toBeVisible({ timeout: 30000 });
  await expect(page.getByTestId("gates-adaptive-human-review-section")).toBeVisible({
    timeout: 15000,
  });
}

/** Navigue vers `/processes` et attend le hub Process Studio v2. */
export async function openProcessesHubPage(page: Page): Promise<void> {
  await page.goto("/processes");
  await expect(page.getByTestId("processes-hub-v2-page")).toBeVisible({ timeout: 30000 });
  await expect(page.getByTestId("processes-hub-vsm-hero-card")).toBeVisible({ timeout: 15000 });
}

/** Navigue vers `/processes/vsm/$vsmId` et attend la carte de chaîne de valeur interactive. */
export async function openVsmPage(page: Page, vsmId: string): Promise<void> {
  await page.goto(`/processes/vsm/${vsmId}`);
  await expect(page.getByTestId("vsm-interactive-view")).toBeVisible({ timeout: 30000 });
}

/** Navigue vers `/processes/studio/$workflowId` et sélectionne éventuellement un mode d'affichage. */
export async function openWorkflowStudioPage(
  page: Page,
  workflowId: string,
  mode?: StudioViewModeSlug,
): Promise<void> {
  await page.goto(`/processes/studio/${workflowId}`);
  await expect(page.getByTestId("workflow-five-blocks-studio-page")).toBeVisible({
    timeout: 30000,
  });
  if (mode) {
    await page.getByTestId(`studio-view-mode-${mode}`).click();
  }
}

/** Navigue vers `/finops` et active éventuellement un des 4 onglets FinOps. */
export async function openFinopsPage(page: Page, tab?: FinopsTabSlug): Promise<void> {
  await page.goto("/finops");
  await expect(page.getByTestId("finops-feature-panel")).toBeVisible({ timeout: 30000 });
  await expect(page.getByTestId("finops-governance-dashboard")).toBeVisible({ timeout: 15000 });
  if (tab) {
    await page.getByTestId(`finops-tab-${tab}`).click();
  }
}

/** Délègue l'ouverture de `/agents` à `openCatalogOrAgentsPage` (`workspaceAndCatalogHelpers.ts`). */
export async function openAgentsPage(
  page: Page,
  tab?: CatalogAgentsTabKey,
): Promise<void> {
  await openCatalogOrAgentsPage(page, { route: "/agents", tab });
}

/** Navigue vers `/assistant` et ouvre optionnellement le panneau Dossiers ou Gouvernance. */
export async function openAssistantPage(
  page: Page,
  options: { readonly openFolders?: boolean; readonly openGovernance?: boolean } = {},
): Promise<void> {
  await page.goto("/assistant");
  await expect(page.getByTestId("inbox-feature-panel")).toBeVisible({ timeout: 30000 });
  await expect(page.getByTestId("assistant-speed-selector-and-stream")).toBeVisible({
    timeout: 15000,
  });
  if (options.openFolders) {
    await page.getByTestId("assistant-folders-toggle-btn").click();
    await expect(page.getByTestId("assistant-folders-and-collaborative-thread-view")).toBeVisible({
      timeout: 10000,
    });
  }
  if (options.openGovernance) {
    await page.getByTestId("assistant-open-governance-btn").click();
  }
}

/** Navigue vers `/help` et attend le Centre d'Aide et la bannière Vitrine. */
export async function openHelpCenterPage(page: Page): Promise<void> {
  await page.goto("/help");
  await expect(page.getByTestId("help-menu-center-view")).toBeVisible({ timeout: 30000 });
  await expect(page.getByTestId("contextual-help-hybrid-panel")).toBeVisible({ timeout: 15000 });
}

/** Navigue vers `/showcase` et active optionnellement un onglet (`macro` | `features` | `architecture` | `changelog`). */
export async function openShowcasePage(page: Page, tab?: ShowcaseTabSlug): Promise<void> {
  await page.goto("/showcase");
  await expect(page.getByTestId("orcia-product-showcase-site-view")).toBeVisible({
    timeout: 30000,
  });
  if (tab) {
    await page.getByTestId(`showcase-tab-${tab}`).click();
    await expect(page.getByTestId(`showcase-pillar-${tab}`)).toBeVisible({ timeout: 10000 });
  }
}
