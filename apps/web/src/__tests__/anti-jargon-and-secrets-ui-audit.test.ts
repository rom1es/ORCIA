import fs from "node:fs";
import path from "node:path";
import ts from "typescript";
import { describe, expect, it } from "vitest";

const REPO_ROOT = path.resolve(__dirname, "../../../..");

const STRUCTURAL_JARGON_REGEXES: ReadonlyArray<{
  readonly name: string;
  readonly re: RegExp;
}> = [
  { name: "HTTP_4XX_5XX", re: /\bHTTP\s+[45]\d\d\b/ },
  { name: "AT_SEMVER", re: /@\d+\.\d+\.\d+/ },
  { name: "UPPER_ARROW_CHAIN", re: /\b[A-Z]{3,}\s*→\s*[A-Z]{3,}\b/ },
  { name: "ESC_SHORTCUT", re: /\(Esc(?:ape)?\)/i },
  { name: "SCREAMING_SNAKE_3SEG", re: /\b[A-Z]{2,}(?:_[A-Z0-9]{2,}){2,}\b/ },
];

const FORBIDDEN_UI_TERMS: readonly string[] = [
  "SYNTHESIS_READY",
  "OAUTH2_PASSTHROUGH",
  "PAUSE_AND_ESCALATE",
  "OPT_A_SPOT_15M",
  "OPT_B_LOCK_48H",
  "DeclarativePackLoader",
  "orcia-connectors",
  "WritePreviewCard",
  "Tier cognitif",
  "Anti-Prompt Injection",
  "1024-dim RAG",
  "AES-256-GCM",
  "LOCK TABLE users IN EXCLUSIVE MODE",
  "Chef1",
  "aqwZSX",
  "[LAYER_5_",
  "[STALE_WARNING]",
  "ORCIA_BOOTSTRAP_TOKEN",
  "docs/site-catalog/index.html",
  "`@`",
  "L4 → L1",
];

function collectFiles(dir: string, extensions: readonly string[]): string[] {
  if (!fs.existsSync(dir)) return [];
  const results: string[] = [];
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    if (
      entry.name === "node_modules" ||
      entry.name === "dist" ||
      entry.name === "__tests__" ||
      entry.name === "generated"
    ) {
      continue;
    }
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      results.push(...collectFiles(full, extensions));
    } else if (
      entry.isFile() &&
      !entry.name.includes(".test.") &&
      extensions.some((ext) => entry.name.endsWith(ext))
    ) {
      results.push(full);
    }
  }
  return results;
}

function isTechnicalTypeOrSanitizerLine(line: string, term: string): boolean {
  const trimmed = line.trim();
  if (trimmed.startsWith("import ") || trimmed.startsWith("export type ")) return true;
  if (trimmed.startsWith("//") || trimmed.startsWith("*")) return true;
  // TypeScript union members or type annotations
  if (new RegExp(`^\\|\\s*["']${escapeRegExp(term)}["']`).test(trimmed)) return true;
  if (new RegExp(`[:<]\\s*["']${escapeRegExp(term)}["']`).test(trimmed)) return true;
  // Sanitization .replace(...) patterns that explicitly strip internal enums
  if (trimmed.includes(".replace(") && trimmed.includes(term)) return true;
  // HTML option values or equality comparisons on internal enum codes
  if (new RegExp(`value\\s*=\\s*["']${escapeRegExp(term)}["']`).test(trimmed)) return true;
  if (new RegExp(`(?:===|!==|case)\\s*["']${escapeRegExp(term)}["']`).test(trimmed)) return true;
  // Internal TypeScript component/interface identifier (e.g. TraceWritePreviewCardProps)
  if (term === "WritePreviewCard" && /\bTraceWritePreviewCard(?:Props)?\b/.test(trimmed)) {
    return true;
  }
  return false;
}

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function scanForbiddenTermsInLines(
  rel: string,
  content: string,
  allowTechnicalTypeLines: boolean,
): string[] {
  const violations: string[] = [];
  content.split("\n").forEach((line, idx) => {
    for (const term of FORBIDDEN_UI_TERMS) {
      if (line.includes(term) && (!allowTechnicalTypeLines || !isTechnicalTypeOrSanitizerLine(line, term))) {
        violations.push(`${rel}:${idx + 1} [${term}] -> ${line.trim()}`);
      }
    }
  });
  return violations;
}

