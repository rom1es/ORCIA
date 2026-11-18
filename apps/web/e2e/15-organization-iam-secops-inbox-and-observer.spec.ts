/** @uj UJ-4, UJ-14 | @cap CAP-040, CAP-041, CAP-043, CAP-050, CAP-051, CAP-065, CAP-067, CAP-203 */
import { expect, test } from "./support/e2eCaptureFixture";
import { resetDay0 } from "./support/day0";
import { expectDbRowCount, expectDbRowExists } from "./support/dbAssertions";
import { E2E_ADMIN } from "./support/firstAdmin";
import {
  bootstrapAdminSession,
  createOrgUnitViaOrganizationUi,
  getBearerTokenFromSession,
  inviteUserViaOrganizationUi,
  loginLocalViaUi,
  logoutViaAccountPopover,
  openSettingsTabViaUi,
} from "./support/authAndOrgHelpers";

test.describe("Organisation, annuaire IAM, exceptions SecOps, notifications et mode observateur", () => {
  test.beforeEach(() => {
    resetDay0();
  });

  test("BU, équipe, invitation scopée, délégation BU_LEAD, garde 403 et journal audit_ledger persistent après F5", async ({
    page,
  }) => {
    await bootstrapAdminSession(page);

    await createOrgUnitViaOrganizationUi(page, {
      level: "BU",
      name: "Direction Produit E2E",
      slug: "bu-produit-e2e",
      billingEnabled: true,
    });
    const buRow = expectDbRowExists(
      "SELECT id, slug, unit_type FROM org_units WHERE slug = :slug AND unit_type = 'BU'",
      { slug: "bu-produit-e2e" },
      "BU Direction Produit persistée dans org_units",
    );
    const buId = String(buRow.id);

    await createOrgUnitViaOrganizationUi(page, {
      level: "TEAM",
      name: "Équipe Core E2E",
      slug: "team-core-e2e",
      parentId: buId,
    });
    const teamRow = expectDbRowExists(
      "SELECT id, slug, unit_type, parent_id FROM org_units WHERE slug = :slug AND unit_type = 'TEAM'",
      { slug: "team-core-e2e" },
      "Équipe Core persistée dans org_units",
    );
    expect(String(teamRow.parent_id)).toBe(buId);

    const leadEmail = "marc.lead@e2e.orcia.test";
    const tempPass = await inviteUserViaOrganizationUi(page, {
      orgUnitId: buId,
      displayName: "Marc Lead BU",
      email: leadEmail,
      role: "BU_LEAD",
    });

    expectDbRowExists(
      "SELECT id, email, status FROM iam_accounts WHERE email = :email",
      { email: leadEmail },
      "compte invité persisté dans iam_accounts",
    );
    expectDbRowExists(
      "SELECT id, event_type, org_unit_id FROM audit_ledger WHERE org_unit_id = :org_unit_id",
      { org_unit_id: buId },
      "trace d'audit scopée avec org_unit_id dans audit_ledger",
    );

    await page.evaluate(() => {
      window.localStorage.clear();
      window.sessionStorage.clear();
    });
    await page.goto("/organization");
    await page.reload();
    await expect(page.getByTestId(`org-unit-name-${buId}`)).toBeVisible({ timeout: 20000 });

    await logoutViaAccountPopover(page);
    await loginLocalViaUi(page, { email: leadEmail, password: tempPass });
    await expect(page.getByTestId("four-zone-direction-c-shell")).toBeVisible({ timeout: 20000 });

    const leadToken = await getBearerTokenFromSession(page);
    const deleteBuRes = await page.request.delete(`/api/v1/org-units/${buId}`, {
      headers: { Authorization: `Bearer ${leadToken}` },
    });
    expect(deleteBuRes.status()).toBe(403);

    const escalateRes = await page.request.post("/api/v1/settings/iam/accounts", {
      headers: { Authorization: `Bearer ${leadToken}` },
      data: {
        account_kind: "HUMAN",
        display_name: "Escalade Interdite",
        email: "escalade@e2e.orcia.test",
        principal_id: "escalade@e2e.orcia.test",
        roles: ["PLATFORM_ADMIN"],
        status: "ACTIVE",
      },
    });
    expect(escalateRes.status()).toBe(403);
  });

  test("annuaire IAM, matrice des rôles et règle RBAC SecOps persistent dans role_permission_grants après F5", async ({
    page,
  }) => {
    await bootstrapAdminSession(page);
    await openSettingsTabViaUi(page, "iam");
    await expect(page.getByTestId("iam-accounts-directory-card")).toBeVisible({ timeout: 15000 });

    await page.getByTestId("iam-open-role-matrix-modal-btn").click();
    await expect(page.getByTestId("iam-role-matrix-modal")).toBeVisible({ timeout: 10000 });
    await page.getByTestId("iam-close-role-matrix-modal-btn").click();
    await expect(page.getByTestId("iam-role-matrix-modal")).toBeHidden();

    await page.getByTestId("iam-secops-drawer-toggle").click();
    await expect(page.getByTestId("iam-secops-drawer-body")).toBeVisible({ timeout: 10000 });
    await page.getByTestId("rbac-subject-type-select").selectOption("ROLE");
    await page.getByTestId("rbac-subject-select").selectOption("CONTRIBUTOR");
    await page.getByTestId("rbac-scope-preset-select").selectOption("GLOBAL");
    await page.getByTestId("rbac-effect-select").selectOption("ALLOW");
    await page.getByTestId("rbac-verb-checkbox-execute").check();
    await page.getByTestId("create-rbac-grant-btn").click();

    await expect(page.locator("[data-testid^='rbac-grant-row-']").first()).toBeVisible({
      timeout: 15000,
    });

    await page.evaluate(() => {
      window.localStorage.clear();
      window.sessionStorage.clear();
    });
    await page.goto("/settings?tab=iam");
    await page.reload();
    await expect(page.getByTestId("iam-secops-drawer-toggle")).toBeVisible({ timeout: 20000 });
    await page.getByTestId("iam-secops-drawer-toggle").click();
    await expect(page.locator("[data-testid^='rbac-grant-row-']").first()).toBeVisible({
      timeout: 15000,
    });

    expectDbRowExists(
      "SELECT id, subject_type, subject_id, scope_path, verb, effect FROM role_permission_grants WHERE subject_type = 'ROLE' AND subject_id = 'CONTRIBUTOR' AND scope_path = 'GLOBAL' AND verb = 'execute' AND effect = 'ALLOW'",
      undefined,
      "exception SecOps RBAC persistée dans role_permission_grants",
    );
  });

  test("mode observateur en lecture seule rejette toute mutation en HTTP 403 ERR_OBSERVER_MODE_READ_ONLY", async ({
    page,
  }) => {
    await bootstrapAdminSession(page);
    const observerEmail = "oscar.observer@e2e.orcia.test";
    const tempPass = await inviteUserViaOrganizationUi(page, {
      displayName: "Oscar Observateur",
      email: observerEmail,
      role: "OBSERVER",
    });

    await logoutViaAccountPopover(page);
    await loginLocalViaUi(page, { email: observerEmail, password: tempPass });
    await expect(page.getByTestId("four-zone-direction-c-shell")).toBeVisible({ timeout: 20000 });

    await page.goto("/organization");
    await expect(page.getByTestId("organization-readonly-access-banner")).toBeVisible({
      timeout: 15000,
    });

    const observerToken = await getBearerTokenFromSession(page);
    const mutationRes = await page.request.post("/api/v1/org-units", {
      headers: { Authorization: `Bearer ${observerToken}` },
      data: {
        kind: "BU",
        name: "BU Interdite Observateur",
        slug: "bu-interdite-obs",
        billing_enabled: false,
      },
    });
    expect(mutationRes.status()).toBe(403);
    const problem = (await mutationRes.json()) as { error_code?: string };
    expect(problem.error_code).toBe("ERR_OBSERVER_MODE_READ_ONLY");
  });

  test("centre de notifications et boîte de réception reflètent task_notifications en base PostgreSQL", async ({
    page,
  }) => {
    await bootstrapAdminSession(page);
    const adminToken = await getBearerTokenFromSession(page);
    const inboxRes = await page.request.get("/api/v1/inbox/notifications", {
      headers: { Authorization: `Bearer ${adminToken}` },
    });
    expect(inboxRes.status()).toBe(200);
    const inboxPayload = (await inboxRes.json()) as { items?: unknown[] };
    expect(Array.isArray(inboxPayload.items)).toBe(true);

    await page.getByTestId("topbar-notifications-toggle").click();
    await expect(page.getByTestId("topbar-notifications-drawer")).toBeVisible({ timeout: 10000 });
    await page.getByTestId("topbar-notifications-close").click();

    await page.goto("/inbox");
    await expect(page.getByTestId("inbox-feature-panel")).toBeVisible({ timeout: 15000 });

    expectDbRowCount(
      "SELECT COUNT(*)::int AS count FROM task_notifications",
      undefined,
      1,
      "notifications d'équipe persistées dans task_notifications PG18",
    );
    expect(E2E_ADMIN.email).toBeTruthy();
  });
});
