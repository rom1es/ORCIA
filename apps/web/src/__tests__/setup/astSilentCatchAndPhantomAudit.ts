import fs from "node:fs";
import path from "node:path";
import ts from "typescript";

export function collectAuditTsFiles(dir: string): string[] {
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
      results.push(...collectAuditTsFiles(full));
    } else if (
      entry.isFile() &&
      !entry.name.includes(".test.") &&
      (entry.name.endsWith(".ts") || entry.name.endsWith(".tsx"))
    ) {
      results.push(full);
    }
  }
  return results;
}

function isSilentReturnExpression(expr: ts.Expression | undefined): boolean {
  if (!expr) return false;
  if (ts.isParenthesizedExpression(expr)) return isSilentReturnExpression(expr.expression);
  if (expr.kind === ts.SyntaxKind.NullKeyword) return true;
  if (ts.isIdentifier(expr) && expr.text === "undefined") return true;
  if (ts.isObjectLiteralExpression(expr) && expr.properties.length === 0) return true;
  if (ts.isArrayLiteralExpression(expr) && expr.elements.length === 0) return true;
  return false;
}

export function scanSilentCatchesInSource(
  rel: string,
  sourceText: string,
  isTsx = false,
): string[] {
  const kind = isTsx ? ts.ScriptKind.TSX : ts.ScriptKind.TS;
  const sf = ts.createSourceFile(rel, sourceText, ts.ScriptTarget.Latest, true, kind);
  const violations: string[] = [];

  const visit = (node: ts.Node) => {
    if (ts.isCatchClause(node)) {
      const line = sf.getLineAndCharacterOfPosition(node.getStart(sf)).line + 1;
      if (!node.variableDeclaration) {
        violations.push(`${rel}:${line} -> bare catch {} without parameter forbidden`);
      } else if (node.block.statements.length === 0) {
        violations.push(`${rel}:${line} -> empty catch block forbidden`);
      }
    }
    if (
      ts.isCallExpression(node) &&
      ts.isPropertyAccessExpression(node.expression) &&
      node.expression.name.text === "catch" &&
      node.arguments.length >= 1
    ) {
      const arg = node.arguments[0]!;
      if (ts.isArrowFunction(arg) || ts.isFunctionExpression(arg)) {
        const line = sf.getLineAndCharacterOfPosition(node.getStart(sf)).line + 1;
        if (ts.isBlock(arg.body)) {
          if (arg.body.statements.length === 0) {
            violations.push(`${rel}:${line} -> silent .catch(() => {}) forbidden`);
          } else if (
            arg.body.statements.length === 1 &&
            ts.isReturnStatement(arg.body.statements[0]!) &&
            isSilentReturnExpression(arg.body.statements[0]!.expression)
          ) {
            violations.push(`${rel}:${line} -> silent .catch(() => null/undefined/{}/[]) forbidden`);
          }
        } else if (isSilentReturnExpression(arg.body)) {
          violations.push(`${rel}:${line} -> silent .catch(() => null/undefined/{}/[]) forbidden`);
        }
      }
    }
    ts.forEachChild(node, visit);
  };
  visit(sf);
  return violations;
}

export function scanSilentCatchesAst(repoRoot: string, dirs: readonly string[]): string[] {
  const violations: string[] = [];
  for (const dir of dirs) {
    for (const filePath of collectAuditTsFiles(dir)) {
      const sourceText = fs.readFileSync(filePath, "utf8");
      const rel = path.relative(repoRoot, filePath);
      violations.push(...scanSilentCatchesInSource(rel, sourceText, filePath.endsWith(".tsx")));
    }
  }
  return violations;
}

const PHANTOM_PATTERNS: ReadonlyArray<{ readonly name: string; readonly re: RegExp }> = [
  { name: "DEFAULT_HUMAN_PROFILE", re: /\bDEFAULT_HUMAN_PROFILE\b/ },
  { name: "GENERAL_SECTIONS_*", re: /\bGENERAL_SECTIONS_[A-Z0-9_]+\b/ },
  { name: "PARALLEL_5_STEPS_LABEL", re: /\b(?:5\s+[ÉEé]tapes|5-Step|Show\s+5\s+steps|Afficher\s+les\s+5\s+étapes)\b/i },
];

