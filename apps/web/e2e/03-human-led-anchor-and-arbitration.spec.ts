/** @uj UJ-5 | @cap CAP-023 */
import { captureMilestoneScreenshot, expect, test } from "./support/e2eCaptureFixture";
import { expectDbRowExists } from "./support/dbAssertions";
import { resetDay0 } from "./support/day0";
import { createFirstAdminViaUi, E2E_ADMIN } from "./support/firstAdmin";
import { createBuAndTeamViaUi, createWorkspaceViaUi } from "./support/orgAndWorkspace";
import { apiGet, apiPost, reloadColdFromPg } from "./support/typedApiRequest";

/**
 * TEST-04 · 03 — Workflow « Human-Led » (UJ-5, Epic 3 / Story 3.4, FR-4/FR-5, BUG-E2E-02).
 *
 * Vérifie dans le navigateur :
 * 1. Le verrouillage de `HumanLedAnchorCard` (< 30 caractères) et l'absence de bouton d'auto-génération IA.
 * 2. La signature humaine (>= 30 caractères, SHA-256) via `POST /api/v1/orchestration/runs/anchors/sign`.
 * 3. Le rejet HTTP 422 `ERR_HUMAN_ANCHOR_REQUIRED` lorsqu'une identité agentique (`author_type: "AGENT"`) tente de signer.
 * 4. La mise en pause `WAITING_FOR_HUMAN_ARBITRATION` et la résolution motivée via `ArbitrationTieBreakCard` (`COMMITTED`).
 * 5. La survie au vrai F5 (`localStorage.clear()` + `page.reload()`) réhydratée par `GET /api/v1/orchestration/...`.
 */
