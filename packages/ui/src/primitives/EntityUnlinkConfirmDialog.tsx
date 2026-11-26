import React from "react";
import { OrciaAlertBanner } from "./OrciaAlertBanner";
import { OrciaDialog } from "./OrciaDialog";
import type {
  EntityUnlinkConfirmDialogLabels,
  UiDraftPackReference,
} from "./PackUiTypes";

export interface EntityUnlinkConfirmDialogProps {
  readonly open: boolean;
  readonly entityLabel: string;
  readonly draftPacks: readonly UiDraftPackReference[];
  readonly isDeleting?: boolean;
  readonly errorMessage?: string | null;
  readonly labels: EntityUnlinkConfirmDialogLabels;
  readonly onCancel: () => void;
  readonly onConfirmUnlinkAndDelete: () => Promise<void> | void;
}

export function EntityUnlinkConfirmDialog({
  open,
  entityLabel,
  draftPacks,
  isDeleting = false,
  errorMessage = null,
  labels,
  onCancel,
  onConfirmUnlinkAndDelete,
}: EntityUnlinkConfirmDialogProps): React.ReactElement {
  return (
    <OrciaDialog
      open={open}
      onOpenChange={(nextOpen) => {
        if (!nextOpen) onCancel();
      }}
      title={labels.title}
      description={`${labels.descriptionPrefix} ${entityLabel}`}
      testId="entity-unlink-confirm-dialog"
      closeLabel={labels.cancelBtn}
    >
      <div className="orcia-ds-dialog-body flex flex-col gap-3">
        {errorMessage ? (
          <OrciaAlertBanner tone="crimson" role="alert" testId="entity-unlink-error-alert">
            {errorMessage}
          </OrciaAlertBanner>
        ) : null}

        <div className="flex flex-col gap-1.5 text-xs">
          <strong>{labels.referencingDraftsHeading}</strong>
          <ul
            data-testid="entity-unlink-draft-packs-list"
            className="list-disc space-y-1 pl-4"
          >
            {draftPacks.map((dp) => (
              <li key={dp.bundleId || dp.slug}>
                <span className="font-semibold">{dp.name || dp.slug}</span>
                {dp.slug ? (
                  <code className="ml-1.5 font-mono text-[11px] text-[var(--orcia-text-secondary)]">
                    {`${dp.slug} · v${dp.version}`}
                  </code>
                ) : null}
              </li>
            ))}
          </ul>
        </div>

        <div className="orcia-ds-dialog-footer flex justify-end gap-2 pt-2">
          <button
            type="button"
            data-testid="entity-unlink-cancel-btn"
            onClick={onCancel}
            disabled={isDeleting}
            className="orcia-ds-btn orcia-ds-btn-secondary orcia-ds-btn-sm"
          >
            {labels.cancelBtn}
          </button>
          <button
            type="button"
            data-testid="entity-unlink-confirm-btn"
            disabled={isDeleting}
            onClick={() => void onConfirmUnlinkAndDelete()}
            className="orcia-ds-btn orcia-ds-btn-danger orcia-ds-btn-sm"
          >
            {isDeleting ? labels.confirmingBtn : labels.confirmBtn}
          </button>
        </div>
      </div>
    </OrciaDialog>
  );
}