function scanStructuralJargonInMarkdown(rel: string, content: string): string[] {
  const violations: string[] = [];
  content.split("\n").forEach((line, idx) => {
    for (const { name, re } of STRUCTURAL_JARGON_REGEXES) {
      if (re.test(line)) violations.push(`${rel}:${idx + 1} [${name}] -> ${line.trim()}`);
    }
  });
  return violations;
}

const UI_VISIBLE_ATTRS = new Set([
  "label",
  "title",
  "placeholder",
  "aria-label",
  "description",
  "reason",
  "closeLabel",
  "emptyMessage",
  "helperText",
]);

function scanStructuralJargonInTsSource(rel: string, src: string, isTsx: boolean): string[] {
  const violations: string[] = [];
  const isStrictUiCopyFile =
    rel.includes("i18n/locales/") || /_contextualHelpSections(?:En)?\.ts$/.test(rel);
  const sf = ts.createSourceFile(
    rel,
    src,
    ts.ScriptTarget.Latest,
    true,
    isTsx ? ts.ScriptKind.TSX : ts.ScriptKind.TS,
  );
  const visit = (node: ts.Node) => {
    if (
      ts.isStringLiteral(node) ||
      ts.isNoSubstitutionTemplateLiteral(node) ||
      ts.isJsxText(node) ||
      ts.isTemplateHead(node) ||
      ts.isTemplateMiddle(node) ||
      ts.isTemplateTail(node)
    ) {
      const parent = node.parent;
      const isJsxAttr = ts.isJsxAttribute(parent) && ts.isIdentifier(parent.name);
      const attrName = isJsxAttr ? parent.name.text : "";
      const isKeyOrType =
        ts.isImportDeclaration(parent) ||
        (ts.isPropertyAssignment(parent) && parent.name === node) ||
        ts.isLiteralTypeNode(parent) ||
        ts.isBinaryExpression(parent) ||
        ts.isCaseClause(parent) ||
        attrName === "data-testid";
      const isVisibleTextContext =
        isStrictUiCopyFile || ts.isJsxText(node) || UI_VISIBLE_ATTRS.has(attrName);
      const isPureCodeEnumDiscriminant =
        !isVisibleTextContext && /^[A-Z][A-Z0-9_]+$/.test(node.text.trim());
      if (!isKeyOrType) {
        const line = sf.getLineAndCharacterOfPosition(node.getStart(sf)).line + 1;
        for (const { name, re } of STRUCTURAL_JARGON_REGEXES) {
          if (name === "SCREAMING_SNAKE_3SEG" && isPureCodeEnumDiscriminant) {
            continue;
          }
          if (re.test(node.text)) {
            violations.push(`${rel}:${line} [${name}] -> ${JSON.stringify(node.text)}`);
          }
        }
        if (/\bContextualHelp(?:SharedBlocks|SectionsAndFooter)\.tsx$/.test(rel)) {
          if (node.text.includes("@") || node.text.includes("→")) {
            violations.push(`${rel}:${line} [HELP_META_FORMAT] -> ${JSON.stringify(node.text)}`);
          }
        }
      }
    }
    ts.forEachChild(node, visit);
  };
  visit(sf);
  return violations;
}

