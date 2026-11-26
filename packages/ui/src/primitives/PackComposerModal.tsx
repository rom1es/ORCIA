import React, { useEffect, useState } from "react";
import { OrciaAlertBanner } from "./OrciaAlertBanner";
import { OrciaDialog } from "./OrciaDialog";
import {
  memberSelectionKey,
  PackComposerMembersStep,
} from "./PackComposerMembersStep";
import {
  PackComposerMetadataStep,
  type PackComposerScopeOption,
} from "./PackComposerMetadataStep";
import type {
  PackComposerModalLabels,
  UiPackDraftItem,
  UiPackDraftMemberOption,
} from "./PackUiTypes";

export type { PackComposerScopeOption };

export interface PackComposerSavePayload {
  readonly bundleId?: string;
  readonly slug: string;
  readonly name: string;
  readonly version: string;
  readonly description: string;
  readonly author: string;
  readonly license: string;
  readonly scopeType: "BU" | "TEAM" | "WORKSPACE";
  readonly scopeId: string;
  readonly members: readonly UiPackDraftMemberOption[];
}

export interface PackComposerModalProps {
  readonly open: boolean;
  readonly draft: UiPackDraftItem | null;
  readonly availableMembers: readonly UiPackDraftMemberOption[];
  readonly scopeOptions: readonly PackComposerScopeOption[];
  readonly defaultScopeId?: string;
  readonly readOnlyObserver?: boolean;
  readonly isBusy?: boolean;
  readonly errorMessage?: string | null;
  readonly labels: PackComposerModalLabels;
  readonly onOpenChange: (open: boolean) => void;
  readonly onSaveDraft: (payload: PackComposerSavePayload) => Promise<void> | void;
  readonly onPublishDraft: (
    draftId: string,
    autoIncludeDependencies: boolean,
  ) => Promise<void> | void;
  readonly onExportDraftZip: (
    draftId: string,
    autoIncludeDependencies: boolean,
  ) => Promise<void> | void;
}

