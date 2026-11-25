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
  const isError = input.startsWith("⚠️");
  const cleaned = input.replace(/^⚠️\s*/u, "").trim();
  return {
    tone: isError ? "crimson" : "emerald",
    message: cleaned,
  };
}
