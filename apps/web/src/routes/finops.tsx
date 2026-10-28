import { createRoute } from "@tanstack/react-router";
import React from "react";
import { ModuleWorkspaceView } from "../components/ModuleWorkspaceView";
import { Route as rootRoute } from "./__root";
import { preloadModuleQueryData, validateOrciaRouteSearch } from "./searchSchema";

export const Route = createRoute({
  getParentRoute: () => rootRoute,
  path: "/finops",
  validateSearch: validateOrciaRouteSearch,
  loaderDeps: ({ search }) => ({ fixture: search.fixture === "test" }),
  loader: ({ context, deps }) =>
    preloadModuleQueryData(context.queryClient, "finops", deps.fixture),
  component: function FinopsRouteComponent() {
    return <ModuleWorkspaceView moduleKey="finops" />;
  },
});