export function scanPhantomConstantsInSource(rel: string, sourceText: string): string[] {
  const violations: string[] = [];
  const lines = sourceText.split("\n");
  lines.forEach((line, idx) => {
    for (const { name, re } of PHANTOM_PATTERNS) {
      if (re.test(line)) {
        violations.push(`${rel}:${idx + 1} [${name}] -> ${line.trim()}`);
      }
    }
  });
  return violations;
}

export function scanPhantomConstantsAndLabels(repoRoot: string, dirs: readonly string[]): string[] {
  const violations: string[] = [];
  for (const dir of dirs) {
    for (const filePath of collectAuditTsFiles(dir)) {
      const sourceText = fs.readFileSync(filePath, "utf8");
      const rel = path.relative(repoRoot, filePath);
      violations.push(...scanPhantomConstantsInSource(rel, sourceText));
    }
  }
  return violations;
}

const DISALLOWED_STORAGE_ERROR_FILE_RE =
  /(?:Hydration|ApiBridge|Controller|SessionStore|StreamingTurn|TurnPayload|Supervision|SourcesRagTab)\.(?:ts|tsx)$/i;
const BROWSER_STORAGE_MARKER_RE =
  /\b(?:localStorage|sessionStorage|window\.history|history\.replaceState|window\.location|URLSearchParams)\b/;

export function scanMisplacedStorageErrorHelperInSource(
  rel: string,
  sourceText: string,
  isTsx = rel.endsWith(".tsx"),
): string[] {
  if (rel.endsWith("benignBrowserError.ts") || !sourceText.includes("ignoreBenignStorageError(")) {
    return [];
  }
  const violations: string[] = [];
  if (DISALLOWED_STORAGE_ERROR_FILE_RE.test(rel)) {
    violations.push(`${rel} -> ignoreBenignStorageError forbidden in API/hydration/controller file`);
  }
  if (!BROWSER_STORAGE_MARKER_RE.test(sourceText)) {
    violations.push(`${rel} -> ignoreBenignStorageError requires localStorage/sessionStorage/history`);
  }
  const sf = ts.createSourceFile(
    rel,
    sourceText,
    ts.ScriptTarget.Latest,
    true,
    isTsx ? ts.ScriptKind.TSX : ts.ScriptKind.TS,
  );
  const visit = (node: ts.Node) => {
    if (
      ts.isCallExpression(node) &&
      ts.isIdentifier(node.expression) &&
      node.expression.text === "ignoreBenignStorageError"
    ) {
      let cur: ts.Node | undefined = node.parent;
      while (cur) {
        if (ts.isCatchClause(cur) && ts.isTryStatement(cur.parent)) {
          const tryText = cur.parent.tryBlock.getText(sf);
          if (/\b(?:await|createOrciaApiClient|fetch)\b/.test(tryText)) {
            const line = sf.getLineAndCharacterOfPosition(node.getStart(sf)).line + 1;
            violations.push(
              `${rel}:${line} -> ignoreBenignStorageError cannot wrap async/API try-block`,
            );
          }
          break;
        }
        cur = cur.parent;
      }
    }
    ts.forEachChild(node, visit);
  };
  visit(sf);
  return violations;
}

export function scanMisplacedStorageErrorHelper(
  repoRoot: string,
  dirs: readonly string[],
): string[] {
  const violations: string[] = [];
  for (const dir of dirs) {
    for (const filePath of collectAuditTsFiles(dir)) {
      const sourceText = fs.readFileSync(filePath, "utf8");
      const rel = path.relative(repoRoot, filePath);
      violations.push(
        ...scanMisplacedStorageErrorHelperInSource(rel, sourceText, filePath.endsWith(".tsx")),
      );
    }
  }
  return violations;
}
