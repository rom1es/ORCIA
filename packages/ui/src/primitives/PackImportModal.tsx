import React, { useRef, useState } from "react";
import { OrciaIcon } from "../components/icons";
import { OrciaAlertBanner } from "./OrciaAlertBanner";
import { OrciaDialog } from "./OrciaDialog";
import type { PackImportModalLabels, UiPackScopeType } from "./PackUiTypes";

export interface PackImportScopeOption {
  readonly id: string;
  readonly label: string;
  readonly scopeType: Exclude<UiPackScopeType, "GLOBAL">;
}

export interface PackImportModalProps {
  readonly open: boolean;
  readonly scopeOptions: readonly PackImportScopeOption[];
  readonly defaultWorkspaceId?: string;
  readonly readOnlyObserver?: boolean;
  readonly isSubmitting?: boolean;
  readonly errorMessage?: string | null;
  readonly labels: PackImportModalLabels;
  readonly onOpenChange: (open: boolean) => void;
  readonly onSubmitImport: (input: {
    readonly file: File;
    readonly scopeType: Exclude<UiPackScopeType, "GLOBAL">;
    readonly scopeId: string;
    readonly replaceDraft: boolean;
  }) => Promise<void> | void;
}

export function PackImportModal({
  open,
  scopeOptions,
  defaultWorkspaceId = "",
  readOnlyObserver = false,
  isSubmitting = false,
  errorMessage = null,
  labels,
  onOpenChange,
  onSubmitImport,
}: PackImportModalProps): React.ReactElement {
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [scopeType, setScopeType] = useState<Exclude<UiPackScopeType, "GLOBAL">>("WORKSPACE");
  const [scopeId, setScopeId] = useState<string>(defaultWorkspaceId || scopeOptions[0]?.id || "");
  const [replaceDraft, setReplaceDraft] = useState<boolean>(false);

  const filteredScopes = scopeOptions.filter((opt) => opt.scopeType === scopeType);
  const effectiveScopeId = filteredScopes.some((opt) => opt.id === scopeId)
    ? scopeId
    : (filteredScopes[0]?.id ?? scopeId);

  const handleScopeTypeChange = (nextType: Exclude<UiPackScopeType, "GLOBAL">) => {
    setScopeType(nextType);
    const firstMatch = scopeOptions.find((opt) => opt.scopeType === nextType);
    if (firstMatch) setScopeId(firstMatch.id);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile || !effectiveScopeId || readOnlyObserver || isSubmitting) return;
    void onSubmitImport({
      file: selectedFile,
      scopeType,
      scopeId: effectiveScopeId,
      replaceDraft,
    });
  };

  return (
    <OrciaDialog
      open={open}
      onOpenChange={onOpenChange}
      title={labels.modalTitle}
      description={labels.modalDescription}
      testId="pack-import-modal"
      closeLabel={labels.closeLabel}
    >
      <form
        onSubmit={handleSubmit}
        autoComplete="off"
        data-lpignore="true"
        data-1p-ignore="true"
        data-bwignore="true"
        data-form-type="other"
        className="orcia-ds-dialog-body flex flex-col gap-3"
      >
        {errorMessage ? (
          <OrciaAlertBanner tone="crimson" role="alert" testId="pack-import-error-alert">
            {errorMessage}
          </OrciaAlertBanner>
        ) : null}
        {readOnlyObserver ? (
          <OrciaAlertBanner tone="amber" role="status" testId="pack-import-observer-banner">
            {labels.observerBlockedHint}
          </OrciaAlertBanner>
        ) : null}

        <div className="flex flex-col gap-1.5">
          <span className="orcia-ds-label">{labels.fileFieldLabel}</span>
          <input
            ref={fileInputRef}
            type="file"
            accept=".zip,.yaml,.yml"
            autoComplete="off"
            data-lpignore="true"
            data-1p-ignore="true"
            data-bwignore="true"
            data-form-type="other"
            data-testid="pack-import-file-input"
            className="sr-only"
            onChange={(e) => {
              const picked = e.target.files?.[0] ?? null;
              setSelectedFile(picked);
            }}
          />
          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              data-testid="pack-import-choose-file-btn"
              disabled={readOnlyObserver || isSubmitting}
              onClick={() => fileInputRef.current?.click()}
              className="orcia-ds-btn orcia-ds-btn-secondary orcia-ds-btn-sm"
            >
              <OrciaIcon name="pack" size={14} />
              <span>{labels.chooseFileBtn}</span>
            </button>
            <span
              data-testid="pack-import-selected-filename"
              className="font-mono text-xs text-[var(--orcia-text-secondary)]"
            >
              {selectedFile ? selectedFile.name : labels.noFileSelected}
            </span>
          </div>
        </div>

        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <label className="orcia-ds-label">
            <span>{labels.scopeTypeLabel}</span>
            <select
              data-testid="pack-import-scope-type-select"
              value={scopeType}
              disabled={readOnlyObserver || isSubmitting}
              onChange={(e) =>
                handleScopeTypeChange(e.target.value as Exclude<UiPackScopeType, "GLOBAL">)
              }
              className="orcia-ds-select"
            >
              <option value="WORKSPACE">{labels.scopeWorkspaceLabel}</option>
              <option value="TEAM">{labels.scopeTeamLabel}</option>
              <option value="BU">{labels.scopeBuLabel}</option>
            </select>
          </label>

          <label className="orcia-ds-label">
            <span>{labels.scopeTargetLabel}</span>
            <select
              data-testid="pack-import-scope-id-select"
              value={effectiveScopeId}
              disabled={readOnlyObserver || isSubmitting || filteredScopes.length === 0}
              onChange={(e) => setScopeId(e.target.value)}
              className="orcia-ds-select"
            >
              {filteredScopes.map((opt) => (
                <option key={opt.id} value={opt.id}>
                  {opt.label}
                </option>
              ))}
            </select>
          </label>
        </div>

        <label className="inline-flex items-center gap-2 text-xs">
          <input
            type="checkbox"
            autoComplete="off"
            data-lpignore="true"
            data-1p-ignore="true"
            data-bwignore="true"
            data-form-type="other"
            data-testid="pack-import-replace-draft-checkbox"
            checked={replaceDraft}
            disabled={readOnlyObserver || isSubmitting}
            onChange={(e) => setReplaceDraft(e.target.checked)}
          />
          <span>{labels.replaceDraftLabel}</span>
        </label>

        <div className="orcia-ds-dialog-footer flex justify-end gap-2 pt-2">
          <button
            type="button"
            data-testid="pack-import-cancel-btn"
            onClick={() => onOpenChange(false)}
            className="orcia-ds-btn orcia-ds-btn-secondary orcia-ds-btn-sm"
          >
            {labels.cancelBtn}
          </button>
          <button
            type="submit"
            data-testid="pack-import-submit-btn"
            disabled={readOnlyObserver || isSubmitting || !selectedFile || !effectiveScopeId}
            className="orcia-ds-btn orcia-ds-btn-primary orcia-ds-btn-sm"
          >
            {isSubmitting ? labels.submittingBtn : labels.submitBtn}
          </button>
        </div>
      </form>
    </OrciaDialog>
  );
}
