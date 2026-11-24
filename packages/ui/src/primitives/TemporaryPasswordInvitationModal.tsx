import React, { useState } from "react";
import { OrciaIcon } from "../components/icons";
import { OrciaDialog } from "./RadixDesignSystemPrimitives";

export interface TemporaryPasswordInvitationModalLabels {
  readonly modalTitle: string;
  readonly closeLabel: string;
  readonly securityPolicyHint: string;
  readonly generatedPasswordTitle: string;
  readonly regeneratingLabel: string;
  readonly regenerateLabel: string;
  readonly copiedCodeLabel: string;
  readonly copyCodeLabel: string;
  readonly invitationMessageLabel: string;
  readonly copiedMessageLabel: string;
  readonly copyMessageLabel: string;
  readonly clipboardBlockedError: string;
  readonly invitationMessageTemplate: string;
}

export interface TemporaryPasswordInvitationModalProps {
  readonly open?: boolean;
  readonly isOpen?: boolean;
  readonly onOpenChange?: (open: boolean) => void;
  readonly displayName: string;
  readonly email: string;
  readonly temporaryPassword: string;
  readonly orciaUrl?: string;
  readonly labels: TemporaryPasswordInvitationModalLabels;
  readonly onRegenerate?: () => void | Promise<void | string>;
  readonly onRegeneratePassword?: () => void | Promise<void | string>;
  readonly onClose?: () => void;
}

export function buildInvitationMessage(params: {
  displayName: string;
  email: string;
  temporaryPassword: string;
  orciaUrl: string;
  template: string;
}): string {
  const { displayName, email, temporaryPassword, orciaUrl, template } = params;
  return template
    .replace("{displayName}", displayName)
    .replace("{email}", email)
    .replace("{temporaryPassword}", temporaryPassword)
    .replace("{orciaUrl}", orciaUrl);
}

export function TemporaryPasswordInvitationModal({
  open,
  isOpen,
  onOpenChange,
  displayName,
  email,
  temporaryPassword,
  orciaUrl,
  labels,
  onRegenerate,
  onRegeneratePassword,
  onClose,
}: TemporaryPasswordInvitationModalProps): React.ReactElement {
  const effectiveOpen = open ?? isOpen ?? true;
  const effectiveOnOpenChange = (next: boolean) => {
    onOpenChange?.(next);
    if (!next) onClose?.();
  };
  const effectiveRegenerate = onRegenerate ?? onRegeneratePassword;

  const [copiedCode, setCopiedCode] = useState(false);
  const [copiedMessage, setCopiedMessage] = useState(false);
  const [copyError, setCopyError] = useState<string | null>(null);
  const [isRegenerating, setIsRegenerating] = useState(false);

  const resolvedUrl =
    orciaUrl ||
    (typeof window !== "undefined" && window.location?.origin
      ? window.location.origin
      : "http://localhost:3100");

  const invitationMessage = buildInvitationMessage({
    displayName,
    email,
    temporaryPassword,
    orciaUrl: resolvedUrl,
    template: labels.invitationMessageTemplate,
  });

  const handleCopyCode = async () => {
    setCopyError(null);
    try {
      if (typeof navigator !== "undefined" && navigator.clipboard) {
        await navigator.clipboard.writeText(temporaryPassword);
      }
      setCopiedCode(true);
      setTimeout(() => setCopiedCode(false), 2000);
    } catch (err: unknown) {
      setCopiedCode(false);
      setCopyError(
        err instanceof Error && err.message.trim()
          ? err.message
          : labels.clipboardBlockedError,
      );
    }
  };

  const handleCopyMessage = async () => {
    setCopyError(null);
    try {
      if (typeof navigator !== "undefined" && navigator.clipboard) {
        await navigator.clipboard.writeText(invitationMessage);
      }
      setCopiedMessage(true);
      setTimeout(() => setCopiedMessage(false), 2000);
    } catch (err: unknown) {
      setCopiedMessage(false);
      setCopyError(
        err instanceof Error && err.message.trim()
          ? err.message
          : labels.clipboardBlockedError,
      );
    }
  };

  const handleRegenerate = async () => {
    if (!effectiveRegenerate) return;
    setIsRegenerating(true);
    try {
      await effectiveRegenerate();
    } finally {
      setIsRegenerating(false);
    }
  };

  return (
    <OrciaDialog
      open={effectiveOpen}
      onOpenChange={effectiveOnOpenChange}
      title={labels.modalTitle}
      testId="temp-password-modal"
      closeLabel={labels.closeLabel}
    >
      <div className="space-y-4 text-xs">
        <p className="text-text-secondary">{labels.securityPolicyHint}</p>

        <div className="rounded border border-border-subtle bg-surface-primary p-3 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-medium text-text-secondary">
              {labels.generatedPasswordTitle}
            </span>
            <div className="flex items-center gap-1.5">
              {effectiveRegenerate && (
                <button
                  type="button"
                  disabled={isRegenerating}
                  data-testid="temp-password-regenerate-btn"
                  onClick={handleRegenerate}
                  className="px-2 py-1 rounded border border-border-subtle bg-surface-secondary text-text-primary hover:bg-surface-hover flex items-center gap-1 text-[11px]"
                >
                  <OrciaIcon name="regenerate" size={12} />
                  <span>{isRegenerating ? labels.regeneratingLabel : labels.regenerateLabel}</span>
                </button>
              )}
              <button
                type="button"
                data-testid="temp-password-copy-code-btn"
                onClick={handleCopyCode}
                className="px-2 py-1 rounded border border-border-subtle bg-surface-secondary text-text-primary hover:bg-surface-hover flex items-center gap-1 text-[11px]"
              >
                <OrciaIcon name={copiedCode ? "checkFilled" : "copy"} size={12} />
                <span>{copiedCode ? labels.copiedCodeLabel : labels.copyCodeLabel}</span>
              </button>
            </div>
          </div>

          <div
            data-testid="temp-password-generated-value"
            className="p-2 rounded bg-surface-secondary text-text-primary font-mono text-sm font-semibold tracking-wider text-center border border-border-subtle select-all"
          >
            {temporaryPassword}
          </div>
        </div>

        <div className="space-y-1.5">
          <label className="block text-[11px] font-medium text-text-secondary">
            {labels.invitationMessageLabel}
          </label>
          <textarea
            readOnly
            rows={7}
            autoComplete="off"
            data-lpignore="true"
            data-1p-ignore="true"
            data-bwignore="true"
            data-form-type="other"
            data-testid="temp-password-invitation-textarea"
            className="w-full p-2.5 rounded border border-border-subtle bg-surface-primary text-text-primary font-mono text-[11px] leading-relaxed resize-none focus:outline-none"
            value={invitationMessage}
          />
        </div>

        {copyError && (
          <p role="alert" className="text-[11px] text-status-error">
            {copyError}
          </p>
        )}

        <div className="flex items-center justify-start pt-2 border-t border-border-subtle">
          <button
            type="button"
            data-testid="temp-password-copy-message-btn"
            onClick={handleCopyMessage}
            className="orcia-ds-btn orcia-ds-btn-secondary px-3 py-1.5 text-xs flex items-center gap-1.5"
          >
            <OrciaIcon name={copiedMessage ? "checkFilled" : "copy"} size={14} />
            <span>{copiedMessage ? labels.copiedMessageLabel : labels.copyMessageLabel}</span>
          </button>
        </div>
      </div>
    </OrciaDialog>
  );
}
