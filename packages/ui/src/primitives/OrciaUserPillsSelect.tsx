import React, { useState } from "react";
import { OrciaKnownUserCombobox, type KnownUserOption } from "./OrciaKnownUserCombobox";

export interface OrciaUserPillsSelectProps {
  readonly inputId?: string;
  readonly inputTestId?: string;
  readonly selectedUserIds: readonly string[];
  readonly onChange: (nextUserIds: readonly string[]) => void;
  readonly knownUsers: readonly KnownUserOption[];
  readonly placeholder?: string;
  readonly disabled?: boolean;
  readonly addButtonLabel?: string;
  readonly removeButtonAriaLabel?: (userLabel: string) => string;
  readonly emptyLabel?: string;
  readonly draftQuery?: string;
  readonly onDraftQueryChange?: (draft: string) => void;
  readonly style?: React.CSSProperties;
}

export function resolvePendingKnownUserId(
  draft: string,
  knownUsers: readonly KnownUserOption[],
): string | null {
  const trimmed = draft.trim();
  if (!trimmed) return null;
  const lower = trimmed.toLowerCase();
  const exact = knownUsers.find(
    (u) =>
      u.principalId.toLowerCase() === lower ||
      (u.email ? u.email.toLowerCase() === lower : false) ||
      u.displayName.toLowerCase() === lower,
  );
  if (exact) return exact.principalId;
  const partial = knownUsers.find(
    (u) =>
      u.principalId.toLowerCase().includes(lower) ||
      (u.email ? u.email.toLowerCase().includes(lower) : false) ||
      u.displayName.toLowerCase().includes(lower),
  );
  return partial ? partial.principalId : trimmed;
}

const PILL_STYLE: React.CSSProperties = {
  display: "inline-flex",
  alignItems: "center",
  gap: "6px",
  padding: "3px 8px",
  borderRadius: "var(--radius-full, 9999px)",
  border: "1px solid var(--color-border)",
  backgroundColor: "var(--color-surface-hover)",
  color: "var(--color-foreground)",
  fontSize: "12px",
  fontWeight: 500,
  lineHeight: "1.4",
};

export function OrciaUserPillsSelect({
  inputId,
  inputTestId = "user-pills-select",
  selectedUserIds,
  onChange,
  knownUsers,
  placeholder,
  disabled = false,
  addButtonLabel = "Ajouter",
  removeButtonAriaLabel,
  emptyLabel,
  draftQuery,
  onDraftQueryChange,
  style,
}: OrciaUserPillsSelectProps): React.ReactElement {
  const [internalDraft, setInternalDraft] = useState("");
  const draft = draftQuery !== undefined ? draftQuery : internalDraft;

  const setDraft = (val: string) => {
    if (draftQuery === undefined) setInternalDraft(val);
    onDraftQueryChange?.(val);
  };

  const handleAddUser = (userIdToAdd?: string) => {
    if (disabled) return;
    const targetId = userIdToAdd ?? resolvePendingKnownUserId(draft, knownUsers);
    if (!targetId) return;
    const already = selectedUserIds.some((id) => id.toLowerCase() === targetId.toLowerCase());
    if (!already) onChange([...selectedUserIds, targetId]);
    setDraft("");
  };

  const handleRemoveUser = (targetId: string) => {
    if (disabled) return;
    onChange(selectedUserIds.filter((id) => id !== targetId));
  };

  const userById = (id: string) =>
    knownUsers.find((u) => u.principalId.toLowerCase() === id.toLowerCase());

  return (
    <div
      style={{ display: "flex", flexDirection: "column", gap: "8px", width: "100%", ...style }}
      data-testid={`${inputTestId}-wrapper`}
    >
      <div style={{ display: "flex", gap: "8px", alignItems: "center", width: "100%" }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          <OrciaKnownUserCombobox
            inputId={inputId}
            inputTestId={inputTestId}
            value={draft}
            onChange={setDraft}
            knownUsers={knownUsers}
            excludedPrincipalIds={selectedUserIds}
            placeholder={placeholder}
            disabled={disabled}
            onSelectOption={(option) => handleAddUser(option.principalId)}
          />
        </div>
        <button
          type="button"
          data-testid={`${inputTestId}-add-btn`}
          disabled={disabled || !draft.trim()}
          onClick={() => handleAddUser()}
          className="orcia-ds-btn-secondary"
          style={{
            whiteSpace: "nowrap",
            padding: "6px 14px",
            fontSize: "13px",
            lineHeight: "1.3",
            borderRadius: "var(--radius-md, 6px)",
            border: "1px solid var(--color-border)",
            backgroundColor: "var(--color-surface)",
            color: "var(--color-foreground)",
            cursor: disabled || !draft.trim() ? "not-allowed" : "pointer",
            opacity: disabled || !draft.trim() ? 0.6 : 1,
          }}
        >
          {addButtonLabel}
        </button>
      </div>

      {selectedUserIds.length > 0 ? (
        <div
          data-testid={`${inputTestId}-pills-container`}
          style={{ display: "flex", flexWrap: "wrap", gap: "6px", alignItems: "center" }}
        >
          {selectedUserIds.map((userId) => {
            const user = userById(userId);
            const label = user ? `${user.displayName} (${user.principalId})` : userId;
            const ariaRemove = removeButtonAriaLabel ? removeButtonAriaLabel(label) : `Retirer ${label}`;
            return (
              <span key={userId} data-testid={`${inputTestId}-pill-${userId}`} style={PILL_STYLE}>
                <span>{label}</span>
                <button
                  type="button"
                  data-testid={`${inputTestId}-remove-${userId}`}
                  aria-label={ariaRemove}
                  disabled={disabled}
                  onClick={() => handleRemoveUser(userId)}
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    justifyContent: "center",
                    border: "none",
                    background: "transparent",
                    color: "var(--color-muted-foreground)",
                    cursor: disabled ? "not-allowed" : "pointer",
                    padding: "0 2px",
                    fontSize: "14px",
                    lineHeight: "1",
                  }}
                >
                  ×
                </button>
              </span>
            );
          })}
        </div>
      ) : emptyLabel ? (
        <span
          data-testid={`${inputTestId}-empty-hint`}
          style={{ fontSize: "12px", color: "var(--color-muted-foreground)" }}
        >
          {emptyLabel}
        </span>
      ) : null}
    </div>
  );
}
