import { createOrciaApiClient, type ToggleAgentGovernanceRequest } from "@orcia/api-client";
import type {
  UiAgentLifecycleStatus,
  UiAgentSkillVisibilityScope,
  UiAgentThinkingLevel,
  UiManagedAgentItem,
} from "@orcia/ui";
import type { SupportedWebLocale } from "../../i18n";
import { formatRfc9457ErrorToBanner } from "../../lib/formatRfc9457ErrorToBanner";
import type { AlertFeedbackInput } from "../shared/alertFeedback";
import {
  type CachedAgentsAndSkillsState,
  type CatalogManagedLabels,
  mapAgentDtoToUi,
} from "./managedAgentsHelpers";

export function useManagedAgentGovernanceActions(params: {
  readonly locale: SupportedWebLocale;
  readonly catalogLabels: CatalogManagedLabels;
  readonly onFeedback: (msg: AlertFeedbackInput) => void;
  readonly onModalError?: (msg: string) => void;
  readonly updateManagedState: (
    updater: (prev: CachedAgentsAndSkillsState) => CachedAgentsAndSkillsState,
  ) => void;
}) {
  const { locale, catalogLabels, onFeedback, onModalError, updateManagedState } = params;
  const resolveAgents = (prev: CachedAgentsAndSkillsState): readonly UiManagedAgentItem[] =>
    prev.agents;

  const reportError = (err: unknown, context: string, inModal = false): string => {
    const detail = formatRfc9457ErrorToBanner(err, locale, context).fullText;
    if (inModal && onModalError) {
      onModalError(detail);
    } else {
      onFeedback({ tone: "crimson", message: detail });
    }
    return detail;
  };

  const handleToggleAgentEnabled = async (
    agentId: string,
    nextEnabled: boolean,
  ): Promise<boolean> => {
    let previous: UiManagedAgentItem | undefined;
    updateManagedState((prev) => {
      const list = resolveAgents(prev);
      previous = list.find((a) => a.agentId === agentId);
      return {
        ...prev,
        agents: list.map((a) =>
          a.agentId === agentId ? { ...a, enabledOnWorkspace: nextEnabled } : a,
        ),
      };
    });
    try {
      const govPayload: ToggleAgentGovernanceRequest = { enabled_in_workspace: nextEnabled };
      await createOrciaApiClient({ baseUrl: "", locale }).updateAgentGovernance(
        agentId,
        govPayload,
      );
      return true;
    } catch (err: unknown) {
      if (previous) {
        const prevItem = previous;
        updateManagedState((prev) => ({
          ...prev,
          agents: prev.agents.map((a) => (a.agentId === agentId ? prevItem : a)),
        }));
      }
      reportError(err, catalogLabels.agentToggleErrorContext, false);
      return false;
    }
  };

  const handleToggleAgentMcpExposure = async (
    agentId: string,
    nextExposed: boolean,
  ): Promise<boolean> => {
    let previous: UiManagedAgentItem | undefined;
    updateManagedState((prev) => {
      const list = resolveAgents(prev);
      previous = list.find((a) => a.agentId === agentId);
      return {
        ...prev,
        agents: list.map((a) =>
          a.agentId === agentId ? { ...a, mcpExposed: nextExposed } : a,
        ),
      };
    });
    try {
      const govPayload: ToggleAgentGovernanceRequest = { mcp_exposed: nextExposed };
      const res = await createOrciaApiClient({ baseUrl: "", locale }).updateAgentGovernance(
        agentId,
        govPayload,
      );
      if (res?.agent_id) {
        const mapped = mapAgentDtoToUi(res);
        updateManagedState((prev) => ({
          ...prev,
          agents: prev.agents.map((a) =>
            a.agentId === agentId
              ? { ...a, ...mapped, lastExecutionOutput: a.lastExecutionOutput }
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
      reportError(err, catalogLabels.mcpExposureErrorContext, true);
      return false;
    }
  };

  const handleUpdateAgentLifecycle = async (
    agentId: string,
    nextLifecycle: UiAgentLifecycleStatus,
  ): Promise<boolean> => {
    let previous: UiManagedAgentItem | undefined;
    updateManagedState((prev) => {
      const list = resolveAgents(prev);
      previous = list.find((a) => a.agentId === agentId);
      return {
        ...prev,
        agents: list.map((a) =>
          a.agentId === agentId
            ? {
                ...a,
                lifecycleStatus: nextLifecycle,
                mcpExposed: nextLifecycle === "DRAFT" ? false : a.mcpExposed,
              }
            : a,
        ),
      };
    });
    try {
      const govPayload: ToggleAgentGovernanceRequest = {
        lifecycle_status: nextLifecycle,
        ...(nextLifecycle === "DRAFT" ? { mcp_exposed: false } : {}),
      };
      const res = await createOrciaApiClient({ baseUrl: "", locale }).updateAgentGovernance(
        agentId,
        govPayload,
      );
      if (res?.agent_id) {
        const mapped = mapAgentDtoToUi(res);
        updateManagedState((prev) => ({
          ...prev,
          agents: prev.agents.map((a) =>
            a.agentId === agentId
              ? { ...a, ...mapped, lastExecutionOutput: a.lastExecutionOutput }
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
      reportError(err, catalogLabels.agentLifecycleErrorContext, true);
      return false;
    }
  };

  const handleUpdateAgentThinkingLevel = async (
    agentId: string,
    nextThinkingLevel: UiAgentThinkingLevel,
  ): Promise<boolean> => {
    let previous: UiManagedAgentItem | undefined;
    updateManagedState((prev) => {
      const list = resolveAgents(prev);
      previous = list.find((a) => a.agentId === agentId);
      return {
        ...prev,
        agents: list.map((a) =>
          a.agentId === agentId ? { ...a, thinkingLevel: nextThinkingLevel } : a,
        ),
      };
    });
    try {
      await createOrciaApiClient({ baseUrl: "", locale }).updateAgentGovernance(agentId, {
        thinking_level: nextThinkingLevel,
      });
      return true;
    } catch (err: unknown) {
      if (previous) {
        const prevItem = previous;
        updateManagedState((prev) => ({
          ...prev,
          agents: prev.agents.map((a) => (a.agentId === agentId ? prevItem : a)),
        }));
      }
      reportError(err, catalogLabels.agentThinkingErrorContext, false);
      return false;
    }
  };

  const handleUpdateAgentVisibility = async (
    agentId: string,
    nextVisibility: UiAgentSkillVisibilityScope,
  ): Promise<boolean> => {
    let previous: UiManagedAgentItem | undefined;
    updateManagedState((prev) => {
      const list = resolveAgents(prev);
      previous = list.find((a) => a.agentId === agentId);
      return {
        ...prev,
        agents: list.map((a) =>
          a.agentId === agentId ? { ...a, visibilityScope: nextVisibility } : a,
        ),
      };
    });
    if (nextVisibility !== "PRIVATE" && nextVisibility !== "TEAM") {
      return true;
    }
    try {
      await createOrciaApiClient({ baseUrl: "", locale }).updateAgentGovernance(agentId, {
        visibility_scope: nextVisibility,
      });
      return true;
    } catch (err: unknown) {
      if (previous) {
        const prevItem = previous;
        updateManagedState((prev) => ({
          ...prev,
          agents: prev.agents.map((a) => (a.agentId === agentId ? prevItem : a)),
        }));
      }
      reportError(err, catalogLabels.agentVisibilityErrorContext, false);
      return false;
    }
  };

  return {
    handleToggleAgentEnabled,
    handleToggleAgentMcpExposure,
    handleUpdateAgentLifecycle,
    handleUpdateAgentThinkingLevel,
    handleUpdateAgentVisibility,
  };
}