test.describe("TEST-04 · 03 — Human-Led : ancrage obligatoire et arbitrage", () => {
  test.beforeEach(async ({ page }) => {
    resetDay0();
    await createFirstAdminViaUi(page);
    await expect
      .poll(async () => {
        const res = await apiGet<{ first_admin_email: string | null }>(
          page,
          "/api/v1/bootstrap/accostage-status",
        );
        return (await res.json()).first_admin_email;
      })
      .toBe(E2E_ADMIN.email);
    await createBuAndTeamViaUi(page);
    await createWorkspaceViaUi(page, "Espace Gouvernance E2E", "ws-gov-e2e");
  });

  test("signature de l'ancrage violet (≥ 30 car.), rejet agent 422, arbitrage motivé et survie au F5", async ({
    page,
  }, testInfo) => {
    await page.goto("/cockpit");

    // Sobriété Cockpit (<= 3 blocs à vide) : la section gouvernance Human-Led se monte au démarrage d'un run
    await expect(page.getByTestId("cockpit-launch-run-form")).toBeVisible({ timeout: 15000 });
    await expect(page.getByTestId("cockpit-human-led-governance-section")).toHaveCount(0);

    await page.getByTestId("cockpit-select-workflow").selectOption("assistant-agent");
    await page.getByTestId("cockpit-run-title-input").fill("Revue Architecture Gouvernance E2E");
    const instantiatePromise = page.waitForResponse(
      (r) => r.url().includes("/api/v1/orchestration/runs") && r.request().method() === "POST",
      { timeout: 20000 },
    );
    await page.getByTestId("cockpit-launch-run-submit-btn").click();
    expect((await instantiatePromise).status()).toBeLessThan(400);

    const section = page.getByTestId("cockpit-human-led-governance-section");
    await expect(section).toBeVisible({ timeout: 15000 });

    const anchorCard = page.getByTestId("cockpit-human-led-anchor-card");
    await anchorCard.scrollIntoViewIfNeeded();
    await expect(anchorCard).toHaveAttribute("data-human-authored-required", "true");
    await expect(anchorCard).toHaveAttribute("data-ai-generation-forbidden", "true");
    await captureMilestoneScreenshot(page, testInfo, "human-led-anchor-violet");

    const textarea = page.getByTestId("cockpit-human-anchor-textarea");
    const submitBtn = page.getByTestId("human-anchor-submit-human_architecture_intent");
    await expect(submitBtn).toBeDisabled();

    // 1. Saisie < 30 caractères : le bouton reste verrouillé
    await textarea.fill("Trop court (< 30 car.)");
    await expect(submitBtn).toBeDisabled();

    // 2. Saisie humaine >= 30 caractères et signature SHA-256
    const validIntent =
      "Invariants d'architecture : isolation hexagonale stricte et contrat OpenAPI 3.1 sans dérive.";
    await textarea.fill(validIntent);
    await expect(submitBtn).toBeEnabled();

    const signRespPromise = page.waitForResponse(
      (r) =>
        r.url().includes("/api/v1/orchestration/runs/anchors/sign") &&
        r.request().method() === "POST",
    );
    await submitBtn.click();
    const signResp = await signRespPromise;
    expect(signResp.status()).toBe(200);

    await expect(page.getByTestId("cockpit-human-anchor-signed-badge")).toBeVisible();
    const runId = (await section.getAttribute("data-run-id")) ?? "";
    expect(runId.length).toBeGreaterThan(0);

    // 3. Rejet 422 ERR_HUMAN_ANCHOR_REQUIRED pour une identité agentique (FR-4)
    const refreshRes = await apiPost<{ access_token?: string }>(page, "/api/v1/auth/refresh");
    expect(refreshRes.status()).toBe(200);
    const { access_token: adminToken } = await refreshRes.json();
    expect(adminToken).toBeTruthy();
    const agentAttempt = await apiPost<{ error_code: string }>(
      page,
      "/api/v1/orchestration/runs/anchors/sign",
      {
        token: adminToken,
        data: {
          run_id: runId,
          step_key: "frame-architecture-intent",
          section_key: "human_architecture_intent",
          content_text:
            "Texte généré automatiquement par un agent dépassant trente caractères.",
          signature_text: "AgentBot",
          author_type: "AGENT",
        },
      },
    );
    expect(agentAttempt.status()).toBe(422);
    expect((await agentAttempt.json()).error_code).toBe(
      "ERR_HUMAN_ANCHOR_REQUIRED",
    );

    // 4. Escalade WAITING_FOR_HUMAN_ARBITRATION puis résolution motivée via ArbitrationTieBreakCard
    await page.getByTestId("cockpit-request-arbitration-btn").click();
    await expect(section).toHaveAttribute("data-step-status", "WAITING_FOR_HUMAN_ARBITRATION");

    const arbCard = page.getByTestId("cockpit-arbitration-tiebreak-card");
    await arbCard.scrollIntoViewIfNeeded();
    await expect(arbCard).toBeVisible();
    await captureMilestoneScreenshot(page, testInfo, "arbitration-tiebreak-amber");
    await arbCard
      .locator('input[type="text"]')
      .fill("Alignement immédiat avec le contrat OpenAPI v3 du partenaire.");

    const resolveRespPromise = page.waitForResponse(
      (r) =>
        r.url().includes("/arbitration/resolve") && r.request().method() === "POST",
    );
    await page.getByTestId("arbitration-select-OPT_A_SPOT_15M").click();
    const resolveResp = await resolveRespPromise;
    expect(resolveResp.status()).toBe(200);

    await expect(section).toHaveAttribute("data-step-status", "COMMITTED");
    const summary = page.getByTestId("cockpit-arbitration-resolved-summary");
    await expect(summary).toHaveAttribute("data-selected-option", "OPT_A_SPOT_15M");
    const snapshotId = (await summary.getAttribute("data-committed-snapshot-id")) ?? "";
    expect(snapshotId.length).toBeGreaterThan(0);

    // 5. Vrai F5 à froid (éviction RAM + localStorage vidé + rechargement) : réhydraté depuis PG18
    const reloadBb = page.waitForResponse(
      (r) =>
        r.url().includes(`/api/v1/orchestration/runs/${runId}/blackboard`) &&
        r.request().method() === "GET",
    );
    await reloadColdFromPg(page);
    expect((await reloadBb).status()).toBe(200);

    await expect(page.getByTestId("cockpit-human-anchor-signed-badge")).toBeVisible();
    await expect(page.getByTestId("cockpit-human-led-governance-section")).toHaveAttribute(
      "data-step-status",
      "COMMITTED",
    );
    await expect(page.getByTestId("cockpit-arbitration-resolved-summary")).toHaveAttribute(
      "data-selected-option",
      "OPT_A_SPOT_15M",
    );
    expectDbRowExists(
      "SELECT id, section_key, char_length FROM human_anchor_signatures WHERE section_key = :section_key AND content_text = :content_text AND char_length >= 30",
      { section_key: "human_architecture_intent", content_text: validIntent },
      "ancrage humain signé persisté dans human_anchor_signatures",
    );
  });
});
