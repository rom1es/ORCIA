import React from "react";

export interface WorkspaceSourcesRenewReferentFormProps {
  readonly datasourceId: string;
  readonly value: string;
  readonly placeholder: string;
  readonly confirmLabel: string;
  readonly cancelLabel: string;
  readonly onChange: (value: string) => void;
  readonly onSubmit: () => void;
  readonly onCancel: () => void;
}

export function WorkspaceSourcesRenewReferentForm({
  datasourceId,
  value,
  placeholder,
  confirmLabel,
  cancelLabel,
  onChange,
  onSubmit,
  onCancel,
}: WorkspaceSourcesRenewReferentFormProps): React.ReactElement {
  return (
    <form
      autoComplete="off"
      data-lpignore="true"
      data-form-type="other"
      data-testid={`renew-referent-form-${datasourceId}`}
      onSubmit={(e) => {
        e.preventDefault();
        onSubmit();
      }}
      style={{
        display: "flex",
        alignItems: "center",
        gap: "8px",
        padding: "8px 12px",
        borderRadius: "var(--radius-sm)",
        backgroundColor: "var(--color-bg-elevated)",
        border: "1px solid var(--color-border)",
      }}
    >
      <input
        type="text"
        autoComplete="off"
        data-lpignore="true"
        data-1p-ignore="true"
        data-bwignore="true"
        data-form-type="other"
        data-testid={`renew-referent-input-${datasourceId}`}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        style={{
          flex: 1,
          padding: "6px 10px",
          fontSize: "12px",
          borderRadius: "var(--radius-sm)",
          border: "1px solid var(--color-border)",
        }}
      />
      <button
        type="submit"
        data-testid={`renew-referent-submit-btn-${datasourceId}`}
        disabled={!value.trim()}
        className="orcia-ds-btn orcia-ds-btn-primary"
        style={{ padding: "5px 10px", fontSize: "11px" }}
      >
        {confirmLabel}
      </button>
      <button
        type="button"
        onClick={onCancel}
        className="orcia-ds-btn orcia-ds-btn-secondary"
        style={{ padding: "5px 10px", fontSize: "11px" }}
      >
        {cancelLabel}
      </button>
    </form>
  );
}
