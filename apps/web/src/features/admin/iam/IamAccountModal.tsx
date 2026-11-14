import type { IamAccountResponse } from "@orcia/api-client";
import { OrciaAlertBanner, OrciaDialog } from "@orcia/ui";
import React, { useEffect, useState } from "react";
import type { ConfiguredOrgUnit } from "../../../components/platformSetupStorageHelpers";
import type { IamTabDictionarySection } from "../../../i18n/locales/iam_accounts_labels";
import { OFFICIAL_IAM_ROLES, type OfficialIamRoleKey } from "./iamApiBridge";

export interface IamAccountModalSubmitValues {
  readonly accountKind: "HUMAN" | "SERVICE_PRINCIPAL";
  readonly displayName: string;
  readonly emailOrPrincipal: string;
  readonly status: "ACTIVE" | "INVITED" | "DISABLED";
  readonly roles: readonly OfficialIamRoleKey[];
  readonly teamIds: readonly string[];
}

export interface IamAccountInitialCreateDefaults {
  readonly displayName?: string;
  readonly emailOrPrincipal?: string;
  readonly teamIds?: readonly string[];
}

export interface IamAccountModalProps {
  readonly open: boolean;
  readonly onOpenChange: (open: boolean) => void;
  readonly canMutate: boolean;
  readonly editingAccount: IamAccountResponse | null;
  readonly orgUnits: readonly ConfiguredOrgUnit[];
  readonly labels: IamTabDictionarySection;
  readonly errorMessage: string | null;
  readonly isSubmitting: boolean;
  readonly initialCreateDefaults?: IamAccountInitialCreateDefaults;
  readonly onSubmit: (values: IamAccountModalSubmitValues) => void;
}

