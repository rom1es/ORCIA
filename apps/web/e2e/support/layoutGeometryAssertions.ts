import { expect, type Page } from "@playwright/test";

export interface HorizontalOverflowReport {
  readonly scrollWidth: number;
  readonly innerWidth: number;
  readonly clippedControls: ReadonlyArray<{
    readonly tag: string;
    readonly testId: string | null;
    readonly text: string;
    readonly right: number;
    readonly left: number;
  }>;
}

/**
 * Vérifie l'absence de débordement horizontal global (`scrollWidth <= innerWidth + 1`)
 * ET l'absence de rognage des contrôles interactifs visibles (`rect.right <= window.innerWidth + 1`).
 */
export async function assertNoHorizontalOverflow(
  page: Page,
  contextLabel = "page courante",
): Promise<void> {
  const report = await page.evaluate<HorizontalOverflowReport>(() => {
    const innerWidth = window.innerWidth;
    const innerHeight = window.innerHeight;
    const scrollWidth = document.documentElement.scrollWidth;
    const clippedControls: Array<{
      tag: string;
      testId: string | null;
      text: string;
      right: number;
      left: number;
    }> = [];

    const hasScrollableXAncestor = (el: HTMLElement): boolean => {
      let cur: HTMLElement | null = el.parentElement;
      while (cur && cur !== document.body && cur !== document.documentElement) {
        const style = window.getComputedStyle(cur);
        if (
          (style.overflowX === "auto" || style.overflowX === "scroll") &&
          cur.scrollWidth > cur.clientWidth + 2
        ) {
          return true;
        }
        cur = cur.parentElement;
      }
      return false;
    };

    const controls = document.querySelectorAll<HTMLElement>(
      "button, a[href], input, select, textarea, [role='tab'], [role='button']",
    );
    for (const el of controls) {
      const style = window.getComputedStyle(el);
      if (style.display === "none" || style.visibility === "hidden" || style.opacity === "0") {
        continue;
      }
      const rect = el.getBoundingClientRect();
      if (rect.width <= 0 || rect.height <= 0) continue;
      if (rect.bottom < 0 || rect.top > innerHeight) continue;
      if (hasScrollableXAncestor(el)) continue;

      if (rect.right > innerWidth + 1 || rect.left < -1) {
        clippedControls.push({
          tag: el.tagName.toLowerCase(),
          testId: el.getAttribute("data-testid"),
          text: (el.innerText || el.getAttribute("aria-label") || "").trim().slice(0, 48),
          right: Math.round(rect.right),
          left: Math.round(rect.left),
        });
      }
    }

    return { scrollWidth, innerWidth, clippedControls };
  });

  expect(
    report.scrollWidth,
    `Débordement horizontal global sur ${contextLabel} (${report.scrollWidth}px > ${report.innerWidth}px)`,
  ).toBeLessThanOrEqual(report.innerWidth + 1);
  expect(
    report.clippedControls,
    `Contrôles rognés hors viewport sur ${contextLabel}: ${JSON.stringify(report.clippedControls)}`,
  ).toEqual([]);
}

/**
 * Vérifie via `document.elementFromPoint(cx, cy)` au centre du bouton `[data-testid="${testId}"]`
 * dans une modale ouverte qu'aucune colonne sticky (Zone 4) ni calque tiers ne recouvre l'action.
 */
