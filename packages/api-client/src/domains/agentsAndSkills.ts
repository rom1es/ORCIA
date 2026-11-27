import type {
  AgentItemResponse,
  AgentsAndSkillsListResponse,
  DeleteSkillOrAgentResponse,
  DuplicateAgentRequest,
  ExecuteAgentRequest,
  ExecuteAgentResponse,
  ExecuteSkillRequest,
  ExecuteSkillResponse,
  ResolveAgentOrSkillResponse,
  SkillItemResponse,
  ToggleAgentGovernanceRequest,
  UpdateAgentSkillsRequest,
  UpsertAgentRequest,
  UpsertSkillRequest,
} from "../generated/agents_and_skills";
import { buildPersonaQuery, type createRequestJson } from "../helpers";

type RequestJsonFn = ReturnType<typeof createRequestJson>;

export interface DeleteEntityGuardOptions {
  readonly personaKey?: string;
  readonly unlinkFromDraftPacks?: boolean;
}

function buildGuardedDeleteQuery(
  personaKeyOrOptions?: string | DeleteEntityGuardOptions,
): string {
  if (!personaKeyOrOptions) return "";
  if (typeof personaKeyOrOptions === "string") {
    return buildPersonaQuery(personaKeyOrOptions);
  }
  const qs = new URLSearchParams();
  if (personaKeyOrOptions.unlinkFromDraftPacks) {
    qs.set("unlink_from_draft_packs", "true");
  }
  if (personaKeyOrOptions.personaKey) {
    qs.set("persona_key", personaKeyOrOptions.personaKey);
  }
  const encoded = qs.toString();
  return encoded ? `?${encoded}` : "";
}

export function createAgentsAndSkillsDomainClient(requestJson: RequestJsonFn) {
  return {
    listAgentsAndSkills(
      personaKey?: string,
      workspaceId?: string,
    ): Promise<AgentsAndSkillsListResponse> {
      const qs = new URLSearchParams();
      if (personaKey) qs.set("persona_key", personaKey);
      if (workspaceId) qs.set("workspace_id", workspaceId);
      const q = qs.toString();
      return requestJson<AgentsAndSkillsListResponse>(
        `/api/v1/agents-and-skills${q ? `?${q}` : ""}`,
      );
    },
    resolveAgentOrSkill(params: {
      ref: string;
      kind?: "agent" | "skill";
      workspaceId?: string;
      strictDisambiguation?: boolean;
      personaKey?: string;
    }): Promise<ResolveAgentOrSkillResponse> {
      const qs = new URLSearchParams({ ref: params.ref });
      if (params.kind) qs.set("kind", params.kind);
      if (params.workspaceId) qs.set("workspace_id", params.workspaceId);
      if (params.strictDisambiguation) qs.set("strict_disambiguation", "true");
      if (params.personaKey) qs.set("persona_key", params.personaKey);
      return requestJson<ResolveAgentOrSkillResponse>(
        `/api/v1/agents-and-skills/resolve?${qs.toString()}`,
      );
    },
    upsertSkill(
      payload: UpsertSkillRequest,
      personaKey?: string,
    ): Promise<SkillItemResponse> {
      return requestJson<SkillItemResponse>(
        `/api/v1/agents-and-skills/skills${buildPersonaQuery(personaKey)}`,
        "POST",
        payload,
      );
    },
    deleteSkill(
      skillId: string,
      personaKeyOrOptions?: string | DeleteEntityGuardOptions,
    ): Promise<DeleteSkillOrAgentResponse> {
      return requestJson<DeleteSkillOrAgentResponse>(
        `/api/v1/agents-and-skills/skills/${encodeURIComponent(skillId)}${buildGuardedDeleteQuery(personaKeyOrOptions)}`,
        "DELETE",
      );
    },
    executeSkill(
      skillId: string,
      payload: ExecuteSkillRequest,
      personaKey?: string,
    ): Promise<ExecuteSkillResponse> {
      return requestJson<ExecuteSkillResponse>(
        `/api/v1/agents-and-skills/skills/${encodeURIComponent(skillId)}/execute${buildPersonaQuery(personaKey)}`,
        "POST",
        payload,
      );
    },
    upsertAgent(
      payload: UpsertAgentRequest,
      personaKey?: string,
    ): Promise<AgentItemResponse> {
      return requestJson<AgentItemResponse>(
        `/api/v1/agents-and-skills/agents${buildPersonaQuery(personaKey)}`,
        "POST",
        payload,
      );
    },
    duplicateAgent(
      agentId: string,
      payload: DuplicateAgentRequest = {},
      personaKey?: string,
    ): Promise<AgentItemResponse> {
      return requestJson<AgentItemResponse>(
        `/api/v1/agents-and-skills/agents/${encodeURIComponent(agentId)}/duplicate${buildPersonaQuery(personaKey)}`,
        "POST",
        payload,
      );
    },
    updateAgentGovernance(
      agentId: string,
      payload: ToggleAgentGovernanceRequest,
      personaKey?: string,
    ): Promise<AgentItemResponse> {
      return requestJson<AgentItemResponse>(
        `/api/v1/agents-and-skills/agents/${encodeURIComponent(agentId)}/governance${buildPersonaQuery(personaKey)}`,
        "PATCH",
        payload,
      );
    },
    updateAgentSkills(
      agentId: string,
      payload: UpdateAgentSkillsRequest,
      personaKey?: string,
    ): Promise<AgentItemResponse> {
      return requestJson<AgentItemResponse>(
        `/api/v1/agents-and-skills/agents/${encodeURIComponent(agentId)}/skills${buildPersonaQuery(personaKey)}`,
        "PATCH",
        payload,
      );
    },
    deleteAgent(
      agentId: string,
      personaKeyOrOptions?: string | DeleteEntityGuardOptions,
    ): Promise<DeleteSkillOrAgentResponse> {
      return requestJson<DeleteSkillOrAgentResponse>(
        `/api/v1/agents-and-skills/agents/${encodeURIComponent(agentId)}${buildGuardedDeleteQuery(personaKeyOrOptions)}`,
        "DELETE",
      );
    },
    executeAgent(
      agentId: string,
      payload: ExecuteAgentRequest,
      personaKey?: string,
    ): Promise<ExecuteAgentResponse> {
      return requestJson<ExecuteAgentResponse>(
        `/api/v1/agents-and-skills/agents/${encodeURIComponent(agentId)}/execute${buildPersonaQuery(personaKey)}`,
        "POST",
        payload,
      );
    },
  };
}
