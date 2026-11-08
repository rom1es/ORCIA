import React from "react";
import { getOrciaIconGlyph, type OrciaIconName } from "./iconRegistry";

export interface OrciaIconProps extends React.HTMLAttributes<HTMLSpanElement> {
  /** Semantic icon key from the centralized `ORCIA_ICONS` registry. */
  readonly name: OrciaIconName;
  /**
   * Optional accessible label. When omitted, the icon is treated as decorative
   * (`aria-hidden="true"`). When provided, renders `role="img"` + `aria-label`.
   */
  readonly ariaLabel?: string;
  /** Optional deterministic `data-testid` attribute. */
  readonly testId?: string;
}

/**
 * Centralized Design System icon component (`@orcia/ui`).
 * Reads its glyph dynamically from `ORCIA_ICONS[name]` so any update to the
 * central registry immediately propagates across all views and components.
 */
export function OrciaIcon({
  name,
  ariaLabel,
  testId,
  className,
  style,
  ...rest
}: OrciaIconProps): React.ReactElement {
  const glyph = getOrciaIconGlyph(name);
  const isDecorative = !ariaLabel || ariaLabel.trim().length === 0;

  return (
    <span
      {...rest}
      data-testid={testId}
      data-orcia-icon={name}
      role={isDecorative ? undefined : "img"}
      aria-label={isDecorative ? undefined : ariaLabel}
      aria-hidden={isDecorative ? "true" : undefined}
      className={className}
      style={style}
    >
      {glyph}
    </span>
  );
}
