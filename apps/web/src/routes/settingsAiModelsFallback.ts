import type { AiModelMappingItemResponse } from "@orcia/api-client";
import type { ConfiguredLlmTierMapping } from "../components/platformSetupStore";

export function buildFallbackMappingsFromProps(
  llmTiers: readonly ConfiguredLlmTierMapping[],
): readonly AiModelMappingItemResponse[] {
  return llmTiers.map((t) => ({
    id: t.tier,
    scope_level: "GLOBAL",
    scope_id: "",
    display_name: t.primaryModel,
    inference_tier: t.tier,
    effort: t.defaultEffort,
    provider_slug: t.modelFamily || "Anthropic",
    model_family: t.modelFamily || "Anthropic",
    model_name: t.primaryModel,
    fallback_model_name: t.secondaryModel || null,
    endpoint_uri: t.endpointUrl || "https://api.anthropic.com/v1",
    auth_mode: t.authMode || "api_key",
    protocol_mode: "openai_compatible",
    env_var_name: null,
    fallback_order: 1,
    max_tokens_budget: 0,
    max_cost_usd: 0,
    is_active: true,
    draining: false,
    health_status: "OPERATIONAL",
    last_tested_at: new Date().toISOString(),
    last_latency_ms: 120,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    secret_status: {
      configured: Boolean(t.apiKeyConfigured),
      fingerprint: t.apiKeyConfigured ? "sha256:propdemo" : null,
      masked_hint: t.apiKeyConfigured ? "••••••••demo" : null,
      updated_at: new Date().toISOString(),
      updated_by: "system",
    },
  }));
}
