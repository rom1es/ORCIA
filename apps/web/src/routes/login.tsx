import { BiModeLoginView, type Rfc9457LoginError } from "@orcia/ui";
import { createRoute } from "@tanstack/react-router";
import React, { useState } from "react";
import { useI18n } from "../i18n";
import { Route as rootRoute } from "./__root";
import { validateOrciaRouteSearch } from "./searchSchema";

function LoginRouteComponent() {
  const { dictionary } = useI18n();
  const [loginError, setLoginError] = useState<Rfc9457LoginError | null>(null);

  return (
    <BiModeLoginView
      labels={dictionary.biModeLogin}
      error={loginError}
      onSubmitLocalLogin={({ email, password, totpCode }) => {
        if (!email.includes("@") || password.length < 6 || totpCode === "000000") {
          setLoginError({
            errorCode: "ERR_INVALID_CREDENTIALS",
            detail: "Identifiants locaux ou code TOTP 2FA invalides.",
            traceId: "0195f000-0000-7000-8000-000000009457",
          });
        } else {
          setLoginError(null);
        }
      }}
    />
  );
}

export const Route = createRoute({
  getParentRoute: () => rootRoute,
  path: "/login",
  validateSearch: validateOrciaRouteSearch,
  component: LoginRouteComponent,
});
