import { createRoute, redirect } from "@tanstack/react-router";
import React from "react";
import { ModuleWorkspaceView } from "../components/ModuleWorkspaceView";
import { Route as rootRoute } from "./__root";
import { preloadModuleQueryData, validateOrciaRouteSearch } from "./searchSchema";

function HomeRouteComponent() {
  return <ModuleWorkspaceView moduleKey="cockpit" />;
}

export const Route = createRoute({
  getParentRoute: () => rootRoute,
  path: "/",
  validateSearch: validateOrciaRouteSearch,
  beforeLoad: ({ search }) => {
    if (search.auth === "unauthenticated") {
      throw redirect({ to: "/login" });
    }
  },
  loaderDeps: ({ search }) => ({ fixture: search.fixture === "test" }),
  loader: ({ context, deps }) =>
    preloadModuleQueryData(context.queryClient, "cockpit", deps.fixture),
  component: HomeRouteComponent,
});
