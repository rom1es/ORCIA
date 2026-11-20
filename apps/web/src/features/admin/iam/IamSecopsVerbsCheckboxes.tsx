import type { UiPermissionVerb } from "@orcia/ui";
import React from "react";
import type { IamTabDictionarySection } from "../../../i18n/locales/iam_accounts_labels";

const ALL_SIX_VERBS: readonly UiPermissionVerb[] = [
  "create",
  "read",
  "update",
  "delete",
  "execute",
  "grant",
];

export interface IamSecopsVerbsCheckboxesProps {
  readonly controlsLocked: boolean;
  readonly hasImpliedRead: boolean;
  readonly effectiveVerbs: readonly UiPermissionVerb[];
  readonly labels: IamTabDictionarySection;
  readonly onToggleVerb: (verb: UiPermissionVerb, checked: boolean) => void;
}

export function IamSecopsVerbsCheckboxes({
  controlsLocked,
  hasImpliedRead,
  effectiveVerbs,
  labels,
  onToggleVerb,
}: IamSecopsVerbsCheckboxesProps): React.ReactElement {
  const sec = labels.secopsDrawer;

  return (
    <div
      data-testid="rbac-verbs-checkbox-group"
      style={{
        display: "flex",
        flexDirection: "column",
        gap: "6px",
        padding: "10px 12px",
        borderRadius: "var(--radius-sm)",
        border: "1px solid var(--color-border)",
        fontSize: "12px",
      }}
    >
      <div style={{ display: "flex", flexWrap: "wrap", gap: "14px", alignItems: "center" }}>
        <span style={{ fontWeight: 600 }}>{sec.verbsFieldsetLabel} :</span>
        {ALL_SIX_VERBS.map((v) => {
          const isReadHeld = v === "read" && hasImpliedRead;
          const checked = effectiveVerbs.includes(v);
          const checkboxDisabled = controlsLocked || isReadHeld;
          return (
            <label
              key={v}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "6px",
                cursor: checkboxDisabled ? "not-allowed" : "pointer",
              }}
            >
              <input
                type="checkbox"
                autoComplete="off"
                data-lpignore="true"
                data-1p-ignore="true"
                data-bwignore="true"
                data-form-type="other"
                data-testid={`rbac-verb-checkbox-${v}`}
                disabled={checkboxDisabled}
                checked={checked}
                onChange={(e) => {
                  if (isReadHeld) return;
                  onToggleVerb(v, e.target.checked);
                }}
              />
              <span>{labels.verbs[v]}</span>
            </label>
          );
        })}
      </div>
      <span style={{ fontSize: "11.5px", color: "var(--color-muted-foreground)" }}>
        {sec.autoReadHint}
      </span>
    </div>
  );
}
