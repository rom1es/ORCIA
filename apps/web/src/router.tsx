import { QueryClient } from "@tanstack/react-query";
import { createRouter, type RouterHistory } from "@tanstack/react-router";
import { Route as rootRoute } from "./routes/__root";
import { Route as bootstrapRoute } from "./routes/bootstrap";
import { Route as catalogRoute } from "./routes/catalog";
import { Route as cockpitRoute } from "./routes/cockpit";
import { Route as finopsRoute } from "./routes/finops";
import { Route as gatesRoute } from "./routes/gates";
import { Route as inboxRoute } from "./routes/inbox";
import { Route as indexRoute } from "./routes/index";
import { Route as loginRoute } from "./routes/login";
import { Route as ontologyRoute } from "./routes/ontology";
import { Route as settingsRoute } from "./routes/settings";
import { Route as wizardsRoute } from "./routes/wizards";
import { Route as workspacesRoute } from "./routes/workspaces";

export const routeTree = rootRoute.addChildren([
  indexRoute,
  loginRoute,
  cockpitRoute,
  inboxRoute,
  catalogRoute,
  ontologyRoute,
  gatesRoute,
  finopsRoute,
  workspacesRoute,
  bootstrapRoute,
  settingsRoute,
  wizardsRoute,
]);

export function createOrciaQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 30_000,
        retry: false,
      },
    },
  });
}

export function createOrciaRouter(options?: {
  queryClient?: QueryClient;
  history?: RouterHistory;
}) {
  const queryClient = options?.queryClient ?? createOrciaQueryClient();
  return createRouter({
    routeTree,
    context: { queryClient },
    defaultPreload: "intent",
    history: options?.history,
  });
}

declare module "@tanstack/react-router" {
  interface Register {
    router: ReturnType<typeof createOrciaRouter>;
  }
}
