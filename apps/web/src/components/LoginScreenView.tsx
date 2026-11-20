import {
  createOrciaApiClient,
  OrciaProblemError,
  type AuthTokenResponse,
  type PublicAuthConfigResponse,
} from "@orcia/api-client";
import {
  BiModeLoginView,
  type LoginTwoFactorStepState,
  type Rfc9457LoginError,
  type UiLoginViewMode,
} from "@orcia/ui";
import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useI18n } from "../i18n";
import { resolveWebApiBaseUrl, useAuthSessionStore } from "../stores/authSessionStore";
import { ignoreBenignStorageError } from "../utils/benignBrowserError";
import { useOrciaNavigation } from "./navigationAdapter";
import { useOptionalPlatformSetup } from "./platformSetupStore";
import {
  readStorageItem,
  syncBrowserBootEpoch,
  writeStorageItem,
} from "./platformSetupStorageHelpers";

const SESSION_STORAGE_KEY = "orcia.auth.session.v1";

export interface LoginScreenViewProps {
  readonly onAuthenticated?: () => void;
}

function mapTwoFactorStepFromResponse(res: AuthTokenResponse): LoginTwoFactorStepState | null {
  if (!res.requires_two_factor || !res.challenge_token || !res.challenge_kind) {
    return null;
  }
  return {
    challengeToken: res.challenge_token,
    challengeKind: res.challenge_kind,
    maskedDestination: res.masked_destination ?? null,
    totpProvisioningUri: res.totp_provisioning_uri ?? null,
    totpManualKey: res.totp_manual_key ?? null,
    expiresInSeconds: res.expires_in_seconds,
  };
}

