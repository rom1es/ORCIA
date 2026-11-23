import { createOrciaApiClient } from "@orcia/api-client";
import type { SupportedWebLocale } from "../../../i18n";
import type { WorkflowDefinitionV2Item } from "../processStudioV2Data";

export function createProcessesApiClient(locale: SupportedWebLocale) {
  return createOrciaApiClient({ baseUrl: "", locale });
}

export function ensureDraftOnEdit(
  base: WorkflowDefinitionV2Item,
): WorkflowDefinitionV2Item {
  if (base.status === "published") {
    const cleanVer = base.version.replace(/-draft$/, "");
    return {
      ...base,
      status: "draft",
      version: `${cleanVer}-draft`,
    };
  }
  return base;
}

export function buildNextPublishedWorkflow(
  base: WorkflowDefinitionV2Item,
): WorkflowDefinitionV2Item {
  const cleanVer = base.version.replace(/-draft$/, "");
  const parts = cleanVer.split(".").map((n) => Number.parseInt(n, 10) || 0);
  const nextVer = `${parts[0] ?? 1}.${parts[1] ?? 0}.${(parts[2] ?? 0) + 1}`;
  return { ...base, status: "published", version: nextVer };
}

export function attachSkillToWorkflow(
  workflow: WorkflowDefinitionV2Item,
  skillUri: string,
): WorkflowDefinitionV2Item | null {
  if (workflow.skills_refs.includes(skillUri)) return null;
  const base = ensureDraftOnEdit(workflow);
  return { ...base, skills_refs: [...base.skills_refs, skillUri] };
}

export function attachMcpToolToWorkflow(
  workflow: WorkflowDefinitionV2Item,
  toolPerm: string,
): WorkflowDefinitionV2Item {
  const base = ensureDraftOnEdit(workflow);
  const nextSubs = base.sub_steps.map((s, idx) =>
    idx === 0 && !s.mcp_tools_allowed.includes(toolPerm)
      ? { ...s, mcp_tools_allowed: [...s.mcp_tools_allowed, toolPerm] }
      : s,
  );
  return { ...base, sub_steps: nextSubs };
}

export function attachDeterministicGateToWorkflow(
  workflow: WorkflowDefinitionV2Item,
  gate: {
    id: string;
    name: string;
    runner: WorkflowDefinitionV2Item["controls"]["deterministic_gates"][number]["runner"];
  },
): WorkflowDefinitionV2Item | null {
  if (workflow.controls.deterministic_gates.some((g) => g.id === gate.id)) {
    return null;
  }
  const base = ensureDraftOnEdit(workflow);
  return {
    ...base,
    controls: {
      ...base.controls,
      deterministic_gates: [
        ...base.controls.deterministic_gates,
        {
          id: gate.id,
          name: gate.name,
          runner: gate.runner,
          config: { required_headings: ["# "] },
          blocking: true,
          max_self_heal_retries: 3,
        },
      ],
    },
  };
}
