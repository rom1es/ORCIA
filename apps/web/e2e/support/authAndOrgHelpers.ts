import { expect, type Page } from "@playwright/test";
import { createFirstAdminViaUi, E2E_ADMIN } from "./firstAdmin";
import { apiPost } from "./typedApiRequest";

export type SettingsDomainTab = "iam" | "authentication" | "models" | "packs" | "connectors";
export type UserSettingsTab =
  | "GENERAL"
  | "PERSONALIZATION"
  | "ACCOUNT_SECURITY"
  | "PASSTHROUGH_SOURCES"
  | "IDE_MCP_KEYS";

export interface LocalLoginParams {
  readonly email: string;
  readonly password: string;
  readonly totpCode?: string;
  readonly openAccordionIfSso?: boolean;
}

export interface CreateOrgUnitParams {
  readonly level: "BU" | "TEAM";
  readonly name: string;
  readonly slug: string;
  readonly parentId?: string;
  readonly leadUserQuery?: string;
  readonly ontologyLeadQuery?: string;
  readonly billingEnabled?: boolean;
}

export interface InviteScopedUserParams {
  readonly orgUnitId?: string;
  readonly displayName: string;
  readonly email: string;
  readonly role: "BU_LEAD" | "TEAM_LEAD" | "ONTOLOGY_LEAD" | "CONTRIBUTOR" | "OBSERVER";
  readonly closePasswordModal?: boolean;
}

/** Récupère un jeton JWT Bearer depuis le cookie HttpOnly de session courante. */
export async function getBearerTokenFromSession(page: Page): Promise<string> {
  const res = await apiPost<{ access_token?: string }>(page, "/api/v1/auth/refresh");
  expect(res.status()).toBe(200);
  const body = await res.json();
  expect(body.access_token).toBeTruthy();
  return body.access_token ?? "";
}

/** Amorce l'admin Jour 0 (via `firstAdmin.ts`) puis retourne son JWT d'accès. */
export async function bootstrapAdminSession(page: Page): Promise<{
  readonly email: string;
  readonly accessToken: string;
}> {
  await createFirstAdminViaUi(page);
  const accessToken = await getBearerTokenFromSession(page);
  return { email: E2E_ADMIN.email, accessToken };
}

/** Soumet une connexion locale sur `/login` (laisse le caller vérifier 2FA, erreur ou shell). */
export async function loginLocalViaUi(page: Page, params: LocalLoginParams): Promise<void> {
  await page.goto("/login");
  await expect(page.getByTestId("login-page-container")).toBeVisible({ timeout: 20000 });
  if (params.openAccordionIfSso) {
    const toggle = page.getByTestId("login-local-accordion-toggle");
    if ((await toggle.count()) > 0 && (await toggle.isVisible())) {
      await toggle.click();
    }
  }
  await page.getByTestId("login-local-email").fill(params.email);
  await page.getByTestId("login-local-password").fill(params.password);
  if (params.totpCode) {
    const inlineTotp = page.getByTestId("login-local-totp");
    if ((await inlineTotp.count()) > 0 && (await inlineTotp.isVisible())) {
      await inlineTotp.fill(params.totpCode);
    }
  }
  await page.getByTestId("login-local-submit").click();
}

/** Déconnecte l'utilisateur courant via le popup « Mon Compte » bas-gauche. */
export async function logoutViaAccountPopover(page: Page): Promise<void> {
  await openAccountPopover(page);
  await page.getByTestId("account-popover-logout-btn").click();
  await expect(page.getByTestId("login-page-container")).toBeVisible({ timeout: 20000 });
}

/** Navigue vers `/settings` et active l'onglet d'administration demandé. */
export async function openSettingsTabViaUi(page: Page, tab: SettingsDomainTab): Promise<void> {
  await page.goto("/settings");
  await expect(page.getByTestId("settings-hub-page")).toBeVisible({ timeout: 30000 });
  await page.getByTestId(`settings-tab-${tab}`).click();
  await expect(page.getByTestId(`settings-panel-${tab}`)).toBeVisible({ timeout: 15000 });
}

