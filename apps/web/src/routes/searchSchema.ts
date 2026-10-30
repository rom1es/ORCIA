import type { UiModuleKey } from "@orcia/ui";
import type { QueryClient } from "@tanstack/react-query";

export interface OrciaRouterContext {
  queryClient: QueryClient;
}

export interface OrciaRouteSearch {
  fixture?: "test";
  q?: string;
  auth?: "unauthenticated";
}

export function validateOrciaRouteSearch(
  search: Record<string, unknown>,
): OrciaRouteSearch {
  const result: OrciaRouteSearch = {};
  if (search.fixture === "test") {
    result.fixture = "test";
  }
  if (typeof search.q === "string" && search.q.trim().length > 0) {
    result.q = search.q.trim();
  }
  if (search.auth === "unauthenticated") {
    result.auth = "unauthenticated";
  }
  return result;
}

export function preloadModuleQueryData(
  queryClient: QueryClient,
  moduleKey: UiModuleKey,
  fixture = false,
): Promise<{ moduleKey: UiModuleKey; fixture: boolean }> {
  return queryClient.ensureQueryData({
    queryKey: ["orcia-module-preload", moduleKey, fixture],
    queryFn: async () => ({ moduleKey, fixture }),
  });
}
