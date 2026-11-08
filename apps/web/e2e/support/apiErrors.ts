import type { Page } from "@playwright/test";

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
