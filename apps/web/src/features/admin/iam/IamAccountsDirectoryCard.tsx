import type { IamAccountResponse } from "@orcia/api-client";
import { OrciaAlertBanner, OrciaButton, OrciaIcon, StatusBadge } from "@orcia/ui";
import React from "react";
import type { ConfiguredOrgUnit } from "../../../components/platformSetupStorageHelpers";
import type { IamTabDictionarySection } from "../../../i18n/locales/iam_accounts_labels";
import type { OfficialIamRoleKey } from "./iamApiBridge";

export interface IamAccountsDirectoryCardProps {
  readonly canMutate: boolean;
  readonly accounts: readonly IamAccountResponse[];
  readonly orgUnits: readonly ConfiguredOrgUnit[];
  readonly labels: IamTabDictionarySection;
  readonly errorMessage: string | null;
  readonly onOpenRoleMatrix: () => void;
  readonly onOpenCreateModal: () => void;
  readonly onOpenEditModal: (account: IamAccountResponse) => void;
  readonly onDeleteAccount: (account: IamAccountResponse) => void;
  readonly onResetTemporaryPassword?: (account: IamAccountResponse) => void;
}

export function IamAccountsDirectoryCard({
  canMutate,
  accounts,
  orgUnits,
  labels,
  errorMessage,
  onOpenRoleMatrix,
  onOpenCreateModal,
  onOpenEditModal,
  onDeleteAccount,
  onResetTemporaryPassword,
}: IamAccountsDirectoryCardProps): React.ReactElement {
  const dir = labels.directory;

  const formatAuthSource = (source: IamAccountResponse["auth_source"]): string => {
    if (source === "LOCAL_BOOTSTRAP") return dir.authLocalBootstrap;
    if (source === "SERVICE_TOKEN") return dir.authServiceToken;
    return dir.authFederated;
  };

  const formatStatus = (
    status: IamAccountResponse["status"],
  ): { readonly label: string; readonly tone: "emerald" | "amber" | "crimson" } => {
    if (status === "ACTIVE") return { label: dir.statusActive, tone: "emerald" };
    if (status === "INVITED") return { label: dir.statusInvited, tone: "amber" };
    return { label: dir.statusDisabled, tone: "crimson" };
  };

  const resolveTeamNames = (teamIds: readonly string[]): string => {
    if (teamIds.length === 0) return dir.noTeamsAssigned;
    const names = teamIds.map((tid) => {
      const matched = orgUnits.find((u) => u.id === tid || u.slug === tid);
      return matched ? matched.name : tid;
    });
    return `${dir.teamsPrefix} ${names.join(", ")}`;
  };

  return (
    <section
      data-testid="iam-accounts-directory-card"
      className="orcia-bento-card"
      style={{ display: "flex", flexDirection: "column", gap: "12px" }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
          flexWrap: "wrap",
          gap: "10px",
        }}
      >
        <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
          <h2 style={{ margin: 0, fontSize: "15px" }}>{dir.sectionTitle}</h2>
          <p
            style={{
              margin: 0,
              fontSize: "12.5px",
              color: "var(--color-muted-foreground)",
            }}
          >
            {dir.sectionSubtitle}
          </p>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
          <OrciaButton
            variant="secondary"
            size="sm"
            testId="iam-open-role-matrix-modal-btn"
            onClick={onOpenRoleMatrix}
          >
            <OrciaIcon name="document" size={14} />
            <span>{labels.directory.openRoleMatrixCta || labels.matrix.openRoleMatrixCta}</span>
          </OrciaButton>
          <button
            type="button"
            data-testid="iam-open-create-account-btn"
            disabled={!canMutate}
            onClick={onOpenCreateModal}
            className="orcia-ds-btn orcia-ds-btn-primary"
          >
            <OrciaIcon name="user" size={14} />
            <span>{dir.createAccountCta}</span>
          </button>
        </div>
      </div>

      {errorMessage ? (
        <OrciaAlertBanner tone="crimson" testId="iam-accounts-error-banner">
          {errorMessage}
        </OrciaAlertBanner>
      ) : null}

      {accounts.length === 0 ? (
        <p
          data-testid="iam-accounts-empty-state"
          style={{ margin: 0, fontSize: "13px", color: "var(--color-muted-foreground)" }}
        >
          {dir.emptyText}
        </p>
      ) : (
        <div style={{ display: "grid", gap: "8px" }}>
          {accounts.map((acc) => {
            const statusInfo = formatStatus(acc.status);
            return (
              <div
                key={acc.id}
                data-testid={`iam-account-row-${acc.id}`}
                data-principal-id={acc.principal_id}
                style={{
                  padding: "10px 12px",
                  borderRadius: "var(--radius-sm)",
                  border: "1px solid var(--color-border)",
                  backgroundColor: "var(--color-surface-card)",
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  flexWrap: "wrap",
                  gap: "10px",
                }}
              >
                <div style={{ display: "flex", flexDirection: "column", gap: "6px", flex: 1, minWidth: "240px" }}>
                  <div style={{ display: "flex", alignItems: "center", flexWrap: "wrap", gap: "8px" }}>
                    <strong style={{ fontSize: "13.5px" }}>{acc.display_name}</strong>
                    <code
                      style={{
                        fontSize: "11.5px",
                        fontFamily: "var(--font-mono)",
                        color: "var(--color-muted-foreground)",
                        padding: "1px 6px",
                        borderRadius: "var(--radius-sm)",
                        backgroundColor: "var(--color-surface-muted)",
                      }}
                    >
                      {acc.email ?? acc.principal_id}
                    </code>
                    <StatusBadge
                      label={
                        acc.account_kind === "SERVICE_PRINCIPAL"
                          ? dir.servicePrincipalBadge
                          : dir.humanBadge
                      }
                      tone="neutral"
                    />
                    <StatusBadge label={formatAuthSource(acc.auth_source)} tone="neutral" />
                    <StatusBadge label={statusInfo.label} tone={statusInfo.tone} />
                  </div>

                  <div style={{ display: "flex", alignItems: "center", flexWrap: "wrap", gap: "6px" }}>
                    {acc.roles.map((roleKey) => (
                      <StatusBadge
                        key={roleKey}
                        label={labels.roles[roleKey as OfficialIamRoleKey] ?? roleKey}
                        tone={
                          roleKey === "PLATFORM_ADMIN" || roleKey === "SECOPS"
                            ? "cobalt"
                            : "emerald"
                        }
                      />
                    ))}
                    <span
                      style={{
                        fontSize: "12px",
                        color: "var(--color-muted-foreground)",
                        marginLeft: "4px",
                      }}
                    >
                      · {resolveTeamNames(acc.team_ids)}
                    </span>
                  </div>
                </div>

                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  {acc.account_kind === "HUMAN" && onResetTemporaryPassword ? (
                    <button
                      type="button"
                      data-testid={`iam-reset-password-account-btn-${acc.id}`}
                      disabled={!canMutate}
                      onClick={() => onResetTemporaryPassword(acc)}
                      className="orcia-ds-btn orcia-ds-btn-secondary"
                      style={{ padding: "5px 10px", fontSize: "12px" }}
                    >
                      {dir.editButton === "Modifier" ? "Mot de passe" : "Password"}
                    </button>
                  ) : null}
                  <button
                    type="button"
                    data-testid={`iam-edit-account-btn-${acc.id}`}
                    disabled={!canMutate}
                    onClick={() => onOpenEditModal(acc)}
                    className="orcia-ds-btn orcia-ds-btn-secondary"
                    style={{ padding: "5px 10px", fontSize: "12px" }}
                  >
                    {dir.editButton}
                  </button>
                  <button
                    type="button"
                    data-testid={`iam-delete-account-btn-${acc.id}`}
                    disabled={!canMutate}
                    onClick={() => onDeleteAccount(acc)}
                    className="orcia-ds-btn orcia-ds-btn-danger"
                    style={{ padding: "5px 10px", fontSize: "12px" }}
                  >
                    {dir.deleteButton}
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}
