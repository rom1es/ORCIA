import React from "react";
import { ContextualInfoTriggerButton } from "../components/ContextualInfoTriggerButton";
import { DisabledButtonAlertIndicator } from "../components/DisabledButtonAlertIndicator";

export type OrciaButtonVariant = "primary" | "secondary" | "danger" | "ghost";

export interface OrciaButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  readonly variant?: OrciaButtonVariant;
  readonly testId?: string;
  readonly disabledReason?: string;
}

const BUTTON_VARIANT_CLASS: Record<OrciaButtonVariant, string> = {
  primary: "orcia-ds-btn orcia-ds-btn-primary",
  secondary: "orcia-ds-btn orcia-ds-btn-secondary",
  danger: "orcia-ds-btn orcia-ds-btn-danger",
  ghost: "orcia-ds-btn orcia-ds-btn-ghost",
};

export function OrciaButton({
  variant = "primary",
  testId,
  disabledReason,
  disabled,
  title,
  className,
  type = "button",
  children,
  ...rest
}: OrciaButtonProps): React.ReactElement {
  const mergedClassName = [BUTTON_VARIANT_CLASS[variant], className]
    .filter(Boolean)
    .join(" ");
  const resolvedTestId =
    testId ??
    (typeof (rest as Record<string, unknown>)["data-testid"] === "string"
      ? ((rest as Record<string, unknown>)["data-testid"] as string)
      : undefined);
  const resolvedDisabledReason =
    disabledReason ??
    (typeof title === "string" && title.trim().length > 0 ? title : undefined);
  return (
    <button
      type={type}
      disabled={disabled}
      title={disabled ? resolvedDisabledReason : title}
      data-testid={resolvedTestId}
      className={mergedClassName}
      {...rest}
    >
      {children}
      <DisabledButtonAlertIndicator
        disabled={Boolean(disabled)}
        reason={resolvedDisabledReason}
        testIdSuffix={resolvedTestId}
      />
    </button>
  );
}

export interface OrciaInputProps
  extends React.InputHTMLAttributes<HTMLInputElement> {
  readonly testId?: string;
  readonly allowPasswordManager?: boolean;
}

export function OrciaInput({
  testId,
  allowPasswordManager = false,
  className,
  autoComplete,
  ...rest
}: OrciaInputProps): React.ReactElement {
  const mergedClassName = ["orcia-ds-input", className]
    .filter(Boolean)
    .join(" ");

  if (allowPasswordManager) {
    const loginProps: React.InputHTMLAttributes<HTMLInputElement> = {
      autoComplete: autoComplete ?? "on",
      ...rest,
    };
    return (
      <input
        data-testid={testId}
        className={mergedClassName}
        {...loginProps}
      />
    );
  }

  return (
    <input
      data-testid={testId}
      className={mergedClassName}
      autoComplete="off"
      data-lpignore="true"
      data-1p-ignore="true"
      data-bwignore="true"
      data-form-type="other"
      spellCheck={false}
      {...rest}
    />
  );
}

export interface OrciaSelectProps
  extends React.SelectHTMLAttributes<HTMLSelectElement> {
  readonly testId?: string;
  readonly allowPasswordManager?: boolean;
}

export function OrciaSelect({
  testId,
  allowPasswordManager = false,
  className,
  autoComplete = "off",
  children,
  ...rest
}: OrciaSelectProps): React.ReactElement {
  const mergedClassName = ["orcia-ds-select", className]
    .filter(Boolean)
    .join(" ");
  const effectiveAutoComplete = allowPasswordManager ? "on" : autoComplete;

  return (
    <select
      data-testid={testId}
      className={mergedClassName}
      autoComplete={effectiveAutoComplete || "off"}
      data-lpignore={allowPasswordManager ? undefined : "true"}
      data-1p-ignore={allowPasswordManager ? undefined : "true"}
      data-bwignore={allowPasswordManager ? undefined : "true"}
      data-form-type={allowPasswordManager ? undefined : "other"}
      {...rest}
    >
      {children}
    </select>
  );
}

