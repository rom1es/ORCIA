/** @uj UJ-5 | @cap CAP-023 */
import { captureMilestoneScreenshot, expect, test } from "./support/e2eCaptureFixture";
import { expectDbRowExists } from "./support/dbAssertions";
import { resetDay0 } from "./support/day0";
import { createFirstAdminViaUi, E2E_ADMIN } from "./support/firstAdmin";
import { assertNoDesktopVerticalPageOverflow } from "./support/layoutGeometryAssertions";
import { createBuAndTeamViaUi, createWorkspaceViaUi } from "./support/orgAndWorkspace";
import { apiGet, apiPost, reloadColdFromPg } from "./support/typedApiRequest";

/**
 * TEST-04 · 03 — Workflow « Human-Led » (UJ-5, Epic 3 / Story 3.4, Story 25.3, FR-4/FR-5).
 *
 * Vérifie dans le navigateur :
 * 1. Sobriété Jour 0 : à 0 run / 0 décision, aucun bandeau "Aucune décision en attente",
 *    aucun bloc "Accès rapide à Mon Assistant" et aucune carte "Human-Led Governance".
 * 2. Montage conditionnel de `HumanLedAnchorCard` uniquement lorsqu'un run actif requiert un ancrage,
 *    verrouillage < 30 car., signature SHA-256 et disparition immédiate après signature.
 * 3. Rejet HTTP 422 `ERR_HUMAN_ANCHOR_REQUIRED` lorsqu'une identité agentique (`author_type: "AGENT"`) tente de signer.
 * 4. Montage de `ArbitrationTieBreakCard` uniquement sur un arbitrage réel PG18 (options réelles, zéro fallback fictif),
 *    résolution motivée, disparition après résolution et survie au vrai F5 à froid.
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

  test("sobriété à 0 décision, signature d'ancrage, rejet agent 422, arbitrage réel PG18 et disparition après F5", async ({
    page,
  }, testInfo) => {
    await page.goto("/cockpit");

    // 0. Story 25.3: Cockpit à 0 run / 0 décision -> zéro bloc d'attente, zéro Human-Led Governance
    await expect(page.getByTestId("cockpit-launch-run-form")).toBeVisible({ timeout: 15000 });
    await expect(page.getByTestId("cockpit-calm-orientation-panel")).toBeVisible();
    await expect(page.getByTestId("cockpit-calm-orientation-panel").locator("button")).toHaveCount(
      3,
    );
    await expect(
      page.getByTestId("cockpit-calm-orientation-panel").locator("input, textarea"),
    ).toHaveCount(0);
    await expect(page.getByTestId("cockpit-human-led-governance-section")).toHaveCount(0);
    await expect(page.getByTestId("cockpit-human-led-anchor-card")).toHaveCount(0);
    await expect(page.getByTestId("cockpit-arbitration-tiebreak-card")).toHaveCount(0);
    await expect(page.locator("body")).not.toContainText(
      /No pending decisions|Aucune décision en attente|Quick access to My Assistant|Accès rapide à Mon Assistant|Human-Led Governance|Gouvernance Human-Led|DECISION REQUIRED/i,
    );

    // 1. Démarrage d'un vrai run PG18 nécessitant un ancrage humain
    await page.getByTestId("cockpit-select-workflow").selectOption("assistant-agent");
    await page.getByTestId("cockpit-run-title-input").fill("Revue Architecture Gouvernance E2E");
    const instantiatePromise = page.waitForResponse(
      (r) =>
        r.url().includes("/api/v1/orchestration/runs/instantiate") &&
        r.request().method() === "POST",
      { timeout: 20000 },
    );
    await page.getByTestId("cockpit-launch-run-submit-btn").click();
    const instantiateResp = await instantiatePromise;
    expect(instantiateResp.status()).toBeLessThan(400);
    const instantiateJson = (await instantiateResp.json()) as { run: { id: string } };
    const runId = instantiateJson.run.id;
    expect(runId.length).toBeGreaterThan(0);

    const section = page.getByTestId("cockpit-human-led-governance-section");
    await expect(section).toBeVisible({ timeout: 15000 });
    await expect(page.getByTestId("progressive-day0-accostage-banner")).toHaveAttribute(
      "data-compact",
      "false",
    );
    if (testInfo.project.name === "desktop-cockpit") {
      await assertNoDesktopVerticalPageOverflow(page, "cockpit-with-active-run-and-anchor");
    }

    // Seul HumanLedAnchorCard est monté (aucun ArbitrationTieBreakCard fictif)
    const anchorCard = page.getByTestId("cockpit-human-led-anchor-card");
    await anchorCard.scrollIntoViewIfNeeded();
    await expect(anchorCard).toBeVisible();
    await expect(page.getByTestId("cockpit-arbitration-tiebreak-card")).toHaveCount(0);
    await expect(anchorCard).toHaveAttribute("data-human-authored-required", "true");
    await expect(anchorCard).toHaveAttribute("data-ai-generation-forbidden", "true");
    await captureMilestoneScreenshot(page, testInfo, "human-led-anchor-violet");

    const textarea = page.getByTestId("cockpit-human-anchor-textarea");
    const submitBtn = page.getByTestId("human-anchor-submit-human_architecture_intent");
    await expect(submitBtn).toBeDisabled();

    // Saisie < 30 caractères : le bouton reste verrouillé
    await textarea.fill("Trop court (< 30 car.)");
    await expect(submitBtn).toBeDisabled();

    // 2. Saisie humaine >= 30 caractères et signature SHA-256 -> la carte disparaît après signature
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

    await expect(anchorCard).toHaveCount(0, { timeout: 15000 });
    await expect(section).toHaveCount(0, { timeout: 15000 });

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
    expect((await agentAttempt.json()).error_code).toBe("ERR_HUMAN_ANCHOR_REQUIRED");

    // 4. Création d'un vrai arbitrage PG18 avec options réelles -> affichage puis disparition après résolution
    const createArbRes = await apiPost<{ arbitration: { id: string } }>(
      page,
      `/api/v1/orchestration/runs/${runId}/steps/frame-architecture-intent/arbitration`,
      {
        token: adminToken,
        data: {
          question_title: "Stratégie d'indexation documentaire PG18",
          context_summary: "Choisir le mécanisme de persistance et d'indexation réel.",
          tie_break_policy: "PAUSE_AND_ESCALATE",
          options_matrix: [
            {
              option_key: "OPT_PG_OUTBOX",
              title: "Outbox PostgreSQL 18 transactionnelle",
              pros: ["Atomicité ACID garantie"],
              cons: ["Polling worker 500 ms"],
              si_impact: "Natif PG18",
              finops_impact: "0 €/mois",
              recommended: true,
            },
            {
              option_key: "OPT_REDIS_STREAMS",
              title: "Redis Streams asynchrone",
              pros: ["Latence sub-milliseconde"],
              cons: ["Double écriture à réconcilier"],
              si_impact: "Dépendance Redis",
              finops_impact: "15 €/mois",
              recommended: false,
            },
          ],
        },
      },
    );
    expect(createArbRes.status()).toBe(200);

    await reloadColdFromPg(page);

    const arbCard = page.getByTestId("cockpit-arbitration-tiebreak-card");
    await expect(arbCard).toBeVisible({ timeout: 15000 });
    await expect(page.getByTestId("cockpit-human-led-anchor-card")).toHaveCount(0);
    await expect(arbCard).toContainText("Outbox PostgreSQL 18 transactionnelle");
    await expect(arbCard).toContainText("Redis Streams asynchrone");
    await expect(page.locator("body")).not.toContainText(/Taux Spot 15 min|Taux Bloqué 48h/);
    await arbCard.scrollIntoViewIfNeeded();
    await captureMilestoneScreenshot(page, testInfo, "arbitration-tiebreak-amber");

    await arbCard
      .locator('input[type="text"]')
      .fill("Atomicité ACID PostgreSQL 18 prioritaire pour la traçabilité.");

    const resolveRespPromise = page.waitForResponse(
      (r) => r.url().includes("/arbitration/resolve") && r.request().method() === "POST",
    );
    await page.getByTestId("arbitration-select-OPT_PG_OUTBOX").click();
    const resolveResp = await resolveRespPromise;
    expect(resolveResp.status()).toBe(200);

    // Disparition immédiate des blocs de gouvernance une fois résolus
    await expect(arbCard).toHaveCount(0, { timeout: 15000 });
    await expect(section).toHaveCount(0, { timeout: 15000 });

    // 5. Vrai F5 à froid : aucune réapparition des blocs résolus
    await reloadColdFromPg(page);
    await expect(page.getByTestId("cockpit-block-accostage")).toBeVisible({ timeout: 20000 });
    await expect(page.getByTestId("cockpit-human-led-governance-section")).toHaveCount(0);
    await expect(page.getByTestId("cockpit-human-led-anchor-card")).toHaveCount(0);
    await expect(page.getByTestId("cockpit-arbitration-tiebreak-card")).toHaveCount(0);

    expectDbRowExists(
      "SELECT id, section_key, char_length FROM human_anchor_signatures WHERE section_key = :section_key AND content_text = :content_text AND char_length >= 30",
      { section_key: "human_architecture_intent", content_text: validIntent },
      "ancrage humain signé persisté dans human_anchor_signatures",
    );
    expectDbRowExists(
      "SELECT id, status, selected_option_key FROM human_arbitration_requests WHERE run_id = CAST(:run_id AS uuid) AND status = 'RESOLVED_BY_HUMAN' AND selected_option_key = 'OPT_PG_OUTBOX'",
      { run_id: runId },
      "arbitrage humain résolu persisté dans human_arbitration_requests",
    );
  });
});
