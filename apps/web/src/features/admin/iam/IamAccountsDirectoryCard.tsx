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
  readonly authMode?: "LOCAL" | "SSO";
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
  authMode,
  onOpenRoleMatrix,
  onOpenCreateModal,
  onOpenEditModal,
  onDeleteAccount,
  onResetTemporaryPassword,
}: IamAccountsDirectoryCardProps): React.ReactElement {
  const dir = labels.directory;

  const formatStatus = (
    status: IamAccountResponse["status"],
  ): { readonly label: string; readonly tone: "emerald" | "amber" | "crimson" } => {
    if (status === "ACTIVE") return { label: dir.statusActive, tone: "emerald" };
    if (status === "INVITED") return { label: dir.statusInvited, tone: "amber" };
    return { label: dir.statusDisabled, tone: "crimson" };
  };

  const resolveAccountTopology = (acc: IamAccountResponse) => {
    const principalLower = acc.principal_id.toLowerCase().trim();
    const emailLower = acc.email ? acc.email.toLowerCase().trim() : null;

    const isMatchUser = (idOrEmail?: string | null) => {
      if (!idOrEmail) return false;
      const lower = idOrEmail.toLowerCase().trim();
      return lower === principalLower || (emailLower !== null && lower === emailLower);
    };

    const ledBus: ConfiguredOrgUnit[] = [];
    const ontologyLedBus: ConfiguredOrgUnit[] = [];
    const ledTeams: ConfiguredOrgUnit[] = [];
    const memberTeams: ConfiguredOrgUnit[] = [];

    for (const unit of orgUnits) {
      const isLead =
        (unit.level === "BU" && acc.led_bu_ids?.includes(unit.id)) ||
        (unit.level === "TEAM" && acc.led_team_ids?.includes(unit.id)) ||
        (Array.isArray(unit.leadUserIds) && unit.leadUserIds.some(isMatchUser)) ||
        isMatchUser(unit.leadUserId);
      const isOntoLead =
        unit.level === "BU" &&
        (Boolean(acc.ontology_led_bu_ids?.includes(unit.id)) ||
          (Array.isArray(unit.ontologyLeadUserIds) &&
            unit.ontologyLeadUserIds.some(isMatchUser)));

      if (unit.level === "BU") {
        if (isLead && !ledBus.some((b) => b.id === unit.id)) {
          ledBus.push(unit);
        }
        if (isOntoLead && !ontologyLedBus.some((b) => b.id === unit.id)) {
          ontologyLedBus.push(unit);
        }
      } else if (unit.level === "TEAM") {
        if (isLead) {
          if (!ledTeams.some((t) => t.id === unit.id)) {
            ledTeams.push(unit);
          }
        } else {
          const isMember =
            acc.team_ids?.includes(unit.id) ||
            acc.team_ids?.includes(unit.slug) ||
            (Array.isArray(unit.memberUserIds) && unit.memberUserIds.some(isMatchUser));
          if (isMember && !memberTeams.some((t) => t.id === unit.id)) {
            memberTeams.push(unit);
          }
        }
      }
    }

    return { ledBus, ontologyLedBus, ledTeams, memberTeams };
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
          <p style={{ margin: 0, fontSize: "12.5px", color: "var(--color-muted-foreground)" }}>
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
            const { ledBus, ontologyLedBus, ledTeams, memberTeams } = resolveAccountTopology(acc);
            const hasBuLeadRole = acc.roles.includes("BU_LEAD");
            const hasTeamLeadRole = acc.roles.includes("TEAM_LEAD");
            const hasOntologyLeadRole = acc.roles.includes("ONTOLOGY_LEAD");
            const showFallbackNoTeams =
              acc.account_kind === "HUMAN" &&
              ledBus.length === 0 &&
              ontologyLedBus.length === 0 &&
              ledTeams.length === 0 &&
              memberTeams.length === 0 &&
              !hasBuLeadRole &&
              !hasTeamLeadRole &&
              !hasOntologyLeadRole &&
              acc.roles.some((r) => r !== "PLATFORM_ADMIN" && r !== "SECOPS");

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
                    {acc.account_kind === "SERVICE_PRINCIPAL" ? (
                      <StatusBadge label={dir.servicePrincipalBadge} tone="neutral" />
                    ) : null}
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

                    {ledBus.length > 0 ? (
                      <span
                        data-testid={`iam-account-led-bus-${acc.id}`}
                        style={{
                          fontSize: "12px",
                          color: "var(--color-foreground)",
                          fontWeight: 600,
                          marginLeft: "4px",
                        }}
                      >
                        · {ledBus.length > 1 ? dir.ledBusPluralPrefix : dir.ledBusPrefix} {ledBus.map((u) => u.name).join(", ")}
                      </span>
                    ) : hasBuLeadRole ? (
                      <span
                        data-testid={`iam-account-led-bus-unassigned-${acc.id}`}
                        style={{
                          fontSize: "12px",
                          color: "var(--color-arbitration-amber)",
                          fontWeight: 500,
                          marginLeft: "4px",
                        }}
                      >
                        · {dir.ledBusPrefix} {dir.noLedBusAssigned}
                      </span>
                    ) : null}

                    {ontologyLedBus.length > 0 ? (
                      <span
                        data-testid={`iam-account-ontology-led-bus-${acc.id}`}
                        style={{
                          fontSize: "12px",
                          color: "var(--color-foreground)",
                          fontWeight: 600,
                          marginLeft: "4px",
                        }}
                      >
                        · {ontologyLedBus.length > 1 ? dir.ontologyLedBusPluralPrefix : dir.ontologyLedBusPrefix} {ontologyLedBus.map((u) => u.name).join(", ")}
                      </span>
                    ) : hasOntologyLeadRole ? (
                      <span
                        data-testid={`iam-account-ontology-led-bus-unassigned-${acc.id}`}
                        style={{
                          fontSize: "12px",
                          color: "var(--color-arbitration-amber)",
                          fontWeight: 500,
                          marginLeft: "4px",
                        }}
                      >
                        · {dir.ontologyLedBusPrefix} {dir.noOntologyLedBusAssigned}
                      </span>
                    ) : null}

                    {ledTeams.length > 0 ? (
                      <span
                        data-testid={`iam-account-led-teams-${acc.id}`}
                        style={{
                          fontSize: "12px",
                          color: "var(--color-foreground)",
                          fontWeight: 600,
                          marginLeft: "4px",
                        }}
                      >
                        · {ledTeams.length > 1 ? dir.ledTeamsPluralPrefix : dir.ledTeamSingularPrefix} {ledTeams.map((u) => u.name).join(", ")}
                      </span>
                    ) : hasTeamLeadRole ? (
                      <span
                        data-testid={`iam-account-led-teams-unassigned-${acc.id}`}
                        style={{
                          fontSize: "12px",
                          color: "var(--color-arbitration-amber)",
                          fontWeight: 500,
                          marginLeft: "4px",
                        }}
                      >
                        · {dir.ledTeamSingularPrefix} {dir.noLedTeamsAssigned}
                      </span>
                    ) : null}

                    {memberTeams.length > 0 ? (
                      <span
                        data-testid={`iam-account-member-teams-${acc.id}`}
                        style={{
                          fontSize: "12px",
                          color: "var(--color-foreground)",
                          fontWeight: 600,
                          marginLeft: "4px",
                        }}
                      >
                        · {memberTeams.length > 1 ? dir.memberTeamsPluralPrefix : dir.memberTeamSingularPrefix} {memberTeams.map((u) => u.name).join(", ")}
                      </span>
                    ) : null}

                    {showFallbackNoTeams ? (
                      <span
                        data-testid={`iam-account-no-teams-${acc.id}`}
                        style={{
                          fontSize: "12px",
                          color: "var(--color-muted-foreground)",
                          marginLeft: "4px",
                        }}
                      >
                        · {dir.noTeamsAssigned}
                      </span>
                    ) : null}
                  </div>
                </div>

                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  {acc.account_kind === "HUMAN" && authMode !== "SSO" && onResetTemporaryPassword ? (
                    <button
                      type="button"
                      data-testid={`iam-reset-password-account-btn-${acc.id}`}
                      disabled={!canMutate}
                      onClick={() => onResetTemporaryPassword(acc)}
                      className="orcia-ds-btn orcia-ds-btn-secondary"
                      style={{ padding: "5px 10px", fontSize: "12px" }}
                    >
                      {dir.resetPasswordButton}
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