export function PackComposerModal({
  open,
  draft,
  availableMembers,
  scopeOptions,
  defaultScopeId = "",
  readOnlyObserver = false,
  isBusy = false,
  errorMessage = null,
  labels,
  onOpenChange,
  onSaveDraft,
  onPublishDraft,
  onExportDraftZip,
}: PackComposerModalProps): React.ReactElement {
  const [step, setStep] = useState<"metadata" | "members">("metadata");
  const [slug, setSlug] = useState("");
  const [name, setName] = useState("");
  const [version, setVersion] = useState("0.1.0");
  const [description, setDescription] = useState("");
  const [author, setAuthor] = useState("");
  const [license, setLicense] = useState("Apache-2.0");
  const [scopeType, setScopeType] = useState<"BU" | "TEAM" | "WORKSPACE">("WORKSPACE");
  const [scopeId, setScopeId] = useState(defaultScopeId || scopeOptions[0]?.id || "");
  const [selectedMembers, setSelectedMembers] = useState<readonly UiPackDraftMemberOption[]>([]);
  const [autoInclude, setAutoInclude] = useState(false);

  useEffect(() => {
    if (!open) return;
    if (draft) {
      setSlug(draft.slug);
      setName(draft.name);
      setVersion(draft.version);
      setDescription(draft.description);
      setAuthor(draft.author);
      setLicense(draft.license);
      setScopeType(draft.scopeType);
      setScopeId(draft.scopeId);
      setSelectedMembers(draft.members);
      setStep("members");
    } else {
      setSlug("");
      setName("");
      setVersion("0.1.0");
      setDescription("");
      setAuthor("");
      setLicense("Apache-2.0");
      setScopeType("WORKSPACE");
      setScopeId(defaultScopeId || scopeOptions[0]?.id || "");
      setSelectedMembers([]);
      setStep("metadata");
    }
    setAutoInclude(false);
  }, [open, draft, defaultScopeId, scopeOptions]);

  const filteredScopes = scopeOptions.filter((opt) => opt.scopeType === scopeType);
  const effectiveScopeId = filteredScopes.some((opt) => opt.id === scopeId)
    ? scopeId
    : (filteredScopes[0]?.id ?? scopeId);

  const toggleMember = (option: UiPackDraftMemberOption) => {
    const key = memberSelectionKey(option);
    setSelectedMembers((prev) =>
      prev.some((m) => memberSelectionKey(m) === key)
        ? prev.filter((m) => memberSelectionKey(m) !== key)
        : [...prev, option],
    );
  };

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    if (readOnlyObserver || isBusy || !slug.trim() || !name.trim() || !effectiveScopeId) return;
    void onSaveDraft({
      bundleId: draft?.bundleId,
      slug: slug.trim().toLowerCase(),
      name: name.trim(),
      version: version.trim() || "0.1.0",
      description: description.trim(),
      author: author.trim(),
      license: license.trim(),
      scopeType,
      scopeId: effectiveScopeId,
      members: selectedMembers,
    });
  };

  return (
    <OrciaDialog
      open={open}
      onOpenChange={onOpenChange}
      title={draft ? labels.editTitle : labels.createTitle}
      testId="pack-composer-modal"
      closeLabel={labels.closeLabel}
    >
      <form
        onSubmit={handleSave}
        autoComplete="off"
        data-lpignore="true"
        data-1p-ignore="true"
        data-bwignore="true"
        data-form-type="other"
        className="orcia-ds-dialog-body flex flex-col gap-3"
      >
        {errorMessage ? (
          <OrciaAlertBanner tone="crimson" role="alert" testId="pack-composer-error-alert">
            {errorMessage}
          </OrciaAlertBanner>
        ) : null}

        <div className="orcia-ds-tabs" role="tablist">
          <button
            type="button"
            role="tab"
            aria-selected={step === "metadata"}
            data-testid="pack-composer-tab-metadata"
            onClick={() => setStep("metadata")}
            className="orcia-ds-filter-pill"
          >
            {labels.stepMetadataTab}
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={step === "members"}
            data-testid="pack-composer-tab-members"
            onClick={() => setStep("members")}
            className="orcia-ds-filter-pill"
          >
            {labels.stepMembersTab}
          </button>
        </div>

        {step === "metadata" ? (
          <PackComposerMetadataStep
            slug={slug}
            name={name}
            version={version}
            description={description}
            author={author}
            scopeType={scopeType}
            scopeId={effectiveScopeId}
            scopeOptions={scopeOptions}
            isEditingExisting={Boolean(draft)}
            readOnlyObserver={readOnlyObserver}
            isBusy={isBusy}
            labels={labels}
            onChangeSlug={setSlug}
            onChangeName={setName}
            onChangeVersion={setVersion}
            onChangeDescription={setDescription}
            onChangeAuthor={setAuthor}
            onChangeScopeType={(nextType) => {
              setScopeType(nextType);
              const firstMatch = scopeOptions.find((o) => o.scopeType === nextType);
              if (firstMatch) setScopeId(firstMatch.id);
            }}
            onChangeScopeId={setScopeId}
          />
        ) : (
          <PackComposerMembersStep
            availableMembers={availableMembers}
            selectedMemberKeys={selectedMembers.map(memberSelectionKey)}
            closureComplete={draft?.closureComplete ?? true}
            missingDependencies={draft?.missingDependencies ?? []}
            nonActiveDependencies={draft?.nonActiveDependencies ?? []}
            proseWarnings={draft?.proseWarnings ?? []}
            autoIncludeDependencies={autoInclude}
            readOnlyObserver={readOnlyObserver}
            isBusy={isBusy}
            labels={labels}
            onToggleMember={toggleMember}
            onToggleAutoInclude={setAutoInclude}
          />
        )}

        <div className="orcia-ds-dialog-footer flex flex-wrap justify-end gap-2 pt-2">
          <button
            type="button"
            data-testid="pack-composer-close-btn"
            onClick={() => onOpenChange(false)}
            className="orcia-ds-btn orcia-ds-btn-secondary orcia-ds-btn-sm"
          >
            {labels.closeLabel}
          </button>
          <button
            type="submit"
            data-testid="pack-composer-save-draft-btn"
            disabled={readOnlyObserver || isBusy || !slug.trim() || !name.trim() || !effectiveScopeId}
            className="orcia-ds-btn orcia-ds-btn-secondary orcia-ds-btn-sm"
          >
            {isBusy ? labels.savingBtn : labels.saveDraftBtn}
          </button>
          {draft ? (
            <>
              <button
                type="button"
                data-testid="pack-composer-publish-btn"
                disabled={readOnlyObserver || isBusy}
                onClick={() => void onPublishDraft(draft.bundleId, autoInclude)}
                className="orcia-ds-btn orcia-ds-btn-secondary orcia-ds-btn-sm"
              >
                {labels.publishBtn}
              </button>
              <button
                type="button"
                data-testid="pack-composer-export-btn"
                disabled={readOnlyObserver || isBusy}
                onClick={() => void onExportDraftZip(draft.bundleId, autoInclude)}
                className="orcia-ds-btn orcia-ds-btn-primary orcia-ds-btn-sm"
              >
                {labels.exportZipBtn}
              </button>
            </>
          ) : null}
        </div>
      </form>
    </OrciaDialog>
  );
}
