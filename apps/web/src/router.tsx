import { QueryClient } from "@tanstack/react-query";
import { createRoute, createRouter, type RouterHistory } from "@tanstack/react-router";
import React from "react";
import { ModuleWorkspaceView } from "./components/ModuleWorkspaceView";
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
import { validateOrciaRouteSearch } from "./routes/searchSchema";
import { Route as settingsRoute, SettingsHubView } from "./routes/settings";
import { Route as wizardsRoute } from "./routes/wizards";
import { Route as workspacesRoute } from "./routes/workspaces";

const assistantRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/assistant",
  validateSearch: validateOrciaRouteSearch,
  component: function AssistantRouteComponent() {
    return <ModuleWorkspaceView moduleKey="inbox" />;
  },
});

const processesRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/processes",
  validateSearch: validateOrciaRouteSearch,
  component: function ProcessesRouteComponent() {
    return <ModuleWorkspaceView moduleKey="gates" />;
  },
});

const agentsRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/agents",
  validateSearch: validateOrciaRouteSearch,
  component: function AgentsRouteComponent() {
    return <ModuleWorkspaceView moduleKey="catalog" />;
  },
});

const spacesRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/spaces",
  validateSearch: validateOrciaRouteSearch,
  component: function SpacesRouteComponent() {
    return <ModuleWorkspaceView moduleKey="admin" />;
  },
});

const configurationRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/configuration",
  validateSearch: validateOrciaRouteSearch,
  component: SettingsHubView,
});

const helpRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/help",
  validateSearch: validateOrciaRouteSearch,
  component: function HelpRouteComponent() {
    return <ModuleWorkspaceView moduleKey="ontology" />;
  },
});

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
  assistantRoute,
  processesRoute,
  agentsRoute,
  spacesRoute,
  configurationRoute,
  helpRoute,
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
