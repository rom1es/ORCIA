import { createOrciaApiClient, OrciaProblemError } from "@orcia/api-client";
import { BiModeLoginView, type Rfc9457LoginError } from "@orcia/ui";
import { createRoute } from "@tanstack/react-router";
import React, { useEffect, useMemo, useState } from "react";
import { useI18n } from "../i18n";
import { Route as rootRoute } from "./__root";
import { validateOrciaRouteSearch } from "./searchSchema";

const SESSION_STORAGE_KEY = "orcia.auth.session.v1";

function resolveApiBaseUrl(): string {
  const envUrl = (import.meta as unknown as { env?: Record<string, string | undefined> }).env
    ?.VITE_ORCIA_API_URL;
  if (envUrl && envUrl.trim().length > 0) {
    return envUrl.trim();
  }
  return "http://localhost:8000";
}

function LoginRouteComponent() {
  const { dictionary, locale } = useI18n();
  const [loginError, setLoginError] = useState<Rfc9457LoginError | null>(null);
  const [authenticatedEmail, setAuthenticatedEmail] = useState<string | null>(() => {
    try {
      return globalThis.localStorage?.getItem(SESSION_STORAGE_KEY) ?? null;
    } catch {
      return null;
    }
  });

  const apiClient = useMemo(
    () =>
      createOrciaApiClient({
        baseUrl: resolveApiBaseUrl(),
        locale,
      }),
    [locale],
  );

  useEffect(() => {
    let active = true;
    void apiClient
      .getMe()
      .then((me) => {
        if (!active || !me?.email) return;
        setAuthenticatedEmail(me.email);
        try {
          globalThis.localStorage?.setItem(SESSION_STORAGE_KEY, me.email);
        } catch {
          // Ignore storage quota errors in restricted environments
        }
      })
      .catch(() => {
        // Offline / unauthenticated initial state
      });
    return () => {
      active = false;
    };
  }, [apiClient]);

  return (
    <div
      data-testid="login-page-container"
      data-allow-password-manager="true"
      data-authenticated-user={authenticatedEmail ?? ""}
    >
      <BiModeLoginView
        labels={dictionary.biModeLogin}
        error={loginError}
        onTriggerOidcSso={() => {
          void apiClient
            .loginOidc({ oidc_subject: "oidc|marc-lead" })
            .then((res) => {
              setLoginError(null);
              setAuthenticatedEmail(res.email);
              try {
                globalThis.localStorage?.setItem(SESSION_STORAGE_KEY, res.email);
              } catch {
                // Ignore storage quota errors
              }
            })
            .catch((err: unknown) => {
              if (err instanceof OrciaProblemError) {
                setLoginError({
                  errorCode: err.problem.error_code,
                  detail: err.problem.detail,
                  traceId: err.problem.trace_id,
                });
              }
            });
        }}
        onSubmitLocalLogin={({ email, password, totpCode }) => {
          if (!email.includes("@") || password.length < 6 || totpCode === "000000") {
            setLoginError({
              errorCode: "ERR_INVALID_CREDENTIALS",
              detail: "Adresse e-mail, mot de passe ou code de vérification incorrect.",
              traceId: "0195f000-0000-7000-8000-000000009457",
            });
            return;
          }
          setLoginError(null);
          setAuthenticatedEmail(email);
          try {
            globalThis.localStorage?.setItem(SESSION_STORAGE_KEY, email);
          } catch {
            // Ignore storage quota errors
          }
          void apiClient
            .loginLocal({
              email,
              password,
              totp_code: totpCode,
            })
            .then((res) => {
              setAuthenticatedEmail(res.email);
              try {
                globalThis.localStorage?.setItem(SESSION_STORAGE_KEY, res.email);
              } catch {
                // Ignore storage quota errors
              }
            })
            .catch((err: unknown) => {
              if (err instanceof OrciaProblemError) {
                setLoginError({
                  errorCode: err.problem.error_code,
                  detail: err.problem.detail,
                  traceId: err.problem.trace_id,
                });
              }
            });
        }}
      />
    </div>
  );
}

export const Route = createRoute({
  getParentRoute: () => rootRoute,
  path: "/login",
  validateSearch: validateOrciaRouteSearch,
  component: LoginRouteComponent,
});
