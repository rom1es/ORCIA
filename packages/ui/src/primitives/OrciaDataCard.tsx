import React from "react";
import { OrciaIcon, type OrciaIconName } from "../components/icons";

export interface OrciaDataCardProps {
  /** Optional card heading rendered inside `<h2>`. */
  readonly title?: string;
  /** Optional concise card subtitle. */
  readonly subtitle?: string;
  /** Optional monochrome icon from `ORCIA_ICONS`. */
  readonly icon?: OrciaIconName;
  /** Optional metadata badge rendered beside the card title. */
  readonly metaBadge?: React.ReactNode;
  /** Optional header action buttons aligned to the right. */
  readonly actions?: React.ReactNode;
  /** Optional card footer strip separated by a subtle divider. */
  readonly footer?: React.ReactNode;
  /** Optional `data-testid` on the root `<section>` card element. */
  readonly testId?: string;
  /** Optional extra CSS classes on the root card. */
  readonly className?: string;
  readonly children: React.ReactNode;
}

/**
 * Canonical white surface card wrapper (`UH-06`).
 * Provides consistent `var(--orcia-surface-card)` and `var(--orcia-border-subtle)` framing
 * for KPI strips, tables, lists, and detail panels on the Direction C canvas background.
 */
export function OrciaDataCard({
  title,
  subtitle,
  icon,
  metaBadge,
  actions,
  footer,
  testId,
  className,
  children,
}: OrciaDataCardProps): React.ReactElement {
  const mergedClassName = ["orcia-bento-card", "orcia-ds-data-card", className]
    .filter(Boolean)
    .join(" ");
  const hasHeader = Boolean(title || subtitle || icon || metaBadge || actions);

  return (
    <section data-testid={testId} className={mergedClassName}>
      {hasHeader ? (
        <header
          data-testid={testId ? `${testId}-header` : undefined}
          className="orcia-ds-data-card-header"
        >
          <div className="orcia-ds-data-card-identity">
            {icon ? (
              <span aria-hidden="true" style={{ color: "var(--color-muted-foreground)", marginTop: "2px" }}>
                <OrciaIcon name={icon} size={16} />
              </span>
            ) : null}
            <div style={{ display: "flex", flexDirection: "column", gap: "4px", minWidth: 0 }}>
              {(title || metaBadge) ? (
                <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
                  {title ? <h2 className="orcia-ds-data-card-title">{title}</h2> : null}
                  {metaBadge}
                </div>
              ) : null}
              {subtitle ? <p className="orcia-ds-data-card-subtitle">{subtitle}</p> : null}
            </div>
          </div>
          {actions ? <div className="orcia-ds-data-card-actions">{actions}</div> : null}
        </header>
      ) : null}

      <div className="orcia-ds-data-card-body">{children}</div>

      {footer ? (
        <footer
          data-testid={testId ? `${testId}-footer` : undefined}
          className="orcia-ds-data-card-footer"
        >
          {footer}
        </footer>
      ) : null}
    </section>
  );
}
