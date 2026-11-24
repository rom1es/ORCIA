import { OrciaAlertBanner } from "@orcia/ui";
import React from "react";
import { resolveDictionaryForFlag } from "../i18n";

export interface TemporaryPasswordWarningBannerProps {
  readonly isFr: boolean;
  readonly onOpenSettings: () => void;
}

export function TemporaryPasswordWarningBanner({
  isFr,
  onOpenSettings,
}: TemporaryPasswordWarningBannerProps): React.ReactElement {
  const copy = resolveDictionaryForFlag(isFr).shellChrome.temporaryPasswordBanner;
  return (
    <OrciaAlertBanner
      tone="amber"
      testId="temporary-password-warning-banner"
      className="flex items-center justify-between gap-3 px-4 py-2 text-xs"
    >
      <span>{copy.warningText}</span>
      <button
        type="button"
        data-testid="temporary-password-open-settings-btn"
        onClick={onOpenSettings}
        className="orcia-ds-btn orcia-ds-btn-primary"
        style={{ padding: "4px 8px", fontSize: "12px" }}
      >
        {copy.changePasswordCta}
      </button>
    </OrciaAlertBanner>
  );
}
