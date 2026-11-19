import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { test as base, expect, type Page, type TestInfo } from "@playwright/test";

const here = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(here, "../../../..");
const rawCampaignDir = process.env.ORCIA_E2E_CAMPAIGN_DIR?.trim();
const campaignDir = rawCampaignDir
  ? path.isAbsolute(rawCampaignDir)
    ? rawCampaignDir
    : path.resolve(repoRoot, rawCampaignDir)
  : path.join(repoRoot, "docs/implementation-artifacts/e2e-campaign-epic-22");
const screenshotsRoot = path.join(campaignDir, "screenshots");
const manifestPath = path.join(campaignDir, "manifest.jsonl");
const MAX_SCREENSHOT_BYTES = 440 * 1024;

const UJ_TOKEN_RE = /\bUJ-[1-9]\d?\b/g;
const CAP_TOKEN_RE = /\bCAP-\d+\b/g;

function slugify(raw: string, maxLength = 96): string {
  const normalized = raw
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
  return (normalized || "unnamed").slice(0, maxLength);
}

function extractHeaderTags(specFile: string): { uj: string[]; cap: string[] } {
  try {
    const head = fs.readFileSync(specFile, "utf8").split(/\r?\n/).slice(0, 40).join("\n");
    const extract = (tag: string, tokenRe: RegExp): string[] => {
      const tagRe = new RegExp(`@${tag}\\s+([^|\\n*]+)`, "g");
      const found = new Set<string>();
      for (const match of head.matchAll(tagRe)) {
        for (const token of (match[1] ?? "").match(tokenRe) ?? []) {
          found.add(token);
        }
      }
      return Array.from(found);
    };
    return {
      uj: extract("uj", UJ_TOKEN_RE),
      cap: extract("cap", CAP_TOKEN_RE),
    };
  } catch {
    return { uj: [], cap: [] };
  }
}

function removePriorStatusCaptures(specDir: string, prefix: string): void {
  try {
    for (const entry of fs.readdirSync(specDir)) {
      if (entry.startsWith(prefix) && entry.endsWith(".png")) {
        fs.unlinkSync(path.join(specDir, entry));
      }
    }
  } catch {
    // Nettoyage best-effort des captures précédentes
  }
}

async function ensureNonBlankPage(page: Page): Promise<void> {
  if (page.isClosed()) return;
  const currentUrl = page.url();
  if (currentUrl && currentUrl !== "about:blank") return;
  try {
    await page.goto("/cockpit", { waitUntil: "domcontentloaded", timeout: 8000 });
  } catch {
    try {
      await page.goto("/", { waitUntil: "domcontentloaded", timeout: 8000 });
    } catch {
      // Ne jamais masquer le résultat métier du test si le serveur est injoignable
    }
  }
}

async function captureFinalState(page: Page, testInfo: TestInfo): Promise<void> {
  const status = testInfo.status ?? "unknown";
  const specBase = path.basename(testInfo.file).replace(/\.spec\.[tj]s$/, "");
  const specSlug = slugify(specBase, 80);
  const projectSlug = slugify(testInfo.project.name || "default", 40);
  const testSlug = slugify(testInfo.title, 88);

  const specDir = path.join(screenshotsRoot, specSlug);
  fs.mkdirSync(specDir, { recursive: true });
  const prefix = `${projectSlug}--${testSlug}--`;
  removePriorStatusCaptures(specDir, prefix);

  const screenshotAbs = path.join(specDir, `${prefix}${status}.png`);
  let screenshotRel: string | null = null;
  let capturedUrl = "";

  try {
    await ensureNonBlankPage(page);
    if (!page.isClosed()) {
      capturedUrl = page.url();
      await page.screenshot({ path: screenshotAbs, fullPage: true, timeout: 8000 });
      if (fs.existsSync(screenshotAbs) && fs.statSync(screenshotAbs).size > MAX_SCREENSHOT_BYTES) {
        await page.screenshot({ path: screenshotAbs, fullPage: false, timeout: 8000 });
      }
      screenshotRel = path.relative(repoRoot, screenshotAbs).replace(/\\/g, "/");
      await testInfo.attach(`final-state-${status}`, {
        path: screenshotAbs,
        contentType: "image/png",
      });
    }
  } catch {
    // Capture best-effort : ne jamais masquer l'échec initial du test
  }

  const tags = extractHeaderTags(testInfo.file);
  const specRel = path.relative(repoRoot, testInfo.file).replace(/\\/g, "/");
  const manifestEntry = {
    spec: specRel,
    test_title: testInfo.title,
    project: testInfo.project.name,
    uj: tags.uj,
    cap: tags.cap,
    status,
    screenshot_path: screenshotRel,
    url: capturedUrl,
    duration_ms: testInfo.duration,
    timestamp: new Date().toISOString(),
    error: testInfo.error?.message ?? null,
  };

  fs.mkdirSync(campaignDir, { recursive: true });
  fs.appendFileSync(manifestPath, `${JSON.stringify(manifestEntry)}\n`, "utf8");
}

export const test = base.extend<{ _autoCaptureFinalState: void }>({
  _autoCaptureFinalState: [
    async ({ page }, use, testInfo) => {
      await use();
      await captureFinalState(page, testInfo);
    },
    { auto: true },
  ],
});

export { expect };
