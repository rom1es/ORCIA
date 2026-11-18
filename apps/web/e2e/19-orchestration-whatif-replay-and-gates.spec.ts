/** @uj UJ-1, UJ-2, UJ-3, UJ-6 | @cap CAP-020, CAP-021, CAP-024, CAP-030, CAP-031, CAP-032, CAP-033 */
import { expect, test } from "./support/e2eCaptureFixture";
import { resetDay0 } from "./support/day0";
import { expectDbRowCount, expectDbRowExists } from "./support/dbAssertions";
import { bootstrapAdminSession, getBearerTokenFromSession } from "./support/authAndOrgHelpers";
import { createOrgAndWorkspaceWithId } from "./support/workspaceAndCatalogHelpers";
import {
  openCockpitPage,
  openGatesPage,
  reloadClearingStorage,
} from "./support/processAndAssistantHelpers";

test.describe("Orchestration durable, contestation amont avec simulation d'impact, reprise et validations croisées", () => {
  test.beforeEach(() => {
    resetDay0();
  });

  test("Instanciation depuis le cockpit, ancrage humain, contestation amont avec reprise et survie F5", async ({
    page,
  }) => {
    await bootstrapAdminSession(page);
    const ws = await createOrgAndWorkspaceWithId(page, {
      name: "Espace Orchestration Durable",
      slug: "ws-orch-durable",
    });

    await openCockpitPage(page);
    await expect(page.getByTestId("cockpit-launch-run-form")).toBeVisible({ timeout: 15000 });
    await page.getByTestId("cockpit-select-workspace").selectOption(ws.uiWorkspaceId);
    await page.getByTestId("cockpit-select-workflow").selectOption("assistant-agent");
    await page.getByTestId("cockpit-run-title-input").fill("Exécution Gouvernance Architecture");
    await page.getByTestId("cockpit-launch-run-submit-btn").click();
    await expect(page.getByTestId("cockpit-active-runs-list")).toBeVisible({ timeout: 15000 });

    const anchorCard = page.getByTestId("cockpit-human-led-anchor-card");
    await expect(anchorCard).toBeVisible({ timeout: 15000 });
    const anchorContent =
      "Invariants stricts d'architecture hexagonale, contrat OpenAPI 3.1 et séparation des contextes.";
    await page.getByTestId("cockpit-human-anchor-textarea").fill(anchorContent);
    const signBtn = page.getByTestId("human-anchor-submit-human_architecture_intent");
    await expect(signBtn).toBeEnabled();
    await signBtn.click();
    await expect(page.getByTestId("cockpit-human-anchor-signed-badge")).toBeVisible({
      timeout: 15000,
    });

    const reasonInput = page.getByTestId("upstream-challenge-reason-input");
    await expect(reasonInput).toBeVisible({ timeout: 15000 });
    await reasonInput.fill("Révision du périmètre contractuel amont suite au cadrage produit.");
    await expect(page.getByTestId("what-if-impact-preview-panel")).toBeVisible({ timeout: 10000 });
    await page.getByTestId("upstream-challenge-submit-btn").click();
    await page.getByTestId("upstream-replay-trigger-btn").click();
    await expect(page.getByText("[STALE_WARNING]").first()).toBeVisible({ timeout: 10000 });

    await reloadClearingStorage(page);
    await expect(page.getByTestId("cockpit-active-scope-badge")).toBeVisible({ timeout: 30000 });
    await expect(page.getByTestId("cockpit-human-anchor-signed-badge")).toBeVisible({
      timeout: 15000,
    });

    expectDbRowCount(
      "SELECT COUNT(*)::int AS count FROM workflow_runs",
      undefined,
      1,
      "Exécution instanciée persistée dans workflow_runs PG18",
    );
    expectDbRowCount(
      "SELECT COUNT(*)::int AS count FROM step_executions",
      undefined,
      1,
      "Étapes d'exécution persistées dans step_executions PG18",
    );
    expectDbRowCount(
      "SELECT COUNT(*)::int AS count FROM blackboard_snapshots",
      undefined,
      1,
      "Instantanés blackboard persistés dans blackboard_snapshots PG18",
    );
    expectDbRowCount(
      "SELECT COUNT(*)::int AS count FROM run_lock_manifests",
      undefined,
      1,
      "Verrou de version persisté dans run_lock_manifests PG18",
    );
    expectDbRowCount(
      "SELECT COUNT(*)::int AS count FROM upstream_challenges",
      undefined,
      1,
      "Contestation amont persistée dans upstream_challenges PG18",
    );
    expectDbRowExists(
      "SELECT id::text AS id, section_key FROM human_anchor_signatures WHERE section_key = :section_key AND content_text = :content_text",
      { section_key: "human_architecture_intent", content_text: anchorContent },
      "Signature d'ancrage humain persistée dans human_anchor_signatures PG18",
    );
  });

  test("Validation déterministe sandbox, validation agentique orthogonale, revue humaine par découpage et survie F5", async ({
    page,
  }) => {
    await bootstrapAdminSession(page);
    const ws = await createOrgAndWorkspaceWithId(page, {
      name: "Espace Gates Orthogonales",
      slug: "ws-gates-ortho",
    });
    const token = await getBearerTokenFromSession(page);
    const authHeaders = { Authorization: `Bearer ${token}` };

    const runId = "0195f100-0000-7000-8000-000000000101";
    const stepExecId = "0195f100-0000-7000-8000-000000000201";

    const detRes = await page.request.post("/api/v1/gates/deterministic/evaluate", {
      headers: authHeaders,
      data: {
        workspace_id: ws.pgWorkspaceId,
        run_id: runId,
        step_execution_id: stepExecId,
        step_key: "step-architecture-gate",
        artifact_payload: { artifact: "Contrat OpenAPI 3.1 et schéma PG18 validés." },
        required_sections: ["artifact"],
      },
    });
    expect(detRes.status()).toBe(200);
    const detBody = (await detRes.json()) as {
      evaluation: { gate_type: string; status: string };
    };
    expect(detBody.evaluation.gate_type).toBe("DETERMINISTIC");
    expect(detBody.evaluation.status).toBe("PASS");

    const agenticRes = await page.request.post("/api/v1/gates/agentic/evaluate", {
      headers: authHeaders,
      data: {
        workspace_id: ws.pgWorkspaceId,
        run_id: runId,
        step_execution_id: stepExecId,
        step_key: "step-architecture-gate",
        executor_model_family: "openai",
        evaluator_model_family: "anthropic",
        evaluator_model_id: "claude-3-5-sonnet",
        candidate_artifact: { summary: "Architecture modulaire validée avec citations." },
      },
    });
    expect(agenticRes.status()).toBe(200);
    const agenticBody = (await agenticRes.json()) as {
      routed_model_family: string;
      evaluation: { gate_type: string };
    };
    expect(agenticBody.routed_model_family).not.toBe("openai");
    expect(agenticBody.evaluation.gate_type).toBe("AGENTIC");

    await openGatesPage(page);
    await page.getByTestId("gates-open-human-review-btn").click();
    await expect(page.getByTestId("review-briefing-grid")).toBeVisible({ timeout: 15000 });
    await expect(page.getByTestId("chunk-validation-workspace")).toBeVisible({ timeout: 15000 });

    await page.getByTestId("inspect-hypotheses-btn").click();
    await page.getByTestId("chunk-approve-btn-sec-architecture").click();
    await page.getByTestId("chunk-coedit-btn-sec-security-jira").click();

    await page.getByTestId("finalize-human-gate-btn").click();
    await expect(page.getByTestId("anti-rubber-stamping-guard-modal")).toBeVisible({
      timeout: 10000,
    });
    await page.getByTestId("rubber-stamp-confirm-checkbox").check();
    await page.getByTestId("rubber-stamp-confirm-submit-btn").click();

    await expect(page.getByTestId("gates-human-evaluation-status-badge")).toContainText("PASS", {
      timeout: 15000,
    });
    await expect(page.getByTestId("gates-staged-jira-status-badge")).toContainText("EXECUTED");

    await reloadClearingStorage(page);
    await expect(page.getByTestId("gates-human-evaluation-status-badge")).toContainText("PASS", {
      timeout: 20000,
    });
    await expect(page.getByTestId("gates-staged-jira-status-badge")).toContainText("EXECUTED");

    expectDbRowCount(
      "SELECT COUNT(*)::int AS count FROM gate_evaluations WHERE gate_type IN ('DETERMINISTIC', 'AGENTIC', 'HUMAN')",
      undefined,
      3,
      "Évaluations déterministe, agentique et humaine persistées dans gate_evaluations PG18",
    );
    expectDbRowCount(
      "SELECT COUNT(*)::int AS count FROM chunk_approvals WHERE status IN ('APPROVED', 'CO_EDITED')",
      undefined,
      2,
      "Décisions par découpage persistées dans chunk_approvals PG18",
    );
  });
});
