import { expect, test } from "@playwright/test";
import { resetDay0 } from "./support/day0";
import { createFirstAdminViaUi } from "./support/firstAdmin";
import { createBuAndTeamViaUi } from "./support/orgAndWorkspace";

test.describe("TEST-05 · 08 — Mes Agents : Studio 6 Blocs Gouvernés, Banc de Test et Survie au F5 (BDD)", () => {
  test("un agent configuré sur les 6 blocs (Identité/Posture, Moteur cognitif, Instructions, Périmètre RAG/Ontologie, Toolbox MCP Write-Preview, Garde-fous & Contrat) est persisté en base, validé au Banc de Test et réaffiché après un vrai F5", async ({
    page,
  }, testInfo) => {
    test.skip(testInfo.project.name !== "desktop-cockpit", "parcours de saisie : bureau");
    resetDay0();
    await createFirstAdminViaUi(page);
    await createBuAndTeamViaUi(page); // l'équipe de facturation déverrouille « Mes Agents »

    await page.goto("/agents");
    await expect(page.getByTestId("agents-and-skills-manager-view")).toBeVisible({ timeout: 30000 });
    await page.getByTestId("open-create-agent-drawer-btn").click();
    await expect(page.getByTestId("create-agent-modal")).toBeVisible();

    // Vérification de la présence des 6 blocs (A..F) et des 6 conditions d'employabilité
    await expect(page.getByTestId("create-agent-block-A")).toBeVisible();
    await expect(page.getByTestId("create-agent-block-B")).toBeVisible();
    await expect(page.getByTestId("create-agent-block-C")).toBeVisible();
    await expect(page.getByTestId("create-agent-block-D")).toBeVisible();
    await expect(page.getByTestId("create-agent-block-E")).toBeVisible();
    await expect(page.getByTestId("create-agent-block-F")).toBeVisible();
    await expect(page.getByTestId("create-agent-readiness-checklist")).toBeVisible();

    // Bloc A : Identité, Posture (Évaluateur Gate -> température 0.0 auto) & Binôme humain
    await page.getByTestId("agent-name-input").fill("Agent E2E Conformité");
    await expect(page.getByTestId("create-agent-handle-preview")).toHaveText(
      "@agent-e2e-conformite",
    );
    await page.getByTestId("create-agent-posture-select").selectOption("EVALUATOR_GATE");
    await page.getByTestId("create-agent-human-partner-select").selectOption("SECURITY_QA");
    await page.getByTestId("agent-role-input").fill("Analyste conformité & Gate contradictoire");

    // Bloc B : Moteur cognitif (vérifie que la température est passée à 0)
    await expect(page.getByTestId("create-agent-temperature-select")).toHaveValue("0");
    await page.getByTestId("create-agent-llm-model-tier-select").selectOption("deep");
    await page.getByTestId("create-agent-max-tokens-select").selectOption("8192");

    // Bloc C : Instructions système, prompt_ref & mécanisme de dialogue
    await page
      .getByTestId("agent-instructions-input")
      .fill("Vérifie la conformité des livrables avec citations obligatoires [S1].");
    await page
      .getByTestId("create-agent-prompt-ref-input")
      .fill("git://sdlc-pack/prompts/compliance-gate.md@main");
    await page.getByTestId("create-agent-dialogue-mechanism-select").selectOption("direct");

    // Bloc D & E : Périmètre RAG/Ontologie & Outils MCP (Write-Preview)
    await page.getByTestId("create-agent-rag-confluence_architecture").check();
    await page.getByTestId("create-agent-ontology-securite_conformite").check();
    await page.getByTestId("create-agent-mcp-tool-jira").selectOption("WRITE_PREVIEW");

    // Vérifie que la jauge d'employabilité affiche 6/6 avant soumission
    await expect(page.getByTestId("create-agent-readiness-pill")).toContainText("6/6");

    const created = page.waitForResponse(
      (r) => r.url().includes("/api/v1/agents-and-skills") && r.request().method() === "POST",
      { timeout: 20000 },
    );
    await page.getByTestId("create-agent-submit-btn").click();
    expect((await created).status()).toBeLessThan(400);

    // Survie au vrai F5 (après purge complète de localStorage / sessionStorage)
    await page.evaluate(() => {
      window.localStorage.clear();
      window.sessionStorage.clear();
    });
    await page.goto("/agents");
    await expect(page.getByText("Agent E2E Conformité").first()).toBeVisible({ timeout: 20000 });
    await expect(
      page.getByTestId("agent-posture-badge-agent-e2e-conformite"),
    ).toContainText("Contradicteur / Gate");
    await expect(
      page.getByTestId("agent-governance-passport-agent-e2e-conformite"),
    ).toContainText("Write-Preview obligatoire");

    // Ouverture de la modale « Configurer & Tester (6 blocs) » et validation au Banc de Test intégré
    await page.getByTestId("open-agent-detail-modal-btn-agent-e2e-conformite").click();
    await expect(page.getByTestId("agent-detail-modal-agent-e2e-conformite")).toBeVisible();
    await page
      .getByTestId("agent-test-input-agent-e2e-conformite")
      .fill("Vérifie le dossier d'architecture Cloud UE");
    await page.getByTestId("run-agent-btn-agent-e2e-conformite").click();
    await expect(
      page.getByTestId("agent-execution-output-agent-e2e-conformite").first(),
    ).toBeVisible();
    await expect(
      page.getByTestId("agent-bench-status-badge-agent-e2e-conformite"),
    ).toContainText("Validé au Banc de Test");
  });
});
