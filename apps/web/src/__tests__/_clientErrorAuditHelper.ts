import path from "node:path";
import ts from "typescript";
import { collectTsSourceFiles, REPO_ROOT } from "./_i18nAuditHelpers";

const CLIENT_ERROR_FILE_RE =
  /(?:ApiBridge|Store|Controller|Hydration|Healthchecks|StreamingTurn|BrokerTickets|ErrorToBanner)\.(?:ts|tsx)$/;

const EXPLICIT_CLIENT_ERROR_PATHS = new Set<string>([
  "apps/web/src/routes/wizards.tsx",
  "apps/web/src/routes/settingsAiModelsPresets.ts",
  "apps/web/src/components/useSidebarAccountSettings.ts",
  "apps/web/src/components/platformSetupWorkspaces.ts",
  "apps/web/src/components/ShellFederatedSearchModal.tsx",
  "apps/web/src/features/workspaces/WorkspaceSourcesRagTab.tsx",
  "apps/web/src/features/processes/ProcessStudioAndPackAuthoringSection.tsx",
  "packages/ui/src/primitives/UserPasswordChangeCard.tsx",
]);

const ERROR_PROSE_RE =
  /\b(?:erreur|error|impossible|unable|failed|échec|expiré|expired|timeout|délai|réseau|network|connexion|connection|introuvable|not found|refusé|denied|interrompu|interrupted|invalide|invalid|veuillez|please|réessayez|retry|try again|vérifiez|verify|unexpected|inattendue|autorisation|permissions|indisponible|unavailable|bloqué|blocked|manquant|missing|conflit|conflict|session|accéder|access)\b/i;

const ERROR_PROP_NAMES = new Set([
  "error",
  "errorMessage",
  "title",
  "message",
  "remediation",
  "detail",
  "fallbackMessage",
  "banner",
]);

const ERROR_CALL_NAMES = new Set([
  "setError",
  "setErrorMessage",
  "setBanner",
  "onError",
  "reject",
]);

const LOCALE_IDENT_RE = /^(?:locale|lang|language|uiLocale|currentLocale|activeLocale)$/i;
const LOCALE_BOOL_RE = /^(?:isFr(?:ench)?|isEn(?:glish)?)$/i;
const LOCALE_LITERAL_RE = /^(?:fr|en|fr-FR|en-US)$/i;

export function collectClientErrorAuditTargets(): string[] {
  const webFiles = collectTsSourceFiles(path.join(REPO_ROOT, "apps/web/src"));
  const apiClientFiles = collectTsSourceFiles(path.join(REPO_ROOT, "packages/api-client/src"));
  const uiFiles = collectTsSourceFiles(path.join(REPO_ROOT, "packages/ui/src"));

  const targets = new Set<string>();
  for (const f of apiClientFiles) {
    targets.add(f);
  }
  for (const f of [...webFiles, ...uiFiles]) {
    const rel = path.relative(REPO_ROOT, f).replace(/\\/g, "/");
    if (rel === "apps/web/src/lib/clientErrorCodes.ts" || rel.startsWith("apps/web/src/i18n/locales/")) {
      continue;
    }
    if (CLIENT_ERROR_FILE_RE.test(rel) || EXPLICIT_CLIENT_ERROR_PATHS.has(rel)) {
      targets.add(f);
    }
  }
  return Array.from(targets).sort();
}

function isProseErrorString(text: string): boolean {
  const cleaned = text.trim();
  const words = cleaned.split(/\s+/).filter((w) => /\p{L}{2,}/u.test(w));
  return words.length >= 2 && ERROR_PROSE_RE.test(cleaned);
}

function isErrorContextNode(node: ts.Node): boolean {
  const parent = node.parent;
  if (!parent) return false;
  if (ts.isNewExpression(parent) && parent.expression.getText() === "Error") {
    return true;
  }
  if (ts.isPropertyAssignment(parent) && parent.initializer === node) {
    const name = ts.isIdentifier(parent.name)
      ? parent.name.text
      : ts.isStringLiteral(parent.name)
        ? parent.name.text
        : "";
    if (ERROR_PROP_NAMES.has(name)) return true;
  }
  if (ts.isCallExpression(parent)) {
    const callee = ts.isIdentifier(parent.expression)
      ? parent.expression.text
      : ts.isPropertyAccessExpression(parent.expression)
        ? parent.expression.name.text
        : "";
    if (ERROR_CALL_NAMES.has(callee)) return true;
  }
  if (ts.isThrowStatement(parent)) return true;
  if (ts.isReturnStatement(parent) && parent.expression === node) return true;
  return false;
}

