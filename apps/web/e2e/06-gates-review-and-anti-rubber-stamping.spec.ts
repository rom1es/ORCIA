import { test } from "@playwright/test";

/**
 * TEST-05 · 06 — Gates tri-modales (UJ-6, Epic 4, FR-6/FR-18/FR-19).
 *
 * ÉCART PRODUIT (BUG-E2E-05) : `CognitiveReviewBriefingGrid` et `ChunkValidationCard` (@orcia/ui)
 * ne sont montés dans AUCUN écran d'`apps/web` ; seuls les endpoints existent
 * (`/api/v1/gates*`, `human_gates.py`). Le parcours navigateur « briefing 4 blocs → validation par
 * découpage → garde-fou anti-rubber-stamp < 15 s » est donc intestable. Scénario cible en `fixme`.
 */
test.describe("TEST-05 · 06 — Gates : briefing de revue et anti-rubber-stamping", () => {
  test.fixme(
    "inspection du Bloc 4, approbation par découpage et garde-fou < 15 s",
    async () => {
      // 1. Run en attente de gate humaine 2. Ouvrir le briefing 4 blocs 3. Approuver un découpage
      // trop vite → ERR_RUBBER_STAMPING_GUARD_TRIGGERED 4. Actions Jira staged exécutées après gate
    },
  );
});
