import { expect, type Page } from "@playwright/test";

export interface AllowedApiStatusRule {
  readonly pathIncludes: string;
  readonly status: number;
}

/** Collecte les réponses `/api/*` en erreur serveur (5xx) pendant un parcours. */
export function watchApiServerErrors(page: Page): string[] {
  const errors: string[] = [];
  page.on("response", (res) => {
    if (res.url().includes("/api/") && res.status() >= 500) {
      errors.push(`${res.request().method()} ${res.url()} → ${res.status()}`);
    }
  });
  return errors;
}

/**
 * Collecte toute réponse `/api/*` HTTP >= 400 (4xx & 5xx) non explicitement attendue,
 * ainsi que toute exception JS non interceptée (`pageerror`).
 */
export function watchUnexpectedPageAndApiErrors(
  page: Page,
  options: { readonly allowedApiStatuses?: ReadonlyArray<AllowedApiStatusRule> } = {},
): string[] {
  const errors: string[] = [];
  const allowed = options.allowedApiStatuses ?? [];
  page.on("response", (res) => {
    const url = res.url();
    const status = res.status();
    if (!url.includes("/api/") || status < 400) {
      return;
    }
    const isAllowed = allowed.some((rule) => url.includes(rule.pathIncludes) && rule.status === status);
    if (!isAllowed) {
      errors.push(`HTTP ${status} ${res.request().method()} ${url}`);
    }
  });
  page.on("pageerror", (err) => {
    errors.push(`pageerror: ${err.message}`);
  });
  return errors;
}

/** Vérifie qu'aucune bannière d'erreur RFC 9457 / alerte UI n'est visible à l'ouverture d'un écran. */
export async function expectZeroVisibleErrorBanners(page: Page): Promise<void> {
  await expect(page.getByTestId("login-rfc9457-error")).toHaveCount(0);
  await expect(page.locator('[role="alert"][data-testid*="error"]')).toHaveCount(0);
}
