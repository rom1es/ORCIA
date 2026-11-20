import { expect, type Page } from "@playwright/test";

const ZONE_TEST_IDS = [
  "four-zone-sidebar",
  "four-zone-top-header-bar",
  "accostage-progress-pill",
] as const;

const HELP_BOX_TEST_IDS = [
  "contextual-help-what-for-box",
  "contextual-help-steps-box",
  "contextual-help-real-example-box",
  "contextual-help-common-pitfalls-box",
] as const;

export async function assertCockpitSobrietyMaxThreeBlocks(page: Page): Promise<void> {
  const blocks = page.locator('[data-testid^="cockpit-block-"]');
  const count = await blocks.count();
  let visibleCount = 0;
  for (let i = 0; i < count; i += 1) {
    if (await blocks.nth(i).isVisible()) {
      visibleCount += 1;
    }
  }
  expect(
    visibleCount,
    `Sobriété Cockpit Direction C violée : ${visibleCount} blocs visibles (max 3 autorisés)`,
  ).toBeLessThanOrEqual(3);
}

export async function assertNoZoneHorizontalTruncation(
  page: Page,
  contextLabel: string,
): Promise<void> {
  const issues = await page.evaluate((zoneIds) => {
    const violations: string[] = [];
    for (const zoneId of zoneIds) {
      const zone =
        Array.from(document.querySelectorAll("[data-testid]")).find(
          (el) => el.getAttribute("data-testid") === zoneId,
        ) ?? null;
      if (!(zone instanceof HTMLElement)) continue;
      const zoneRect = zone.getBoundingClientRect();
      if (zoneRect.width <= 0 || zoneRect.height <= 0) continue;
      if (zone.scrollWidth > zone.clientWidth + 1) {
        violations.push(
          `${zoneId} overflow (${zone.scrollWidth} > ${zone.clientWidth})`,
        );
      }
      const children = zone.querySelectorAll("button, a, span, p");
      for (const el of children) {
        if (!(el instanceof HTMLElement)) continue;
        if (el.closest(".sr-only") !== null) continue;
        const rect = el.getBoundingClientRect();
        if (rect.width <= 0 || rect.height <= 0) continue;
        const style = window.getComputedStyle(el);
        if (
          rect.width <= 2 &&
          rect.height <= 2 &&
          style.position === "absolute" &&
          style.overflow === "hidden"
        ) {
          continue;
        }
        const isClipped =
          style.overflowX === "hidden" &&
          style.textOverflow !== "ellipsis" &&
          el.scrollWidth > el.clientWidth + 2;
        if (isClipped) {
          const text = (el.textContent ?? "").trim().slice(0, 40);
          violations.push(`${zoneId} child "${text}" clipped (${el.scrollWidth} > ${el.clientWidth})`);
        }
      }
    }
    return violations;
  }, [...ZONE_TEST_IDS]);

  expect(
    issues,
    `Troncature horizontale détectée (${contextLabel}) : ${issues.join("; ")}`,
  ).toEqual([]);
}

export async function assertSingleDesktopWorkspaceSelector(page: Page): Promise<void> {
  const viewport = page.viewportSize();
  if (viewport && viewport.width < 1024) return;

  const sidebarVisible = await page
    .getByTestId("sidebar-unified-scope-selector")
    .first()
    .isVisible()
    .catch(() => false);
  const topbarVisible = await page
    .getByTestId("topbar-fixed-workspace-selector")
    .first()
    .isVisible()
    .catch(() => false);

  const count = (sidebarVisible ? 1 : 0) + (topbarVisible ? 1 : 0);
  expect(
    count,
    `Doublon de sélecteur d'espace détecté sur Desktop (sidebar=${sidebarVisible}, topbar=${topbarVisible})`,
  ).toBeLessThanOrEqual(1);
}

export async function assertMaxOneDialogCloseOrCancelButton(page: Page): Promise<void> {
  const violations = await page.evaluate(() => {
    const dialogs = Array.from(document.querySelectorAll('[role="dialog"]')).filter(
      (el): el is HTMLElement => {
        if (!(el instanceof HTMLElement)) return false;
        const rect = el.getBoundingClientRect();
        return rect.width > 0 && rect.height > 0;
      },
    );
    const errors: string[] = [];
    for (const dialog of dialogs) {
      const dialogId = dialog.getAttribute("data-testid") ?? dialog.id ?? "dialog";
      const bg = window.getComputedStyle(dialog).backgroundColor;
      if (!bg || bg === "transparent" || bg === "rgba(0, 0, 0, 0)") {
        errors.push(`${dialogId} has transparent backgroundColor (${bg})`);
      }
      const buttons = Array.from(dialog.querySelectorAll("button")).filter((btn) => {
        const rect = btn.getBoundingClientRect();
        if (rect.width <= 0 || rect.height <= 0) return false;
        const testId = btn.getAttribute("data-testid") ?? "";
        const label = (btn.getAttribute("aria-label") ?? btn.textContent ?? "").trim();
        return (
          testId.endsWith("-close-btn") ||
          testId.endsWith("-cancel-btn") ||
          /^(fermer|annuler|terminer|close|cancel|×|✕)$/i.test(label)
        );
      });
      if (buttons.length > 1) {
        const names = buttons.map(
          (b) => b.getAttribute("data-testid") ?? (b.textContent ?? "").trim(),
        );
        errors.push(`${dialogId} has ${buttons.length} close/cancel buttons: [${names.join(", ")}]`);
      }
    }
    return errors;
  });

  expect(
    violations,
    `Modale avec boutons Fermer/Annuler en doublon : ${violations.join("; ")}`,
  ).toEqual([]);
}

export async function assertZeroBulletPlaceholders(
  page: Page,
  contextLabel = "page",
): Promise<void> {
  const count = await page.locator('input[placeholder*="•"]').count();
  expect(
    count,
    `Placeholder avec puces '•' détecté sur ${contextLabel}`,
  ).toBe(0);
}

export async function assertZone4ContextualHelpRoutesFidelity(page: Page): Promise<void> {
  const snapshots: string[] = [];
  for (const route of ["/cockpit", "/assistant", "/spaces"]) {
    await page.goto(route, { waitUntil: "domcontentloaded" });
    const helpColumn = page.getByTestId("four-zone-contextual-help-column");
    await expect(
      helpColumn,
      `Colonne d'aide contextuelle Zone 4 absente sur ${route}`,
    ).toBeVisible({ timeout: 10000 });
    for (const boxTestId of HELP_BOX_TEST_IDS) {
      await expect(
        helpColumn.getByTestId(boxTestId),
        `Bloc Zone 4 manquant (${boxTestId}) sur ${route}`,
      ).toBeVisible({ timeout: 8000 });
    }
    const text = (await helpColumn.innerText()).replace(/\s+/g, " ").trim();
    expect(text.length, `Contenu Zone 4 vide sur ${route}`).toBeGreaterThan(20);
    snapshots.push(text);
  }
  const uniqueSnapshots = new Set(snapshots);
  expect(
    uniqueSnapshots.size,
    "Zone 4 doit afficher un contenu contextuel distinct entre /cockpit, /assistant et /spaces",
  ).toBeGreaterThanOrEqual(3);
}
