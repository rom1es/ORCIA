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
import type { AlertFeedbackInput } from "../shared/alertFeedback";
import {
  buildAgentUpsertPayload,
  buildOptimisticAgent,
  type CatalogManagedLabels,
  mapAgentDtoToUi,
} from "./managedAgentsHelpers";
import {
  type CachedAgentsAndSkillsState,
  mergeManagedStateWithActivePacks,
  slugifyIdentifier,
} from "./packAgentsCatalog";
import { useManagedAgentExecutionActions } from "./useManagedAgentExecutionActions";
import { useManagedAgentGovernanceActions } from "./useManagedAgentGovernanceActions";

export function useManagedAgentActions(params: {
  readonly activePacks: readonly ConfiguredPackItem[];
  readonly locale: SupportedWebLocale;
  readonly catalogLabels: CatalogManagedLabels;
  readonly onFeedback: (msg: AlertFeedbackInput) => void;
  readonly onModalError?: (msg: string) => void;
  readonly updateManagedState: (
    updater: (prev: CachedAgentsAndSkillsState) => CachedAgentsAndSkillsState,
  ) => void;
}) {
  const { activePacks, locale, catalogLabels, onFeedback, onModalError, updateManagedState } = params;
  const resolveAgents = (prev: CachedAgentsAndSkillsState): readonly UiManagedAgentItem[] =>
    prev.agents.length > 0
      ? prev.agents
      : mergeManagedStateWithActivePacks(prev, activePacks).agents;

  const reportError = (err: unknown, context: string, inModal = false): void => {
    const detail = formatRfc9457ErrorToBanner(err, locale, context).fullText;
    if (inModal && onModalError) {
      onModalError(detail);
    } else {
      onFeedback({ tone: "crimson", message: detail });
    }
  };

  const handleCreateAgent = async (draft: CreateAgentSixBlocksInput): Promise<boolean> => {
    const optimisticAgent = buildOptimisticAgent(draft);
    let previous: UiManagedAgentItem | undefined;
    updateManagedState((prev) => {
      previous = prev.agents.find((a) => a.agentId === optimisticAgent.agentId);
      return {
        ...prev,
        agents: [
          ...prev.agents.filter((a) => a.agentId !== optimisticAgent.agentId),
          optimisticAgent,
        ],
      };
    });
    try {
      const res = await createOrciaApiClient({ baseUrl: "", locale }).upsertAgent(
        buildAgentUpsertPayload(optimisticAgent.agentId, optimisticAgent),
      );
      if (res?.agent_id) {
        const synced = mapAgentDtoToUi(res);
        updateManagedState((prev) => ({
          ...prev,
          agents: [...prev.agents.filter((a) => a.agentId !== synced.agentId), synced],
        }));
      }
      return true;
    } catch (err: unknown) {
      updateManagedState((prev) => ({
        ...prev,
        agents: previous
          ? [...prev.agents.filter((a) => a.agentId !== optimisticAgent.agentId), previous]
          : prev.agents.filter((a) => a.agentId !== optimisticAgent.agentId),
      }));
      reportError(err, catalogLabels.agentErrorContext, false);
      return false;
    }
  };

  const handleDuplicateAgent = async (sourceAgent: UiManagedAgentItem): Promise<boolean> => {
    const customName = `${sourceAgent.name} ${catalogLabels.agentDuplicateSuffix}`;
    const slug = slugifyIdentifier(customName, "agent-copy");
    const agentId = slug.startsWith("agent-") ? slug : `agent-${slug}`;
    const handleSlug = slug.startsWith("agent-") ? slug.slice(6) || slug : slug;
    const isPackSource = sourceAgent.visibilityScope === "PACK";
    const duplicated: UiManagedAgentItem = {
      ...sourceAgent,
      agentId,
      slug: handleSlug,
      handle: `@${handleSlug}`,
      name: customName,
      visibilityScope: "TEAM",
      sourcePackKey: isPackSource ? sourceAgent.sourcePackKey ?? null : null,
      enabledOnWorkspace: true,
      mcpExposed: false,
      lifecycleStatus: "DRAFT",
      testBenchStatus: "UNTESTED",
      testBenchValidated: false,
    };
    let previousAgents: readonly UiManagedAgentItem[] | undefined;
    updateManagedState((prev) => {
      previousAgents = prev.agents;
      return {
        ...prev,
        agents: [...prev.agents.filter((a) => a.agentId !== agentId), duplicated],
      };
    });
    try {
      const client = createOrciaApiClient({ baseUrl: "", locale });
      const res = isPackSource
        ? await client.upsertAgent(buildAgentUpsertPayload(agentId, duplicated))
        : await client.duplicateAgent(sourceAgent.agentId, {
            new_name: customName,
            visibility_scope: "TEAM",
          });
      if (res?.agent_id) {
        const synced = mapAgentDtoToUi(res);
        updateManagedState((prev) => ({
          ...prev,
          agents: [
            ...prev.agents.filter((a) => a.agentId !== agentId && a.agentId !== synced.agentId),
            synced,
          ],
        }));
      }
      onFeedback(catalogLabels.agentDuplicatedBannerTemplate.replace("{name}", duplicated.name));
      return true;
    } catch (err: unknown) {
      if (previousAgents !== undefined) {
        const restored = previousAgents;
        updateManagedState((prev) => ({ ...prev, agents: restored }));
      }
      reportError(err, catalogLabels.agentDuplicateErrorContext, false);
      return false;
    }
  };

  const handleUpdateAgentDetails = async (
    agentId: string,
    patch: Partial<AgentSixBlocksDraftState> & {
      name: string;
      roleMission: string;
      instructions: string;
      thinkingLevel: UiAgentThinkingLevel;
      visibilityScope?: UiAgentSkillVisibilityScope;
      mcpExposed?: boolean;
    },
  ): Promise<boolean> => {
    let previous: UiManagedAgentItem | undefined;
    updateManagedState((prev) => {
      const list = resolveAgents(prev);
      previous = list.find((a) => a.agentId === agentId);
      return {
        ...prev,
        agents: list.map((a) => (a.agentId === agentId ? { ...a, ...patch } : a)),
      };
    });
    try {
      const res = await createOrciaApiClient({ baseUrl: "", locale }).upsertAgent(
        buildAgentUpsertPayload(agentId, patch),
      );
      if (res?.agent_id) {
        const synced = mapAgentDtoToUi(res);
        updateManagedState((prev) => ({
          ...prev,
          agents: prev.agents.map((a) =>
            a.agentId === agentId
              ? { ...a, ...synced, lastExecutionOutput: a.lastExecutionOutput }
              : a,
          ),
        }));
      }
      return true;
    } catch (err: unknown) {
      if (previous) {
        const prevItem = previous;
        updateManagedState((prev) => ({
          ...prev,
          agents: prev.agents.map((a) => (a.agentId === agentId ? prevItem : a)),
        }));
      }
      reportError(err, catalogLabels.agentUpdateErrorContext, true);
      return false;
    }
  };

  const handleToggleAgentSkill = async (
    agentId: string,
    skillId: string,
    nextChecked: boolean,
  ): Promise<boolean> => {
    let previousIds: readonly string[] = [];
    let nextSkillIdsForApi: string[] = [];
    updateManagedState((prev) => ({
      ...prev,
      agents: resolveAgents(prev).map((agent) => {
        if (agent.agentId !== agentId) return agent;
        previousIds = agent.skillIds;
        const without = agent.skillIds.filter((id) => id !== skillId);
        const updatedIds = nextChecked ? [...without, skillId] : without;
        nextSkillIdsForApi = updatedIds;
        return { ...agent, skillIds: updatedIds };
      }),
    }));
    try {
      await createOrciaApiClient({ baseUrl: "", locale }).updateAgentSkills(agentId, {
        skill_ids: nextSkillIdsForApi,
      });
      return true;
    } catch (err: unknown) {
      updateManagedState((prev) => ({
        ...prev,
        agents: prev.agents.map((a) =>
          a.agentId === agentId ? { ...a, skillIds: previousIds } : a,
        ),
      }));
      reportError(err, catalogLabels.agentSkillsErrorContext, true);
      return false;
    }
  };

  const handleDeleteAgent = async (agentId: string): Promise<boolean> => {
    let previous: UiManagedAgentItem | undefined;
    updateManagedState((prev) => {
      previous = prev.agents.find((a) => a.agentId === agentId);
      return {
        ...prev,
        agents: prev.agents.filter((a) => a.agentId !== agentId),
      };
    });
    try {
      await createOrciaApiClient({ baseUrl: "", locale }).deleteAgent(agentId);
      return true;
    } catch (err: unknown) {
      if (previous) {
        const prevItem = previous;
        updateManagedState((prev) => ({
          ...prev,
          agents: [...prev.agents.filter((a) => a.agentId !== agentId), prevItem],
        }));
      }
      reportError(err, catalogLabels.agentDeleteErrorContext, false);
      return false;
    }
  };

  const { handleExecuteAgent } = useManagedAgentExecutionActions({
    locale,
    catalogLabels,
    onFeedback,
    onModalError,
    updateManagedState,
  });

  const governanceActions = useManagedAgentGovernanceActions({
    activePacks,
    locale,
    catalogLabels,
    onFeedback,
    onModalError,
    updateManagedState,
  });

  return {
    handleCreateAgent,
    handleDuplicateAgent,
    handleUpdateAgentDetails,
    handleToggleAgentSkill,
    handleDeleteAgent,
    handleExecuteAgent,
    ...governanceActions,
  };
}
