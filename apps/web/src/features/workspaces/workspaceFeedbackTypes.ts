export interface WorkspaceAlertFeedback {
  readonly tone: "crimson" | "emerald";
  readonly message: string;
}

export type WorkspaceFeedbackInput = WorkspaceAlertFeedback | string | null;

export function normalizeWorkspaceFeedback(
  input: WorkspaceFeedbackInput,
): WorkspaceAlertFeedback | null {
  if (!input) return null;
  if (typeof input !== "string") return input;
  const cleaned = input.replace(/^⚠️\s*/u, "").trim();
  const isError =
    input.startsWith("⚠️") ||
    /\[(ERR_|HTTP_)|^(Erreur|Error|Impossible|Failed|Échec|Echec)/i.test(cleaned);
  return {
    tone: isError ? "crimson" : "emerald",
    message: cleaned,
  };
}
