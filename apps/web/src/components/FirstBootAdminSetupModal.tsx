import {
  DEFAULT_RGAA_MODAL_LABELS_EN,
  DEFAULT_RGAA_MODAL_LABELS_FR,
  DisabledButtonAlertIndicator,
  handleRgaaSubmitKeyDown,
  OrciaDialog,
  RgaaUnsavedChangesAlert,
  useUnsavedChangesDialogGuard,
} from "@orcia/ui";
import React, { useState } from "react";

export interface FirstBootAdminSetupModalProps {
  readonly isOpen: boolean;
  readonly isFr: boolean;
  readonly onClose: () => void;
  readonly onCreatePlatformAdmin: (input: {
    displayName: string;
    email: string;
    password?: string;
  }) => void;
}

export function FirstBootAdminSetupModal({
  isOpen,
  isFr,
  onClose,
  onCreatePlatformAdmin,
}: FirstBootAdminSetupModalProps) {
  const [adminFullName, setAdminFullName] = useState<string>("");
  const [adminEmail, setAdminEmail] = useState<string>("");
  const [adminPassword, setAdminPassword] = useState<string>("");

  const isAdminModalDirty = Boolean(
    adminFullName.trim() || adminEmail.trim() || adminPassword.trim(),
  );
  const canCreateAdmin = Boolean(adminFullName.trim() && adminEmail.trim());
  const rgaaLabels = isFr ? DEFAULT_RGAA_MODAL_LABELS_FR : DEFAULT_RGAA_MODAL_LABELS_EN;

  const {
    showUnsavedConfirm: showAdminUnsavedConfirm,
    requestClose: requestCloseAdminModal,
    confirmDiscardAndClose: confirmDiscardAdminModal,
    cancelDiscardAndStay: cancelDiscardAdminModal,
    handleDialogKeyDown: handleAdminDialogKeyDown,
  } = useUnsavedChangesDialogGuard({
    isOpen,
    isDirty: isAdminModalDirty,
    onClose,
    onDiscardUnsavedChanges: () => {
      setAdminFullName("");
      setAdminEmail("");
      setAdminPassword("");
    },
  });

  if (!isOpen) {
    return null;
  }

  const submitFirstBootAdmin = () => {
    if (!canCreateAdmin) {
      return;
    }
    onCreatePlatformAdmin({
      displayName: adminFullName.trim(),
      email: adminEmail.trim(),
      password: adminPassword,
    });
  };

  const handleFirstBootAdminSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    submitFirstBootAdmin();
  };

  return (
    <OrciaDialog
      open={isOpen}
      onOpenChange={(nextOpen) => {
        if (!nextOpen) {
          requestCloseAdminModal();
        }
      }}
      onEscapeKeyDown={(event) => {
        event.preventDefault();
        requestCloseAdminModal();
      }}
      onInteractOutside={(event) => {
        if (isAdminModalDirty) {
          event.preventDefault();
          requestCloseAdminModal();
        }
      }}
      title={
        isFr
          ? "Création du compte Administrateur de la plateforme"
          : "Create Platform Administrator Account"
      }
      description={
        isFr
          ? "Aucun compte administrateur n'est encore enregistré. Créez le premier compte Administrateur pour configurer votre organisation."
          : "No administrator account is registered yet. Create the first Administrator account to configure your organization."
      }
      testId="first-boot-admin-setup-modal"
      closeLabel={`${rgaaLabels.cancelCta} (Esc)`}
    >
      <div onKeyDown={handleAdminDialogKeyDown} className="flex min-h-0 flex-1 flex-col gap-3">
        <div className="orcia-ds-dialog-body">
          <div>
            <span
              className="inline-block rounded px-2 py-0.5 text-[11px] font-semibold"
              style={{
                backgroundColor: "var(--color-action-primary-subtle)",
                color: "var(--color-action-primary)",
              }}
            >
              {isFr ? "Première mise en route" : "First-Time Setup"}
            </span>
          </div>

          {showAdminUnsavedConfirm ? (
            <RgaaUnsavedChangesAlert
              testIdPrefix="first-boot-admin"
              labels={rgaaLabels}
              onStay={cancelDiscardAdminModal}
              onDiscard={confirmDiscardAdminModal}
            />
          ) : null}

          <form
            id="first-boot-admin-setup-form"
            onSubmit={handleFirstBootAdminSubmit}
            autoComplete="off"
            data-lpignore="true"
            data-form-type="other"
            className="space-y-3 text-xs"
          >
            <label className="flex flex-col gap-1">
              <span className="font-medium">{isFr ? "Nom complet" : "Full name"}</span>
              <input
                type="text"
                autoComplete="off"
                data-lpignore="true"
                data-1p-ignore="true"
                data-bwignore="true"
                data-form-type="other"
                data-testid="first-boot-admin-name-input"
                value={adminFullName}
                onChange={(e) => setAdminFullName(e.target.value)}
                placeholder={isFr ? "Ex : Romain" : "e.g. Romain"}
                className="rounded border px-3 py-1.5"
                style={{
                  backgroundColor: "var(--color-bg-canvas)",
                  borderColor: "var(--color-border-subtle)",
                }}
              />
            </label>

            <label className="flex flex-col gap-1">
              <span className="font-medium">{isFr ? "Adresse e-mail" : "Email address"}</span>
              <input
                type="email"
                autoComplete="off"
                data-lpignore="true"
                data-1p-ignore="true"
                data-bwignore="true"
                data-form-type="other"
                data-testid="first-boot-admin-email-input"
                value={adminEmail}
                onChange={(e) => setAdminEmail(e.target.value)}
                placeholder={isFr ? "admin@entreprise.fr" : "admin@company.com"}
                className="rounded border px-3 py-1.5"
                style={{
                  backgroundColor: "var(--color-bg-canvas)",
                  borderColor: "var(--color-border-subtle)",
                }}
              />
            </label>

            <label className="flex flex-col gap-1">
              <span className="font-medium">{isFr ? "Mot de passe" : "Password"}</span>
              <input
                type="text"
                spellCheck={false}
                autoComplete="off"
                data-lpignore="true"
                data-1p-ignore="true"
                data-bwignore="true"
                data-form-type="other"
                data-testid="first-boot-admin-password-input"
                value={adminPassword}
                onChange={(e) => setAdminPassword(e.target.value)}
                placeholder="••••••••••••"
                className="orcia-masked-secret-input rounded border px-3 py-1.5"
                style={
                  {
                    backgroundColor: "var(--color-bg-canvas)",
                    borderColor: "var(--color-border-subtle)",
                    WebkitTextSecurity: "disc",
                  } as React.CSSProperties
                }
              />
            </label>
          </form>
        </div>

        <div
          className="orcia-ds-dialog-footer"
          style={{ justifyContent: "space-between" }}
        >
          <span
            data-testid="first-boot-admin-role-badge"
            className="text-[11px] font-medium"
            style={{ color: "var(--color-text-secondary)" }}
          >
            {isFr
              ? "Rôle attribué : Administrateur de la plateforme"
              : "Assigned role: Platform Administrator"}
          </span>
          <div className="flex items-center gap-2">
            <button
              type="button"
              data-testid="first-boot-admin-cancel-btn"
              onClick={requestCloseAdminModal}
              className="orcia-ds-btn orcia-ds-btn-secondary"
            >
              {rgaaLabels.cancelCta} (Esc)
            </button>
            <button
              type="submit"
              form="first-boot-admin-setup-form"
              data-testid="first-boot-admin-submit-btn"
              disabled={!canCreateAdmin}
              title={
                !canCreateAdmin
                  ? isFr
                    ? "Renseignez le nom complet et l'adresse e-mail pour créer le compte Administrateur."
                    : "Enter full name and email address to create the Administrator account."
                  : undefined
              }
              onKeyDown={(e) =>
                handleRgaaSubmitKeyDown(e, submitFirstBootAdmin, !canCreateAdmin)
              }
              className="orcia-ds-btn orcia-ds-btn-primary inline-flex items-center gap-1.5"
            >
              <span>
                {isFr
                  ? "Créer le compte Administrateur"
                  : "Create Administrator Account"}
              </span>
              <DisabledButtonAlertIndicator
                disabled={!canCreateAdmin}
                reason={
                  isFr
                    ? "Renseignez le nom complet et l'adresse e-mail pour créer le compte Administrateur."
                    : "Enter full name and email address to create the Administrator account."
                }
                testIdSuffix="first-boot-admin-submit-btn"
              />
            </button>
          </div>
        </div>
      </div>
    </OrciaDialog>
  );
}
