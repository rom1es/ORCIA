import React from "react";
import {
  getOrciaIconGlyph,
  hasCustomGlyphOverride,
  type OrciaIconName,
} from "./iconRegistry";
import { ORCIA_ICON_SVG_PATHS } from "./iconSvgPaths";

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
  /** Pixel dimension of the square wireframe SVG (defaults to `16`). */
  readonly size?: number;
}

/**
 * Centralized Design System wireframe SVG icon component (`@orcia/ui`).
 * Renders a monochrome `16px` `<svg>` stroked with `currentColor` (`strokeWidth={1.75}`).
 */
export function OrciaIcon({
  name,
  ariaLabel,
  testId,
  size = 16,
  className,
  style,
  ...rest
}: OrciaIconProps): React.ReactElement {
  const glyph = getOrciaIconGlyph(name);
  const paths = ORCIA_ICON_SVG_PATHS[name];
  const isDecorative = !ariaLabel || ariaLabel.trim().length === 0;
  const customGlyphOverride = hasCustomGlyphOverride(name);

  return (
    <span
      {...rest}
      data-testid={testId}
      data-orcia-icon={name}
      role={isDecorative ? undefined : "img"}
      aria-label={isDecorative ? undefined : ariaLabel}
      aria-hidden={isDecorative ? "true" : undefined}
      className={className}
      style={{
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
        flexShrink: 0,
        lineHeight: 1,
        ...style,
      }}
    >
      <svg
        width={size}
        height={size}
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth={1.75}
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
        focusable="false"
      >
        {paths.map((d, idx) => (
          <path key={idx} d={d} />
        ))}
      </svg>
      {customGlyphOverride ? (
        <span style={{ fontSize: 0, lineHeight: 0 }}>{glyph}</span>
      ) : null}
    </span>
  );
}
