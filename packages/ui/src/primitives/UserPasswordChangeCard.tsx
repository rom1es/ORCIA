import React, { useEffect, useState } from "react";
import { OrciaIcon } from "../components/icons";
import { OrciaAlertBanner } from "./DesignSystemControls";
import type {
  UiLocalePreference,
  UserPasswordSecurityLabels,
} from "./UserAccountDropdownTypes";

export const DEFAULT_FR_PASSWORD_LABELS: UserPasswordSecurityLabels = {
  title: "Sécurité & Mot de Passe",
  renewalRequiredBadge: "Renouvellement Requis",
  temporaryPasswordWarning:
    "Vous utilisez un mot de passe temporaire à renouveler obligatoirement.",
  currentPasswordLabel: "Mot de passe actuel", // pragma: allowlist secret
  newPasswordLabel: "Nouveau mot de passe (min. 12 car., Maj/Min/Chiffre)", // pragma: allowlist secret
  confirmPasswordLabel: "Confirmer le nouveau mot de passe", // pragma: allowlist secret
  submitButtonLabel: "Changer mon mot de passe",
  submittingButtonLabel: "Mise à jour...",
  updatedSuccessMessage: "Mot de passe mis à jour avec succès.",
  missingCurrentPasswordError: "Veuillez renseigner votre mot de passe actuel.", // pragma: allowlist secret
  weakPasswordError:
    "Le mot de passe doit comporter au moins 12 caractères (min. 1 min, 1 maj, 1 chiffre).",
  unchangedPasswordError:
    "Le nouveau mot de passe doit être différent de l'actuel.", // pragma: allowlist secret
  mismatchPasswordError: "Les deux mots de passe ne correspondent pas.", // pragma: allowlist secret
  actionNotConfiguredError: "Action non configurée.",
  genericError: "Erreur lors de la modification du mot de passe.",
};

export const DEFAULT_EN_PASSWORD_LABELS: UserPasswordSecurityLabels = {
  title: "Security & Password",
  renewalRequiredBadge: "Renewal Required",
  temporaryPasswordWarning:
    "You are using a temporary password that must be renewed.",
  currentPasswordLabel: "Current password", // pragma: allowlist secret
  newPasswordLabel: "New password (min. 12 chars, upper/lower/digit)", // pragma: allowlist secret
  confirmPasswordLabel: "Confirm new password", // pragma: allowlist secret
  submitButtonLabel: "Change password",
  submittingButtonLabel: "Updating...",
  updatedSuccessMessage: "Password updated successfully.",
  missingCurrentPasswordError: "Please enter your current password.", // pragma: allowlist secret
  weakPasswordError:
    "Password requires 12+ chars with upper, lower, and digit.",
  unchangedPasswordError: "New password must differ from current password.", // pragma: allowlist secret
  mismatchPasswordError: "Passwords do not match.", // pragma: allowlist secret
  actionNotConfiguredError: "Action not configured.",
  genericError: "Failed to change password.",
};

export interface UserPasswordChangeCardProps {
  readonly mustChangePassword?: boolean;
  readonly locale?: UiLocalePreference;
  readonly labels?: UserPasswordSecurityLabels;
  readonly onChangePassword?: (
    currentPassword: string,
    newPassword: string,
  ) => Promise<{ success: boolean; error?: string } | void>;
}

