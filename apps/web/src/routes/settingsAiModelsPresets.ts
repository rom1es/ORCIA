import { createOrciaApiClient, type DiscoveredModelItem } from "@orcia/api-client";
import type { LlmAuthMode } from "../components/platformSetupStore";
import type { AiModelsHubDictionary } from "../i18n/locales/ai_models_hub_labels";

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
  readonly isFr: boolean;
  readonly model: string;
  readonly uri: string;
  readonly mode: LlmAuthMode;
  readonly rawKey: string;
  readonly keyAlreadyConfigured: boolean;
}): ConnectionTestFeedback | null {
  const { isFr } = params;
  const modelClean = params.model.trim();
  const uriClean = params.uri.trim();
  const hasKey = Boolean(params.rawKey.trim() || params.keyAlreadyConfigured);

  if (!modelClean) {
    return {
      ok: false,
      message: isFr
        ? "❌ Échec du test : veuillez renseigner l'identifiant du modèle principal (ex. : llama3.2, mistral-large-latest)."
        : "❌ Test failed: please enter the primary model identifier (e.g. llama3.2, mistral-large-latest).",
    };
  }

  if (
    !uriClean ||
    !(uriClean.startsWith("http://") || uriClean.startsWith("https://"))
  ) {
    return {
      ok: false,
      message: isFr
        ? "❌ Échec du test : veuillez indiquer une URL d'API valide commençant par https:// ou http:// (ex. https://generativelanguage.googleapis.com/v1beta ou http://localhost:11434/v1)."
        : "❌ Test failed: please enter a valid API URL starting with https:// or http:// (e.g. https://generativelanguage.googleapis.com/v1beta or http://localhost:11434/v1).",
    };
  }

  if (params.mode === "api_key" && !hasKey) {
    return {
      ok: false,
      message: isFr
        ? "❌ Échec du test : veuillez saisir votre clé d'API (jeton secret) ou choisir « Sans clé (Serveur local) » / « Variable d'environnement du serveur »."
        : "❌ Test failed: please enter your API key (secret token) or select 'No key (Local server)' / 'Server environment variable'.",
    };
  }

  return null;
}

export async function runRemoteLlmConnectionTestEvaluation(params: {
  readonly isFr: boolean;
  readonly provider: string;
  readonly model: string;
  readonly uri: string;
  readonly mode: LlmAuthMode;
  readonly rawKey: string;
  readonly keyAlreadyConfigured: boolean;
}): Promise<ConnectionTestFeedback> {
  try {
    const client = createOrciaApiClient({ baseUrl: "" });
    const remote = await client.testLlmEndpointConnection({
      provider_slug: params.provider.trim() || "Anthropic",
      model_name: params.model.trim(),
      endpoint_uri: params.uri.trim(),
      auth_mode: params.mode,
      api_key: params.rawKey.trim() || null,
      api_key_configured: params.keyAlreadyConfigured,
    });
    return {
      ok: remote.ok,
      message: params.isFr ? remote.message_fr : remote.message_en,
    };
  } catch (err: unknown) {
    let msg = params.isFr
      ? "❌ Échec du test : impossible de joindre le fournisseur LLM."
      : "❌ Test failed: unable to contact LLM provider.";
    if (err && typeof err === "object" && "problem" in err) {
      const p = (err as { problem?: { detail?: string; title?: string } }).problem;
      if (p?.detail) msg = `❌ ${p.detail}`;
      else if (p?.title) msg = `❌ ${p.title}`;
    } else if (err instanceof Error && err.message) {
      msg = `❌ ${err.message}`;
    }
    return {
      ok: false,
      message: msg,
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
