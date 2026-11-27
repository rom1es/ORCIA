import { createOrciaApiClient } from "@orcia/api-client";
import { useEffect, useState } from "react";
import type { SupportedWebLocale } from "../i18n";
import { mapAgentDtoToUi, mapSkillDtoToUi } from "./agentDtoMappers";
import {
  readCachedAgentsAndSkills,
  writeCachedAgentsAndSkills,
} from "./agentsAndSkillsBridgeStore";

/**
 * Hydrates the shared client cache from GET /api/v1/agents-and-skills so cold
 * page loads on /assistant or /processes/studio reflect live PG18 lifecycle status.
 */
export function useSyncManagedAgentsCache(
  locale: SupportedWebLocale,
  defaultSkillOutputFormat: string,
  workspaceId?: string,
): readonly [number, ReturnType<typeof readCachedAgentsAndSkills>["agents"]] {
  const [syncTick, setSyncTick] = useState<number>(0);
  const [agents, setAgents] = useState(() => readCachedAgentsAndSkills().agents);

  useEffect(() => {
    let cancelled = false;
    createOrciaApiClient({ baseUrl: "", locale })
      .listAgentsAndSkills(undefined, workspaceId || undefined)
      .then((res) => {
        if (cancelled) return;
        const mappedSkills = (res.skills ?? []).map((s) =>
          mapSkillDtoToUi(s, defaultSkillOutputFormat),
        );
        const mappedAgents = (res.agents ?? []).map(mapAgentDtoToUi);
        writeCachedAgentsAndSkills({ agents: mappedAgents, skills: mappedSkills });
        setAgents(mappedAgents);
        setSyncTick((n) => n + 1);
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          console.warn("[ORCIA] Failed to sync managed agents cache:", err);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [locale, defaultSkillOutputFormat, workspaceId]);

  return [syncTick, agents] as const;
}
