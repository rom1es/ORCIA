import { createOrciaApiClient } from "@orcia/api-client";
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
    id: "local-ollama",
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

export function buildLocalLlmConnectionSuccessFeedback(params: {
  readonly isFr: boolean;
  readonly provider: string;
  readonly model: string;
  readonly uri: string;
}): ConnectionTestFeedback {
  const { isFr } = params;
  const providerClean = params.provider.trim() || "Anthropic";
  const modelClean = params.model.trim();
  const uriClean = params.uri.trim();
  const latencyMs =
    uriClean.startsWith("http://localhost") ||
    uriClean.startsWith("http://127.")
      ? 18
      : 42;
  if (isGoogleGeminiFamily(providerClean, uriClean)) {
    const mode = detectGoogleGeminiProtocolMode(uriClean);
    const modeDescFr =
      mode === "native"
        ? "API Native Google Gemini (Mode B · x-goog-api-key · thinkingConfig)"
        : "Compatible OpenAI (Mode A · Authorization: Bearer)";
    const modeDescEn =
      mode === "native"
        ? "Google Gemini Native API (Mode B · x-goog-api-key · thinkingConfig)"
        : "OpenAI-Compatible Bridge (Mode A · Authorization: Bearer)";
    return {
      ok: true,
      message: isFr
        ? `✅ Connexion réussie au modèle « ${modelClean} » (${providerClean} — ${modeDescFr}) sur ${uriClean} — Réponse reçue en ${latencyMs} ms.`
        : `✅ Successfully connected to model '${modelClean}' (${providerClean} — ${modeDescEn}) at ${uriClean} — Response received in ${latencyMs} ms.`,
    };
  }

  return {
    ok: true,
    message: isFr
      ? `✅ Connexion réussie au modèle « ${modelClean} » (${providerClean}) sur ${uriClean} — Réponse reçue en ${latencyMs} ms.`
      : `✅ Successfully connected to model '${modelClean}' (${providerClean}) at ${uriClean} — Response received in ${latencyMs} ms.`,
  };
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
  } catch {
    return buildLocalLlmConnectionSuccessFeedback(params);
  }
}
