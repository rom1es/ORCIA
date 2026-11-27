import React, { useRef, useState } from "react";
import { OrciaIcon } from "../components/icons";
import {
  AssistantAttachedFilesInlineBar,
  type AssistantAttachedFilesInlineBarProps,
  type UiAssistantAttachedFileItem,
} from "./AssistantAttachedFilesInlineBar";

export {
  AssistantAttachedFilesInlineBar,
  type AssistantAttachedFilesInlineBarProps,
  type UiAssistantAttachedFileItem,
};

export interface UiAssistantAutocompleteOption {
  readonly slug: string;
  readonly label: string;
  readonly description: string;
  readonly kind: "agent" | "skill";
  readonly badge?: string;
}

export interface UiAssistantOrciaDocumentOption {
  readonly id: string;
  readonly title: string;
  readonly uri: string;
}

export interface AssistantPromptPlusLabels {
  readonly removeFilePrefix: string;
  readonly selectAgentHeading: string;
  readonly selectSkillHeading: string;
  readonly plusInsertAgentLabel: string;
  readonly plusInsertSkillLabel: string;
  readonly plusUploadLocalFileLabel: string;
  readonly plusAttachOrciaDocLabel: string;
  readonly plusOpenFoldersLabel: string;
}

export function detectActiveAutocompleteTrigger(promptText: string): {
  readonly kind: "agent" | "skill";
  readonly query: string;
  readonly tokenStartIndex: number;
} | null {
  const match = /(?:^|\s)([@/])([a-zA-Z0-9_/:.-]*)$/.exec(promptText);
  if (!match) {
    return null;
  }
  const symbol = match[1];
  const query = match[2] ?? "";
  const fullMatch = match[0];
  const leadingSpaceOffset = fullMatch.startsWith(" ") ? 1 : 0;
  const tokenStartIndex = match.index + leadingSpaceOffset;
  return {
    kind: symbol === "@" ? "agent" : "skill",
    query,
    tokenStartIndex,
  };
}

export function applyAutocompleteSelectionToPrompt(
  promptText: string,
  option: UiAssistantAutocompleteOption,
): string {
  const prefix = option.kind === "agent" ? `@${option.slug}` : `/${option.slug}`;
  const active = detectActiveAutocompleteTrigger(promptText);
  const stripped =
    active !== null
      ? `${promptText.slice(0, active.tokenStartIndex)}${promptText.slice(
          active.tokenStartIndex + 1 + active.query.length,
        )}`.trim()
      : promptText.trim();
  if (stripped.startsWith(`${prefix} `) || stripped === prefix) {
    return `${stripped} `;
  }
  return stripped ? `${prefix} ${stripped} ` : `${prefix} `;
}

export interface AssistantPromptPlusAndAutocompleteProps {
  readonly plusMenuOpen: boolean;
  readonly autocompleteTrigger: {
    readonly kind: "agent" | "skill";
    readonly query: string;
  } | null;
  readonly agentOptions?: readonly UiAssistantAutocompleteOption[];
  readonly skillOptions?: readonly UiAssistantAutocompleteOption[];
  readonly orciaDocuments?: readonly UiAssistantOrciaDocumentOption[];
  readonly attachedFiles?: readonly UiAssistantAttachedFileItem[];
  readonly labels: AssistantPromptPlusLabels;
  readonly onSelectAutocompleteOption: (option: UiAssistantAutocompleteOption) => void;
  readonly onTriggerAgentAutocompleteFromPlus: () => void;
  readonly onTriggerSkillAutocompleteFromPlus: () => void;
  readonly onAttachFile: (file: UiAssistantAttachedFileItem) => void;
  readonly onRemoveAttachedFile?: (fileId: string) => void;
  readonly onOpenFoldersAndCloseMenus?: () => void;
}

