import React from "react";
import type { PackComposerModalLabels } from "./PackUiTypes";

export interface PackComposerScopeOption {
  readonly id: string;
  readonly label: string;
  readonly scopeType: "BU" | "TEAM" | "WORKSPACE";
}

export interface PackComposerMetadataStepProps {
  readonly slug: string;
  readonly name: string;
  readonly version: string;
  readonly description: string;
  readonly author: string;
  readonly scopeType: "BU" | "TEAM" | "WORKSPACE";
  readonly scopeId: string;
  readonly scopeOptions: readonly PackComposerScopeOption[];
  readonly isEditingExisting: boolean;
  readonly readOnlyObserver: boolean;
  readonly isBusy: boolean;
  readonly labels: PackComposerModalLabels;
  readonly onChangeSlug: (next: string) => void;
  readonly onChangeName: (next: string) => void;
  readonly onChangeVersion: (next: string) => void;
  readonly onChangeDescription: (next: string) => void;
  readonly onChangeAuthor: (next: string) => void;
  readonly onChangeScopeType: (next: "BU" | "TEAM" | "WORKSPACE") => void;
  readonly onChangeScopeId: (next: string) => void;
}

export function PackComposerMetadataStep({
  slug,
  name,
  version,
  description,
  author,
  scopeType,
  scopeId,
  scopeOptions,
  isEditingExisting,
  readOnlyObserver,
  isBusy,
  labels,
  onChangeSlug,
  onChangeName,
  onChangeVersion,
  onChangeDescription,
  onChangeAuthor,
  onChangeScopeType,
  onChangeScopeId,
}: PackComposerMetadataStepProps): React.ReactElement {
  const filteredScopes = scopeOptions.filter((opt) => opt.scopeType === scopeType);
  const effectiveScopeId = filteredScopes.some((opt) => opt.id === scopeId)
    ? scopeId
    : (filteredScopes[0]?.id ?? scopeId);

  return (
    <div
      className="grid grid-cols-1 gap-3 sm:grid-cols-2"
      data-testid="pack-composer-metadata-step"
    >
      <label className="orcia-ds-label">
        <span>{labels.slugLabel}</span>
        <input
          type="text"
          value={slug}
          disabled={isEditingExisting || readOnlyObserver || isBusy}
          autoComplete="off"
          data-lpignore="true"
          data-1p-ignore="true"
          data-bwignore="true"
          data-form-type="other"
          data-testid="pack-composer-slug-input"
          onChange={(e) => onChangeSlug(e.target.value)}
          className="orcia-ds-input font-mono"
        />
      </label>
      <label className="orcia-ds-label">
        <span>{labels.nameLabel}</span>
        <input
          type="text"
          value={name}
          disabled={readOnlyObserver || isBusy}
          autoComplete="off"
          data-lpignore="true"
          data-1p-ignore="true"
          data-bwignore="true"
          data-form-type="other"
          data-testid="pack-composer-name-input"
          onChange={(e) => onChangeName(e.target.value)}
          className="orcia-ds-input"
        />
      </label>
      <label className="orcia-ds-label">
        <span>{labels.versionLabel}</span>
        <input
          type="text"
          value={version}
          disabled={readOnlyObserver || isBusy}
          autoComplete="off"
          data-lpignore="true"
          data-1p-ignore="true"
          data-bwignore="true"
          data-form-type="other"
          data-testid="pack-composer-version-input"
          onChange={(e) => onChangeVersion(e.target.value)}
          className="orcia-ds-input font-mono"
        />
      </label>
      <label className="orcia-ds-label">
        <span>{labels.authorLabel}</span>
        <input
          type="text"
          value={author}
          disabled={readOnlyObserver || isBusy}
          autoComplete="off"
          data-lpignore="true"
          data-1p-ignore="true"
          data-bwignore="true"
          data-form-type="other"
          data-testid="pack-composer-author-input"
          onChange={(e) => onChangeAuthor(e.target.value)}
          className="orcia-ds-input"
        />
      </label>
      <label className="orcia-ds-label sm:col-span-2">
        <span>{labels.descriptionLabel}</span>
        <input
          type="text"
          value={description}
          disabled={readOnlyObserver || isBusy}
          autoComplete="off"
          data-lpignore="true"
          data-1p-ignore="true"
          data-bwignore="true"
          data-form-type="other"
          data-testid="pack-composer-description-input"
          onChange={(e) => onChangeDescription(e.target.value)}
          className="orcia-ds-input"
        />
      </label>
      <label className="orcia-ds-label">
        <span>{labels.scopeTypeLabel}</span>
        <select
          data-testid="pack-composer-scope-type-select"
          value={scopeType}
          disabled={isEditingExisting || readOnlyObserver || isBusy}
          onChange={(e) => onChangeScopeType(e.target.value as "BU" | "TEAM" | "WORKSPACE")}
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
          data-testid="pack-composer-scope-id-select"
          value={effectiveScopeId}
          disabled={isEditingExisting || readOnlyObserver || isBusy}
          onChange={(e) => onChangeScopeId(e.target.value)}
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
  );
}
