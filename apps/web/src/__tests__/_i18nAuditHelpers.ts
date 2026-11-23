import fs from "node:fs";
import path from "node:path";
import ts from "typescript";

export const REPO_ROOT = path.resolve(__dirname, "../../../..");

export function collectTsSourceFiles(
  rootDir: string,
  excludedSubdirs: readonly string[] = ["__tests__", "generated", "node_modules", "dist"],
): string[] {
  if (!fs.existsSync(rootDir)) return [];
  const results: string[] = [];
  for (const entry of fs.readdirSync(rootDir, { withFileTypes: true })) {
    if (excludedSubdirs.includes(entry.name)) continue;
    const full = path.join(rootDir, entry.name);
    if (entry.isDirectory()) {
      results.push(...collectTsSourceFiles(full, excludedSubdirs));
    } else if (
      entry.isFile() &&
      !entry.name.includes(".test.") &&
      !entry.name.includes(".spec.") &&
      (entry.name.endsWith(".ts") || entry.name.endsWith(".tsx"))
    ) {
      results.push(full);
    }
  }
  return results.sort();
}

export const UI_VISIBLE_JSX_ATTRS = new Set([
  "title",
  "placeholder",
  "aria-label",
  "alt",
  "label",
  "description",
  "emptyMessage",
  "helperText",
  "submitLabel",
  "cancelLabel",
  "closeLabel",
  "emptyTitle",
  "emptyDescription",
]);

const LOCALE_IDENT_RE = /^(?:locale|lang|language|uiLocale|currentLocale|activeLocale)$/i;
const LOCALE_BOOL_RE = /^(?:isFr(?:ench)?|isEn(?:glish)?)$/i;
const LOCALE_LITERAL_RE = /^(?:fr|en|fr-FR|en-US)$/i;
const WORD_LETTERS_RE = /\p{L}{2,}/u;

function hasNonUserFacingComment(lines: readonly string[], lineIndexZeroBased: number): boolean {
  const current = lines[lineIndexZeroBased] ?? "";
  const prev = lineIndexZeroBased > 0 ? (lines[lineIndexZeroBased - 1] ?? "") : "";
  return (
    current.includes("i18n-non-user-facing") || prev.includes("i18n-non-user-facing")
  );
}

function isInsideIntlOrLocaleFormatting(node: ts.Node): boolean {
  let cur: ts.Node | undefined = node.parent;
  while (cur) {
    if (ts.isCallExpression(cur)) {
      const exprText = cur.expression.getText();
      if (
        exprText.includes("Intl.") ||
        exprText.endsWith(".toLocaleDateString") ||
        exprText.endsWith(".toLocaleTimeString") ||
        exprText.endsWith(".toLocaleString")
      ) {
        return true;
      }
    }
    if (ts.isNewExpression(cur) && cur.expression.getText().includes("Intl.")) {
      return true;
    }
    cur = cur.parent;
  }
  return false;
}

function isLocaleComparisonBinary(node: ts.BinaryExpression): boolean {
  const op = node.operatorToken.kind;
  if (
    op !== ts.SyntaxKind.EqualsEqualsEqualsToken &&
    op !== ts.SyntaxKind.ExclamationEqualsEqualsToken &&
    op !== ts.SyntaxKind.EqualsEqualsToken &&
    op !== ts.SyntaxKind.ExclamationEqualsToken
  ) {
    return false;
  }
  const leftText = ts.isIdentifier(node.left)
    ? node.left.text
    : ts.isPropertyAccessExpression(node.left)
      ? node.left.name.text
      : "";
  const rightText = ts.isIdentifier(node.right)
    ? node.right.text
    : ts.isPropertyAccessExpression(node.right)
      ? node.right.name.text
      : "";
  const leftLit = ts.isStringLiteral(node.left) ? node.left.text : "";
  const rightLit = ts.isStringLiteral(node.right) ? node.right.text : "";

  return (
    (LOCALE_IDENT_RE.test(leftText) && LOCALE_LITERAL_RE.test(rightLit)) ||
    (LOCALE_IDENT_RE.test(rightText) && LOCALE_LITERAL_RE.test(leftLit))
  );
}

function extractStaticStringFromExpr(expr: ts.Expression): string | null {
  if (ts.isStringLiteral(expr) || ts.isNoSubstitutionTemplateLiteral(expr)) {
    return expr.text;
  }
  if (ts.isTemplateExpression(expr)) {
    return [expr.head.text, ...expr.templateSpans.map((s) => s.literal.text)].join(" ");
  }
  return null;
}

export interface AstViolation {
  readonly line: number;
  readonly kind: "LOCALE_CONDITIONAL" | "JSX_TEXT" | "JSX_ATTR";
  readonly detail: string;
}

export function scanFileForHardcodedLocaleAst(rel: string, src: string): AstViolation[] {
  const kind = rel.endsWith(".tsx") ? ts.ScriptKind.TSX : ts.ScriptKind.TS;
  const sf = ts.createSourceFile(rel, src, ts.ScriptTarget.Latest, true, kind);
  const lines = src.split("\n");
  const violations: AstViolation[] = [];

  const record = (node: ts.Node, vKind: AstViolation["kind"], detail: string) => {
    const lineIdx = sf.getLineAndCharacterOfPosition(node.getStart(sf)).line;
    if (hasNonUserFacingComment(lines, lineIdx)) return;
    violations.push({ line: lineIdx + 1, kind: vKind, detail });
  };

  const visit = (node: ts.Node) => {
    if (ts.isBinaryExpression(node) && isLocaleComparisonBinary(node)) {
      if (!isInsideIntlOrLocaleFormatting(node)) {
        record(node, "LOCALE_CONDITIONAL", node.getText(sf));
      }
    } else if (
      ts.isConditionalExpression(node) &&
      ts.isIdentifier(node.condition) &&
      LOCALE_BOOL_RE.test(node.condition.text)
    ) {
      if (!isInsideIntlOrLocaleFormatting(node)) {
        record(node, "LOCALE_CONDITIONAL", node.condition.text);
      }
    } else if (ts.isJsxText(node)) {
      const text = node.text.replace(/\s+/g, " ").trim();
      if (WORD_LETTERS_RE.test(text)) {
        record(node, "JSX_TEXT", text.slice(0, 60));
      }
    } else if (ts.isJsxAttribute(node) && ts.isIdentifier(node.name)) {
      const attrName = node.name.text;
      if (UI_VISIBLE_JSX_ATTRS.has(attrName) && node.initializer) {
        let text: string | null = null;
        if (ts.isStringLiteral(node.initializer)) {
          text = node.initializer.text;
        } else if (ts.isJsxExpression(node.initializer) && node.initializer.expression) {
          text = extractStaticStringFromExpr(node.initializer.expression);
        }
        if (
          text !== null &&
          WORD_LETTERS_RE.test(text) &&
          !/^(?:https?|orcia):\/\/\S+$/.test(text.trim())
        ) {
          record(node, "JSX_ATTR", `${attrName}=${JSON.stringify(text.slice(0, 50))}`);
        }
      }
    }
    ts.forEachChild(node, visit);
  };

  visit(sf);
  return violations;
}
