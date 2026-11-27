import { expect, type Page } from "./e2eCaptureFixture";
import { apiPost } from "./typedApiRequest";
import { openAgentsPage } from "./processAndAssistantHelpers";

export async function seedSkillAndActiveAgentForComposer(
  page: Page,
  token: string,
  workspaceId: string,
): Promise<{ readonly agentId: string; readonly agentSlug: string }> {
  const conceptRes = await apiPost(page, "/api/v1/ontology-rag/ontology/concepts", {
    token,
    data: {
      concept_key: "qa_readiness",
      canonical_term: "QA Readiness",
      level: "3_WORKSPACE",
      scope_id: workspaceId,
      definition_text: "Readiness criteria for declarative release packs.",
    },
  });
  expect(conceptRes.status()).toBe(200);

  const skillRes = await apiPost<{ skill_id: string }>(page, "/api/v1/agents-and-skills/skills", {
    token,
    data: {
      name: "Pack QA Check",
      objective: "Verify release criteria",
      instructions: "Check requirements cleanly.",
      visibility_scope: "TEAM",
    },
  });
  expect(skillRes.status()).toBe(200);
  const skillId = (await skillRes.json()).skill_id;

  await openAgentsPage(page);
  await page.getByTestId("open-create-agent-drawer-btn").click();
  await page.getByTestId("agent-name-input").fill("Pack QA Bot");
  await page.getByTestId("agent-role-input").fill("Release QA specialist");
  await page.getByTestId("agent-instructions-input").fill("Run release readiness checks.");
  await page.getByTestId("create-agent-submit-btn").click();

  const agentId = "agent-pack-qa-bot";
  await expect(page.getByTestId(`open-agent-detail-modal-btn-${agentId}`)).toBeVisible({
    timeout: 15000,
  });

  const attachSkillRes = await apiPost(page, "/api/v1/agents-and-skills/agents", {
    token,
    data: {
      agent_id: agentId,
      name: "Pack QA Bot",
      role_mission: "Release QA specialist",
      instructions: "Run release readiness checks.",
      skill_ids: [skillId],
      ontology_views: ["qa_readiness"],
      visibility_scope: "TEAM",
    },
  });
  expect(attachSkillRes.status()).toBe(200);

  await page.getByTestId(`open-agent-detail-modal-btn-${agentId}`).click();
  await page.getByTestId(`agent-test-input-${agentId}`).fill("Verify readiness check");
  await Promise.all([
    page.waitForResponse(
      (r) =>
        r.url().includes(`/api/v1/agents-and-skills/agents/${agentId}/execute`) &&
        r.status() === 200,
      { timeout: 20000 },
    ),
    page.getByTestId(`run-agent-btn-${agentId}`).click(),
  ]);
  await expect(page.getByTestId(`agent-modal-lifecycle-badge-${agentId}`)).toContainText("Actif");
  await page.getByTestId(`cancel-agent-detail-modal-btn-${agentId}`).click();
  return { agentId, agentSlug: "pack-qa-bot" };
}
