import React, { useEffect, useState } from "react";
import { OrciaIcon } from "../components/icons";
import { OrciaAlertBanner } from "./DesignSystemControls";
import type {
  UiLocalePreference,
  UserPasswordSecurityLabels,
} from "./UserAccountDropdownTypes";

export interface UserPasswordChangeCardProps {
  readonly mustChangePassword?: boolean;
  readonly locale?: UiLocalePreference;
  readonly labels: UserPasswordSecurityLabels;
  readonly onChangePassword?: (
    currentPassword: string,
    newPassword: string,
  ) => Promise<{ success: boolean; error?: string } | void>;
}

export function UserPasswordChangeCard({
  mustChangePassword = false,
  labels,
  onChangePassword,
}: UserPasswordChangeCardProps): React.ReactElement {
  const copy = labels;

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