describe("CI Guardrail — Zero Technical Jargon, Internal Enums, or Secrets in Visible UI & Help", () => {
  it("forbids all banned jargon and secret tokens across i18n dictionaries, contextual help, and markdown help docs", () => {
    const targetFiles: string[] = [
      ...collectFiles(path.join(REPO_ROOT, "apps/web/src/i18n/locales"), [".ts"]),
      path.join(REPO_ROOT, "apps/web/src/components/_contextualHelpSections.ts"),
      path.join(REPO_ROOT, "apps/web/src/components/_contextualHelpSectionsEn.ts"),
      ...collectFiles(path.join(REPO_ROOT, "docs/help"), [".md"]),
      ...collectFiles(path.join(REPO_ROOT, "packs"), [".md"]).filter((p) =>
        p.includes(`${path.sep}help${path.sep}`),
      ),
    ];

    expect(targetFiles.length).toBeGreaterThan(5);

    const violations: string[] = [];
    for (const filePath of targetFiles) {
      const content = fs.readFileSync(filePath, "utf8");
      const rel = path.relative(REPO_ROOT, filePath);
      violations.push(...scanForbiddenTermsInLines(rel, content, false));
    }

    expect(violations).toEqual([]);
  });

  it("forbids visible UI leaks of banned jargon and secret tokens in packages/ui/src primitives and components", () => {
    const uiFiles = collectFiles(path.join(REPO_ROOT, "packages/ui/src"), [".ts", ".tsx"]).filter(
      (filePath) => path.basename(filePath) !== "OrciaProductShowcaseSiteView.tsx",
    );

    expect(uiFiles.length).toBeGreaterThan(10);

    const violations: string[] = [];
    for (const filePath of uiFiles) {
      const content = fs.readFileSync(filePath, "utf8");
      const rel = path.relative(REPO_ROOT, filePath);
      violations.push(...scanForbiddenTermsInLines(rel, content, true));
    }

    expect(violations).toEqual([]);
  });

  it("enforces all 5 structural anti-jargon regexes without exemptions across 100% of apps/web/src, packages/ui/src, and help docs", () => {
    const markdownFiles = [
      ...collectFiles(path.join(REPO_ROOT, "docs/help"), [".md"]),
      ...collectFiles(path.join(REPO_ROOT, "packs"), [".md"]).filter((p) =>
        p.includes(`${path.sep}help${path.sep}`),
      ),
    ];
    const tsUiTargets = [
      ...collectFiles(path.join(REPO_ROOT, "apps/web/src"), [".ts", ".tsx"]),
      ...collectFiles(path.join(REPO_ROOT, "packages/ui/src"), [".ts", ".tsx"]).filter(
        (filePath) => path.basename(filePath) !== "OrciaProductShowcaseSiteView.tsx",
      ),
    ];
    const violations: string[] = [];

    for (const mdFile of markdownFiles) {
      const rel = path.relative(REPO_ROOT, mdFile);
      violations.push(...scanStructuralJargonInMarkdown(rel, fs.readFileSync(mdFile, "utf8")));
    }

    for (const tsFile of tsUiTargets) {
      const rel = path.relative(REPO_ROOT, tsFile);
      const src = fs.readFileSync(tsFile, "utf8");
      violations.push(...scanStructuralJargonInTsSource(rel, src, tsFile.endsWith(".tsx")));
    }

    expect(violations).toEqual([]);
  });

  it("explicitly rejects synthetic jargon, secrets, structural regexes, and ContextualHelp @/→ metadata without false positives", () => {
    const badTermsHits = scanForbiddenTermsInLines(
      "apps/web/src/i18n/locales/synthetic.ts",
      'const msg = "SYNTHESIS_READY with ORCIA_BOOTSTRAP_TOKEN and AES-256-GCM";',
      false,
    );
    expect(badTermsHits).toHaveLength(3);

    const badMdHits = scanStructuralJargonInMarkdown(
      "docs/help/synthetic.md",
      "Erreur HTTP 502 sur pack@1.2.3 : SPEC → PLAN (Esc) avec MY_INTERNAL_ENUM",
    );
    expect(badMdHits).toHaveLength(5);

    const badTsHits = scanStructuralJargonInTsSource(
      "packages/ui/src/primitives/ContextualHelpSharedBlocks.tsx",
      `
        import React from "react";
        export function BadHelp() {
          return (
            <div data-testid="SAFE_INTERNAL_TESTID">
              <span>Erreur HTTP 500 sur pack@1.0.0 SPEC → PLAN (Esc) RAW_ENUM_TOKEN</span>
            </div>
          );
        }
      `,
      true,
    );
    expect(badTsHits.some((h) => h.includes("HTTP_4XX_5XX"))).toBe(true);
    expect(badTsHits.some((h) => h.includes("AT_SEMVER"))).toBe(true);
    expect(badTsHits.some((h) => h.includes("UPPER_ARROW_CHAIN"))).toBe(true);
    expect(badTsHits.some((h) => h.includes("ESC_SHORTCUT"))).toBe(true);
    expect(badTsHits.some((h) => h.includes("SCREAMING_SNAKE_3SEG"))).toBe(true);
    expect(badTsHits.some((h) => h.includes("HELP_META_FORMAT"))).toBe(true);
    expect(badTsHits.some((h) => h.includes("SAFE_INTERNAL_TESTID"))).toBe(false);
  });
});
