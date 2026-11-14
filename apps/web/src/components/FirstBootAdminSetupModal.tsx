import {
  DEFAULT_RGAA_MODAL_LABELS_EN,
  DEFAULT_RGAA_MODAL_LABELS_FR,
  DisabledButtonAlertIndicator,
  handleRgaaSubmitKeyDown,
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
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="first-boot-admin-modal-title"
      data-testid="first-boot-admin-setup-modal"
      onKeyDown={handleAdminDialogKeyDown}
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ backgroundColor: "rgba(15, 23, 42, 0.45)" }}
    >
      <div
        className="w-full max-w-md rounded-xl border p-6 shadow-xl space-y-4"
        style={{
          backgroundColor: "var(--color-bg-surface)",
          borderColor: "var(--color-border-subtle)",
          color: "var(--color-text-primary)",
        }}
      >
        <div>
          <span
            className="inline-block rounded px-2 py-0.5 text-[11px] font-semibold mb-2"
            style={{
              backgroundColor: "var(--color-action-primary-subtle)",
              color: "var(--color-action-primary)",
            }}
          >
            {isFr ? "Première mise en route" : "First-Time Setup"}
          </span>
          <h2 id="first-boot-admin-modal-title" className="text-base font-bold">
            {isFr
              ? "Création du compte Administrateur de la plateforme"
              : "Create Platform Administrator Account"}
          </h2>
          <p className="mt-1 text-xs" style={{ color: "var(--color-text-secondary)" }}>
            {isFr
              ? "Aucun compte administrateur n'est encore enregistré. Créez le premier compte Administrateur pour configurer votre organisation."
              : "No administrator account is registered yet. Create the first Administrator account to configure your organization."}
          </p>
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
              className="rounded border px-3 py-1.5 orcia-masked-secret-input"
              style={
                {
                  backgroundColor: "var(--color-bg-canvas)",
                  borderColor: "var(--color-border-subtle)",
                  WebkitTextSecurity: "disc",
                } as React.CSSProperties
              }
            />
          </label>

          <div className="flex items-center justify-between gap-2 pt-2 flex-wrap">
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
                className="rounded border px-3 py-1.5 font-medium"
                style={{
                  backgroundColor: "var(--color-bg-canvas)",
                  borderColor: "var(--color-border-subtle)",
                  color: "var(--color-text-secondary)",
                  cursor: "pointer",
                }}
              >
                {rgaaLabels.cancelCta} (Esc)
              </button>
              <button
                type="submit"
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
                className="inline-flex items-center gap-1.5 rounded px-4 py-1.5 font-semibold"
                style={{
                  backgroundColor: "var(--color-action-primary)",
                  color: "var(--color-bg-surface)",
                  opacity: !canCreateAdmin ? 0.55 : 1,
                  cursor: !canCreateAdmin ? "not-allowed" : "pointer",
                }}
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
        </form>
      </div>
    </div>
  );
}
