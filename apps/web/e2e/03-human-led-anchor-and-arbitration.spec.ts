import { test } from "@playwright/test";

/**
 * TEST-04 · 03 — Workflow « Human-Led » (UJ-5, Epic 3, FR-4/FR-5).
 *
 * ÉCART PRODUIT (BUG-E2E-02) : `HumanLedAnchorCard` et `ArbitrationTieBreakCard` (@orcia/ui) ne sont
 * montés dans AUCUN écran d'`apps/web` ; seuls les endpoints API existent
 * (`POST /api/v1/orchestration/runs/anchors/sign`, `/{run_id}/steps/{step_key}/arbitration[/resolve]`).
 * Le parcours navigateur « signature d'ancrage → arbitrage → commit Blackboard » est donc
 * impossible à tester tant que l'UI n'est pas câblée. Scénario cible conservé en `fixme`.
 */
test.describe("TEST-04 · 03 — Human-Led : ancrage obligatoire et arbitrage", () => {
  test.fixme(
    "signature de l'ancrage violet (≥ 30 car.) puis arbitrage motivé, état commité en base",
    async () => {
      // 1. Créer un run (cockpit) 2. Saisir/signer l'ancrage (HumanLedAnchorCard, violet réservé)
      // 3. Pause WAITING_FOR_HUMAN_ARBITRATION 4. Résoudre l'arbitrage avec motif
      // 5. Recharger (F5) : l'état persiste (GET) 6. Rejet 422 ERR_HUMAN_ANCHOR_REQUIRED pour un agent
    },
  );
});
