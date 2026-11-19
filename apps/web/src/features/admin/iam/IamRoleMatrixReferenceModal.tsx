import type { RoleMatrixEntryResponse } from "@orcia/api-client";
import { OrciaButton, OrciaDialog, OrciaIcon } from "@orcia/ui";
import React, { useEffect } from "react";
import type { IamTabDictionarySection } from "../../../i18n/locales/iam_accounts_labels";
import { IamNativeRoleMatrixCard } from "./IamNativeRoleMatrixCard";

export interface IamRoleMatrixReferenceModalProps {
  readonly isOpen: boolean;
  readonly onClose: () => void;
  readonly roleMatrix: readonly RoleMatrixEntryResponse[];
  readonly labels: IamTabDictionarySection;
  readonly openHelpSection: (sectionId: string) => void;
}

export function IamRoleMatrixReferenceModal({
  isOpen,
  onClose,
  roleMatrix,
  labels,
  openHelpSection,
}: IamRoleMatrixReferenceModalProps): React.ReactElement | null {
  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.stopPropagation();
        e.preventDefault();
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown, true);
    return () => window.removeEventListener("keydown", handleKeyDown, true);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <OrciaDialog
      open={isOpen}
      onOpenChange={(nextOpen) => {
        if (!nextOpen) onClose();
      }}
      title={labels.matrix.sectionTitle}
      testId="iam-role-matrix-modal"
      closeLabel={labels.matrix.closeRoleMatrixCta || "Fermer"}
      contentClassName="orcia-ds-dialog-content-wide"
      onEscapeKeyDown={(event) => {
        event.preventDefault();
        onClose();
      }}
    >
      <div className="orcia-ds-dialog-body">
        <div style={{ display: "flex", justifyContent: "flex-end" }}>
          <OrciaButton
            variant="secondary"
            size="sm"
            testId="iam-close-role-matrix-modal-btn"
            onClick={onClose}
          >
            <OrciaIcon name="close" size={14} />
            <span>{labels.matrix.closeRoleMatrixCta || "Fermer"}</span>
          </OrciaButton>
        </div>
        <IamNativeRoleMatrixCard
          roleMatrix={roleMatrix}
          labels={labels}
          openHelpSection={openHelpSection}
        />
      </div>
    </OrciaDialog>
  );
}
