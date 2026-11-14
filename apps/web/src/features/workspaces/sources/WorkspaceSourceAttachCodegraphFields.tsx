import { OrciaSwitch } from "@orcia/ui";
import React from "react";

export const modalInputStyle: React.CSSProperties = {
  padding: "6px 10px",
  borderRadius: "var(--radius-sm)",
  border: "1px solid var(--color-border)",
  backgroundColor: "var(--color-surface-card)",
  color: "var(--color-foreground)",
  fontSize: "12px",
  width: "100%",
  boxSizing: "border-box",
};

export interface FormInputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  readonly testId: string;
}

export function FormInput({ testId, style, ...rest }: FormInputProps): React.ReactElement {
  return (
    <input
      data-testid={testId}
      autoComplete="off"
      data-lpignore="true"
      data-1p-ignore="true"
      data-bwignore="true"
      data-form-type="other"
      style={{ ...modalInputStyle, ...style }}
      {...rest}
    />
  );
}

export interface WorkspaceSourceAttachCodegraphFieldsProps {
  readonly cgEnabled: boolean;
  readonly cgAuthMode: "SERVICE_ACCOUNT" | "WORKSPACE_LEAD_TOKEN";
  readonly cgOwnerUserId: string;
  readonly isWorkspaceLead: boolean;
  readonly copy: {
    readonly gitnexusSectionTitle: string;
    readonly gitnexusEnableLabel: string;
    readonly gitnexusAuthModeLabel: string;
    readonly gitnexusOwnerUserLabel: string;
    readonly ragServiceAccount: string;
  };
  readonly onCgEnabledChange: (val: boolean) => void;
  readonly onCgAuthModeChange: (val: "SERVICE_ACCOUNT" | "WORKSPACE_LEAD_TOKEN") => void;
  readonly onCgOwnerUserIdChange: (val: string) => void;
}

export function WorkspaceSourceAttachCodegraphFields({
  cgEnabled,
  cgAuthMode,
  cgOwnerUserId,
  isWorkspaceLead,
  copy,
  onCgEnabledChange,
  onCgAuthModeChange,
  onCgOwnerUserIdChange,
}: WorkspaceSourceAttachCodegraphFieldsProps): React.ReactElement {
  return (
    <div
      data-testid="modal-gitnexus-section"
      style={{
        padding: "10px",
        borderRadius: "var(--radius-sm)",
        backgroundColor: "var(--color-bg-elevated)",
        border: "1px solid var(--color-border-subtle)",
        display: "flex",
        flexDirection: "column",
        gap: "8px",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <span style={{ fontSize: "12px", fontWeight: 600 }}>{copy.gitnexusSectionTitle}</span>
        <OrciaSwitch
          checked={cgEnabled}
          disabled={!isWorkspaceLead}
          ariaLabel={copy.gitnexusEnableLabel}
          testId="modal-gitnexus-enabled-switch"
          onCheckedChange={onCgEnabledChange}
        />
      </div>
      {cgEnabled ? (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "8px" }}>
          <div>
            <label style={{ fontSize: "11px" }}>{copy.gitnexusAuthModeLabel}</label>
            <select
              data-testid="modal-gitnexus-auth-mode-select"
              value={cgAuthMode}
              disabled={!isWorkspaceLead}
              onChange={(e) =>
                onCgAuthModeChange(e.target.value as "SERVICE_ACCOUNT" | "WORKSPACE_LEAD_TOKEN")
              }
              style={modalInputStyle}
            >
              <option value="SERVICE_ACCOUNT">{copy.ragServiceAccount}</option>
              <option value="WORKSPACE_LEAD_TOKEN">{copy.gitnexusOwnerUserLabel}</option>
            </select>
          </div>
          <div>
            <label style={{ fontSize: "11px" }}>{copy.gitnexusOwnerUserLabel}</label>
            <FormInput
              testId="modal-gitnexus-owner-user-input"
              type="text"
              disabled={!isWorkspaceLead}
              value={cgOwnerUserId}
              onChange={(e) => onCgOwnerUserIdChange(e.target.value)}
            />
          </div>
        </div>
      ) : null}
    </div>
  );
}
