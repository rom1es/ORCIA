import type {
  AgentItemResponse,
  AgentsAndSkillsListResponse,
  DeleteSkillOrAgentResponse,
  ExecuteAgentRequest,
  ExecuteAgentResponse,
  ExecuteSkillRequest,
  ExecuteSkillResponse,
  SkillItemResponse,
  UpdateAgentSkillsRequest,
  UpsertAgentRequest,
  UpsertSkillRequest,
} from "../generated/agents_and_skills";
import { buildPersonaQuery, type createRequestJson } from "../helpers";

type RequestJsonFn = ReturnType<typeof createRequestJson>;

export function createAgentsAndSkillsDomainClient(requestJson: RequestJsonFn) {
  return {
    listAgentsAndSkills(personaKey?: string): Promise<AgentsAndSkillsListResponse> {
      return requestJson<AgentsAndSkillsListResponse>(
        `/api/v1/agents-and-skills${buildPersonaQuery(personaKey)}`,
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
      personaKey?: string,
    ): Promise<DeleteSkillOrAgentResponse> {
      return requestJson<DeleteSkillOrAgentResponse>(
        `/api/v1/agents-and-skills/skills/${encodeURIComponent(skillId)}${buildPersonaQuery(personaKey)}`,
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
      personaKey?: string,
    ): Promise<DeleteSkillOrAgentResponse> {
      return requestJson<DeleteSkillOrAgentResponse>(
        `/api/v1/agents-and-skills/agents/${encodeURIComponent(agentId)}${buildPersonaQuery(personaKey)}`,
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
