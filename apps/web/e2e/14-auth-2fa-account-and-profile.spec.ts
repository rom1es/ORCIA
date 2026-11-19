/** @uj UJ-13, UJ-16 | @cap CAP-001, CAP-058, CAP-063, CAP-069 */
import { createHmac } from "node:crypto";
import { expect, test } from "./support/e2eCaptureFixture";
import { resetDay0 } from "./support/day0";
import { expectDbRowExists, queryDbRows } from "./support/dbAssertions";
import { E2E_ADMIN } from "./support/firstAdmin";
import {
  bootstrapAdminSession,
  loginLocalViaUi,
  logoutViaAccountPopover,
  openAccountPopover,
  openSettingsTabViaUi,
  openUserSettingsTab,
  inviteUserViaOrganizationUi,
} from "./support/authAndOrgHelpers";

function computeTotpCode(secretBase32: string): string {
  const alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"; // pragma: allowlist secret
  const cleaned = secretBase32.replace(/[\s=-]+/g, "").toUpperCase();
  let bits = 0;
  let value = 0;
  const bytes: number[] = [];
  for (const ch of cleaned) {
    const idx = alphabet.indexOf(ch);
    if (idx < 0) continue;
    value = (value << 5) | idx;
    bits += 5;
    if (bits >= 8) {
      bytes.push((value >>> (bits - 8)) & 0xff);
      bits -= 8;
    }
  }
  const counter = Math.floor(Date.now() / 1000 / 30);
  const counterBuf = Buffer.alloc(8);
  counterBuf.writeBigUInt64BE(BigInt(counter), 0);
  const digest = createHmac("sha1", Buffer.from(bytes)).update(counterBuf).digest();
  const offset = digest[digest.length - 1] & 0x0f;
  const code =
    ((digest[offset] & 0x7f) << 24) |
    ((digest[offset + 1] & 0xff) << 16) |
    ((digest[offset + 2] & 0xff) << 8) |
    (digest[offset + 3] & 0xff);
  return String(code % 1_000_000).padStart(6, "0");
}

