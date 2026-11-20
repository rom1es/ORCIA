import React from "react";
import { OrciaSpinnerSvg } from "../components/icons/OrciaSpinnerSvg";

export type OrciaSpinnerSize = "xs" | "sm" | "md" | "lg";

const SPINNER_SIZE_PX: Readonly<Record<OrciaSpinnerSize, number>> = {
  xs: 12,
  sm: 14,
  md: 18,
  lg: 24,
};

const SPINNER_SIZE_CLASS: Readonly<Record<OrciaSpinnerSize, string>> = {
  xs: "h-3 w-3",
  sm: "h-3.5 w-3.5",
  md: "h-4.5 w-4.5",
  lg: "h-6 w-6",
};

export interface OrciaSpinnerProps {
  readonly size?: OrciaSpinnerSize;
  readonly className?: string;
  readonly label?: string;
  readonly testId?: string;
}

export function OrciaSpinner({
  size = "sm",
  className = "",
  label,
  testId = "orcia-spinner",
}: OrciaSpinnerProps): React.ReactElement {
  const px = SPINNER_SIZE_PX[size];
  const mergedClassName = ["inline-block shrink-0 animate-spin", SPINNER_SIZE_CLASS[size], className]
    .filter(Boolean)
    .join(" ");

  return (
    <OrciaSpinnerSvg
      sizePx={px}
      sizeName={size}
      className={mergedClassName}
      label={label}
      testId={testId}
    />
  );
}
