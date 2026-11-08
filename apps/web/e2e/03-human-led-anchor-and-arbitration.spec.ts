import { expect, test } from "@playwright/test";
import { resetDay0 } from "./support/day0";
import { createFirstAdminViaUi, E2E_ADMIN } from "./support/firstAdmin";

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
        const res = await page.request.get("/api/v1/bootstrap/accostage-status");
        return ((await res.json()) as { first_admin_email: string | null }).first_admin_email;
      })
      .toBe(E2E_ADMIN.email);
  });

  test("signature de l'ancrage violet (≥ 30 car.), rejet agent 422, arbitrage motivé et survie au F5", async ({
    page,
  }) => {
    await page.goto("/cockpit");

    const section = page.getByTestId("cockpit-human-led-governance-section");
    await expect(section).toBeVisible();

    const anchorCard = page.getByTestId("cockpit-human-led-anchor-card");
    await expect(anchorCard).toHaveAttribute("data-human-authored-required", "true");
    await expect(anchorCard).toHaveAttribute("data-ai-generation-forbidden", "true");

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
    const agentAttempt = await page.request.post(
      "/api/v1/orchestration/runs/anchors/sign?persona_key=marc",
      {
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
    expect(((await agentAttempt.json()) as { error_code: string }).error_code).toBe(
      "ERR_HUMAN_ANCHOR_REQUIRED",
    );

    // 4. Escalade WAITING_FOR_HUMAN_ARBITRATION puis résolution motivée via ArbitrationTieBreakCard
    await page.getByTestId("cockpit-request-arbitration-btn").click();
    await expect(section).toHaveAttribute("data-step-status", "WAITING_FOR_HUMAN_ARBITRATION");

    const arbCard = page.getByTestId("cockpit-arbitration-tiebreak-card");
    await expect(arbCard).toBeVisible();
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

    // 5. Vrai F5 (localStorage vidé + rechargement) : l'état est réhydraté depuis GET /api/v1/orchestration/...
    await page.evaluate(() => window.localStorage.clear());
    const reloadBb = page.waitForResponse(
      (r) =>
        r.url().includes(`/api/v1/orchestration/runs/${runId}/blackboard`) &&
        r.request().method() === "GET",
    );
    await page.reload();
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
  });
});
