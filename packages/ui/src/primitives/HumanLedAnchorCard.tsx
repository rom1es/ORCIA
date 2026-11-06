import React from "react";
import { DisabledButtonAlertIndicator } from "../components/DisabledButtonAlertIndicator";

export interface HumanLedAnchorCardLabels {
  badgeTitle: string;
  authorLabel: string;
  placeholderText: string;
  submitLabel: string;
}

export interface HumanLedAnchorCardProps {
  sectionKey: string;
  sectionTitle: string;
  authorName: string;
  value: string;
  readOnly?: boolean;
  labels: HumanLedAnchorCardLabels;
  testId?: string;
  justificationTestId?: string;
  signatureLabel?: string;
  signatureValue?: string;
  signaturePlaceholder?: string;
  signatureTestId?: string;
  hideSubmitButton?: boolean;
  minCharactersRequired?: number;
  onChange?: (nextValue: string) => void;
  onSignatureChange?: (nextSignature: string) => void;
  onSignAnchor?: (sectionKey: string, content: string) => void;
}

/**
 * HumanLedAnchorCard — Exclusive consumer of `--color-human-led-violet` (DESIGN.md, AD-3, UX-DR3).
 * Represents a mandatory human-authored section (`human_authored_required: true`).
 * Never renders an AI auto-generation button and locks agent execution below 30 characters.
 */
export function HumanLedAnchorCard({
  sectionKey,
  sectionTitle,
  authorName,
  value,
  readOnly = false,
  labels,
  testId,
  justificationTestId,
  signatureLabel,
  signatureValue,
  signaturePlaceholder,
  signatureTestId,
  hideSubmitButton = false,
  minCharactersRequired = 30,
  onChange,
  onSignatureChange,
  onSignAnchor,
}: HumanLedAnchorCardProps) {
  const charCount = value.trim().length;
  const isLocked = charCount < minCharactersRequired;

  return (
    <section
      data-testid={testId ?? `human-anchor-card-${sectionKey}`}
      data-human-authored-required="true"
      data-ai-generation-forbidden="true"
      data-char-count={String(charCount)}
      data-anchor-locked={isLocked ? "true" : "false"}
      style={{
        backgroundColor: "var(--color-human-led-bg)",
        border: "1px solid var(--color-human-led-violet)",
        borderLeft: "4px solid var(--color-human-led-violet)",
        borderRadius: "var(--radius-md)",
        padding: "16px",
        display: "flex",
        flexDirection: "column",
        gap: "10px",
      }}
    >
      <header
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          gap: "8px",
          flexWrap: "wrap",
        }}
      >
        <span
          style={{
            color: "var(--color-human-led-violet)",
            fontWeight: 700,
            fontSize: "var(--font-size-mono)",
            fontFamily: "var(--font-mono)",
          }}
        >
          {labels.badgeTitle}
        </span>
        <span
          style={{
            color: "var(--color-muted-foreground)",
            fontSize: "var(--font-size-mono)",
          }}
        >
          {labels.authorLabel}: {authorName} ({charCount}/{minCharactersRequired})
        </span>
      </header>

      <h3
        style={{
          margin: 0,
          fontFamily: "var(--font-serif)",
          fontSize: "var(--font-size-display)",
          color: "var(--color-foreground)",
        }}
      >
        {sectionTitle}
      </h3>

      <textarea
        autoComplete="off"
        data-lpignore="true"
        data-1p-ignore="true"
        data-bwignore="true"
        data-form-type="other"
        data-testid={justificationTestId}
        aria-label={sectionTitle}
        value={value}
        disabled={readOnly}
        placeholder={labels.placeholderText}
        onChange={(e) => onChange?.(e.target.value)}
        style={{
          width: "100%",
          minHeight: "84px",
          padding: "8px",
          borderRadius: "var(--radius-sm)",
          border: "1px solid var(--color-human-led-violet)",
          backgroundColor: "var(--color-surface-card)",
          color: "var(--color-foreground)",
          fontFamily: "var(--font-sans)",
          boxSizing: "border-box",
        }}
      />

      {signatureLabel && (
        <input
          type="text"
          autoComplete="off"
          data-lpignore="true"
          data-1p-ignore="true"
          data-bwignore="true"
          data-form-type="other"
          data-testid={signatureTestId}
          aria-label={signatureLabel}
          value={signatureValue ?? ""}
          disabled={readOnly}
          placeholder={signaturePlaceholder}
          onChange={(e) => onSignatureChange?.(e.target.value)}
          style={{
            width: "100%",
            padding: "6px 8px",
            borderRadius: "var(--radius-sm)",
            border: "1px solid var(--color-human-led-violet)",
            backgroundColor: "var(--color-surface-card)",
            color: "var(--color-foreground)",
            fontFamily: "var(--font-mono)",
            fontSize: "var(--font-size-mono)",
            boxSizing: "border-box",
          }}
        />
      )}

      {!readOnly && !hideSubmitButton && (
        <div>
          <button
            type="button"
            disabled={isLocked}
            data-testid={`human-anchor-submit-${sectionKey}`}
            onClick={() => {
              if (!isLocked) {
                onSignAnchor?.(sectionKey, value);
              }
            }}
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "6px",
              backgroundColor: "var(--color-human-led-violet)",
              color: "var(--color-primary-foreground)",
              border: "none",
              borderRadius: "var(--radius-sm)",
              padding: "6px 12px",
              fontWeight: 600,
              cursor: isLocked ? "not-allowed" : "pointer",
              opacity: isLocked ? 0.55 : 1,
            }}
          >
            <span>{labels.submitLabel}</span>
            <DisabledButtonAlertIndicator
              disabled={isLocked}
              reason={labels.placeholderText}
              testIdSuffix={`human-anchor-submit-${sectionKey}`}
            />
          </button>
        </div>
      )}
    </section>
  );
}