export interface OrciaTextareaProps
  extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  readonly testId?: string;
  readonly allowPasswordManager?: boolean;
}

export function OrciaTextarea({
  testId,
  allowPasswordManager = false,
  className,
  autoComplete,
  ...rest
}: OrciaTextareaProps): React.ReactElement {
  const mergedClassName = ["orcia-ds-textarea", className]
    .filter(Boolean)
    .join(" ");

  if (allowPasswordManager) {
    const loginProps: React.TextareaHTMLAttributes<HTMLTextAreaElement> = {
      autoComplete: autoComplete ?? "on",
      ...rest,
    };
    return (
      <textarea
        data-testid={testId}
        className={mergedClassName}
        {...loginProps}
      />
    );
  }

  return (
    <textarea
      data-testid={testId}
      className={mergedClassName}
      autoComplete="off"
      data-lpignore="true"
      data-1p-ignore="true"
      data-bwignore="true"
      data-form-type="other"
      spellCheck={false}
      {...rest}
    />
  );
}

export interface OrciaSectionCardProps {
  readonly title: string;
  readonly subtitle?: string;
  readonly helpSectionId?: string;
  readonly helpLabel?: string;
  readonly onOpenHelpSection?: (sectionId: string) => void;
  readonly actions?: React.ReactNode;
  readonly testId?: string;
  readonly className?: string;
  readonly children: React.ReactNode;
}

export function OrciaSectionCard({
  title,
  subtitle,
  helpSectionId,
  helpLabel,
  onOpenHelpSection,
  actions,
  testId,
  className,
  children,
}: OrciaSectionCardProps): React.ReactElement {
  const mergedClassName = ["orcia-bento-card", "orcia-ds-card", className]
    .filter(Boolean)
    .join(" ");
  return (
    <section data-testid={testId} className={mergedClassName}>
      <header className="orcia-ds-header">
        <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
            <h2 style={{ margin: 0, fontSize: "var(--font-size-h3)" }}>{title}</h2>
            {helpSectionId && onOpenHelpSection ? (
              <ContextualInfoTriggerButton
                sectionId={helpSectionId}
                label={helpLabel ?? title}
                onOpenHelpSection={onOpenHelpSection}
              />
            ) : null}
          </div>
          {subtitle ? (
            <p
              style={{
                margin: 0,
                fontSize: "var(--font-size-body)",
                color: "var(--color-muted-foreground)",
              }}
            >
              {subtitle}
            </p>
          ) : null}
        </div>
        {actions ? (
          <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
            {actions}
          </div>
        ) : null}
      </header>
      {children}
    </section>
  );
}

export {
  OrciaDialog,
  OrciaDropdownMenu,
  OrciaRadixSelect,
  OrciaSwitch,
  OrciaTabBar,
  OrciaTooltip,
  type OrciaDialogProps,
  type OrciaDropdownMenuItem,
  type OrciaDropdownMenuProps,
  type OrciaRadixSelectOption,
  type OrciaRadixSelectProps,
  type OrciaSwitchProps,
  type OrciaTabBarProps,
  type OrciaTabItem,
  type OrciaTooltipProps,
} from "./RadixDesignSystemPrimitives";

export type OrciaAlertTone = "emerald" | "amber" | "crimson" | "cobalt";

export interface OrciaAlertBannerProps {
  readonly tone?: OrciaAlertTone;
  readonly role?: "alert" | "status";
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

export function OrciaAlertBanner({
  tone = "cobalt",
  role,
  testId,
  className,
  children,
}: OrciaAlertBannerProps): React.ReactElement {
  const effectiveRole =
    role ?? (tone === "crimson" || tone === "amber" ? "alert" : "status");
  const mergedClassName = [ALERT_TONE_CLASS[tone], className]
    .filter(Boolean)
    .join(" ");
  return (
    <div role={effectiveRole} data-testid={testId} className={mergedClassName}>
      {children}
    </div>
  );
}
