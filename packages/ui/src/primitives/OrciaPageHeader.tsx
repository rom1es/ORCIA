import React from "react";
import { OrciaIcon, type OrciaIconName } from "../components/icons";

export interface OrciaPageHeaderProps {
  /** Primary page title rendered inside the semantic `<h1>` heading. */
  readonly title: string;
  /** Optional concise 1-line intent subtitle rendered below the title. */
  readonly subtitle?: string;
  /** Optional monochrome icon key from `ORCIA_ICONS`. */
  readonly icon?: OrciaIconName;
  /** Optional status or scope badge rendered inline beside the `<h1>`. */
  readonly contextBadge?: React.ReactNode;
  /** Optional secondary actions placed to the left of the primary CTA. */
  readonly secondaryActions?: React.ReactNode;
  /** Optional right-aligned primary Cobalt CTA (at most one per header). */
  readonly primaryAction?: React.ReactNode;
  /** Optional additional right-aligned action group. */
  readonly actions?: React.ReactNode;
  /** Optional Tier-2 tab strip slot (typically `<OrciaTabStrip />`). */
  readonly tabs?: React.ReactNode;
  /** Optional Tier-2 scope switcher or contextual toolbar slot. */
  readonly scopeBar?: React.ReactNode;
  /** Optional page-level alert banner rendered strictly beneath the header card. */
  readonly alertSlot?: React.ReactNode;
  /** Optional `data-testid` applied to the `.orcia-bento-card` `<header>` element. */
  readonly testId?: string;
  /** Optional override for the `<h1>` element's `data-testid` (defaults to `${testId}-title`). */
  readonly titleTestId?: string;
  /** Optional override for the `<p>` subtitle element's `data-testid` (defaults to `${testId}-subtitle`). */
  readonly subtitleTestId?: string;
  /** Optional extra CSS class names on the `<header>` card. */
  readonly className?: string;
}

/**
 * Canonical Direction C two-tier page header (`UH-06`).
 * Enforces one white `.orcia-bento-card` `<header>` with semantic `<h1>`,
 * monochrome `<OrciaIcon />`, right-aligned action slots, optional Tier-2 navigation,
 * and an aligned alert slot strictly beneath the header card.
 */
export function OrciaPageHeader({
  title,
  subtitle,
  icon,
  contextBadge,
  secondaryActions,
  primaryAction,
  actions,
  tabs,
  scopeBar,
  alertSlot,
  testId,
  titleTestId,
  subtitleTestId,
  className,
}: OrciaPageHeaderProps): React.ReactElement {
  const headerClassName = ["orcia-bento-card", "orcia-ds-page-header", className]
    .filter(Boolean)
    .join(" ");
  const hasActions = Boolean(secondaryActions || actions || primaryAction);
  const hasTier2 = Boolean(tabs || scopeBar);

  return (
    <div
      className="orcia-ds-page-header-region"
      data-testid={testId ? `${testId}-region` : undefined}
    >
      <header data-testid={testId} className={headerClassName}>
        <div className="orcia-ds-page-header-tier1">
          <div className="orcia-ds-page-header-identity">
            {icon ? (
              <span className="orcia-ds-page-header-icon" aria-hidden="true">
                <OrciaIcon name={icon} size={20} />
              </span>
            ) : null}
            <div className="orcia-ds-page-header-copy">
              <div className="orcia-ds-page-header-title-row">
                <h1
                  data-testid={titleTestId ?? (testId ? `${testId}-title` : undefined)}
                  className="orcia-ds-page-header-title"
                >
                  {title}
                </h1>
                {contextBadge}
              </div>
              {subtitle ? (
                <p
                  data-testid={subtitleTestId ?? (testId ? `${testId}-subtitle` : undefined)}
                  className="orcia-ds-page-header-subtitle"
                >
                  {subtitle}
                </p>
              ) : null}
            </div>
          </div>

          {hasActions ? (
            <div
              data-testid={testId ? `${testId}-actions` : undefined}
              className="orcia-ds-page-header-actions"
            >
              {secondaryActions}
              {actions}
              {primaryAction}
            </div>
          ) : null}
        </div>

        {hasTier2 ? (
          <div
            data-testid={testId ? `${testId}-tier2` : undefined}
            className="orcia-ds-page-header-tier2"
          >
            <div>{tabs}</div>
            {scopeBar ? <div>{scopeBar}</div> : null}
          </div>
        ) : null}
      </header>

      {alertSlot ? (
        <div
          data-testid={testId ? `${testId}-alert-slot` : undefined}
          className="orcia-ds-page-header-alert-slot"
        >
          {alertSlot}
        </div>
      ) : null}
    </div>
  );
}