export async function assertModalActionClickableViaElementFromPoint(
  page: Page,
  testId: string,
): Promise<void> {
  const locator = page.getByTestId(testId);
  await expect(locator, `Action modale '${testId}' doit être visible`).toBeVisible({
    timeout: 15000,
  });
  await locator.scrollIntoViewIfNeeded();

  const hit = await locator.evaluate((target) => {
    const rect = target.getBoundingClientRect();
    const cx = rect.left + rect.width / 2;
    const cy = rect.top + rect.height / 2;
    const topEl = document.elementFromPoint(cx, cy);
    const sameOrDescendant =
      topEl !== null && (topEl === target || target.contains(topEl) || topEl.contains(target));
    return {
      cx: Math.round(cx),
      cy: Math.round(cy),
      width: Math.round(rect.width),
      height: Math.round(rect.height),
      sameOrDescendant,
      topTag: topEl ? topEl.tagName.toLowerCase() : null,
      topTestId: topEl ? topEl.getAttribute("data-testid") : null,
      topClass: topEl ? topEl.className : null,
    };
  });

  expect(hit.width, `Largeur nulle pour '${testId}'`).toBeGreaterThan(0);
  expect(hit.height, `Hauteur nulle pour '${testId}'`).toBeGreaterThan(0);
  expect(
    hit.sameOrDescendant,
    `Le bouton '${testId}' est recouvert à (${hit.cx}, ${hit.cy}) par ${hit.topTag} (data-testid=${hit.topTestId}, class=${String(hit.topClass)})`,
  ).toBe(true);
}

export interface CapturedHttpError {
  readonly method: string;
  readonly url: string;
  readonly status: number;
}

export interface ErrorAlertProbe {
  getHttpErrors(): ReadonlyArray<CapturedHttpError>;
  assertNoUnexpectedHttpErrors(
    allowedPathIncludes?: ReadonlyArray<string>,
    allowedUnauth401Paths?: ReadonlyArray<string>,
  ): void;
  assertAlertVisible(): Promise<void>;
}

/**
 * Attache une sonde réseau sur `/api/*` pour tracer toute réponse HTTP `>= 400`
 * et vérifier la présence d'une bannière `[role="alert"]` lorsqu'une erreur survient.
 */
export function attachErrorAlertProbe(page: Page): ErrorAlertProbe {
  const errors: CapturedHttpError[] = [];
  page.on("response", (res) => {
    const url = res.url();
    const status = res.status();
    if (url.includes("/api/") && status >= 400) {
      errors.push({ method: res.request().method(), url, status });
    }
  });

  return {
    getHttpErrors: () => [...errors],
    assertNoUnexpectedHttpErrors: (
      allowedPathIncludes = [],
      allowedUnauth401Paths = [],
    ) => {
      const unexpected = errors.filter((err) => {
        if (allowedPathIncludes.some((allowed) => err.url.includes(allowed))) {
          return false;
        }
        if (
          err.status === 401 &&
          allowedUnauth401Paths.some((allowed) => err.url.includes(allowed))
        ) {
          return false;
        }
        return true;
      });
      expect(
        unexpected,
        `Réponses HTTP >= 400 inattendues: ${JSON.stringify(unexpected)}`,
      ).toEqual([]);
    },
    assertAlertVisible: async () => {
      const alert = page.locator('[role="alert"]').first();
      await expect(alert, "Une bannière [role='alert'] doit être visible après erreur HTTP >= 400").toBeVisible({
        timeout: 10000,
      });
    },
  };
}

/**
 * Exécute une action déclenchant une erreur HTTP `>= 400` attendue et vérifie
 * que l'UI affiche immédiatement un message d'alerte accessible (`[role="alert"]`)
 * sans avaler l'erreur silencieusement.
 */
export async function assertVisibleErrorBannerOnHttpError(
  page: Page,
  action: () => Promise<unknown>,
  options: {
    readonly urlIncludes?: string;
    readonly expectedStatus?: number;
    readonly alertSelector?: string;
  } = {},
): Promise<void> {
  const [response] = await Promise.all([
    page.waitForResponse(
      (res) =>
        res.url().includes(options.urlIncludes ?? "/api/") &&
        (options.expectedStatus !== undefined
          ? res.status() === options.expectedStatus
          : res.status() >= 400),
      { timeout: 15000 },
    ),
    action(),
  ]);

  expect(response.status()).toBeGreaterThanOrEqual(400);
  const alertLocator = page.locator(options.alertSelector ?? '[role="alert"]').first();
  await expect(
    alertLocator,
    `Aucun [role="alert"] visible après HTTP ${response.status()} sur ${response.url()}`,
  ).toBeVisible({ timeout: 10000 });
  const text = (await alertLocator.innerText()).trim();
  expect(text.length, "La bannière [role='alert'] ne doit pas être vide").toBeGreaterThan(0);
}

