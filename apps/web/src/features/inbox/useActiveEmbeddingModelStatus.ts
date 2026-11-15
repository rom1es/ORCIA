import { createOrciaApiClient } from "@orcia/api-client";
import { useEffect, useState } from "react";

export function useActiveEmbeddingModelStatus(): {
  readonly hasActiveEmbeddingModel: boolean;
} {
  const [hasActiveEmbeddingModel, setHasActiveEmbeddingModel] = useState<boolean>(true);

  useEffect(() => {
    let isMounted = true;
    const client = createOrciaApiClient({ baseUrl: "" });
    client.aiModelsHub
      .listAiModelMappings({ usage: "embedding", is_active: true })
      .then((res) => {
        if (isMounted) {
          const items = res.items ?? [];
          const hasActive = items.some((m) => m.is_active && m.usage === "embedding");
          setHasActiveEmbeddingModel(hasActive);
        }
      })
      .catch((err: unknown) => {
        if (isMounted) {
          console.warn("[ORCIA-UI] Failed to verify active embedding model status:", err);
          setHasActiveEmbeddingModel(false);
        }
      });
    return () => {
      isMounted = false;
    };
  }, []);

  return { hasActiveEmbeddingModel };
}
