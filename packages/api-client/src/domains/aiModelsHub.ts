import type {
  AiModelCreateRequest,
  AiModelDeleteImpactResponse,
  AiModelDeleteResponse,
  AiModelDiscoverRequest,
  AiModelDiscoveryResponse,
  AiModelMappingItemResponse,
  AiModelMappingsListResponse,
  AiModelPatchRequest,
  AiModelTestResponse,
  RagReindexStatusResponse,
  RagReindexTriggerResponse,
} from "../generated/ai_models_hub";
import { buildPersonaQuery, type createRequestJson } from "../helpers";

type RequestJsonFn = ReturnType<typeof createRequestJson>;

export interface ListAiModelMappingsParams {
  scope_level?: "GLOBAL" | "BU" | "TEAM" | "WORKSPACE";
  scope_id?: string;
  inference_tier?: "simple" | "medium" | "complex" | "auto";
  is_active?: boolean;
  usage?: "chat" | "embedding";
}

export function createAiModelsHubDomainClient(requestJson: RequestJsonFn) {
  return {
    listAiModelMappings(params?: ListAiModelMappingsParams): Promise<AiModelMappingsListResponse> {
      const q = new URLSearchParams();
      if (params?.scope_level) q.set("scope_level", params.scope_level);
      if (params?.scope_id) q.set("scope_id", params.scope_id);
      if (params?.inference_tier) q.set("inference_tier", params.inference_tier);
      if (params?.is_active !== undefined) q.set("is_active", String(params.is_active));
      if (params?.usage) q.set("usage", params.usage);
      const qs = q.toString();
      return requestJson<AiModelMappingsListResponse>(
        `/api/v1/settings/ai-models/mappings${qs ? `?${qs}` : ""}`,
      );
    },

    createAiModelMapping(
      payload: AiModelCreateRequest,
      actorPersona?: string,
    ): Promise<AiModelMappingItemResponse> {
      return requestJson<AiModelMappingItemResponse>(
        `/api/v1/settings/ai-models/mappings${buildPersonaQuery(actorPersona)}`,
        "POST",
        payload,
      );
    },

    updateAiModelMapping(
      mappingId: string,
      payload: AiModelPatchRequest,
      actorPersona?: string,
    ): Promise<AiModelMappingItemResponse> {
      return requestJson<AiModelMappingItemResponse>(
        `/api/v1/settings/ai-models/mappings/${encodeURIComponent(mappingId)}${buildPersonaQuery(actorPersona)}`,
        "PATCH",
        payload,
      );
    },

    testAiModelMapping(
      mappingId: string,
      options?: { signal?: AbortSignal },
    ): Promise<AiModelTestResponse> {
      return requestJson<AiModelTestResponse>(
        `/api/v1/settings/ai-models/mappings/${encodeURIComponent(mappingId)}/test`,
        "POST",
        undefined,
        undefined,
        options?.signal,
      );
    },

    discoverAiModels(
      payload: AiModelDiscoverRequest,
      actorPersona?: string,
    ): Promise<AiModelDiscoveryResponse> {
      return requestJson<AiModelDiscoveryResponse>(
        `/api/v1/settings/ai-models/discover${buildPersonaQuery(actorPersona)}`,
        "POST",
        payload,
      );
    },

    getAiModelDeleteImpact(mappingId: string): Promise<AiModelDeleteImpactResponse> {
      return requestJson<AiModelDeleteImpactResponse>(
        `/api/v1/settings/ai-models/mappings/${encodeURIComponent(mappingId)}/delete-impact`,
      );
    },

    deleteAiModelMapping(
      mappingId: string,
      mode: "reject" | "drain" | "force" = "reject",
      actorRole = "PLATFORM_ADMIN",
    ): Promise<AiModelDeleteResponse> {
      const q = new URLSearchParams({ mode, actor_role: actorRole });
      return requestJson<AiModelDeleteResponse>(
        `/api/v1/settings/ai-models/mappings/${encodeURIComponent(mappingId)}?${q.toString()}`,
        "DELETE",
      );
    },

    getReindexStatus(): Promise<RagReindexStatusResponse> {
      return requestJson<RagReindexStatusResponse>(
        "/api/v1/settings/ai-models/reindex-status",
      );
    },

    reindexEmbeddings(actorPersona?: string): Promise<RagReindexTriggerResponse> {
      return requestJson<RagReindexTriggerResponse>(
        `/api/v1/settings/ai-models/reindex-embeddings${buildPersonaQuery(actorPersona)}`,
        "POST",
      );
    },
  };
}