/**
 * Vérifie sur Desktop (>= 768px) le verrouillage strict du viewport sans scroll vertical externe
 * ni bande vide `#EAF2FB` sous le shell (`USER24-BUG-1`, `UX23-14`, `UX23-16`).
 */
export async function assertNoDesktopVerticalPageOverflow(
  page: Page,
  contextLabel = "desktop shell",
): Promise<void> {
  const viewport = page.viewportSize();
  if (viewport && viewport.width < 768) {
    return;
  }

  const report = await page.evaluate(() => {
    window.scrollTo(0, 99999);
    const scrollYAfterAttempt = window.scrollY;
    window.scrollTo(0, 0);

    const innerHeight = window.innerHeight;
    const docScrollHeight = document.documentElement.scrollHeight;
    const bodyScrollHeight = document.body.scrollHeight;
    const rootEl = document.getElementById("root");
    const rootScrollHeight = rootEl ? rootEl.scrollHeight : null;

    const rectOf = (testId: string) => {
      const el = document.querySelector(`[data-testid="${testId}"]`);
      if (!(el instanceof HTMLElement)) return null;
      const r = el.getBoundingClientRect();
      return {
        top: Math.round(r.top),
        bottom: Math.round(r.bottom),
        height: Math.round(r.height),
      };
    };

    return {
      innerHeight,
      docScrollHeight,
      bodyScrollHeight,
      rootScrollHeight,
      scrollYAfterAttempt,
      shell: rectOf("four-zone-direction-c-shell"),
      topHeader: rectOf("four-zone-top-header-bar"),
      sidebar: rectOf("four-zone-sidebar"),
      workspace: rectOf("four-zone-central-workspace"),
      helpColumn: rectOf("four-zone-contextual-help-column"),
    };
  });

  expect(
    report.docScrollHeight,
    `Scroll vertical externe détecté sur ${contextLabel} (scrollHeight=${report.docScrollHeight} > innerHeight=${report.innerHeight}, body=${report.bodyScrollHeight}, root=${report.rootScrollHeight})`,
  ).toBeLessThanOrEqual(report.innerHeight + 1);
  expect(
    report.scrollYAfterAttempt,
    `window.scrollTo(0, 99999) a défilé la page sur ${contextLabel} (scrollY=${report.scrollYAfterAttempt})`,
  ).toBe(0);

  expect(report.topHeader, `four-zone-top-header-bar manquant sur ${contextLabel}`).not.toBeNull();
  expect(report.topHeader!.top, `top-header-bar top !== 0 sur ${contextLabel}`).toBe(0);

  expect(report.shell, `four-zone-direction-c-shell manquant sur ${contextLabel}`).not.toBeNull();
  expect(report.shell!.bottom).toBeLessThanOrEqual(report.innerHeight + 1);
  expect(
    Math.abs(report.shell!.bottom - report.innerHeight),
    `Bande vide sous four-zone-direction-c-shell sur ${contextLabel} (shell.bottom=${report.shell!.bottom}, innerHeight=${report.innerHeight})`,
  ).toBeLessThanOrEqual(1);

  if (report.sidebar) {
    expect(report.sidebar.bottom).toBeLessThanOrEqual(report.innerHeight + 1);
  }
  if (report.workspace) {
    expect(report.workspace.bottom).toBeLessThanOrEqual(report.innerHeight + 1);
  }
  if (report.helpColumn) {
    expect(report.helpColumn.bottom).toBeLessThanOrEqual(report.innerHeight + 1);
  }
}

export {
  assertCockpitSobrietyMaxThreeBlocks,
  assertMaxOneDialogCloseOrCancelButton,
  assertNoZoneHorizontalTruncation,
  assertSingleDesktopWorkspaceSelector,
  assertZeroBulletPlaceholders,
  assertZone4ContextualHelpRoutesFidelity,
} from "./directionCSobrietyAssertions";
