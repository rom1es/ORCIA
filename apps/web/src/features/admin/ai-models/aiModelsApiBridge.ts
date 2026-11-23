import {
  createOrciaApiClient,
  type AiModelCreateRequest,
  type AiModelDeleteImpactResponse,
  type AiModelDeleteResponse,
  type AiModelMappingItemResponse,
  type AiModelPatchRequest,
  type AiModelTestResponse,
} from "@orcia/api-client";
import { extractLocalizedApiError } from "../../../lib/formatRfc9457ErrorToBanner";
import { useAuthSessionStore } from "../../../stores/authSessionStore";

export type AiModelOperationResult<T> =
  | { readonly ok: true; readonly data: T }
  | { readonly ok: false; readonly errorMessage: string; readonly errorCode?: string };

function buildAiModelsClient(locale: "fr" | "en") {
  return createOrciaApiClient({
    baseUrl: "",
    locale,
  });
}

function resolveActorPersona(): string {
  const { roles } = useAuthSessionStore.getState();
  if (roles.includes("PLATFORM_ADMIN") || roles.includes("SECOPS")) return "karim";
  return "marc";
}

function extractAiModelsApiError(
  err: unknown,
  locale: "fr" | "en",
): { readonly errorMessage: string; readonly errorCode?: string } {
  const extracted = extractLocalizedApiError(
    err,
    locale,
    "ERR_CLIENT_AI_HUB_COMMUNICATION",
  );
  if (extracted.errorCode === "ERR_CLIENT_TIMEOUT") {
    return {
      errorMessage: extracted.errorMessage,
      errorCode: "ERR_MODEL_CONNECTION_TIMEOUT",
    };
  }
  return extracted;
}

export async function fetchAiModelMappings(
  locale: "fr" | "en",
): Promise<AiModelOperationResult<readonly AiModelMappingItemResponse[]>> {
  try {
    const client = buildAiModelsClient(locale);
    const resp = await client.aiModelsHub.listAiModelMappings();
    const items = Array.isArray(resp) ? resp : Array.isArray(resp?.items) ? resp.items : [];
    return { ok: true, data: items };
  } catch (err: unknown) {
    return { ok: false, ...extractAiModelsApiError(err, locale) };
  }
}

export async function createAiModelMappingViaApi(
  payload: AiModelCreateRequest,
  locale: "fr" | "en",
): Promise<AiModelOperationResult<AiModelMappingItemResponse>> {
  try {
    const client = buildAiModelsClient(locale);
    const persona = resolveActorPersona();
    const created = await client.aiModelsHub.createAiModelMapping(payload, persona);
    return { ok: true, data: created };
  } catch (err: unknown) {
    return { ok: false, ...extractAiModelsApiError(err, locale) };
  }
}

export async function patchAiModelMappingViaApi(
  mappingId: string,
  payload: AiModelPatchRequest,
  locale: "fr" | "en",
): Promise<AiModelOperationResult<AiModelMappingItemResponse>> {
  try {
    const client = buildAiModelsClient(locale);
    const persona = resolveActorPersona();
    const patched = await client.aiModelsHub.updateAiModelMapping(mappingId, payload, persona);
    return { ok: true, data: patched };
  } catch (err: unknown) {
    return { ok: false, ...extractAiModelsApiError(err, locale) };
  }
}

export async function testAiModelConnectionViaApi(
  mappingId: string,
  locale: "fr" | "en",
): Promise<AiModelOperationResult<AiModelTestResponse>> {
  const signal =
    typeof AbortSignal !== "undefined" && typeof AbortSignal.timeout === "function"
      ? AbortSignal.timeout(16_000)
      : undefined;
  try {
    const client = buildAiModelsClient(locale);
    const testRes = await client.aiModelsHub.testAiModelMapping(
      mappingId,
      signal ? { signal } : undefined,
    );
    return { ok: true, data: testRes };
  } catch (err: unknown) {
    return { ok: false, ...extractAiModelsApiError(err, locale) };
  }
}

export async function fetchAiModelDeleteImpactViaApi(
  mappingId: string,
  locale: "fr" | "en",
): Promise<AiModelOperationResult<AiModelDeleteImpactResponse>> {
  try {
    const client = buildAiModelsClient(locale);
    const impact = await client.aiModelsHub.getAiModelDeleteImpact(mappingId);
    return { ok: true, data: impact };
  } catch (err: unknown) {
    return { ok: false, ...extractAiModelsApiError(err, locale) };
  }
}

export async function deleteAiModelMappingViaApi(
  mappingId: string,
  mode: "reject" | "drain" | "force",
  locale: "fr" | "en",
): Promise<AiModelOperationResult<AiModelDeleteResponse>> {
  try {
    const client = buildAiModelsClient(locale);
    const persona = resolveActorPersona();
    const res = await client.aiModelsHub.deleteAiModelMapping(mappingId, mode, persona);
    return { ok: true, data: res };
  } catch (err: unknown) {
    return { ok: false, ...extractAiModelsApiError(err, locale) };
  }
}
