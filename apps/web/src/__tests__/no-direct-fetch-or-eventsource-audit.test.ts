import fs from "node:fs";
import path from "node:path";
import ts from "typescript";
import { describe, expect, it } from "vitest";

const REPO_ROOT = path.resolve(__dirname, "../../../..");
const WEB_SRC_DIR = path.join(REPO_ROOT, "apps/web/src");
const API_CLIENT_SRC_DIR = path.join(REPO_ROOT, "packages/api-client/src");
const ALLOWED_FETCH_FILE = path.normalize(path.join(API_CLIENT_SRC_DIR, "helpers.ts"));

function collectSourceFiles(dir: string): string[] {
  if (!fs.existsSync(dir)) return [];
  const files: string[] = [];
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
      files.push(...collectSourceFiles(full));
    } else if (
      entry.isFile() &&
      !entry.name.includes(".test.") &&
      (entry.name.endsWith(".ts") || entry.name.endsWith(".tsx"))
    ) {
      files.push(full);
    }
  }
  return files;
}

function isDirectFetchCall(expr: ts.Expression): boolean {
  if (ts.isIdentifier(expr) && expr.text === "fetch") {
    return true;
  }
  if (
    ts.isPropertyAccessExpression(expr) &&
    expr.name.text === "fetch" &&
    ts.isIdentifier(expr.expression) &&
    (expr.expression.text === "globalThis" ||
      expr.expression.text === "window" ||
      expr.expression.text === "self")
  ) {
    return true;
  }
  return false;
}

function scanSourceTextForDirectTransportCalls(
  rel: string,
  sourceText: string,
  scriptKind: ts.ScriptKind,
): string[] {
  const sf = ts.createSourceFile(rel, sourceText, ts.ScriptTarget.Latest, true, scriptKind);
  const violations: string[] = [];

  const visit = (node: ts.Node) => {
    if (ts.isCallExpression(node) && isDirectFetchCall(node.expression)) {
      const { line } = sf.getLineAndCharacterOfPosition(node.getStart(sf));
      violations.push(`${rel}:${line + 1} -> direct fetch(...) call forbidden outside helpers.ts`);
    }
    if (
      ts.isNewExpression(node) &&
      ts.isIdentifier(node.expression) &&
      node.expression.text === "EventSource"
    ) {
      const { line } = sf.getLineAndCharacterOfPosition(node.getStart(sf));
      violations.push(`${rel}:${line + 1} -> direct new EventSource(...) forbidden`);
    }
    ts.forEachChild(node, visit);
  };
  visit(sf);
  return violations;
}

function scanForDirectTransportCalls(filePath: string): string[] {
  const normalized = path.normalize(filePath);
  if (normalized === ALLOWED_FETCH_FILE) {
    return [];
  }
  const sourceText = fs.readFileSync(normalized, "utf8");
  const scriptKind = normalized.endsWith(".tsx") ? ts.ScriptKind.TSX : ts.ScriptKind.TS;
  const rel = path.relative(REPO_ROOT, normalized);
  return scanSourceTextForDirectTransportCalls(rel, sourceText, scriptKind);
}

describe("Anti-Goodhart Lock 2 — Zero direct fetch() or new EventSource() outside @orcia/api-client helpers", () => {
  it("forbids direct fetch() and new EventSource() in apps/web/src/** and packages/api-client/src/**", () => {
    const filesToScan = [
      ...collectSourceFiles(WEB_SRC_DIR),
      ...collectSourceFiles(API_CLIENT_SRC_DIR),
    ];
    const violations = filesToScan.flatMap(scanForDirectTransportCalls);
    expect(violations).toEqual([]);
  });

  it("explicitly rejects synthetic direct fetch(), window/globalThis/self.fetch(), and new EventSource()", () => {
    const badSnippet = `
      export async function badCalls() {
        await fetch("/api/v1/workspaces");
        await window.fetch("/api/v1/health");
        await globalThis.fetch("/api/v1/ready");
        await self.fetch("/api/v1/auth/session");
        return new EventSource("/api/v1/stream");
      }
    `;
    const violations = scanSourceTextForDirectTransportCalls(
      "synthetic/badTransport.ts",
      badSnippet,
      ts.ScriptKind.TS,
    );
    expect(violations).toHaveLength(5);
    expect(violations.some((v) => v.includes("direct fetch(...)"))).toBe(true);
    expect(violations.some((v) => v.includes("direct new EventSource(...)"))).toBe(true);

    const safeSnippet = `
      import { apiClient } from "@orcia/api-client";
      export function safeCall() {
        const fetchConfig = { method: "GET" };
        return apiClient.GET("/api/v1/health", fetchConfig);
      }
    `;
    expect(
      scanSourceTextForDirectTransportCalls("synthetic/safe.ts", safeSnippet, ts.ScriptKind.TS),
    ).toEqual([]);
  });
});
