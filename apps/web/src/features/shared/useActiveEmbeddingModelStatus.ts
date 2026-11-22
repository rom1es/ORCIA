import { createOrciaApiClient } from "@orcia/api-client";
import { useEffect, useState } from "react";

export function useActiveEmbeddingModelStatus(): {
  readonly hasActiveEmbeddingModel: boolean;
  readonly hasActiveChatModel: boolean;
  readonly hasSupportsTools: boolean;
  readonly isLoaded: boolean;
} {
  const [hasActiveEmbeddingModel, setHasActiveEmbeddingModel] = useState<boolean>(true);
  const [hasActiveChatModel, setHasActiveChatModel] = useState<boolean>(true);
  const [hasSupportsTools, setHasSupportsTools] = useState<boolean>(true);
  const [isLoaded, setIsLoaded] = useState<boolean>(false);

  useEffect(() => {
    let isMounted = true;
    const client = createOrciaApiClient({ baseUrl: "" });
    client.aiModelsHub
      .listAiModelMappings({ is_active: true })
      .then((res) => {
        if (isMounted) {
          const items = res.items ?? [];
          const hasEmbedding = items.some(
            (m) =>
              m.is_active &&
              !m.draining &&
              (m.scope_level ?? "GLOBAL") === "GLOBAL" &&
              m.usage === "embedding",
          );
          const activeChatModels = items.filter(
            (m) => m.is_active && !m.draining && m.usage !== "embedding",
          );
          const hasChat = activeChatModels.length > 0;
          const supportsTools =
            hasChat &&
            activeChatModels.some((m) => {
              const eff = m.supports_tools_override ?? m.supports_tools;
              return eff === undefined || eff === null ? true : Boolean(eff);
            });
          setHasActiveEmbeddingModel(hasEmbedding);
          setHasActiveChatModel(hasChat);
          setHasSupportsTools(supportsTools);
          setIsLoaded(true);
        }
      })
      .catch((err: unknown) => {
        if (isMounted) {
          console.warn("[ORCIA-UI] Failed to verify active AI model statuses:", err);
          setHasActiveEmbeddingModel(false);
          setHasActiveChatModel(false);
          setHasSupportsTools(false);
          setIsLoaded(true);
        }
      });
    return () => {
      isMounted = false;
    };
  }, []);

  return { hasActiveEmbeddingModel, hasActiveChatModel, hasSupportsTools, isLoaded };
}
