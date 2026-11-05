import React from "react";
import { ContextualInfoTriggerButton } from "../components/ContextualInfoTriggerButton";

export type OrciaButtonVariant = "primary" | "secondary" | "danger" | "ghost";

export interface OrciaButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  readonly variant?: OrciaButtonVariant;
  readonly testId?: string;
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
  className,
  type = "button",
  children,
  ...rest
}: OrciaButtonProps): React.ReactElement {
  const mergedClassName = [BUTTON_VARIANT_CLASS[variant], className]
    .filter(Boolean)
    .join(" ");
  return (
    <button
      type={type}
      data-testid={testId}
      className={mergedClassName}
      {...rest}
    >
      {children}
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
  const antiPasswordManagerProps = allowPasswordManager
    ? { autoComplete: autoComplete ?? "on" }
    : {
        autoComplete: autoComplete ?? "off",
        "data-lpignore": "true",
        "data-1p-ignore": "true",
        "data-form-type": "other",
      };

  return (
    <input
      data-testid={testId}
      className={mergedClassName}
      {...antiPasswordManagerProps}
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
  autoComplete,
  children,
  ...rest
}: OrciaSelectProps): React.ReactElement {
  const mergedClassName = ["orcia-ds-select", className]
    .filter(Boolean)
    .join(" ");
  const antiPasswordManagerProps = allowPasswordManager
    ? { autoComplete: autoComplete ?? "on" }
    : {
        autoComplete: autoComplete ?? "off",
        "data-lpignore": "true",
        "data-1p-ignore": "true",
        "data-form-type": "other",
      };

  return (
    <select
      data-testid={testId}
      className={mergedClassName}
      {...antiPasswordManagerProps}
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
  const antiPasswordManagerProps = allowPasswordManager
    ? { autoComplete: autoComplete ?? "on" }
    : {
        autoComplete: autoComplete ?? "off",
        "data-lpignore": "true",
        "data-1p-ignore": "true",
        "data-form-type": "other",
      };

  return (
    <textarea
      data-testid={testId}
      className={mergedClassName}
      {...antiPasswordManagerProps}
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

export interface OrciaTabItem<T extends string = string> {
  readonly key: T;
  readonly label: string;
  readonly testId?: string;
}

export interface OrciaTabBarProps<T extends string = string> {
  readonly tabs: readonly OrciaTabItem<T>[];
  readonly activeTab: T;
  readonly onSelectTab: (tabKey: T) => void;
  readonly ariaLabel: string;
  readonly testIdPrefix?: string;
}

export function OrciaTabBar<T extends string = string>({
  tabs,
  activeTab,
  onSelectTab,
  ariaLabel,
  testIdPrefix = "orcia-tab",
}: OrciaTabBarProps<T>): React.ReactElement {
  return (
    <nav role="tablist" aria-label={ariaLabel} className="orcia-ds-tabs">
      {tabs.map((tab) => {
        const isSelected = tab.key === activeTab;
        return (
          <button
            key={tab.key}
            type="button"
            role="tab"
            aria-selected={isSelected}
            data-testid={tab.testId ?? `${testIdPrefix}-${tab.key}`}
            onClick={() => onSelectTab(tab.key)}
            className="orcia-ds-tab"
          >
            {tab.label}
          </button>
        );
      })}
    </nav>
  );
}

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