export function AssistantPromptPlusAndAutocomplete({
  plusMenuOpen,
  autocompleteTrigger,
  agentOptions = [],
  skillOptions = [],
  orciaDocuments = [],
  labels,
  onSelectAutocompleteOption,
  onTriggerAgentAutocompleteFromPlus,
  onTriggerSkillAutocompleteFromPlus,
  onAttachFile,
  onOpenFoldersAndCloseMenus,
}: AssistantPromptPlusAndAutocompleteProps): React.JSX.Element {
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [orciaDocsSubmenuOpen, setOrciaDocsSubmenuOpen] = useState<boolean>(false);

  const filteredOptions =
    autocompleteTrigger === null
      ? []
      : (autocompleteTrigger.kind === "agent" ? agentOptions : skillOptions).filter(
          (opt) => {
            const q = autocompleteTrigger.query.toLowerCase();
            return !q || opt.slug.toLowerCase().includes(q) || opt.label.toLowerCase().includes(q);
          },
        );

  return (
    <>
      <input
        ref={fileInputRef}
        type="file"
        autoComplete="off"
        data-lpignore="true"
        data-1p-ignore="true"
        data-bwignore="true"
        data-form-type="other"
        data-testid="assistant-local-file-input"
        style={{ display: "none" }}
        onChange={(e) => {
          const picked = e.target.files?.[0];
          if (picked) {
            onAttachFile({
              id: `local-${Date.now()}-${picked.name}`,
              name: picked.name,
              sourceKind: "LOCAL_PC",
              uri: `#local-file-${encodeURIComponent(picked.name)}`,
            });
          }
          e.target.value = "";
        }}
      />

      {autocompleteTrigger !== null && filteredOptions.length > 0 && (
        <div
          data-testid="assistant-autocomplete-dropdown"
          data-trigger-kind={autocompleteTrigger.kind}
          role="listbox"
          style={{ position: "absolute", bottom: "calc(100% + 8px)", left: 0, zIndex: 45, minWidth: "300px" }}
          className="rounded-xl border border-border-subtle bg-surface-primary p-2 text-xs shadow-lg space-y-1"
        >
          <div className="px-2 py-1 text-[11px] font-semibold text-text-secondary border-b border-border-subtle">
            {autocompleteTrigger.kind === "agent" ? (
              <><OrciaIcon name="agents" /> {labels.selectAgentHeading}</>
            ) : (
              <><OrciaIcon name="tools" /> {labels.selectSkillHeading}</>
            )}
          </div>
          {filteredOptions.map((opt, idx) => (
            <button
              key={`${opt.kind}-${opt.slug}`}
              type="button"
              role="option"
              aria-selected={idx === 0}
              data-testid={`assistant-autocomplete-option-${opt.slug}`}
              onClick={() => onSelectAutocompleteOption(opt)}
              className={`flex w-full flex-col items-start rounded-lg px-2.5 py-1.5 text-left hover:bg-surface-secondary ${
                idx === 0 ? "bg-surface-secondary/70" : ""
              }`}
            >
              <div className="flex w-full items-center justify-between gap-2">
                <span className="font-semibold text-text-primary">
                  {opt.kind === "agent" ? `@${opt.slug}` : `/${opt.slug}`} — {opt.label}
                </span>
                {opt.badge ? (
                  <span
                    data-testid={`assistant-autocomplete-badge-${opt.slug}`}
                    className="rounded-full border border-border-subtle bg-surface-secondary px-2 py-0.5 font-mono text-[10px] font-semibold text-text-secondary"
                  >
                    {opt.badge}
                  </span>
                ) : null}
              </div>
              <span className="text-[11px] text-text-secondary">{opt.description}</span>
            </button>
          ))}
        </div>
      )}

      {plusMenuOpen && (
        <div
          data-testid="assistant-prompt-plus-popover"
          role="menu"
          style={{ position: "absolute", bottom: "calc(100% + 8px)", left: 0, zIndex: 40, minWidth: "290px" }}
          className="flex flex-col gap-1 rounded-xl border border-border-subtle bg-surface-primary p-2 text-xs shadow-lg"
        >
          <button
            type="button"
            role="menuitem"
            data-testid="assistant-plus-insert-agent-btn"
            onClick={() => { setOrciaDocsSubmenuOpen(false); onTriggerAgentAutocompleteFromPlus(); }}
            className="flex w-full items-center gap-2 rounded-lg px-2.5 py-1.5 text-left font-medium text-text-primary hover:bg-surface-secondary"
          >
            <span>{labels.plusInsertAgentLabel}</span>
          </button>

          <button
            type="button"
            role="menuitem"
            data-testid="assistant-plus-insert-skill-btn"
            onClick={() => { setOrciaDocsSubmenuOpen(false); onTriggerSkillAutocompleteFromPlus(); }}
            className="flex w-full items-center gap-2 rounded-lg px-2.5 py-1.5 text-left font-medium text-text-primary hover:bg-surface-secondary"
          >
            <span>{labels.plusInsertSkillLabel}</span>
          </button>

          <button
            type="button"
            role="menuitem"
            data-testid="assistant-plus-upload-local-file-btn"
            onClick={() => { setOrciaDocsSubmenuOpen(false); fileInputRef.current?.click(); }}
            className="flex w-full items-center gap-2 rounded-lg px-2.5 py-1.5 text-left font-medium text-text-primary hover:bg-surface-secondary"
          >
            <span><OrciaIcon name="laptop" /> {labels.plusUploadLocalFileLabel}</span>
          </button>

          <button
            type="button"
            role="menuitem"
            data-testid="assistant-plus-attach-orcia-doc-btn"
            onClick={() => setOrciaDocsSubmenuOpen((prev) => !prev)}
            className="flex w-full items-center justify-between gap-2 rounded-lg px-2.5 py-1.5 text-left font-medium text-text-primary hover:bg-surface-secondary"
          >
            <span><OrciaIcon name="workspaceFolder" /> {labels.plusAttachOrciaDocLabel}</span>
            <OrciaIcon name="caretRight" />
          </button>

          {orciaDocsSubmenuOpen && (
            <div data-testid="assistant-plus-orcia-docs-submenu" className="ml-2 space-y-1 border-l border-border-subtle pl-2 py-1">
              {orciaDocuments.map((doc) => (
                <button
                  key={doc.id}
                  type="button"
                  data-testid={`assistant-orcia-doc-option-${doc.id}`}
                  onClick={() => {
                    onAttachFile({ id: `orcia-${doc.id}`, name: doc.title, sourceKind: "ORCIA_WORKSPACE", uri: doc.uri });
                    setOrciaDocsSubmenuOpen(false);
                  }}
                  className="flex w-full items-center gap-1.5 rounded px-2 py-1 text-left text-[11px] text-text-secondary hover:bg-surface-secondary hover:text-text-primary"
                >
                  <span><OrciaIcon name="document" /> {doc.title}</span>
                </button>
              ))}
            </div>
          )}

          {onOpenFoldersAndCloseMenus && (
            <button
              type="button"
              role="menuitem"
              data-testid="assistant-plus-open-folders-btn"
              onClick={() => { setOrciaDocsSubmenuOpen(false); onOpenFoldersAndCloseMenus(); }}
              className="flex w-full items-center gap-2 rounded-lg border-t border-border-subtle pt-2 mt-1 px-2.5 py-1.5 text-left font-medium text-text-primary hover:bg-surface-secondary"
            >
              <span><OrciaIcon name="folder" /> {labels.plusOpenFoldersLabel}</span>
            </button>
          )}
        </div>
      )}
    </>
  );
}
