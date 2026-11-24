import { createOrciaApiClient } from "@orcia/api-client";
import type {
  AgentSixBlocksDraftState,
  CreateAgentSixBlocksInput,
  UiAgentSkillVisibilityScope,
  UiAgentThinkingLevel,
  UiManagedAgentItem,
} from "@orcia/ui";
import type { ConfiguredPackItem } from "../../components/platformSetupStore";
import type { SupportedWebLocale } from "../../i18n";
import { formatRfc9457ErrorToBanner } from "../../lib/formatRfc9457ErrorToBanner";
import {
  buildAgentLocalOutput,
  buildAgentUpsertPayload,
  buildOptimisticAgent,
  type CatalogManagedLabels,
} from "./managedAgentsHelpers";
import {
  type CachedAgentsAndSkillsState,
  mergeManagedStateWithActivePacks,
  PACK_AGENTS_BY_PACK_KEY,
  PACK_SKILLS_BY_PACK_KEY,
  slugifyIdentifier,
} from "./packAgentsCatalog";

export function useManagedAgentActions(params: {
  readonly activePacks: readonly ConfiguredPackItem[];
  readonly locale: SupportedWebLocale;
  readonly catalogLabels: CatalogManagedLabels;
  readonly onFeedback: (msg: string) => void;
  readonly updateManagedState: (
    updater: (prev: CachedAgentsAndSkillsState) => CachedAgentsAndSkillsState,
  ) => void;
}) {
  const { activePacks, locale, catalogLabels, onFeedback, updateManagedState } = params;
  const resolveAgents = (prev: CachedAgentsAndSkillsState): readonly UiManagedAgentItem[] =>
    prev.agents.length > 0
      ? prev.agents
      : mergeManagedStateWithActivePacks(prev, activePacks).agents;

  const reportError = (err: unknown, context: string) =>
    onFeedback(`⚠️ ${formatRfc9457ErrorToBanner(err, locale, context).fullText}`);

  const handleCreateAgent = (draft: CreateAgentSixBlocksInput) => {
    const optimisticAgent = buildOptimisticAgent(draft);
    updateManagedState((prev) => ({
      ...prev,
      agents: [...prev.agents.filter((a) => a.agentId !== optimisticAgent.agentId), optimisticAgent],
    }));
    void createOrciaApiClient({ baseUrl: "" })
      .upsertAgent(buildAgentUpsertPayload(optimisticAgent.agentId, optimisticAgent))
      .catch((err: unknown) => reportError(err, catalogLabels.agentErrorContext));
  };

  const handleDuplicateAgent = (sourceAgent: UiManagedAgentItem) => {
    const customName = `${sourceAgent.name} ${catalogLabels.agentDuplicateSuffix}`;
    const slug = slugifyIdentifier(customName, "agent-copy");
    const agentId = slug.startsWith("agent-") ? slug : `agent-${slug}`;
    const handleSlug = slug.startsWith("agent-") ? slug.slice(6) || slug : slug;
    const duplicated: UiManagedAgentItem = {
      ...sourceAgent,
      agentId,
      slug: handleSlug,
      handle: `@${handleSlug}`,
      name: customName,
      visibilityScope: "TEAM",
      sourcePackKey: null,
      enabledOnWorkspace: true,
    };
    updateManagedState((prev) => ({
      ...prev,
      agents: [...resolveAgents(prev).filter((a) => a.agentId !== agentId), duplicated],
    }));
    onFeedback(catalogLabels.agentDuplicatedBannerTemplate.replace("{name}", duplicated.name));
    void createOrciaApiClient({ baseUrl: "" })
      .duplicateAgent(sourceAgent.agentId, { new_name: customName, visibility_scope: "TEAM" })
      .catch((err: unknown) => reportError(err, catalogLabels.agentDuplicateErrorContext));
  };

  const handleToggleAgentEnabled = (agentId: string, nextEnabled: boolean) => {
    updateManagedState((prev) => ({
      ...prev,
      agents: resolveAgents(prev).map((a) =>
        a.agentId === agentId ? { ...a, enabledOnWorkspace: nextEnabled } : a,
      ),
    }));
    void createOrciaApiClient({ baseUrl: "" })
      .updateAgentGovernance(agentId, { enabled_in_workspace: nextEnabled })
      .catch((err: unknown) => reportError(err, catalogLabels.agentToggleErrorContext));
  };

  const handleToggleAgentMcpExposure = (agentId: string, nextExposed: boolean) => {
    updateManagedState((prev) => ({
      ...prev,
      agents: resolveAgents(prev).map((a) =>
        a.agentId === agentId ? { ...a, mcpExposed: nextExposed } : a,
      ),
    }));
    void createOrciaApiClient({ baseUrl: "" })
      .updateAgentGovernance(agentId, { mcp_exposed: nextExposed })
      .catch((err: unknown) => reportError(err, catalogLabels.mcpExposureErrorContext));
  };

  const handleUpdateAgentDetails = (
    agentId: string,
    patch: Partial<AgentSixBlocksDraftState> & {
      name: string;
      roleMission: string;
      instructions: string;
      thinkingLevel: UiAgentThinkingLevel;
      visibilityScope?: UiAgentSkillVisibilityScope;
      mcpExposed?: boolean;
    },
  ) => {
    updateManagedState((prev) => ({
      ...prev,
      agents: resolveAgents(prev).map((a) => (a.agentId === agentId ? { ...a, ...patch } : a)),
    }));
    void createOrciaApiClient({ baseUrl: "" })
      .upsertAgent(buildAgentUpsertPayload(agentId, patch))
      .catch((err: unknown) => reportError(err, catalogLabels.agentUpdateErrorContext));
  };

  const handleToggleAgentSkill = (agentId: string, skillId: string, nextChecked: boolean) => {
    let nextSkillIdsForApi: string[] = [];
    updateManagedState((prev) => ({
      ...prev,
      agents: resolveAgents(prev).map((agent) => {
        if (agent.agentId !== agentId) return agent;
        const without = agent.skillIds.filter((id) => id !== skillId);
        const updatedIds = nextChecked ? [...without, skillId] : without;
        nextSkillIdsForApi = updatedIds;
        return { ...agent, skillIds: updatedIds };
      }),
    }));
    void createOrciaApiClient({ baseUrl: "" })
      .updateAgentSkills(agentId, { skill_ids: nextSkillIdsForApi })
      .catch((err: unknown) => reportError(err, catalogLabels.agentSkillsErrorContext));
  };

  const handleUpdateAgentThinkingLevel = (
    agentId: string,
    nextThinkingLevel: UiAgentThinkingLevel,
  ) => {
    updateManagedState((prev) => ({
      ...prev,
      agents: resolveAgents(prev).map((a) =>
        a.agentId === agentId ? { ...a, thinkingLevel: nextThinkingLevel } : a,
      ),
    }));
    void createOrciaApiClient({ baseUrl: "" })
      .updateAgentGovernance(agentId, { thinking_level: nextThinkingLevel })
      .catch((err: unknown) => reportError(err, catalogLabels.agentThinkingErrorContext));
  };

  const handleUpdateAgentVisibility = (
    agentId: string,
    nextVisibility: UiAgentSkillVisibilityScope,
  ) => {
    updateManagedState((prev) => ({
      ...prev,
      agents: resolveAgents(prev).map((a) =>
        a.agentId === agentId ? { ...a, visibilityScope: nextVisibility } : a,
      ),
    }));
    if (nextVisibility === "PRIVATE" || nextVisibility === "TEAM") {
      void createOrciaApiClient({ baseUrl: "" })
        .updateAgentGovernance(agentId, { visibility_scope: nextVisibility })
        .catch((err: unknown) => reportError(err, catalogLabels.agentVisibilityErrorContext));
    }
  };

  const handleDeleteAgent = (agentId: string) => {
    updateManagedState((prev) => ({
      ...prev,
      agents: prev.agents.filter((a) => a.agentId !== agentId),
    }));
    void createOrciaApiClient({ baseUrl: "" })
      .deleteAgent(agentId)
      .catch((err: unknown) => reportError(err, catalogLabels.agentDeleteErrorContext));
  };

  const handleExecuteAgent = (agentId: string, prompt: string) => {
    updateManagedState((prev) => {
      const baseAgents = prev.agents.some((a) => a.agentId === agentId)
        ? prev.agents
        : [
            ...prev.agents,
            ...Object.values(PACK_AGENTS_BY_PACK_KEY)
              .flat()
              .filter((a) => a.agentId === agentId),
          ];
      const allSkills = [
        ...prev.skills,
        ...Object.values(PACK_SKILLS_BY_PACK_KEY)
          .flat()
          .filter((sk) => !prev.skills.some((ps) => ps.skillId === sk.skillId)),
      ];
      return {
        ...prev,
        agents: baseAgents.map((agent) =>
          agent.agentId === agentId
            ? {
                ...agent,
                testBenchValidated: true,
                lastExecutionOutput: buildAgentLocalOutput(agent, allSkills, prompt, catalogLabels),
              }
            : agent,
        ),
      };
    });
    void createOrciaApiClient({ baseUrl: "" })
      .executeAgent(agentId, { prompt })
      .then((res) =>
        updateManagedState((prev) => ({
          ...prev,
          agents: prev.agents.map((a) =>
            a.agentId === agentId
              ? {
                  ...a,
                  testBenchValidated: true,
                  lastExecutionOutput: res.response_text,
                  lastInvokedSkills: (res.invoked_skills ?? []).map(
                    (s) => `${s.skill_name} (${s.command_handle})`,
                  ),
                }
              : a,
          ),
        })),
      )
      .catch((err: unknown) => {
        const detail = formatRfc9457ErrorToBanner(
          err,
          locale,
          catalogLabels.agentExecuteErrorContext,
        ).fullText;
        onFeedback(`⚠️ ${detail}`);
        updateManagedState((prev) => ({
          ...prev,
          agents: prev.agents.map((a) =>
            a.agentId === agentId
              ? {
                  ...a,
                  testBenchValidated: true,
                  lastExecutionOutput: `${a.lastExecutionOutput ?? ""}\n⚠️ ${detail}`,
                }
              : a,
          ),
        }));
      });
  };

  return {
    handleCreateAgent,
    handleDuplicateAgent,
    handleToggleAgentEnabled,
    handleToggleAgentMcpExposure,
    handleUpdateAgentDetails,
    handleToggleAgentSkill,
    handleUpdateAgentThinkingLevel,
    handleUpdateAgentVisibility,
    handleDeleteAgent,
    handleExecuteAgent,
  };
}
