import React, { useState } from "react";
import { OrciaIcon } from "../components/icons";
import type { UiLocalePreference } from "./UserAccountDropdownTypes";

export interface UserPasswordChangeCardProps {
  readonly mustChangePassword?: boolean;
  readonly locale?: UiLocalePreference;
  readonly onChangePassword?: (
    currentPassword: string,
    newPassword: string,
  ) => Promise<{ success: boolean; error?: string } | void>;
}

export function UserPasswordChangeCard({
  mustChangePassword = false,
  locale = "fr",
  onChangePassword,
}: UserPasswordChangeCardProps): React.ReactElement {
  const isFr = locale !== "en";
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [feedback, setFeedback] = useState<{ type: "success" | "error"; message: string } | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFeedback(null);
    if (!currentPassword) {
      return setFeedback({ type: "error", message: isFr ? "Veuillez renseigner votre mot de passe actuel." : "Please enter your current password." });
    }
    if (newPassword.length < 12 || !/[a-z]/.test(newPassword) || !/[A-Z]/.test(newPassword) || !/[0-9]/.test(newPassword)) {
      return setFeedback({ type: "error", message: isFr ? "Le mot de passe doit comporter au moins 12 caractères (min. 1 min, 1 maj, 1 chiffre)." : "Password requires 12+ chars with upper, lower, and digit." });
    }
    if (newPassword === currentPassword) {
      return setFeedback({ type: "error", message: isFr ? "Le nouveau mot de passe doit être différent de l'actuel." : "New password must differ from current password." });
    }
    if (newPassword !== confirmPassword) {
      return setFeedback({ type: "error", message: isFr ? "Les deux mots de passe ne correspondent pas." : "Passwords do not match." });
    }
    if (!onChangePassword) {
      return setFeedback({ type: "error", message: isFr ? "Action non configurée." : "Action not configured." });
    }
    setIsSubmitting(true);
    try {
      const res = await onChangePassword(currentPassword, newPassword);
      if (res && res.success === false) {
        setFeedback({ type: "error", message: res.error || (isFr ? "Erreur de modification." : "Failed to change password.") });
      } else {
        setFeedback({ type: "success", message: isFr ? "Mot de passe mis à jour avec succès." : "Password updated successfully." });
        setCurrentPassword(""); setNewPassword(""); setConfirmPassword("");
      }
    } catch (err: unknown) {
      setFeedback({ type: "error", message: err instanceof Error ? err.message : isFr ? "Erreur inattendue." : "Unexpected error." });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div data-testid="user-password-change-card" className="rounded-lg border border-surface-border bg-surface-card p-3 space-y-3">
      <div className="font-semibold text-text-primary text-xs flex items-center justify-between">
        <span className="flex items-center gap-1.5"><OrciaIcon name="lock" size={14} /><span>{isFr ? "Sécurité & Mot de Passe" : "Security & Password"}</span></span>
        {mustChangePassword && (
          <span data-testid="user-must-change-password-badge" className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-500/10 text-amber-500 border border-amber-500/30">
            {isFr ? "Renouvellement Requis" : "Renewal Required"}
          </span>
        )}
      </div>

      {mustChangePassword && (
        <div data-testid="user-must-change-password-alert" className="rounded p-2.5 bg-amber-500/10 border border-amber-500/20 text-xs text-amber-700 flex items-start gap-2">
          <OrciaIcon name="warning" size={14} className="mt-0.5 shrink-0" />
          <span>{isFr ? "Vous utilisez un mot de passe temporaire à renouveler obligatoirement." : "You are using a temporary password that must be renewed."}</span>
        </div>
      )}

      <form autoComplete="off" data-lpignore="true" data-form-type="other" onSubmit={handleSubmit} className="space-y-2 text-xs">
        <div>
          <label className="block text-text-secondary text-[11px] mb-1">{isFr ? "Mot de passe actuel" : "Current password"}</label>
          <input type="text" className="orcia-masked-secret-input w-full px-2.5 py-1.5 rounded border border-border-subtle bg-surface-primary text-text-primary text-xs"
            spellCheck={false} autoComplete="off" data-lpignore="true" data-1p-ignore="true" data-bwignore="true" data-form-type="other"
            data-testid="user-current-password-input" value={currentPassword} onChange={(e) => setCurrentPassword(e.target.value)} />
        </div>
        <div>
          <label className="block text-text-secondary text-[11px] mb-1">{isFr ? "Nouveau mot de passe (min. 12 car., Maj/Min/Chiffre)" : "New password (min. 12 chars, upper/lower/digit)"}</label>
          <input type="text" className="orcia-masked-secret-input w-full px-2.5 py-1.5 rounded border border-border-subtle bg-surface-primary text-text-primary text-xs"
            spellCheck={false} autoComplete="off" data-lpignore="true" data-1p-ignore="true" data-bwignore="true" data-form-type="other"
            data-testid="user-new-password-input" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} />
        </div>
        <div>
          <label className="block text-text-secondary text-[11px] mb-1">{isFr ? "Confirmer le nouveau mot de passe" : "Confirm new password"}</label>
          <input type="text" className="orcia-masked-secret-input w-full px-2.5 py-1.5 rounded border border-border-subtle bg-surface-primary text-text-primary text-xs"
            spellCheck={false} autoComplete="off" data-lpignore="true" data-1p-ignore="true" data-bwignore="true" data-form-type="other"
            data-testid="user-confirm-password-input" value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} />
        </div>
        {feedback && (
          <div data-testid="user-change-password-feedback" className={`p-2 rounded text-xs ${feedback.type === "success" ? "bg-status-success/10 text-status-success border border-status-success/20" : "bg-status-danger/10 text-status-danger border border-status-danger/20"}`}>
            {feedback.message}
          </div>
        )}
        <div className="pt-1 flex justify-end">
          <button type="submit" disabled={isSubmitting} data-testid="user-change-password-submit-btn" className="orcia-ds-btn orcia-ds-btn-primary px-3 py-1.5 text-xs">
            {isSubmitting ? (isFr ? "Mise à jour..." : "Updating...") : isFr ? "Changer mon mot de passe" : "Change password"}
          </button>
        </div>
      </form>
    </div>
  );
}
