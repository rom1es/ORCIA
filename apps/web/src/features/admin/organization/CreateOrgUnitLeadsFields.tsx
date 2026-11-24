import { OrciaUserPillsSelect, type KnownUserOption } from "@orcia/ui";
import React from "react";
import type { AdminAndStudioDictionarySection } from "../../../i18n/locales/admin_and_studio_labels";

interface CreateOrgUnitLeadsFieldsProps {
  readonly kind: "BU" | "TEAM";
  readonly canMutate: boolean;
  readonly isSubmitting: boolean;
  readonly labels: AdminAndStudioDictionarySection["settingsHub"]["organizationTab"]["createModal"];
  readonly leadUserIds: readonly string[];
  readonly onChangeLeadUserIds: (ids: readonly string[]) => void;
  readonly leadDraft: string;
  readonly onChangeLeadDraft: (val: string) => void;
  readonly leadKnownUsers: readonly KnownUserOption[];
  readonly leadValidationError: string | null;
  readonly ontologyLeadUserIds: readonly string[];
  readonly onChangeOntologyLeadUserIds: (ids: readonly string[]) => void;
  readonly ontologyLeadDraft: string;
  readonly onChangeOntologyLeadDraft: (val: string) => void;
  readonly ontologyKnownUsers: readonly KnownUserOption[];
}

export function CreateOrgUnitLeadsFields({
  kind,
  canMutate,
  isSubmitting,
  labels,
  leadUserIds,
  onChangeLeadUserIds,
  leadDraft,
  onChangeLeadDraft,
  leadKnownUsers,
  leadValidationError,
  ontologyLeadUserIds,
  onChangeOntologyLeadUserIds,
  ontologyLeadDraft,
  onChangeOntologyLeadDraft,
  ontologyKnownUsers,
}: CreateOrgUnitLeadsFieldsProps): React.ReactElement {
  return (
    <>
      <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
        <label htmlFor="org-unit-lead-input" className="orcia-ds-label">
          {labels.leadLabel}
        </label>
        <OrciaUserPillsSelect
          inputId="org-unit-lead-input"
          inputTestId="org-unit-lead-input"
          disabled={!canMutate || isSubmitting}
          selectedUserIds={leadUserIds}
          onChange={onChangeLeadUserIds}
          draftQuery={leadDraft}
          onDraftQueryChange={onChangeLeadDraft}
          knownUsers={leadKnownUsers}
          placeholder={labels.leadPlaceholder}
        />
        {leadValidationError ? (
          <div
            data-testid="org-unit-unknown-user-error"
            style={{ fontSize: "12px", color: "var(--color-status-error)", marginTop: "2px" }}
          >
            {leadValidationError}
          </div>
        ) : null}
      </div>

      {kind === "BU" ? (
        <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
          <label htmlFor="org-unit-ontology-lead-input" className="orcia-ds-label">
            {labels.ontologyLeadLabel}
          </label>
          <OrciaUserPillsSelect
            inputId="org-unit-ontology-lead-input"
            inputTestId="org-unit-ontology-lead-input"
            disabled={!canMutate || isSubmitting}
            selectedUserIds={ontologyLeadUserIds}
            onChange={onChangeOntologyLeadUserIds}
            draftQuery={ontologyLeadDraft}
            onDraftQueryChange={onChangeOntologyLeadDraft}
            knownUsers={ontologyKnownUsers}
            placeholder={labels.ontologyLeadPlaceholder}
          />
        </div>
      ) : null}
    </>
  );
}
