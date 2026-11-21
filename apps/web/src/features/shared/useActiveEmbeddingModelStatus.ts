import { createOrciaApiClient } from "@orcia/api-client";
import { useEffect, useState } from "react";

export function useActiveEmbeddingModelStatus(): {
  readonly hasActiveEmbeddingModel: boolean;
  readonly hasActiveChatModel: boolean;
  readonly isLoaded: boolean;
} {
  const [hasActiveEmbeddingModel, setHasActiveEmbeddingModel] = useState<boolean>(true);
  const [hasActiveChatModel, setHasActiveChatModel] = useState<boolean>(true);
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
          const hasChat = items.some(
            (m) => m.is_active && !m.draining && m.usage !== "embedding",
          );
          setHasActiveEmbeddingModel(hasEmbedding);
          setHasActiveChatModel(hasChat);
          setIsLoaded(true);
        }
      })
      .catch((err: unknown) => {
        if (isMounted) {
          console.warn("[ORCIA-UI] Failed to verify active AI model statuses:", err);
          setHasActiveEmbeddingModel(false);
          setHasActiveChatModel(false);
          setIsLoaded(true);
        }
      });
    return () => {
      isMounted = false;
    };
  }, []);

  return { hasActiveEmbeddingModel, hasActiveChatModel, isLoaded };
}