export function LoginScreenView({ onAuthenticated }: LoginScreenViewProps = {}) {
  const { dictionary, locale } = useI18n();
  const setup = useOptionalPlatformSetup();
  const isDay0Unconfigured = setup !== null && setup.platformAdmin === null;
  const { navigateTo } = useOrciaNavigation();
  const loginWithSession = useAuthSessionStore((s) => s.loginWithSession);
  const resetAuthSession = useAuthSessionStore((s) => s.resetAuthSession);
  const [publicConfig, setPublicConfig] = useState<PublicAuthConfigResponse | null>(null);
  const [loginError, setLoginError] = useState<Rfc9457LoginError | null>(null);
  const [twoFactorStep, setTwoFactorStep] = useState<LoginTwoFactorStepState | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const oidcCallbackHandledRef = useRef(false);
  const [authenticatedEmail, setAuthenticatedEmail] = useState<string | null>(() =>
    readStorageItem(SESSION_STORAGE_KEY),
  );

  const apiClient = useMemo(
    () =>
      createOrciaApiClient({
        baseUrl: resolveWebApiBaseUrl(),
        locale,
      }),
    [locale],
  );

  const toProblemError = useCallback(
    (err: unknown): Rfc9457LoginError => {
      if (err instanceof OrciaProblemError) {
        return {
          errorCode: err.problem.error_code,
          detail: err.problem.detail,
          traceId: err.problem.trace_id,
        };
      }
      return {
        errorCode: "ERR_AUTH_UNAVAILABLE",
        detail:
          err instanceof Error && err.message
            ? err.message
            : dictionary.biModeLogin.errorBannerTitle,
      };
    },
    [dictionary.biModeLogin.errorBannerTitle],
  );

  const completeAuthenticatedSession = useCallback(
    (res: AuthTokenResponse) => {
      setLoginError(null);
      setTwoFactorStep(null);
      setAuthenticatedEmail(res.email);
      loginWithSession({
        access_token: res.access_token,
        email: res.email,
        display_name: res.display_name,
        platform_role: res.platform_role,
        roles: res.roles,
        must_change_password: res.must_change_password,
      });
      writeStorageItem(SESSION_STORAGE_KEY, res.email);
      if (onAuthenticated) {
        onAuthenticated();
      }
      navigateTo("/");
    },
    [loginWithSession, navigateTo, onAuthenticated],
  );

  useEffect(() => {
    let cancelled = false;
    void apiClient
      .getPublicAuthConfig()
      .then((cfg) => {
        if (cancelled) return;
        if (syncBrowserBootEpoch(cfg.boot_epoch)) {
          resetAuthSession();
          setAuthenticatedEmail(null);
        }
        setPublicConfig(cfg);
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        // Pre-flight config failure must never render a user login-attempt error banner on mount.
        console.warn("[orcia/auth] public-config bootstrap fallback to LOCAL mode", err);
      });
    return () => {
      cancelled = true;
    };
  }, [apiClient, resetAuthSession]);

  useEffect(() => {
    if (oidcCallbackHandledRef.current || typeof window === "undefined") {
      return;
    }
    const params = new URLSearchParams(window.location.search);
    const code = params.get("code")?.trim();
    const state = params.get("state")?.trim();
    if (!code || !state) {
      return;
    }
    oidcCallbackHandledRef.current = true;
    setIsSubmitting(true);
    setLoginError(null);
    void apiClient
      .exchangeOidcCallback({ code, state })
      .then((res) => {
        try {
          const cleanedUrl = new URL(window.location.href);
          cleanedUrl.searchParams.delete("code");
          cleanedUrl.searchParams.delete("state");
          cleanedUrl.searchParams.delete("session_state");
          window.history.replaceState({}, "", cleanedUrl.toString());
        } catch (err: unknown) {
          ignoreBenignStorageError("login.history_replace", err);
        }
        completeAuthenticatedSession(res);
      })
      .catch((err: unknown) => {
        setLoginError(toProblemError(err));
      })
      .finally(() => {
        setIsSubmitting(false);
      });
  }, [apiClient, completeAuthenticatedSession, toProblemError]);

  const handleAuthResponse = useCallback(
    (res: AuthTokenResponse) => {
      const challenge = mapTwoFactorStepFromResponse(res);
      if (challenge) {
        setLoginError(null);
        setTwoFactorStep(challenge);
        return;
      }
      completeAuthenticatedSession(res);
    },
    [completeAuthenticatedSession],
  );

  const authMode: UiLoginViewMode = publicConfig?.auth_mode === "SSO" ? "SSO" : "LOCAL";

  if (isDay0Unconfigured) {
    return (
      <div
        data-testid="login-page-container"
        data-allow-password-manager="true"
        data-auth-mode={authMode}
        data-authenticated-user=""
        className="flex min-h-[400px] items-center justify-center p-8 text-center"
      >
        <div className="space-y-2" style={{ color: "var(--color-text-secondary)" }}>
          <p className="text-sm">
            {locale === "en"
              ? "Platform initialization in progress..."
              : "Initialisation de la plateforme en cours..."}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div
      data-testid="login-page-container"
      data-allow-password-manager="true"
      data-auth-mode={authMode}
      data-authenticated-user={authenticatedEmail ?? ""}
      className="flex h-full min-h-0 w-full items-center justify-center overflow-y-auto p-6"
    >
      <BiModeLoginView
        labels={dictionary.biModeLogin}
        authMode={authMode}
        showInlineTotpField={false}
        ssoButtonLabel={publicConfig?.sso_button_label ?? undefined}
        oidcConfigured={publicConfig?.oidc_enabled ?? false}
        isSubmitting={isSubmitting}
        error={loginError}
        twoFactorStep={twoFactorStep}
        onTriggerOidcSso={() => {
          setIsSubmitting(true);
          setLoginError(null);
          void apiClient
            .getOidcAuthorizeUrl()
            .then((res) => {
              if (typeof window !== "undefined" && window.location?.assign) {
                window.location.assign(res.authorize_url);
              }
            })
            .catch((err: unknown) => {
              setLoginError(toProblemError(err));
            })
            .finally(() => {
              setIsSubmitting(false);
            });
        }}
        onSubmitLocalLogin={({ email, password }) => {
          if (!email.includes("@") || password.length < 6) {
            setLoginError({
              errorCode: "ERR_INVALID_CREDENTIALS",
              detail: dictionary.biModeLogin.errorBannerTitle,
            });
            return;
          }
          setIsSubmitting(true);
          setLoginError(null);
          void apiClient
            .loginLocal({
              email,
              password,
            })
            .then((res) => {
              handleAuthResponse(res);
            })
            .catch((err: unknown) => {
              setLoginError(toProblemError(err));
            })
            .finally(() => {
              setIsSubmitting(false);
            });
        }}
        onSubmitTwoFactor={async (code) => {
          if (!twoFactorStep) return;
          setIsSubmitting(true);
          setLoginError(null);
          try {
            const res = await apiClient.verifyLoginTwoFactor({
              challenge_token: twoFactorStep.challengeToken,
              code,
            });
            completeAuthenticatedSession(res);
          } catch (err: unknown) {
            setLoginError(toProblemError(err));
          } finally {
            setIsSubmitting(false);
          }
        }}
        onResendTwoFactor={async () => {
          if (!twoFactorStep) return;
          setIsSubmitting(true);
          setLoginError(null);
          try {
            const res = await apiClient.resendLoginTwoFactor({
              challenge_token: twoFactorStep.challengeToken,
            });
            setTwoFactorStep((prev) =>
              prev
                ? {
                    ...prev,
                    maskedDestination: res.masked_destination ?? prev.maskedDestination,
                    expiresInSeconds: res.expires_in_seconds,
                  }
                : null,
            );
          } catch (err: unknown) {
            setLoginError(toProblemError(err));
          } finally {
            setIsSubmitting(false);
          }
        }}
        onCancelTwoFactor={() => {
          setTwoFactorStep(null);
          setLoginError(null);
        }}
      />
    </div>
  );
}

export const LoginRouteComponent = LoginScreenView;
