import { createOrciaApiClient } from "@orcia/api-client";
import { ClientCodedError } from "../lib/clientErrorCodes";

export function resolveWebApiBaseUrl(): string {
  const meta = import.meta as unknown as { env?: Record<string, string | undefined> };
  const envUrl = meta?.env?.VITE_ORCIA_API_BASE_URL ?? meta?.env?.VITE_ORCIA_API_URL;
  if (envUrl && envUrl.trim().length > 0) {
    const trimmed = envUrl.trim().replace(/\/+$/, "");
    if (trimmed === "/api" || trimmed.endsWith("/api")) {
      return trimmed.slice(0, -4);
    }
    return trimmed;
  }
  return "";
}

export interface HydratedSessionPayload {
  readonly accessToken: string;
  readonly roles: readonly string[];
  readonly activeHat: string;
  readonly email: string | null;
  readonly displayName: string | null;
  readonly mustChangePassword: boolean;
}

export async function executeSessionHydrationWithTimeout(
  timeoutMs = 5000,
): Promise<HydratedSessionPayload | null> {
  let timeoutId: ReturnType<typeof setTimeout> | undefined;
  const timeoutPromise = new Promise<never>((_, reject) => {
    timeoutId = setTimeout(() => {
      reject(
        new ClientCodedError("ERR_CLIENT_AUTH_HYDRATION_TIMEOUT", {
          seconds: Math.round(timeoutMs / 1000),
        }),
      );
    }, timeoutMs);
  });

  try {
    const hydrationWork = (async (): Promise<HydratedSessionPayload | null> => {
      const baseUrl = resolveWebApiBaseUrl();
      const client = createOrciaApiClient({ baseUrl });
      const bootstrap = await client.getSessionBootstrap();
      const tokenRes = bootstrap?.authenticated ? bootstrap.session : null;
      if (!tokenRes || !tokenRes.access_token) {
        return null;
      }

      const authedClient = createOrciaApiClient({
        baseUrl,
        accessToken: tokenRes.access_token,
      });
      let me: Awaited<ReturnType<typeof authedClient.getMe>> | null = null;
      try {
        me = await authedClient.getMe();
      } catch (err: unknown) {
        console.warn(
          "[orcia:auth.hydrate_getMe]",
          err instanceof Error ? err.message : String(err),
        );
      }

      const roles =
        tokenRes.roles && tokenRes.roles.length > 0
          ? tokenRes.roles
          : me?.roles && me.roles.length > 0
            ? me.roles
            : [tokenRes.platform_role];

      return {
        accessToken: tokenRes.access_token,
        roles,
        activeHat: roles[0] || "CONTRIBUTOR",
        email: tokenRes.email || me?.email || null,
        displayName: tokenRes.display_name || me?.display_name || null,
        mustChangePassword: Boolean(tokenRes.must_change_password || me?.must_change_password),
      };
    })();

    return await Promise.race([hydrationWork, timeoutPromise]);
  } finally {
    if (timeoutId !== undefined) {
      clearTimeout(timeoutId);
    }
  }
}
