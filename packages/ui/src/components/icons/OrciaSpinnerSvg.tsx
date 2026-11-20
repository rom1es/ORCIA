import React from "react";

export interface OrciaSpinnerSvgProps {
  readonly sizePx: number;
  readonly className: string;
  readonly sizeName: string;
  readonly label?: string;
  readonly testId: string;
}

export function OrciaSpinnerSvg({
  sizePx,
  className,
  sizeName,
  label,
  testId,
}: OrciaSpinnerSvgProps): React.ReactElement {
  return (
    <svg
      data-testid={testId}
      data-size={sizeName}
      width={sizePx}
      height={sizePx}
      viewBox="0 0 24 24"
      fill="none"
      className={className}
      role={label ? "status" : undefined}
      aria-label={label}
      aria-hidden={label ? undefined : true}
    >
      <circle
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="3"
        strokeOpacity="0.25"
      />
      <path
        d="M12 2a10 10 0 0 1 10 10"
        stroke="currentColor"
        strokeWidth="3"
        strokeLinecap="round"
      />
    </svg>
  );
}
