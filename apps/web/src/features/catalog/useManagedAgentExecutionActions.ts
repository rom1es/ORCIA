import { createOrciaApiClient } from "@orcia/api-client";
import type { UiManagedAgentItem } from "@orcia/ui";
import type { SupportedWebLocale } from "../../i18n";
import { formatRfc9457ErrorToBanner } from "../../lib/formatRfc9457ErrorToBanner";
import type { AlertFeedbackInput } from "../shared/alertFeedback";
import {
  type CachedAgentsAndSkillsState,
  type CatalogManagedLabels,
  buildAgentLocalOutput,
} from "./managedAgentsHelpers";

export function useManagedAgentExecutionActions(params: {
  readonly locale: SupportedWebLocale;
  readonly catalogLabels: CatalogManagedLabels;
  readonly onFeedback: (msg: AlertFeedbackInput) => void;
  readonly onModalError?: (msg: string) => void;
  readonly updateManagedState: (
    updater: (prev: CachedAgentsAndSkillsState) => CachedAgentsAndSkillsState,
  ) => void;
}) {
  const { locale, catalogLabels, onFeedback, onModalError, updateManagedState } = params;

  const handleExecuteAgent = async (agentId: string, prompt: string): Promise<boolean> => {
    let previousAgent: UiManagedAgentItem | undefined;
    updateManagedState((prev) => {
      previousAgent = prev.agents.find((a) => a.agentId === agentId);
      const allSkills = prev.skills;
      return {
        ...prev,
        agents: prev.agents.map((agent: UiManagedAgentItem) =>
          agent.agentId === agentId
            ? {
                ...agent,
                lastExecutionOutput: buildAgentLocalOutput(agent, allSkills, prompt, catalogLabels),
              }
            : agent,
        ),
      };
    });
    try {
      const res = await createOrciaApiClient({ baseUrl: "", locale }).executeAgent(agentId, {
        prompt,
      });
      const benchStatus = res.test_bench_status ?? "PASSED";
      const nextLifecycle = res.lifecycle_status ?? "ACTIVE";
      updateManagedState((prev) => ({
        ...prev,
        agents: prev.agents.map((a) =>
          a.agentId === agentId
            ? {
                ...a,
                testBenchValidated: benchStatus === "PASSED",
                testBenchStatus: benchStatus,
                lifecycleStatus: nextLifecycle,
                lastExecutionOutput: res.response_text,
                lastInvokedSkills: (res.invoked_skills ?? []).map(
                  (s) => `${s.skill_name} (${s.command_handle})`,
                ),
              }
            : a,
        ),
      }));
      return true;
    } catch (err: unknown) {
      const detail = formatRfc9457ErrorToBanner(
        err,
        locale,
        catalogLabels.agentExecuteErrorContext,
      ).fullText;
      if (onModalError) {
        onModalError(detail);
      } else {
        onFeedback({ tone: "crimson", message: detail });
      }
      updateManagedState((prev) => ({
        ...prev,
        agents: prev.agents.map((a) =>
          a.agentId === agentId
            ? {
                ...a,
                testBenchValidated: false,
                testBenchStatus: "FAILED",
                lifecycleStatus: previousAgent?.lifecycleStatus ?? a.lifecycleStatus,
                lastExecutionOutput: `${previousAgent?.lastExecutionOutput ?? a.lastExecutionOutput ?? ""}\n${detail}`,
              }
            : a,
        ),
      }));
      return false;
    }
  };

  return { handleExecuteAgent };
}
