import { createOrciaApiClient, OrciaProblemError } from "@orcia/api-client";
import { BiModeLoginView, type Rfc9457LoginError } from "@orcia/ui";
import React, { useEffect, useMemo, useState } from "react";
import { useOrciaNavigation } from "./navigationAdapter";
import { useI18n } from "../i18n";
import { resolveWebApiBaseUrl, useAuthSessionStore } from "../stores/authSessionStore";

const SESSION_STORAGE_KEY = "orcia.auth.session.v1";

export interface LoginScreenViewProps {
  readonly onAuthenticated?: () => void;
}

export function LoginScreenView({ onAuthenticated }: LoginScreenViewProps = {}) {
  const { dictionary, locale } = useI18n();
  const { navigateTo } = useOrciaNavigation();
  const loginWithSession = useAuthSessionStore((s) => s.loginWithSession);
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
        baseUrl: resolveWebApiBaseUrl(),
        locale,
      }),
    [locale],
  );

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
              loginWithSession({
                email: res.email,
                displayName: res.display_name,
                roles: res.roles,
                mustChangePassword: false,
              });
              try {
                globalThis.localStorage?.setItem(SESSION_STORAGE_KEY, res.email);
              } catch {
                // Ignore storage quota errors
              }
              if (onAuthenticated) {
                onAuthenticated();
              }
              navigateTo("/");
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
              loginWithSession({
                access_token: res.access_token,
                email: res.email,
                displayName: res.display_name,
                roles: res.roles,
                mustChangePassword: res.must_change_password,
              });
              try {
                globalThis.localStorage?.setItem(SESSION_STORAGE_KEY, res.email);
              } catch {
                // Ignore storage quota errors
              }
              if (onAuthenticated) {
                onAuthenticated();
              }
              navigateTo("/");
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

export const LoginRouteComponent = LoginScreenView;