export function IamAccountModal({
  open,
  onOpenChange,
  canMutate,
  editingAccount,
  orgUnits,
  labels,
  errorMessage,
  isSubmitting,
  initialCreateDefaults,
  onSubmit,
}: IamAccountModalProps): React.ReactElement {
  const dir = labels.directory;
  const teamUnits = orgUnits.filter((u) => u.level === "TEAM");

  const [accountKind, setAccountKind] = useState<"HUMAN" | "SERVICE_PRINCIPAL">("HUMAN");
  const [displayName, setDisplayName] = useState("");
  const [emailOrPrincipal, setEmailOrPrincipal] = useState("");
  const [status, setStatus] = useState<"ACTIVE" | "INVITED" | "DISABLED">("ACTIVE");
  const [selectedRoles, setSelectedRoles] = useState<readonly OfficialIamRoleKey[]>([
    "CONTRIBUTOR",
  ]);
  const [selectedTeamIds, setSelectedTeamIds] = useState<readonly string[]>([]);

  useEffect(() => {
    if (!open) return;
    if (editingAccount) {
      setAccountKind(editingAccount.account_kind);
      setDisplayName(editingAccount.display_name);
      setEmailOrPrincipal(editingAccount.email ?? editingAccount.principal_id);
      setStatus(editingAccount.status);
      setSelectedRoles(editingAccount.roles as readonly OfficialIamRoleKey[]);
      setSelectedTeamIds(editingAccount.team_ids);
    } else {
      setAccountKind("HUMAN");
      setDisplayName(initialCreateDefaults?.displayName ?? "");
      setEmailOrPrincipal(initialCreateDefaults?.emailOrPrincipal ?? "");
      setStatus("ACTIVE");
      setSelectedRoles(["CONTRIBUTOR"]);
      setSelectedTeamIds(initialCreateDefaults?.teamIds ?? []);
    }
  }, [open, editingAccount, initialCreateDefaults]);

  const isEditing = editingAccount !== null;
  const submitDisabled =
    !canMutate ||
    isSubmitting ||
    !displayName.trim() ||
    (!isEditing && !emailOrPrincipal.trim()) ||
    selectedRoles.length === 0;

  return (
    <OrciaDialog
      open={open}
      onOpenChange={onOpenChange}
      title={isEditing ? dir.modalEditTitle : dir.modalCreateTitle}
      description={dir.modalDescription}
      testId="iam-account-modal"
      closeLabel={dir.cancelButton}
    >
      <form
        data-testid="iam-account-modal-form"
        autoComplete="off"
        data-lpignore="true"
        data-1p-ignore="true"
        data-bwignore="true"
        data-form-type="other"
        onSubmit={(e) => {
          e.preventDefault();
          if (submitDisabled) return;
          onSubmit({
            accountKind,
            displayName: displayName.trim(),
            emailOrPrincipal: emailOrPrincipal.trim(),
            status,
            roles: selectedRoles,
            teamIds: selectedTeamIds,
          });
        }}
        style={{ display: "flex", flexDirection: "column", gap: "12px", marginTop: "8px" }}
      >
        {errorMessage ? (
          <OrciaAlertBanner tone="crimson" testId="iam-account-modal-error-banner">
            {errorMessage}
          </OrciaAlertBanner>
        ) : null}

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px" }}>
          <label style={{ display: "flex", flexDirection: "column", gap: "4px", fontSize: "12px" }}>
            <span style={{ fontWeight: 600 }}>{dir.kindLabel}</span>
            <select
              data-testid="iam-account-kind-select"
              disabled={!canMutate || isSubmitting || isEditing}
              value={accountKind}
              onChange={(e) =>
                setAccountKind(e.target.value as "HUMAN" | "SERVICE_PRINCIPAL")
              }
              className="orcia-ds-select"
            >
              <option value="HUMAN">{dir.kindHumanOption}</option>
              <option value="SERVICE_PRINCIPAL">{dir.kindServicePrincipalOption}</option>
            </select>
          </label>

          <label style={{ display: "flex", flexDirection: "column", gap: "4px", fontSize: "12px" }}>
            <span style={{ fontWeight: 600 }}>{dir.statusLabel}</span>
            <select
              data-testid="iam-account-status-select"
              disabled={!canMutate || isSubmitting}
              value={status}
              onChange={(e) =>
                setStatus(e.target.value as "ACTIVE" | "INVITED" | "DISABLED")
              }
              className="orcia-ds-select"
            >
              <option value="ACTIVE">{dir.statusActive}</option>
              <option value="INVITED">{dir.statusInvited}</option>
              <option value="DISABLED">{dir.statusDisabled}</option>
            </select>
          </label>
        </div>

        <label style={{ display: "flex", flexDirection: "column", gap: "4px", fontSize: "12px" }}>
          <span style={{ fontWeight: 600 }}>{dir.displayNameLabel}</span>
          <input
            type="text"
            autoComplete="off"
            data-lpignore="true"
            data-1p-ignore="true"
            data-bwignore="true"
            data-form-type="other"
            data-testid="iam-account-display-name-input"
            disabled={!canMutate || isSubmitting}
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            placeholder={dir.displayNamePlaceholder}
            className="orcia-ds-input"
          />
        </label>

        <label style={{ display: "flex", flexDirection: "column", gap: "4px", fontSize: "12px" }}>
          <span style={{ fontWeight: 600 }}>{dir.emailOrPrincipalLabel}</span>
          <input
            type="text"
            autoComplete="off"
            data-lpignore="true"
            data-1p-ignore="true"
            data-bwignore="true"
            data-form-type="other"
            data-testid="iam-account-principal-input"
            disabled={!canMutate || isSubmitting || (isEditing && accountKind === "SERVICE_PRINCIPAL")}
            value={emailOrPrincipal}
            onChange={(e) => setEmailOrPrincipal(e.target.value)}
            placeholder={
              accountKind === "SERVICE_PRINCIPAL"
                ? dir.principalSpPlaceholder
                : dir.emailPlaceholder
            }
            className="orcia-ds-input"
          />
        </label>

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
          <legend style={{ fontSize: "12px", fontWeight: 600, padding: "0 4px" }}>
            {dir.rolesFieldsetLabel}
          </legend>
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
                  cursor: !canMutate || isSubmitting ? "not-allowed" : "pointer",
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
                  disabled={!canMutate || isSubmitting}
                  checked={selectedRoles.includes(roleKey)}
                  onChange={(e) =>
                    setSelectedRoles((prev) =>
                      e.target.checked
                        ? prev.includes(roleKey)
                          ? prev
                          : [...prev, roleKey]
                        : prev.filter((r) => r !== roleKey),
                    )
                  }
                />
                <span>{labels.roles[roleKey]}</span>
              </label>
            ))}
          </div>
        </fieldset>

        <fieldset
          data-testid="iam-account-teams-fieldset"
          style={{
            margin: 0,
            padding: "10px 12px",
            borderRadius: "var(--radius-sm)",
            border: "1px solid var(--color-border)",
            display: "flex",
            flexDirection: "column",
            gap: "6px",
          }}
        >
          <legend style={{ fontSize: "12px", fontWeight: 600, padding: "0 4px" }}>
            {dir.teamsFieldsetLabel}
          </legend>
          {teamUnits.length === 0 ? (
            <p style={{ margin: 0, fontSize: "12px", color: "var(--color-muted-foreground)" }}>
              {dir.noTeamsAvailableHint}
            </p>
          ) : (
            <div style={{ display: "flex", flexWrap: "wrap", gap: "10px" }}>
              {teamUnits.map((team) => {
                const checked =
                  selectedTeamIds.includes(team.id) || selectedTeamIds.includes(team.slug);
                return (
                  <label
                    key={team.id}
                    style={{
                      display: "inline-flex",
                      alignItems: "center",
                      gap: "6px",
                      fontSize: "12.5px",
                      cursor: !canMutate || isSubmitting ? "not-allowed" : "pointer",
                    }}
                  >
                    <input
                      type="checkbox"
                      autoComplete="off"
                      data-lpignore="true"
                      data-1p-ignore="true"
                      data-bwignore="true"
                      data-form-type="other"
                      data-testid={`iam-account-team-checkbox-${team.id}`}
                      disabled={!canMutate || isSubmitting}
                      checked={checked}
                      onChange={(e) =>
                        setSelectedTeamIds((prev) =>
                          e.target.checked
                            ? [...prev.filter((id) => id !== team.slug), team.id]
                            : prev.filter((id) => id !== team.id && id !== team.slug),
                        )
                      }
                    />
                    <span>{team.name}</span>
                  </label>
                );
              })}
            </div>
          )}
        </fieldset>

        <div style={{ display: "flex", justifyContent: "flex-end", gap: "8px", marginTop: "4px" }}>
          <button
            type="button"
            data-testid="iam-account-modal-cancel-btn"
            onClick={() => onOpenChange(false)}
            className="orcia-ds-btn orcia-ds-btn-secondary"
          >
            {dir.cancelButton}
          </button>
          <button
            type="submit"
            data-testid="iam-account-modal-submit-btn"
            disabled={submitDisabled}
            className="orcia-ds-btn orcia-ds-btn-primary"
          >
            {isEditing ? dir.saveEditButton : dir.saveCreateButton}
          </button>
        </div>
      </form>
    </OrciaDialog>
  );
}