export interface ClientErrorViolation {
  readonly line: number;
  readonly kind: "LOCALE_TERNARY" | "HARDCODED_ERROR_STRING";
  readonly detail: string;
}

export function scanFileForClientErrorViolations(
  rel: string,
  src: string,
): ClientErrorViolation[] {
  const kind = rel.endsWith(".tsx") ? ts.ScriptKind.TSX : ts.ScriptKind.TS;
  const sf = ts.createSourceFile(rel, src, ts.ScriptTarget.Latest, true, kind);
  const lines = src.split("\n");
  const violations: ClientErrorViolation[] = [];

  const isIgnoredLine = (lineIdx: number) => {
    const cur = lines[lineIdx] ?? "";
    const prev = lineIdx > 0 ? (lines[lineIdx - 1] ?? "") : "";
    return cur.includes("i18n-non-user-facing") || prev.includes("i18n-non-user-facing");
  };

  const visit = (node: ts.Node) => {
    if (ts.isBinaryExpression(node)) {
      const op = node.operatorToken.kind;
      if (
        op === ts.SyntaxKind.EqualsEqualsEqualsToken ||
        op === ts.SyntaxKind.ExclamationEqualsEqualsToken
      ) {
        const leftId = ts.isIdentifier(node.left) ? node.left.text : "";
        const rightLit = ts.isStringLiteral(node.right) ? node.right.text : "";
        const rightId = ts.isIdentifier(node.right) ? node.right.text : "";
        const leftLit = ts.isStringLiteral(node.left) ? node.left.text : "";
        if (
          (LOCALE_IDENT_RE.test(leftId) && LOCALE_LITERAL_RE.test(rightLit)) ||
          (LOCALE_IDENT_RE.test(rightId) && LOCALE_LITERAL_RE.test(leftLit))
        ) {
          const lineIdx = sf.getLineAndCharacterOfPosition(node.getStart(sf)).line;
          if (!isIgnoredLine(lineIdx)) {
            violations.push({
              line: lineIdx + 1,
              kind: "LOCALE_TERNARY",
              detail: node.getText(sf),
            });
          }
        }
      }
    } else if (
      ts.isConditionalExpression(node) &&
      ts.isIdentifier(node.condition) &&
      LOCALE_BOOL_RE.test(node.condition.text)
    ) {
      const lineIdx = sf.getLineAndCharacterOfPosition(node.getStart(sf)).line;
      if (!isIgnoredLine(lineIdx)) {
        violations.push({
          line: lineIdx + 1,
          kind: "LOCALE_TERNARY",
          detail: node.condition.text,
        });
      }
    } else if (
      (ts.isStringLiteral(node) || ts.isNoSubstitutionTemplateLiteral(node)) &&
      isErrorContextNode(node) &&
      isProseErrorString(node.text)
    ) {
      const lineIdx = sf.getLineAndCharacterOfPosition(node.getStart(sf)).line;
      if (!isIgnoredLine(lineIdx)) {
        violations.push({
          line: lineIdx + 1,
          kind: "HARDCODED_ERROR_STRING",
          detail: node.text.slice(0, 70),
        });
      }
    } else if (ts.isTemplateExpression(node) && isErrorContextNode(node)) {
      const text = [node.head.text, ...node.templateSpans.map((s) => s.literal.text)].join(" ");
      if (isProseErrorString(text)) {
        const lineIdx = sf.getLineAndCharacterOfPosition(node.getStart(sf)).line;
        if (!isIgnoredLine(lineIdx)) {
          violations.push({
            line: lineIdx + 1,
            kind: "HARDCODED_ERROR_STRING",
            detail: text.slice(0, 70),
          });
        }
      }
    }
    ts.forEachChild(node, visit);
  };

  visit(sf);
  return violations;
}
