export interface AlertFeedback {
  readonly tone: "crimson" | "emerald";
  readonly message: string;
}

export type AlertFeedbackInput = AlertFeedback | string | null;

const LEGACY_WARNING_PREFIX_RE = /^(?:\u26A0\uFE0F|\u26A0)\s*/u;
const LEGACY_ERROR_TEXT_RE =
  /\[(ERR_|HTTP_)|^(Erreur|Error|Impossible|Unable|Failed|Échec|Echec|Vérification incomplète|Verification incomplete)/i;

/**
 * Normalize either an explicit `{ tone, message }` object or a legacy string
 * message into a typed banner feedback descriptor without requiring emoji prefixes.
 */
export function normalizeAlertFeedback(
  input: AlertFeedbackInput,
): AlertFeedback | null {
  if (!input) return null;
  if (typeof input !== "string") return input;
  const cleaned = input.replace(LEGACY_WARNING_PREFIX_RE, "").trim();
  const isError =
    LEGACY_WARNING_PREFIX_RE.test(input) || LEGACY_ERROR_TEXT_RE.test(cleaned);
  return {
    tone: isError ? "crimson" : "emerald",
    message: cleaned,
  };
}