test.describe("Auth, 2FA, compte utilisateur et profil personnel", () => {
  test.beforeEach(() => {
    resetDay0();
  });

  test("politique d'authentification et bascule 2FA persistent après F5 en base PostgreSQL", async ({
    page,
  }, testInfo) => {
    await bootstrapAdminSession(page);
    await openSettingsTabViaUi(page, "authentication");
    await expect(page.getByTestId("auth-mode-option-LOCAL")).toHaveAttribute("aria-checked", "true");

    await page.getByTestId("two-factor-mode-option-EMAIL_OTP").click();
    await expect(page.getByTestId("auth-smtp-status-badge")).toBeVisible();
    await expect(page.getByTestId("auth-goto-connectors-btn")).toBeVisible();
    await page.getByTestId("auth-save-settings-btn").click();
    await expect(page.getByTestId("auth-save-feedback")).toBeVisible({ timeout: 10000 });

    await page.getByTestId("two-factor-mode-option-TOTP").click();
    await page.getByTestId("auth-save-settings-btn").click();
    await expect(page.getByTestId("auth-save-feedback")).toBeVisible({ timeout: 10000 });

    await page.evaluate(() => {
      window.localStorage.clear();
      window.sessionStorage.clear();
    });
    await page.goto("/settings?tab=authentication");
    await page.reload();
    await expect(page.getByTestId("two-factor-mode-option-TOTP")).toHaveAttribute(
      "aria-checked",
      "true",
      { timeout: 15000 },
    );

    expectDbRowExists(
      "SELECT singleton_key, auth_mode, two_factor_mode FROM platform_auth_settings WHERE singleton_key = 'GLOBAL' AND auth_mode = 'LOCAL' AND two_factor_mode = 'TOTP'",
      undefined,
      "politique 2FA TOTP persistée dans platform_auth_settings",
    );

    await logoutViaAccountPopover(page);
    await loginLocalViaUi(page, { email: E2E_ADMIN.email, password: E2E_ADMIN.password });
    await expect(page.getByTestId("login-2fa-panel")).toBeVisible({ timeout: 15000 });
    await expect(page.getByTestId("login-2fa-totp-enroll-box")).toBeVisible();
    const manualKey = (await page.getByTestId("login-2fa-totp-manual-key").innerText()).trim();
    expect(manualKey.length).toBeGreaterThan(8);

    await page.getByTestId("login-2fa-code-input").fill(computeTotpCode(manualKey));
    await page.getByTestId("login-2fa-submit-btn").click();
    await expect(page.getByTestId("four-zone-direction-c-shell")).toBeVisible({ timeout: 20000 });

    await openSettingsTabViaUi(page, "authentication");
    await page.getByTestId("two-factor-mode-option-NONE").click();
    await page.getByTestId("auth-save-settings-btn").click();
    await expect(page.getByTestId("auth-save-feedback")).toBeVisible({ timeout: 10000 });
    expectDbRowExists(
      "SELECT singleton_key, two_factor_mode FROM platform_auth_settings WHERE singleton_key = 'GLOBAL' AND two_factor_mode = 'NONE'",
      undefined,
      "retour politique 2FA NONE persisté",
    );

    if (testInfo.project.name === "mobile-companion") {
      const overflow = await page.evaluate(
        () => document.documentElement.scrollWidth - window.innerWidth,
      );
      expect(overflow).toBeLessThanOrEqual(1);
    }
  });

  test("mot de passe temporaire d'un compte invité force le renouvellement et persiste dans users", async ({
    page,
  }) => {
    await bootstrapAdminSession(page);
    const invitedEmail = "claire.invite@e2e.orcia.test";
    const tempPass = await inviteUserViaOrganizationUi(page, {
      displayName: "Claire Invitée",
      email: invitedEmail,
      role: "CONTRIBUTOR",
    });
    expect(tempPass.length).toBeGreaterThanOrEqual(8);

    expectDbRowExists(
      "SELECT email, must_change_password FROM users WHERE email = :email AND must_change_password = TRUE",
      { email: invitedEmail },
      "mot de passe temporaire initialisé dans users",
    );

    await logoutViaAccountPopover(page);
    await loginLocalViaUi(page, { email: invitedEmail, password: tempPass });
    await expect(page.getByTestId("temporary-password-warning-banner")).toBeVisible({
      timeout: 20000,
    });
    await page.getByTestId("temporary-password-open-settings-btn").click();
    await expect(page.getByTestId("user-password-change-card")).toBeVisible({ timeout: 15000 });
    await expect(page.getByTestId("user-must-change-password-badge")).toBeVisible();

    const updatedPass = "Claire-N3w-Secur3-Pass!"; // pragma: allowlist secret
    await page.getByTestId("user-current-password-input").fill(tempPass);
    await page.getByTestId("user-new-password-input").fill(updatedPass);
    await page.getByTestId("user-confirm-password-input").fill(updatedPass);
    await page.getByTestId("user-change-password-submit-btn").click();
    await expect(page.getByTestId("user-change-password-feedback")).toBeVisible({ timeout: 15000 });
    await page.getByTestId("user-settings-modal-close-btn").click();
    await expect(page.getByTestId("temporary-password-warning-banner")).toBeHidden({
      timeout: 15000,
    });

    await page.evaluate(() => {
      window.localStorage.clear();
      window.sessionStorage.clear();
    });
    await page.reload();
    await expect(page.getByTestId("four-zone-direction-c-shell")).toBeVisible({ timeout: 20000 });
    await expect(page.getByTestId("temporary-password-warning-banner")).toBeHidden();

    expectDbRowExists(
      "SELECT email, must_change_password FROM users WHERE email = :email AND must_change_password = FALSE",
      { email: invitedEmail },
      "renouvellement mot de passe persisté dans users",
    );

    await logoutViaAccountPopover(page);
    await loginLocalViaUi(page, { email: invitedEmail, password: updatedPass });
    await expect(page.getByTestId("four-zone-direction-c-shell")).toBeVisible({ timeout: 20000 });
  });

  test("popup Mon Compte, paramètres 5 onglets, clé IDE/MCP et page profil survivent à un F5", async ({
    page,
  }, testInfo) => {
    await bootstrapAdminSession(page);

    await openAccountPopover(page);
    await expect(page.getByTestId("account-popover-identity-header")).toBeVisible();
    await page.getByTestId("account-popover-settings-btn").click();
    await expect(page.getByTestId("user-settings-modal")).toBeVisible({ timeout: 15000 });
    for (const tabKey of [
      "GENERAL",
      "PERSONALIZATION",
      "ACCOUNT_SECURITY",
      "PASSTHROUGH_SOURCES",
      "IDE_MCP_KEYS",
    ] as const) {
      await expect(page.getByTestId(`user-settings-tab-${tabKey}`)).toBeVisible();
    }

    await openUserSettingsTab(page, "PERSONALIZATION");
    await page.getByTestId("settings-assistant-hat-select").selectOption("ARCHITECT");
    await page.getByTestId("settings-assistant-tone-select").selectOption("concise");
    await page
      .getByTestId("settings-personal-instructions-input")
      .fill("Réponses synthétiques orientées conception.");
    await page.getByTestId("settings-personalization-save-btn").click();
    await expect(page.getByTestId("settings-personalization-saved-banner")).toBeVisible({
      timeout: 15000,
    });

    await openUserSettingsTab(page, "IDE_MCP_KEYS");
    await page.getByTestId("mcp-token-label-input").fill("VSCode E2E");
    await page.getByTestId("mcp-target-slug-input").fill("default");
    await page.getByTestId("mcp-generate-token-btn").click();
    await expect(page.getByTestId("mcp-issued-plaintext-banner")).toBeVisible({ timeout: 15000 });
    await expect(page.getByTestId("mcp-issued-plaintext-value")).toContainText("pat_mcp_");
    await page.getByTestId("user-settings-modal-close-btn").click();

    await openAccountPopover(page);
    await page.getByTestId("account-popover-profile-btn").click();
    await expect(page.getByTestId("user-profile-overview-page")).toBeVisible({ timeout: 20000 });
    const kpiEmptyState = page.getByTestId("profile-kpis-empty-state");
    const kpiTotalTokens = page.getByTestId("profile-kpi-total-tokens");
    if (await kpiEmptyState.isVisible()) {
      await expect(kpiTotalTokens).toHaveCount(0);
    } else {
      for (const kpiId of [
        "profile-kpi-total-tokens",
        "profile-kpi-peak-tokens",
        "profile-kpi-longest-streak",
        "profile-kpi-current-streak",
      ]) {
        await expect(page.getByTestId(kpiId)).toBeVisible();
      }
    }
    await page.getByTestId("profile-open-account-settings-btn").click();
    await expect(page.getByTestId("user-settings-modal")).toBeVisible({ timeout: 15000 });
    await page.getByTestId("user-settings-modal-close-btn").click();

    await page.evaluate(() => {
      window.localStorage.clear();
      window.sessionStorage.clear();
    });
    await page.goto("/profile");
    await page.reload();
    await expect(page.getByTestId("user-profile-overview-page")).toBeVisible({ timeout: 20000 });
    await expect(
      page.getByTestId("profile-kpis-empty-state").or(page.getByTestId("profile-kpi-total-tokens")),
    ).toBeVisible();

    await openUserSettingsTab(page, "PERSONALIZATION");
    await expect(page.getByTestId("settings-assistant-hat-select")).toHaveValue("ARCHITECT");
    await expect(page.getByTestId("settings-assistant-tone-select")).toHaveValue("concise");
    await openUserSettingsTab(page, "IDE_MCP_KEYS");
    await expect(page.getByTestId("mcp-tokens-list")).toContainText("VSCode E2E");

    expectDbRowExists(
      "SELECT user_id, default_assistant_hat, assistant_tone FROM user_preferences WHERE default_assistant_hat = 'ARCHITECT' AND assistant_tone = 'concise'",
      undefined,
      "préférences assistant persistées dans user_preferences",
    );
    expectDbRowExists(
      "SELECT id, label, target_slug FROM user_mcp_tokens WHERE label = :label AND revoked_at IS NULL",
      { label: "VSCode E2E" },
      "jeton IDE/MCP persisté dans user_mcp_tokens",
    );
    const ledgerRows = queryDbRows<{ total_tokens: number }>(
      "SELECT COALESCE(SUM(input_tokens + output_tokens), 0)::int AS total_tokens FROM audit_ledger WHERE LOWER(COALESCE(actor_email, '')) = LOWER(:email)",
      { email: E2E_ADMIN.email },
    );
    expect(ledgerRows[0]?.total_tokens).toBeGreaterThanOrEqual(0);

    if (testInfo.project.name === "mobile-companion") {
      const overflow = await page.evaluate(
        () => document.documentElement.scrollWidth - window.innerWidth,
      );
      expect(overflow).toBeLessThanOrEqual(1);
    }
  });
});
