import React from "react";
import { OrciaIcon } from "../components/icons";

export interface UiAssistantAttachedFileItem {
  readonly id: string;
  readonly name: string;
  readonly sourceKind: "LOCAL_PC" | "ORCIA_WORKSPACE";
  readonly uri?: string;
  readonly contentExcerpt?: string;
}

export interface AssistantAttachedFilesInlineBarProps {
  readonly attachedFiles: readonly UiAssistantAttachedFileItem[];
  readonly removeFilePrefix: string;
  readonly onRemoveAttachedFile: (fileId: string) => void;
}

export function AssistantAttachedFilesInlineBar({
  attachedFiles,
  removeFilePrefix,
  onRemoveAttachedFile,
}: AssistantAttachedFilesInlineBarProps): React.JSX.Element | null {
  if (attachedFiles.length === 0) {
    return null;
  }
  return (
    <div
      data-testid="assistant-attached-files-bar"
      className="flex flex-wrap items-center gap-1.5"
    >
      {attachedFiles.map((file) => (
        <span
          key={file.id}
          data-testid="assistant-attached-file-pill"
          className="inline-flex items-center gap-1.5 rounded-md bg-surface-secondary px-2 py-0.5 text-[11px] font-medium text-text-primary"
        >
          <OrciaIcon name={file.sourceKind === "LOCAL_PC" ? "laptop" : "workspaceFolder"} />
          <span>{file.name}</span>
          <button
            type="button"
            aria-label={`${removeFilePrefix} ${file.name}`}
            title={`${removeFilePrefix} ${file.name}`}
            onClick={() => onRemoveAttachedFile(file.id)}
            className="border-0 bg-transparent p-0.5 text-text-secondary hover:text-text-primary leading-none"
          >
            <OrciaIcon name="times" />
          </button>
        </span>
      ))}
    </div>
  );
}
