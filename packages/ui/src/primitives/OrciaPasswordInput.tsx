import React, { useState } from "react";
import { OrciaIcon } from "../components/icons";

export interface OrciaPasswordInputProps {
  readonly id?: string;
  readonly testId?: string;
  readonly toggleTestId?: string;
  readonly value: string;
  readonly onChange: (nextValue: string) => void;
  readonly maskMode?: "masked-text" | "password";
  readonly placeholder?: string;
  readonly autoComplete?: string;
  readonly required?: boolean;
  readonly disabled?: boolean;
  readonly showPasswordLabel: string;
  readonly hidePasswordLabel: string;
  readonly inputClassName?: string;
  readonly inputStyle?: React.CSSProperties;
}

/**
 * Reusable Password / Secret Input with eye visibility toggle (`@orcia/ui`).
 * - `maskMode="masked-text"` (default): uses `.orcia-masked-secret-input` (`WebkitTextSecurity`)
 *   to prevent password-manager heuristics outside `/login`.
 * - `maskMode="password"`: uses native masked input on `/login` with reveal toggle.
 */
export function OrciaPasswordInput({
  id,
  testId,
  toggleTestId,
  value,
  onChange,
  maskMode = "masked-text",
  placeholder = "",
  autoComplete,
  required,
  disabled,
  showPasswordLabel,
  hidePasswordLabel,
  inputClassName,
  inputStyle,
}: OrciaPasswordInputProps): React.ReactElement {
  const [revealed, setRevealed] = useState<boolean>(false);

  const isNativePassword = maskMode === "password";
  const maskedNativeType = "password" as const;
  const effectiveType = isNativePassword ? (revealed ? "text" : maskedNativeType) : "text";
  const maskedClass = !isNativePassword && !revealed ? "orcia-masked-secret-input " : "";
  const toggleLabel = revealed ? hidePasswordLabel : showPasswordLabel;

  const computedStyle: React.CSSProperties = {
    backgroundColor: "var(--color-bg-canvas)",
    borderColor: "var(--color-border-subtle)",
    color: "var(--color-text-primary)",
    ...(isNativePassword
      ? {}
      : ({ WebkitTextSecurity: revealed ? "none" : "disc" } as React.CSSProperties)),
    ...inputStyle,
  };

  const loginProps: React.InputHTMLAttributes<HTMLInputElement> = {
    autoComplete: autoComplete ?? "current-password",
  };

  return (
    <div className="relative flex w-full items-center">
      {isNativePassword ? (
        <input
          id={id}
          type={effectiveType}
          spellCheck={false}
          {...loginProps}
          required={required}
          disabled={disabled}
          placeholder={placeholder}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          data-testid={testId}
          className={`w-full rounded border py-1.5 pl-3 pr-9 ${inputClassName ?? ""}`.trim()}
          style={computedStyle}
        />
      ) : (
        <input
          id={id}
          type="text"
          spellCheck={false}
          autoComplete="off"
          data-lpignore="true"
          data-1p-ignore="true"
          data-bwignore="true"
          data-form-type="other"
          required={required}
          disabled={disabled}
          placeholder={placeholder}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          data-testid={testId}
          className={`${maskedClass}w-full rounded border py-1.5 pl-3 pr-9 ${inputClassName ?? ""}`.trim()}
          style={computedStyle}
        />
      )}
      <button
        type="button"
        data-testid={toggleTestId ?? (testId ? `${testId}-toggle-visibility` : undefined)}
        aria-label={toggleLabel}
        aria-pressed={revealed}
        title={toggleLabel}
        disabled={disabled}
        onClick={() => setRevealed((prev) => !prev)}
        className="absolute right-1.5 inline-flex h-6 w-6 items-center justify-center rounded transition-opacity hover:opacity-100 focus-visible:outline-none"
        style={{
          color: "var(--color-text-secondary)",
          backgroundColor: "transparent",
          opacity: 0.85,
        }}
      >
        <OrciaIcon name={revealed ? "eyeOff" : "eye"} size={15} />
      </button>
    </div>
  );
}
