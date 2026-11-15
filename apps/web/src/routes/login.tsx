import { createRoute } from "@tanstack/react-router";
import {
  LoginRouteComponent,
  LoginScreenView,
  type LoginScreenViewProps,
} from "../components/LoginScreenView";
import { Route as rootRoute } from "./__root";
import { validateOrciaRouteSearch } from "./searchSchema";

export { LoginRouteComponent, LoginScreenView, type LoginScreenViewProps };

export const Route = createRoute({
  getParentRoute: () => rootRoute,
  path: "/login",
  validateSearch: validateOrciaRouteSearch,
  component: LoginRouteComponent,
});
