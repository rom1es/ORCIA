import { createOrciaApiClient, type DiscoveredModelItem } from "@orcia/api-client";
import type { LlmAuthMode } from "../components/platformSetupStore";
import type { AiModelsHubDictionary } from "../i18n/locales/ai_models_hub_labels";
import {
  extractLocalizedApiError,
  resolveLocalizedClientError,
} from "../lib/formatRfc9457ErrorToBanner";

export type GoogleGeminiProtocolMode = "native" | "openai";

export const GOOGLE_GEMINI_NATIVE_ENDPOINT =
  "https://generativelanguage.googleapis.com/v1beta";
export const GOOGLE_GEMINI_OPENAI_ENDPOINT =
  "https://generativelanguage.googleapis.com/v1beta/openai";

export interface ProviderPresetSpec {
  readonly id: string;
  readonly label: string;
  readonly familyValue: string;
  readonly defaultEndpointUrl: string;
  readonly defaultAuthMode: LlmAuthMode;
}

export const AI_PROVIDER_PRESETS: readonly ProviderPresetSpec[] = [
  {
    id: "anthropic",
    label: "Anthropic (Claude)",
    familyValue: "Anthropic",
    defaultEndpointUrl: "https://api.anthropic.com/v1",
    defaultAuthMode: "api_key",
  },
  {
    id: "openai",
    label: "OpenAI",
    familyValue: "OpenAI",
    defaultEndpointUrl: "https://api.openai.com/v1",
    defaultAuthMode: "api_key",
  },
  {
    id: "mistral",
    label: "Mistral AI",
    familyValue: "Mistral AI",
    defaultEndpointUrl: "https://api.mistral.ai/v1",
    defaultAuthMode: "api_key",
  },
  {
    id: "google",
    label: "Google Gemini",
    familyValue: "Google Gemini",
    defaultEndpointUrl: GOOGLE_GEMINI_NATIVE_ENDPOINT,
    defaultAuthMode: "api_key",
  },
  {
    id: "ollama",
    label: "Ollama / vLLM (Serveur local)",
    familyValue: "Ollama Local",
    defaultEndpointUrl: "http://localhost:11434/v1",
    defaultAuthMode: "none_local",
  },
];

export interface ConnectionTestFeedback {
  readonly ok: boolean;
  readonly message: string;
}

export function isGoogleGeminiFamily(
  modelFamily: string,
  endpointUrl: string,
): boolean {
  const f = modelFamily.trim().toLowerCase();
  const u = endpointUrl.trim().toLowerCase();
  return (
    f.includes("google") ||
    f.includes("gemini") ||
    u.includes("generativelanguage.googleapis.com")
  );
}

export function detectGoogleGeminiProtocolMode(
  endpointUrl: string,
): GoogleGeminiProtocolMode {
  return endpointUrl.trim().toLowerCase().includes("/openai")
    ? "openai"
    : "native";
}

export type LlmProtocolMode =
  | "openai_compatible"
  | "gemini_native"
  | "anthropic_messages";

export function resolveEffectiveLlmProtocolMode(
  modelFamily: string,
  endpointUrl: string,
  fallbackMode: LlmProtocolMode = "openai_compatible",
): LlmProtocolMode {
  if (isGoogleGeminiFamily(modelFamily, endpointUrl)) {
    return detectGoogleGeminiProtocolMode(endpointUrl) === "openai"
      ? "openai_compatible"
      : "gemini_native";
  }
  const fam = modelFamily.toLowerCase();
  const uri = endpointUrl.trim().toLowerCase().replace(/\/+$/, "");
  if (
    fam.includes("anthropic") ||
    uri.includes("anthropic.com") ||
    uri.endsWith("/messages")
  ) {
    return "anthropic_messages";
  }
  return fallbackMode;
}

export function resolvePrimaryModelPlaceholder(
  modelFamily: string,
  labels: AiModelsHubDictionary,
): string {
  const f = modelFamily.trim().toLowerCase();
  if (f.includes("mistral")) {
    return labels.primaryModelPlaceholderMistral;
  }
  if (f.includes("ollama") || f.includes("vllm") || f.includes("local")) {
    return labels.primaryModelPlaceholderOllama;
  }
  return labels.primaryModelPlaceholderGeneric;
}

