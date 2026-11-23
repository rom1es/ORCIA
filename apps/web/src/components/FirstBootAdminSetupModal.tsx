import {
  DEFAULT_RGAA_MODAL_LABELS_EN,
  DEFAULT_RGAA_MODAL_LABELS_FR,
  DisabledButtonAlertIndicator,
  handleRgaaSubmitKeyDown,
  OrciaDialog,
  OrciaPasswordInput,
  RgaaUnsavedChangesAlert,
  useUnsavedChangesDialogGuard,
} from "@orcia/ui";
import React, { useState } from "react";
import { resolveDictionaryForFlag, resolveLocaleForFlag } from "../i18n";

const RGAA_MODAL_LABELS_BY_LOCALE = {
  fr: DEFAULT_RGAA_MODAL_LABELS_FR,
  en: DEFAULT_RGAA_MODAL_LABELS_EN,
} as const;

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
  const [adminPasswordConfirm, setAdminPasswordConfirm] = useState<string>("");

  const resolvedLocale = resolveLocaleForFlag(isFr);
  const dict = resolveDictionaryForFlag(isFr);
  const copy = dict.firstBootAdminModal;
  const rgaaLabels = RGAA_MODAL_LABELS_BY_LOCALE[resolvedLocale];

  const isAdminModalDirty = Boolean(
    adminFullName.trim() ||
      adminEmail.trim() ||
      adminPassword.trim() ||
      adminPasswordConfirm.trim(),
  );
  const hasPasswordMismatch =
    adminPassword.length > 0 && adminPasswordConfirm !== adminPassword;
  const canCreateAdmin = Boolean(
    adminFullName.trim() && adminEmail.trim() && !hasPasswordMismatch,
  );

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
      setAdminPasswordConfirm("");
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
        event.preventDefault();
      }}
      title={copy.title}
      description={copy.description}
      testId="first-boot-admin-setup-modal"
      closeLabel={rgaaLabels.closeButtonLabel}
      hideHeaderCloseButton={true}
      headerExtra={
        <span
          data-testid="first-boot-admin-mandatory-badge"
          className="inline-flex items-center rounded px-2 py-0.5 text-[11px] font-semibold"
          style={{
            backgroundColor: "var(--color-action-primary-subtle)",
            color: "var(--color-action-primary)",
          }}
        >
          {dict.shellChrome.firstBootMandatoryBadge}
        </span>
      }
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
              {copy.firstTimeBadge}
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
              <span className="font-medium">{copy.fullNameLabel}</span>
              <input
                type="text"
                autoFocus
                autoComplete="off"
                data-lpignore="true"
                data-1p-ignore="true"
                data-bwignore="true"
                data-form-type="other"
                data-testid="first-boot-admin-name-input"
                value={adminFullName}
                onChange={(e) => setAdminFullName(e.target.value)}
                placeholder={copy.fullNamePlaceholder}
                className="rounded border px-3 py-1.5"
                style={{
                  backgroundColor: "var(--color-bg-canvas)",
                  borderColor: "var(--color-border-subtle)",
                }}
              />
            </label>

            <label className="flex flex-col gap-1">
              <span className="font-medium">{copy.emailLabel}</span>
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
                placeholder={copy.emailPlaceholder}
                className="rounded border px-3 py-1.5"
                style={{
                  backgroundColor: "var(--color-bg-canvas)",
                  borderColor: "var(--color-border-subtle)",
                }}
              />
            </label>

            <label className="flex flex-col gap-1">
              <span className="font-medium">{copy.passwordLabel}</span>
              <OrciaPasswordInput
                testId="first-boot-admin-password-input"
                value={adminPassword}
                onChange={setAdminPassword}
                maskMode="masked-text"
                placeholder=""
                showPasswordLabel={copy.showPasswordLabel}
                hidePasswordLabel={copy.hidePasswordLabel}
              />
            </label>

            <label className="flex flex-col gap-1">
              <span className="font-medium">{copy.confirmPasswordLabel}</span>
              <OrciaPasswordInput
                testId="first-boot-admin-password-confirm-input"
                value={adminPasswordConfirm}
                onChange={setAdminPasswordConfirm}
                maskMode="masked-text"
                placeholder=""
                showPasswordLabel={copy.showPasswordLabel}
                hidePasswordLabel={copy.hidePasswordLabel}
              />
            </label>

            {adminPasswordConfirm.length > 0 && hasPasswordMismatch ? (
              <p
                data-testid="first-boot-admin-password-mismatch"
                role="status"
                className="text-[11px] font-medium"
                style={{ color: "var(--color-state-danger)" }}
              >
                {copy.passwordMismatchError}
              </p>
            ) : null}
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
            {copy.assignedRoleBadge}
          </span>
          <div className="flex items-center gap-2">
            <button
              type="submit"
              form="first-boot-admin-setup-form"
              data-testid="first-boot-admin-submit-btn"
              disabled={!canCreateAdmin}
              title={!canCreateAdmin ? copy.missingFieldsHint : undefined}
              onKeyDown={(e) =>
                handleRgaaSubmitKeyDown(e, submitFirstBootAdmin, !canCreateAdmin)
              }
              className="orcia-ds-btn orcia-ds-btn-primary inline-flex items-center gap-1.5"
            >
              <span>{copy.submitCta}</span>
              <DisabledButtonAlertIndicator
                disabled={!canCreateAdmin}
                reason={copy.missingFieldsHint}
                testIdSuffix="first-boot-admin-submit-btn"
              />
            </button>
          </div>
        </div>
      </div>
    </OrciaDialog>
  );
}
