import { createOrciaApiClient } from "@orcia/api-client";
import type { UiManagedAgentItem } from "@orcia/ui";
import type { SupportedWebLocale } from "../../i18n";
import type { CachedAgentsAndSkillsState } from "./managedAgentsHelpers";

export type InterceptPackDraftDeleteFn = (params: {
  readonly error: unknown;
  readonly entityType: "AGENT" | "SKILL";
  readonly entityId: string;
  readonly entityLabel: string;
  readonly executeUnlinkedDelete: () => Promise<boolean>;
}) => boolean;

export async function executeGuardedAgentDelete(params: {
  readonly agentId: string;
  readonly unlinkFromDraftPacks: boolean;
  readonly locale: SupportedWebLocale;
  readonly errorContext: string;
  readonly updateManagedState: (
    updater: (prev: CachedAgentsAndSkillsState) => CachedAgentsAndSkillsState,
  ) => void;
  readonly reportError: (err: unknown, context: string, inModal?: boolean) => void;
  readonly onInterceptDraftDeleteError?: InterceptPackDraftDeleteFn;
}): Promise<boolean> {
  const {
    agentId,
    unlinkFromDraftPacks,
    locale,
    errorContext,
    updateManagedState,
    reportError,
    onInterceptDraftDeleteError,
  } = params;
  let previous: UiManagedAgentItem | undefined;
  updateManagedState((prev) => {
    previous = prev.agents.find((a) => a.agentId === agentId);
    return {
      ...prev,
      agents: prev.agents.filter((a) => a.agentId !== agentId),
    };
  });
  try {
    await createOrciaApiClient({ baseUrl: "", locale }).deleteAgent(agentId, {
      unlinkFromDraftPacks,
    });
    return true;
  } catch (err: unknown) {
    if (previous) {
      const prevItem = previous;
      updateManagedState((prev) => ({
        ...prev,
        agents: [...prev.agents.filter((a) => a.agentId !== agentId), prevItem],
      }));
    }
    const intercepted =
      !unlinkFromDraftPacks &&
      Boolean(
        onInterceptDraftDeleteError?.({
          error: err,
          entityType: "AGENT",
          entityId: agentId,
          entityLabel: previous?.name ?? agentId,
          executeUnlinkedDelete: () =>
            executeGuardedAgentDelete({ ...params, unlinkFromDraftPacks: true }),
        }),
      );
    if (!intercepted) {
      reportError(err, errorContext, false);
    }
    return false;
  }
}
