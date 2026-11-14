import { OrciaAlertBanner, OrciaIcon } from "@orcia/ui";
import React from "react";

export interface TemporaryPasswordWarningBannerProps {
  readonly isFr: boolean;
  readonly onOpenSettings: () => void;
}

export function TemporaryPasswordWarningBanner({
  isFr,
  onOpenSettings,
}: TemporaryPasswordWarningBannerProps): React.ReactElement {
  return (
    <OrciaAlertBanner
      tone="amber"
      testId="temporary-password-warning-banner"
      className="flex items-center justify-between gap-3 px-4 py-2 text-xs"
    >
      <div className="flex items-center gap-2">
        <OrciaIcon name="warning" />
        <span>
          {isFr
            ? "Attention : vous utilisez un mot de passe temporaire. Modifiez-le dès maintenant pour sécuriser votre compte."
            : "Warning: you are using a temporary password. Change it now to secure your account."}
        </span>
      </div>
      <button
        type="button"
        data-testid="temporary-password-open-settings-btn"
        onClick={onOpenSettings}
        className="orcia-ds-btn orcia-ds-btn-primary"
        style={{ padding: "4px 8px", fontSize: "12px" }}
      >
        {isFr ? "Modifier mon mot de passe" : "Change my password"}
      </button>
    </OrciaAlertBanner>
  );
}
