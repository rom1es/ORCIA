import { OrciaButton } from "@orcia/ui";
import React from "react";
import type { IamTabDictionarySection } from "../../../i18n/locales/iam_accounts_labels";
import { OFFICIAL_IAM_ROLES, type OfficialIamRoleKey } from "./iamApiBridge";

interface IamAccountRolesFieldsetProps {
  readonly labels: IamTabDictionarySection;
  readonly selectedRoles: readonly OfficialIamRoleKey[];
  readonly disabled: boolean;
  readonly onToggleRole: (roleKey: OfficialIamRoleKey, checked: boolean) => void;
  readonly onOpenRoleMatrix: () => void;
}

export function IamAccountRolesFieldset({
  labels,
  selectedRoles,
  disabled,
  onToggleRole,
  onOpenRoleMatrix,
}: IamAccountRolesFieldsetProps): React.ReactElement {
  const dir = labels.directory;
  return (
    <fieldset
      data-testid="iam-account-roles-fieldset"
      style={{
        margin: 0,
        padding: "10px 12px",
        borderRadius: "var(--radius-sm)",
        border: "1px solid var(--color-border)",
        display: "flex",
        flexDirection: "column",
        gap: "8px",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "8px" }}>
        <legend style={{ fontSize: "12px", fontWeight: 600, padding: "0 4px" }}>
          {dir.rolesFieldsetLabel}
        </legend>
        <OrciaButton
          variant="secondary"
          size="sm"
          testId="iam-modal-open-role-matrix-btn"
          onClick={onOpenRoleMatrix}
        >
          {labels.matrix.openRoleMatrixCta}
        </OrciaButton>
      </div>
      <p style={{ margin: 0, fontSize: "11.5px", color: "var(--color-muted-foreground)" }}>
        {dir.rolesHelperText}
      </p>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "6px" }}>
        {OFFICIAL_IAM_ROLES.map((roleKey) => (
          <label
            key={roleKey}
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "6px",
              fontSize: "12.5px",
              cursor: disabled ? "not-allowed" : "pointer",
            }}
          >
            <input
              type="checkbox"
              autoComplete="off"
              data-lpignore="true"
              data-1p-ignore="true"
              data-bwignore="true"
              data-form-type="other"
              data-testid={`iam-account-role-checkbox-${roleKey}`}
              disabled={disabled}
              checked={selectedRoles.includes(roleKey)}
              onChange={(e) => onToggleRole(roleKey, e.target.checked)}
            />
            <span>{labels.roles[roleKey]}</span>
          </label>
        ))}
      </div>
    </fieldset>
  );
}
