import fs from "node:fs";
import path from "node:path";
import ts from "typescript";
import {
  collectObjectLiteralStrings,
  extractStaticString,
  isUserFacingText,
  UI_VISIBLE_JSX_ATTRS,
  type AstViolation,
} from "./_i18nAuditRules";

export type { AstViolation };
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

const LOCALE_IDENT_RE = /^(?:locale|lang|language|uiLocale|currentLocale|activeLocale)$/i;
const LOCALE_BOOL_RE = /^(?:isFr(?:ench)?|isEn(?:glish)?)$/i;
const LOCALE_LITERAL_RE = /^(?:fr|en|fr-FR|en-US)$/i;
const WORD_LETTERS_RE = /\p{L}{2,}/u;
const UI_CONST_NAME_RE = /^(?:DEFAULT_[A-Z0-9_]+|[A-Z0-9_]+_LABELS_(?:FR|EN))$/;

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

function isInsideSwitchStatement(node: ts.Node): boolean {
  let cur: ts.Node | undefined = node.parent;
  while (cur) {
    if (ts.isSwitchStatement(cur)) return true;
    if (ts.isFunctionLike(cur)) return false;
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

export function scanFileForHardcodedLocaleAst(rel: string, src: string): AstViolation[] {
  const kind = rel.endsWith(".tsx") ? ts.ScriptKind.TSX : ts.ScriptKind.TS;
  const sf = ts.createSourceFile(rel, src, ts.ScriptTarget.Latest, true, kind);
  const lines = src.split("\n");
  const isUiPackage = rel.startsWith("packages/ui/src/");
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
      LOCALE_BOOL_RE.test(node.condition.text) &&
      !isInsideIntlOrLocaleFormatting(node)
    ) {
      record(node, "LOCALE_CONDITIONAL", node.condition.text);
    } else if (ts.isJsxText(node)) {
      const text = node.text.replace(/\s+/g, " ").trim();
      if (WORD_LETTERS_RE.test(text)) record(node, "JSX_TEXT", text.slice(0, 60));
    } else if (ts.isJsxAttribute(node) && ts.isIdentifier(node.name) && node.initializer) {
      const attrName = node.name.text;
      if (UI_VISIBLE_JSX_ATTRS.has(attrName)) {
        const text = ts.isStringLiteral(node.initializer)
          ? node.initializer.text
          : ts.isJsxExpression(node.initializer) && node.initializer.expression
            ? extractStaticString(node.initializer.expression)
            : null;
        if (text !== null && isUserFacingText(text, attrName)) {
          record(node, "JSX_ATTR", `${attrName}=${JSON.stringify(text.slice(0, 50))}`);
        }
      }
    } else if ((ts.isParameter(node) || ts.isBindingElement(node)) && node.initializer) {
      const paramName = ts.isIdentifier(node.name) ? node.name.text : node.name.getText(sf);
      const str = extractStaticString(node.initializer);
      if (str !== null && isUserFacingText(str, paramName)) {
        record(node, "PARAM_DEFAULT", `${paramName}=${JSON.stringify(str.slice(0, 50))}`);
      } else if (
        ts.isPropertyAccessExpression(node.initializer) &&
        UI_CONST_NAME_RE.test(node.initializer.expression.getText(sf))
      ) {
        record(node, "PARAM_DEFAULT", `${paramName}=${node.initializer.getText(sf)}`);
      } else if (
        ts.isIdentifier(node.initializer) &&
        UI_CONST_NAME_RE.test(node.initializer.text)
      ) {
        record(node, "PARAM_DEFAULT", `${paramName}=${node.initializer.text}`);
      }
    } else if (
      ts.isBinaryExpression(node) &&
      (node.operatorToken.kind === ts.SyntaxKind.QuestionQuestionToken ||
        node.operatorToken.kind === ts.SyntaxKind.BarBarToken)
    ) {
      const lhs = node.left.getText(sf);
      const rightStr = extractStaticString(node.right);
      const inSwitch = isInsideSwitchStatement(node);
      if (rightStr !== null && isUserFacingText(rightStr, lhs)) {
        record(
          node,
          inSwitch ? "SWITCH_FALLBACK" : "FALLBACK_LITERAL",
          `${lhs.slice(0, 35)} ${node.operatorToken.getText(sf)} ${JSON.stringify(rightStr.slice(0, 45))}`,
        );
      } else if (ts.isObjectLiteralExpression(node.right)) {
        for (const item of collectObjectLiteralStrings(node.right, lhs)) {
          if (isUserFacingText(item.text, item.key)) {
            record(item.node, "FALLBACK_LITERAL", `${item.key}: ${JSON.stringify(item.text.slice(0, 45))}`);
            break;
          }
        }
      }
    } else if (
      isUiPackage &&
      ts.isVariableDeclaration(node) &&
      ts.isIdentifier(node.name) &&
      UI_CONST_NAME_RE.test(node.name.text) &&
      node.initializer
    ) {
      const str = extractStaticString(node.initializer);
      if (str !== null && isUserFacingText(str, node.name.text)) {
        record(node, "UI_DEFAULT_CONST", `${node.name.text}=${JSON.stringify(str.slice(0, 50))}`);
      } else if (ts.isObjectLiteralExpression(node.initializer)) {
        const hits = collectObjectLiteralStrings(node.initializer, node.name.text).filter((e) =>
          isUserFacingText(e.text, e.key),
        );
        if (hits.length > 0) {
          record(node, "UI_DEFAULT_CONST", `${node.name.text} (${hits.length} strings)`);
        }
      }
    }
    ts.forEachChild(node, visit);
  };

  visit(sf);
  return violations;
}