/** Ouvre le popup « Mon Compte » (barre latérale bureau ou tiroir mobile). */
export async function openAccountPopover(page: Page): Promise<void> {
  await expect(page.getByTestId("four-zone-direction-c-shell")).toBeVisible({ timeout: 15000 });
  const accountBtn = page.getByTestId("sidebar-open-my-account-btn");
  if ((await accountBtn.count()) === 0 || !(await accountBtn.isVisible())) {
    const mobileToggle = page.getByTestId("mobile-menu-drawer-toggle");
    if ((await mobileToggle.count()) > 0 && (await mobileToggle.isVisible())) {
      await page.evaluate(() => window.scrollTo(0, 0));
      await mobileToggle.click();
    }
  }
  await expect(accountBtn).toBeVisible({ timeout: 10000 });
  await accountBtn.scrollIntoViewIfNeeded();
  await accountBtn.click();
  await expect(page.getByTestId("sidebar-account-popover-menu")).toBeVisible({ timeout: 10000 });
}

/** Ouvre la modale Paramètres utilisateur (5 onglets) sur l'onglet ciblé. */
export async function openUserSettingsTab(page: Page, tab: UserSettingsTab): Promise<void> {
  const modal = page.getByTestId("user-settings-modal");
  if ((await modal.count()) === 0 || !(await modal.isVisible())) {
    await openAccountPopover(page);
    await page.getByTestId("account-popover-settings-btn").click();
    await expect(modal).toBeVisible({ timeout: 15000 });
  }
  await page.getByTestId(`user-settings-tab-${tab}`).click();
  await expect(page.getByTestId(`user-settings-panel-${tab}`)).toBeVisible({ timeout: 10000 });
}

/** Crée une unité organisationnelle (BU ou TEAM) depuis `/organization`. */
export async function createOrgUnitViaOrganizationUi(
  page: Page,
  params: CreateOrgUnitParams,
): Promise<void> {
  await page.goto("/organization");
  await expect(page.getByTestId("settings-organization-section")).toBeVisible({ timeout: 30000 });
  await page.getByTestId("open-create-org-unit-modal-btn").click();
  await expect(page.getByTestId("create-org-unit-form")).toBeVisible({ timeout: 15000 });
  await page.getByTestId("org-unit-level-select").selectOption(params.level);
  await page.getByTestId("org-unit-name-input").fill(params.name);
  await page.getByTestId("org-unit-slug-input").fill(params.slug);
  if (params.parentId) {
    await page.getByTestId("org-unit-parent-select-trigger").click();
    await page.getByTestId(`org-unit-parent-select-option-${params.parentId}`).click();
  }
  if (params.leadUserQuery) {
    await page.getByTestId("org-unit-lead-input").fill(params.leadUserQuery);
    await page.getByTestId("org-unit-lead-input-add-btn").click();
  }
  if (params.level === "BU" && params.ontologyLeadQuery) {
    await page.getByTestId("org-unit-ontology-lead-input").fill(params.ontologyLeadQuery);
    await page.getByTestId("org-unit-ontology-lead-input-add-btn").click();
  }
  if (params.billingEnabled !== undefined) {
    const billingBox = page.getByTestId("org-unit-billing-checkbox");
    if ((await billingBox.isChecked()) !== params.billingEnabled) {
      await billingBox.setChecked(params.billingEnabled);
    }
  }
  await page.getByTestId("create-org-unit-btn").click();
  await expect(page.getByTestId("create-org-unit-form")).toBeHidden({ timeout: 15000 });
}

/** Invite un utilisateur scopé depuis `/organization` et retourne son mot de passe temporaire. */
export async function inviteUserViaOrganizationUi(
  page: Page,
  params: InviteScopedUserParams,
): Promise<string> {
  await page.goto("/organization");
  await expect(page.getByTestId("settings-organization-section")).toBeVisible({ timeout: 30000 });
  await page.getByTestId("open-invite-org-user-modal-btn").click();
  await expect(page.getByTestId("invite-org-user-form")).toBeVisible({ timeout: 15000 });
  if (params.orgUnitId) {
    await page.getByTestId("invite-org-unit-select").selectOption(params.orgUnitId);
  }
  await page.getByTestId("invite-org-user-display-name").fill(params.displayName);
  await page.getByTestId("invite-org-user-email").fill(params.email);
  await page.getByTestId("invite-org-user-role-select").selectOption(params.role);
  await page.getByTestId("submit-invite-org-user-btn").click();

  const tempValue = page.getByTestId("temp-password-generated-value");
  await expect(tempValue).toBeVisible({ timeout: 15000 });
  const generatedCode = (await tempValue.innerText()).trim();
  if (params.closePasswordModal !== false) {
    await page.getByTestId("temp-password-close-btn").click();
    await expect(tempValue).toBeHidden({ timeout: 10000 });
  }
  return generatedCode;
}
