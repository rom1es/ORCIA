import ts from "typescript";

export interface AstViolation {
  readonly line: number;
  readonly kind:
    | "LOCALE_CONDITIONAL"
    | "JSX_TEXT"
    | "JSX_ATTR"
    | "PARAM_DEFAULT"
    | "FALLBACK_LITERAL"
    | "SWITCH_FALLBACK"
    | "UI_DEFAULT_CONST";
  readonly detail: string;
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
  "reason",
  "disabledReason",
  "noResultsLabel",
  "truncatedHint",
  "addButtonLabel",
  "emptyText",
]);

const WORD_LETTERS_RE = /\p{L}{2,}/u;
const FRENCH_ACCENT_RE = /[àâäçéèêëîïôöùûüÿœæÀÂÄÇÉÈÊËÎÏÔÖÙÛÜŸŒÆ]/;
const MULTI_WORD_PROSE_RE = /\p{L}{2,}\s+\p{L}{2,}/u;
const LABEL_IDENT_RE =
  /(?:label|title|text|message|hint|reason|placeholder|cta|notice|warning|error|alert|description|tooltip|badge|caption|heading|subtitle|summary|prompt|empty|prefix|suffix|fallback|copy|aria|button)/i;
const NON_LABEL_IDENT_RE =
  /^(?:testId|testIdPrefix|testIdSuffix|inputTestId|closeButtonTestId|idPrefix|className|tabsClassName|contentClassName)$/i;
const SCREAMING_ENUM_RE = /^[A-Z0-9_]+$/;
const SLUG_OR_ID_RE = /^[a-z0-9]+(?:[-_.:/][a-z0-9]+)+$/;
const URI_OR_PATH_RE = /^(?:(?:https?|orcia|pack|git|cas|ftp|mailto):\/\/|\/[a-z0-9/_-]*$)/i;
const TECHNICAL_SHORT_TOKENS = new Set([
  "fr", "en", "fr-FR", "en-US", "ms", "s", "px", "rem", "em", "sm", "md", "lg", "xl", "2xl",
  "on", "off", "id", "wf", "all", "code", "text", "user", "tool", "chat", "low", "medium",
  "high", "max", "default", "balanced", "button", "submit", "reset", "primary", "secondary",
  "danger", "ghost", "neutral", "cobalt", "amber", "emerald", "crimson", "violet", "info",
  "warning", "error", "success", "search", "password", "email", "tel", "url", "number",
  "date", "json", "csv", "yaml", "sql", "git", "jira", "confluence", "nexus", "orcia",
  "assistant", "cockpit", "agents", "macro", "place", "unknown", "main", "agent", "source",
  "step", "Anthropic", "OpenAI", "Gemini", "Ollama", "Mistral", "ORCIA", "1H", "24H", "7D",
  "30D", "openid profile email", "g c", "g s", "IDE / Git",
]);
const CSS_CLASS_HINT_RE =
  /^(?:orcia-|flex|grid|border|rounded|text-|bg-|px-|py-|gap-|items-|justify-|min-|max-|w-|h-|inline-|block|hidden|sr-only)/;
const UI_SINGLE_WORD_RE =
  /^(?:Fermer|Annuler|Valider|Ajouter|Enregistrer|Supprimer|Modifier|Espace|Équipe|Direction|Pair|Base|Templates|Workflows|Runs|Cancel|Close|Save|Delete|Edit|Add|Space|Team|Peer|Dismiss|Confirm|Submit|Accostage|Temps|Actif|Inactif|Brouillon|Partagé|Publié|Étape|Steps?)$/i;

export function isPureTechnicalToken(raw: string): boolean {
  const trimmed = raw.trim();
  if (!trimmed || !WORD_LETTERS_RE.test(trimmed)) return true;
  if (TECHNICAL_SHORT_TOKENS.has(trimmed)) return true;
  if (SCREAMING_ENUM_RE.test(trimmed)) return true;
  if (SLUG_OR_ID_RE.test(trimmed)) return true;
  if (URI_OR_PATH_RE.test(trimmed)) return true;
  if (trimmed.startsWith("{") || trimmed.startsWith("[")) return true;
  if (CSS_CLASS_HINT_RE.test(trimmed)) return true;
  return false;
}

export function isUserFacingText(raw: string, hintName = ""): boolean {
  const trimmed = raw.trim();
  if (isPureTechnicalToken(trimmed)) return false;
  if (FRENCH_ACCENT_RE.test(trimmed)) return true;
  if (MULTI_WORD_PROSE_RE.test(trimmed)) return true;
  if (!NON_LABEL_IDENT_RE.test(hintName) && LABEL_IDENT_RE.test(hintName)) return true;
  if (UI_SINGLE_WORD_RE.test(trimmed)) return true;
  return false;
}

export function extractStaticString(expr: ts.Expression): string | null {
  if (ts.isStringLiteral(expr) || ts.isNoSubstitutionTemplateLiteral(expr)) {
    return expr.text;
  }
  if (ts.isTemplateExpression(expr)) {
    return [expr.head.text, ...expr.templateSpans.map((s) => s.literal.text)].join(" ");
  }
  return null;
}

export function collectObjectLiteralStrings(
  obj: ts.ObjectLiteralExpression,
  prefix = "",
): Array<{ key: string; text: string; node: ts.Node }> {
  const out: Array<{ key: string; text: string; node: ts.Node }> = [];
  for (const prop of obj.properties) {
    if (ts.isPropertyAssignment(prop)) {
      const key = ts.isIdentifier(prop.name) || ts.isStringLiteral(prop.name) ? prop.name.text : "";
      const nextKey = prefix ? `${prefix}.${key}` : key;
      const str = extractStaticString(prop.initializer);
      if (str !== null) {
        out.push({ key: nextKey, text: str, node: prop.initializer });
      } else if (ts.isObjectLiteralExpression(prop.initializer)) {
        out.push(...collectObjectLiteralStrings(prop.initializer, nextKey));
      } else if (ts.isArrayLiteralExpression(prop.initializer)) {
        for (const el of prop.initializer.elements) {
          if (ts.isExpression(el)) {
            const s = extractStaticString(el);
            if (s !== null) out.push({ key: nextKey, text: s, node: el });
          }
        }
      }
    }
  }
  return out;
}