export function validateLlmConnectionParameters(params: {
  readonly isFr?: boolean;
  readonly locale?: "fr" | "en";
  readonly model: string;
  readonly uri: string;
  readonly mode: LlmAuthMode;
  readonly rawKey: string;
  readonly keyAlreadyConfigured: boolean;
}): ConnectionTestFeedback | null {
  const activeLocale: "fr" | "en" =
    params.locale ?? (params.isFr === false ? "en" : "fr");
  const modelClean = params.model.trim();
  const uriClean = params.uri.trim();
  const hasKey = Boolean(params.rawKey.trim() || params.keyAlreadyConfigured);

  if (!modelClean) {
    return {
      ok: false,
      message: resolveLocalizedClientError("ERR_CLIENT_AI_MODEL_ID_REQUIRED", activeLocale),
    };
  }

  if (
    !uriClean ||
    !(uriClean.startsWith("http://") || uriClean.startsWith("https://"))
  ) {
    return {
      ok: false,
      message: resolveLocalizedClientError("ERR_CLIENT_AI_ENDPOINT_URL_INVALID", activeLocale),
    };
  }

  if (params.mode === "api_key" && !hasKey) {
    return {
      ok: false,
      message: resolveLocalizedClientError("ERR_CLIENT_AI_API_KEY_REQUIRED", activeLocale),
    };
  }

  return null;
}

export async function runRemoteLlmConnectionTestEvaluation(params: {
  readonly isFr?: boolean;
  readonly locale?: "fr" | "en";
  readonly provider: string;
  readonly model: string;
  readonly uri: string;
  readonly mode: LlmAuthMode;
  readonly rawKey: string;
  readonly keyAlreadyConfigured: boolean;
}): Promise<ConnectionTestFeedback> {
  const activeLocale: "fr" | "en" =
    params.locale ?? (params.isFr === false ? "en" : "fr");
  try {
    const client = createOrciaApiClient({ baseUrl: "", locale: activeLocale });
    const remote = await client.testLlmEndpointConnection({
      provider_slug: params.provider.trim() || "Anthropic",
      model_name: params.model.trim(),
      endpoint_uri: params.uri.trim(),
      auth_mode: params.mode,
      api_key: params.rawKey.trim() || null,
      api_key_configured: params.keyAlreadyConfigured,
    });
    const remoteMsgKey = ({ fr: "message_fr", en: "message_en" } as const)[activeLocale];
    return {
      ok: remote.ok,
      message: remote[remoteMsgKey],
    };
  } catch (err: unknown) {
    const extracted = extractLocalizedApiError(
      err,
      activeLocale,
      "ERR_CLIENT_AI_PROVIDER_UNREACHABLE",
    );
    const message = extracted.errorMessage.startsWith("❌")
      ? extracted.errorMessage
      : `❌ ${extracted.errorMessage}`;
    return {
      ok: false,
      message,
    };
  }
}

export async function discoverProviderModelsViaApi(params: {
  readonly endpointUri: string;
  readonly protocolMode: "openai_compatible" | "gemini_native" | "anthropic_messages";
  readonly providerSlug?: string;
  readonly mappingId?: string;
  readonly apiKey?: string;
}): Promise<{ ok: boolean; models: DiscoveredModelItem[]; error?: string }> {
  try {
    const client = createOrciaApiClient({ baseUrl: "" });
    const res = await client.discoverAiModels({
      endpoint_uri: params.endpointUri.trim(),
      protocol_mode: params.protocolMode,
      provider_slug: params.providerSlug?.trim() || null,
      mapping_id: params.mappingId?.trim() || null,
      api_key: params.apiKey?.trim() || null,
    });
    return { ok: true, models: res.models };
  } catch (err: unknown) {
    const errMsg = err instanceof Error ? err.message : String(err);
    return { ok: false, models: [], error: errMsg };
  }
}
