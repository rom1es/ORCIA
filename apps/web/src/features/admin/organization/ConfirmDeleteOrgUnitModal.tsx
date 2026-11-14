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
  readonly onOpenWorkspaces: () => void;
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
  onOpenWorkspaces,
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
          <>
            <div
              data-testid="org-unit-delete-dependencies-list"
              style={{
                display: "flex",
                flexDirection: "column",
                gap: "6px",
                padding: "10px 12px",
                borderRadius: "var(--radius-sm)",
                border: "1px solid var(--color-border)",
                backgroundColor: "var(--color-surface-secondary)",
                fontSize: "12.5px",
              }}
            >
              <strong style={{ color: "var(--color-foreground)" }}>
                {labels.deleteDependenciesHeading}
              </strong>
              <ul
                style={{
                  margin: 0,
                  paddingLeft: "18px",
                  display: "flex",
                  flexDirection: "column",
                  gap: "4px",
                }}
              >
                {rowItem?.childUnits.map((child) => (
                  <li key={`sub-${child.id}`} style={{ color: "var(--color-foreground)" }}>
                    <span>{labels.deleteDependencySubUnitPrefix} : </span>
                    <strong>{child.name}</strong>
                    <span style={{ color: "var(--color-muted-foreground)", marginLeft: "4px" }}>
                      ({child.slug})
                    </span>
                  </li>
                ))}
                {rowItem?.attachedWorkspaces.map((ws) => (
                  <li key={`ws-${ws.id}`} style={{ color: "var(--color-foreground)" }}>
                    <span>{labels.deleteDependencyWorkspacePrefix} : </span>
                    <strong>{ws.name}</strong>
                    <span style={{ color: "var(--color-muted-foreground)", marginLeft: "4px" }}>
                      ({ws.slug})
                    </span>
                  </li>
                ))}
              </ul>
            </div>

            <OrciaAlertBanner tone="crimson" testId="org-unit-delete-blocked-banner">
              <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
                <strong>{labels.blockedNonEmptyTitle}</strong>
                <span>{nonEmptyMessage}</span>
                <span>{labels.blockedNonEmptyHint}</span>
                {attachedWorkspacesCount > 0 || (rowItem?.attachedWorkspaces.length ?? 0) > 0 ? (
                  <div style={{ marginTop: "6px" }}>
                    <OrciaButton
                      variant="secondary"
                      testId="org-unit-delete-open-workspaces-btn"
                      onClick={() => {
                        onOpenChange(false);
                        onOpenWorkspaces();
                      }}
                    >
                      <OrciaIcon name="spaces" size={14} />
                      <span>{labels.deleteOpenWorkspacesAction}</span>
                    </OrciaButton>
                  </div>
                ) : null}
              </div>
            </OrciaAlertBanner>
          </>
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
            disabled={!canMutate || isSubmitting || isNonEmpty}
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
