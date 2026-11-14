import { OrciaAlertBanner, OrciaButton, OrciaDialog, OrciaIcon } from "@orcia/ui";
import React from "react";
import type { AdminAndStudioDictionarySection } from "../../../i18n/locales/admin_and_studio_labels";
import { buildNonEmptyDeleteSummary, type OrgTreeRowItem } from "./orgTreeHelpers";

export interface ConfirmDeleteOrgUnitModalProps {
  readonly rowItem: OrgTreeRowItem | null;
  readonly open: boolean;
  readonly onOpenChange: (open: boolean) => void;
  readonly isFr: boolean;
  readonly canMutate: boolean;
  readonly labels: AdminAndStudioDictionarySection["settingsHub"]["organizationTab"]["deleteModal"];
  readonly errorMessage: string | null;
  readonly isSubmitting: boolean;
  readonly onConfirmDelete: (orgUnitId: string) => void;
}

export function ConfirmDeleteOrgUnitModal({
  rowItem,
  open,
  onOpenChange,
  isFr,
  canMutate,
  labels,
  errorMessage,
  isSubmitting,
  onConfirmDelete,
}: ConfirmDeleteOrgUnitModalProps): React.ReactElement {
  const unit = rowItem?.unit ?? null;
  const childrenCount = rowItem?.childrenCount ?? 0;
  const attachedWorkspacesCount = rowItem?.attachedWorkspacesCount ?? 0;
  const isNonEmpty = childrenCount > 0 || attachedWorkspacesCount > 0;
  const billingEnabled = unit ? unit.billingEnabled !== false : false;

  const nonEmptyMessage = unit
    ? buildNonEmptyDeleteSummary({
        unitName: unit.name,
        childrenCount,
        attachedWorkspacesCount,
        isFr,
      })
    : "";

  return (
    <OrciaDialog
      open={open && unit !== null}
      onOpenChange={onOpenChange}
      title={unit ? `${labels.titlePrefix} ${unit.name}` : labels.titlePrefix}
      description={labels.description}
      testId="confirm-delete-org-unit-modal"
      closeLabel={labels.cancelButton}
    >
      <div style={{ display: "flex", flexDirection: "column", gap: "12px", marginTop: "8px" }}>
        {billingEnabled ? (
          <OrciaAlertBanner tone="amber" testId="org-unit-delete-finops-warning">
            <span style={{ display: "inline-flex", alignItems: "center", gap: "8px" }}>
              <OrciaIcon name="warning" size={14} />
              <span>{labels.finopsWarningText}</span>
            </span>
          </OrciaAlertBanner>
        ) : null}

        {isNonEmpty ? (
          <OrciaAlertBanner tone="crimson" testId="org-unit-delete-blocked-banner">
            <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
              <strong>{labels.blockedNonEmptyTitle}</strong>
              <span>{nonEmptyMessage}</span>
              <span>{labels.blockedNonEmptyHint}</span>
            </div>
          </OrciaAlertBanner>
        ) : null}

        {errorMessage ? (
          <OrciaAlertBanner tone="crimson" testId="org-unit-delete-modal-error">
            {errorMessage}
          </OrciaAlertBanner>
        ) : null}

        <div style={{ display: "flex", justifyContent: "flex-end", gap: "8px", marginTop: "4px" }}>
          <OrciaButton
            variant="secondary"
            testId={unit ? `cancel-delete-org-unit-btn-${unit.id}` : "cancel-delete-org-unit-btn"}
            onClick={() => onOpenChange(false)}
          >
            {labels.cancelButton}
          </OrciaButton>
          <OrciaButton
            variant="danger"
            testId={
              unit ? `confirm-delete-org-unit-btn-${unit.id}` : "confirm-delete-org-unit-btn"
            }
            disabled={!canMutate || isSubmitting}
            onClick={() => {
              if (unit) {
                onConfirmDelete(unit.id);
              }
            }}
          >
            {labels.confirmDeleteButton}
          </OrciaButton>
        </div>
      </div>
    </OrciaDialog>
  );
}