export function UserPasswordChangeCard({
  mustChangePassword = false,
  locale = "fr",
  labels,
  onChangePassword,
}: UserPasswordChangeCardProps): React.ReactElement {
  const fallback =
    locale === "en" ? DEFAULT_EN_PASSWORD_LABELS : DEFAULT_FR_PASSWORD_LABELS;
  const copy: UserPasswordSecurityLabels = { ...fallback, ...labels };

  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isPasswordChanged, setIsPasswordChanged] = useState(false);
  const [feedback, setFeedback] = useState<{
    type: "success" | "error";
    message: string;
  } | null>(null);

  useEffect(() => {
    if (mustChangePassword) {
      setIsPasswordChanged(false);
    }
  }, [mustChangePassword]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFeedback(null);
    if (!currentPassword) {
      return setFeedback({
        type: "error",
        message: copy.missingCurrentPasswordError,
      });
    }
    if (
      newPassword.length < 12 ||
      !/[a-z]/.test(newPassword) ||
      !/[A-Z]/.test(newPassword) ||
      !/[0-9]/.test(newPassword)
    ) {
      return setFeedback({
        type: "error",
        message: copy.weakPasswordError,
      });
    }
    if (newPassword === currentPassword) {
      return setFeedback({
        type: "error",
        message: copy.unchangedPasswordError,
      });
    }
    if (newPassword !== confirmPassword) {
      return setFeedback({
        type: "error",
        message: copy.mismatchPasswordError,
      });
    }
    if (!onChangePassword) {
      return setFeedback({
        type: "error",
        message: copy.actionNotConfiguredError,
      });
    }
    setIsSubmitting(true);
    try {
      const res = await onChangePassword(currentPassword, newPassword);
      if (res && res.success === false) {
        setFeedback({
          type: "error",
          message: res.error || copy.genericError,
        });
      } else {
        setFeedback({
          type: "success",
          message: copy.updatedSuccessMessage,
        });
        setCurrentPassword("");
        setNewPassword("");
        setConfirmPassword("");
        setIsPasswordChanged(true);
      }
    } catch (err: unknown) {
      setFeedback({
        type: "error",
        message: err instanceof Error ? err.message : copy.genericError,
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div
      data-testid="user-password-change-card"
      className="rounded-lg border border-surface-border bg-surface-card p-3 space-y-3"
    >
      <div className="font-semibold text-text-primary text-xs flex items-center justify-between">
        <span className="flex items-center gap-1.5">
          <OrciaIcon name="lock" size={14} />
          <span>{copy.title}</span>
        </span>
        {mustChangePassword && !isPasswordChanged && (
          <span
            data-testid="user-must-change-password-badge"
            className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-500/10 text-amber-500 border border-amber-500/30"
          >
            {copy.renewalRequiredBadge}
          </span>
        )}
      </div>

      {mustChangePassword && !isPasswordChanged && (
        <OrciaAlertBanner tone="amber" testId="user-must-change-password-alert">
          {copy.temporaryPasswordWarning}
        </OrciaAlertBanner>
      )}

      {isPasswordChanged ? (
        feedback &&
        feedback.type === "success" && (
          <OrciaAlertBanner
            tone="emerald"
            testId="user-change-password-feedback"
          >
            {feedback.message}
          </OrciaAlertBanner>
        )
      ) : (
        <form
          autoComplete="off"
          data-lpignore="true"
          data-form-type="other"
          onSubmit={handleSubmit}
          className="space-y-2 text-xs"
        >
          <div>
            <label className="block text-text-secondary text-[11px] mb-1">
              {copy.currentPasswordLabel}
            </label>
            <input
              type="text"
              className="orcia-masked-secret-input w-full px-2.5 py-1.5 rounded border border-border-subtle bg-surface-primary text-text-primary text-xs"
              spellCheck={false}
              autoComplete="off"
              data-lpignore="true"
              data-1p-ignore="true"
              data-bwignore="true"
              data-form-type="other"
              data-testid="user-current-password-input"
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
            />
          </div>
          <div>
            <label className="block text-text-secondary text-[11px] mb-1">
              {copy.newPasswordLabel}
            </label>
            <input
              type="text"
              className="orcia-masked-secret-input w-full px-2.5 py-1.5 rounded border border-border-subtle bg-surface-primary text-text-primary text-xs"
              spellCheck={false}
              autoComplete="off"
              data-lpignore="true"
              data-1p-ignore="true"
              data-bwignore="true"
              data-form-type="other"
              data-testid="user-new-password-input"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
            />
          </div>
          <div>
            <label className="block text-text-secondary text-[11px] mb-1">
              {copy.confirmPasswordLabel}
            </label>
            <input
              type="text"
              className="orcia-masked-secret-input w-full px-2.5 py-1.5 rounded border border-border-subtle bg-surface-primary text-text-primary text-xs"
              spellCheck={false}
              autoComplete="off"
              data-lpignore="true"
              data-1p-ignore="true"
              data-bwignore="true"
              data-form-type="other"
              data-testid="user-confirm-password-input"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
            />
          </div>
          {feedback && feedback.type === "error" && (
            <OrciaAlertBanner
              tone="crimson"
              testId="user-change-password-feedback"
            >
              {feedback.message}
            </OrciaAlertBanner>
          )}
          <div className="pt-1 flex justify-end">
            <button
              type="submit"
              disabled={isSubmitting}
              data-testid="user-change-password-submit-btn"
              className="orcia-ds-btn orcia-ds-btn-primary px-3 py-1.5 text-xs"
            >
              {isSubmitting
                ? copy.submittingButtonLabel
                : copy.submitButtonLabel}
            </button>
          </div>
        </form>
      )}
    </div>
  );
}
