import React from "react";
import { OrciaIcon, type OrciaIconName } from "../components/icons";

export type OrciaAlertTone = "emerald" | "amber" | "crimson" | "cobalt";

export interface OrciaAlertBannerProps
  extends Omit<React.HTMLAttributes<HTMLDivElement>, "title"> {
  readonly tone?: OrciaAlertTone;
  readonly role?: "alert" | "status";
  readonly title?: React.ReactNode;
  readonly code?: string | null;
  readonly action?: React.ReactNode;
  readonly hideIcon?: boolean;
  readonly testId?: string;
  readonly className?: string;
  readonly children: React.ReactNode;
}

const ALERT_TONE_CLASS: Record<OrciaAlertTone, string> = {
  emerald: "orcia-ds-alert orcia-ds-alert-success",
  amber: "orcia-ds-alert orcia-ds-alert-warning",
  crimson: "orcia-ds-alert orcia-ds-alert-error",
  cobalt: "orcia-ds-alert orcia-ds-alert-info",
};

const ALERT_TONE_ICON: Record<OrciaAlertTone, OrciaIconName> = {
  emerald: "check",
  amber: "warning",
  crimson: "cross",
  cobalt: "infoSymbol",
};

export function OrciaAlertBanner({
  tone = "cobalt",
  role,
  title,
  code,
  action,
  hideIcon = false,
  testId,
  className,
  children,
  ...rest
}: OrciaAlertBannerProps): React.ReactElement {
  const effectiveRole = role ?? (tone === "crimson" ? "alert" : "status");
  const mergedClassName = [ALERT_TONE_CLASS[tone], className]
    .filter(Boolean)
    .join(" ");
  return (
    <div
      role={effectiveRole}
      data-testid={testId}
      className={mergedClassName}
      {...rest}
    >
      {!hideIcon && (
        <span className="orcia-ds-alert-icon" aria-hidden="true">
          <OrciaIcon name={ALERT_TONE_ICON[tone]} size={16} />
        </span>
      )}
      <div className="orcia-ds-alert-content">
        {(title || code) && (
          <div className="font-semibold text-xs mb-1">
            {title}
            {code && (
              <span className="font-mono text-xs opacity-75 ml-1.5">
                {title ? `(${code})` : code}
              </span>
            )}
          </div>
        )}
        <div>{children}</div>
      </div>
      {action && <div className="orcia-ds-alert-action">{action}</div>}
    </div>
  );
}
