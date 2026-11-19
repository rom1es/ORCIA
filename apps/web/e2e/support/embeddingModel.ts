import { expect, type Page } from "@playwright/test";
import { apiPost } from "./typedApiRequest";

/**
 * Configure un modèle d'embedding sémantique GLOBAL actif via l'API réelle
 * (prérequis Story 19.6 pour débloquer Mon Assistant et la recherche fédérée v2).
 */
export async function configureActiveEmbeddingModelViaApi(page: Page): Promise<void> {
  const refreshRes = await apiPost<{ access_token?: string }>(page, "/api/v1/auth/refresh");
  expect(refreshRes.status()).toBe(200);
  const { access_token: token } = await refreshRes.json();
  expect(token).toBeTruthy();

  const createRes = await apiPost(page, "/api/v1/settings/ai-models/mappings", {
    token,
    data: {
      scope_level: "GLOBAL",
      scope_id: "0195f000-0000-7000-8000-000000000301",
      display_name: "Embedding E2E Cassette",
      inference_tier: "simple",
      effort: "default",
      provider_slug: "ollama",
      model_family: "ollama",
      model_name: "bge-m3:latest",
      endpoint_uri: "http://127.0.0.1:11434/v1",
      auth_mode: "none_local",
      protocol_mode: "openai_compatible",
      usage: "embedding",
    },
  });
  expect([200, 201]).toContain(createRes.status());
}
