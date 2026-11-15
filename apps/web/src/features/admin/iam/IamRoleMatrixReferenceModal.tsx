import type { RoleMatrixEntryResponse } from "@orcia/api-client";
import { OrciaButton, OrciaIcon } from "@orcia/ui";
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
    <div
      role="dialog"
      aria-modal="true"
      aria-label={labels.matrix.sectionTitle}
      data-testid="iam-role-matrix-modal"
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 60,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        backgroundColor: "var(--color-modal-backdrop, rgba(15, 23, 42, 0.45))",
        padding: "16px",
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget) {
          onClose();
        }
      }}
    >
      <div
        style={{
          position: "relative",
          width: "920px",
          maxWidth: "96vw",
          maxHeight: "90vh",
          overflowY: "auto",
          backgroundColor: "var(--color-surface-card)",
          border: "1px solid var(--color-border)",
          borderRadius: "var(--radius-lg)",
          boxShadow: "var(--shadow-dropdown)",
          padding: "20px",
          display: "flex",
          flexDirection: "column",
          gap: "16px",
        }}
        onClick={(e) => e.stopPropagation()}
      >
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
    </div>
  );
}
