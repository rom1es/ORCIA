import React from "react";
import { OrciaIcon } from "../components/icons";
import type { UiAssistantAttachedFileItem } from "./AssistantPromptPlusAndAutocomplete";

export function sanitizeAssistantDisplayReply(rawText: string): string {
  if (!rawText) {
    return "";
  }
  let cleaned = rawText.replace(
    /^\s*\[(?:⚡|🛠️|🧠)\s*Vitesse\s*\d[^\]]*\]\s*/i,
    "",
  );
  cleaned = cleaned.replace(
    /Réponse directe générée avec prompt 5 couches \((?:HIT|MISS) Redis\)\s*:\s*/gi,
    "",
  );
  cleaned = cleaned.replace(
    /\s*\(rôle(?:\s+actif)?\s*:\s*PLATFORM_ADMIN\)/gi,
    "",
  );
  cleaned = cleaned.replace(/\bPLATFORM_ADMIN\b/g, "Administrateur");
  cleaned = cleaned.replace(
    /\s*«\s*([^»]+)\s*»\s*(?:\[(?:S\d+|G\d+|O\d+)\]\s*)+(\.?)$/i,
    (_, inner: string, dot: string) => ` « ${inner.trim()} »${dot || "."}`,
  );
  cleaned = cleaned.replace(
    /(?:\s*\[(?:S\d+|G\d+|O\d+)\])+(\.?)\s*$/g,
    (_, trailingDot: string) => (trailingDot ? "." : ""),
  );
  return cleaned.trim();
}

export interface AssistantUserQuestionBubbleProps {
  readonly userPrompt: string;
  readonly isFr?: boolean;
  readonly modelLabel?: string;
  readonly effortLabel?: string;
  readonly attachedFiles?: readonly UiAssistantAttachedFileItem[];
  readonly testId?: string;
}

export function AssistantUserQuestionBubble({
  userPrompt,
  attachedFiles = [],
  testId = "assistant-user-question-bubble",
}: AssistantUserQuestionBubbleProps): React.JSX.Element {
  return (
    <div className="flex flex-col items-end space-y-1">
      <div
        data-testid={testId}
        style={{
          marginLeft: "auto",
          maxWidth: "75%",
          borderRadius: "18px 18px 4px 18px",
          backgroundColor: "var(--color-action-primary)",
          color: "var(--color-primary-foreground)",
          padding: "10px 16px",
          fontWeight: 500,
        }}
        className="text-xs leading-relaxed whitespace-pre-wrap shadow-sm"
      >
        {userPrompt}
      </div>
      {attachedFiles.length > 0 && (
        <div
          data-testid="assistant-user-question-attached-files"
          className="flex flex-wrap justify-end gap-1.5 pt-0.5"
        >
          {attachedFiles.map((file) => (
            <span
              key={file.id}
              data-testid="assistant-user-question-attached-pill"
              className="inline-flex items-center gap-1 rounded-md bg-surface-secondary px-2 py-0.5 text-[11px] font-medium text-text-secondary"
            >
              <OrciaIcon
                name={file.sourceKind === "LOCAL_PC" ? "laptop" : "workspaceFolder"}
              />
              <span>{file.name}</span>
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
