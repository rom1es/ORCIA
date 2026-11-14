import type { IamAccountResponse } from "@orcia/api-client";
import {
  OrciaAlertBanner,
  OrciaIcon,
  StatusBadge,
  type ControlCenterWorkspaceGovItem,
} from "@orcia/ui";
import React, { useState } from "react";
import type {
  ConfiguredOrgUnit,
  ConfiguredRbacGrant,
} from "../../../components/platformSetupStorageHelpers";
import type { IamTabDictionarySection } from "../../../i18n/locales/iam_accounts_labels";
import { SettingsIamGrantsList } from "../../../routes/SettingsIamGrantsList";
import {
  IamSecopsExceptionForm,
  type CreateSecopsExceptionInput,
} from "./IamSecopsExceptionForm";

export type { CreateSecopsExceptionInput };

export interface IamSecopsExceptionsDrawerProps {
  readonly isFr: boolean;
  readonly isSecopsAuthorized: boolean;
  readonly accounts: readonly IamAccountResponse[];
  readonly orgUnits: readonly ConfiguredOrgUnit[];
  readonly workspaces: readonly ControlCenterWorkspaceGovItem[];
  readonly rbacGrants: readonly ConfiguredRbacGrant[];
  readonly labels: IamTabDictionarySection;
  readonly errorMessage: string | null;
  readonly isSubmitting: boolean;
  readonly openHelpSection: (sectionId: string) => void;
  readonly onCreateException: (input: CreateSecopsExceptionInput) => void;
  readonly onDeleteGrant: (grantId: string) => void;
  readonly onBulkDeleteGrants: (grantIds: readonly string[]) => void;
}

export function IamSecopsExceptionsDrawer({
  isFr,
  isSecopsAuthorized,
  accounts,
  orgUnits,
  workspaces,
  rbacGrants,
  labels,
  errorMessage,
  isSubmitting,
  openHelpSection,
  onCreateException,
  onDeleteGrant,
  onBulkDeleteGrants,
}: IamSecopsExceptionsDrawerProps): React.ReactElement {
  const sec = labels.secopsDrawer;
  const [isOpen, setIsOpen] = useState(false);
  const [selectedGrantIds, setSelectedGrantIds] = useState<readonly string[]>([]);

  const formatTargetScopeLabel = (rawScope: string): string => {
    if (rawScope === "GLOBAL") return labels.roleScopes.GLOBAL;
    const matchedUnit = orgUnits.find((u) => u.slug === rawScope || u.id === rawScope);
    if (matchedUnit) {
      const prefix =
        matchedUnit.level === "TEAM" ? sec.teamScopePrefix : sec.buScopePrefix;
      return `${prefix} ${matchedUnit.name} (${matchedUnit.slug})`;
    }
    const matchedWs = workspaces.find((w) => w.name === rawScope);
    if (matchedWs) return `${sec.workspaceScopePrefix} ${matchedWs.name}`;
    return rawScope;
  };

  return (
    <section
      data-testid="iam-secops-exceptions-drawer"
      className="orcia-bento-card"
      style={{ display: "flex", flexDirection: "column", gap: "12px" }}
    >
      <button
        type="button"
        data-testid="iam-secops-drawer-toggle"
        aria-expanded={isOpen}
        onClick={() => setIsOpen((prev) => !prev)}
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: "12px",
          width: "100%",
          padding: "4px 0",
          border: "none",
          background: "transparent",
          color: "var(--color-foreground)",
          cursor: "pointer",
          textAlign: "left",
        }}
      >
        <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
          <div style={{ display: "flex", alignItems: "center", flexWrap: "wrap", gap: "8px" }}>
            <OrciaIcon name={isOpen ? "chevronDown" : "chevronRight"} size={15} />
            <span style={{ fontSize: "15px", fontWeight: 700 }}>{sec.toggleTitle}</span>
            <StatusBadge label={sec.secopsBadge} tone="amber" />
            {rbacGrants.length > 0 ? (
              <StatusBadge label={String(rbacGrants.length)} tone="cobalt" />
            ) : null}
          </div>
          <span style={{ fontSize: "12.5px", color: "var(--color-muted-foreground)" }}>
            {sec.toggleSubtitle}
          </span>
        </div>
        <span style={{ fontSize: "12px", fontWeight: 600, color: "var(--color-primary-cobalt)" }}>
          {isOpen ? sec.collapseLabel : sec.expandLabel}
        </span>
      </button>

      {isOpen ? (
        <div
          data-testid="iam-secops-drawer-body"
          style={{
            display: "flex",
            flexDirection: "column",
            gap: "12px",
            paddingTop: "8px",
            borderTop: "1px solid var(--color-border)",
          }}
        >
          {!isSecopsAuthorized ? (
            <OrciaAlertBanner tone="cobalt" testId="iam-secops-locked-notice">
              {sec.nonSecopsLockedNotice}
            </OrciaAlertBanner>
          ) : null}

          {errorMessage ? (
            <OrciaAlertBanner tone="crimson" testId="iam-grants-error-banner">
              {errorMessage}
            </OrciaAlertBanner>
          ) : null}

          <IamSecopsExceptionForm
            isSecopsAuthorized={isSecopsAuthorized}
            isSubmitting={isSubmitting}
            accounts={accounts}
            orgUnits={orgUnits}
            workspaces={workspaces}
            labels={labels}
            openHelpSection={openHelpSection}
            onCreateException={onCreateException}
          />

          <SettingsIamGrantsList
            isFr={isFr}
            canMutate={isSecopsAuthorized && !isSubmitting}
            rbacGrants={rbacGrants}
            selectedGrantIds={selectedGrantIds}
            verbDescriptions={labels.verbs}
            effectBadgeLabels={{
              ALLOW: sec.badgeAllow,
              DENY: sec.badgeDeny,
              INHERITANCE_BLOCK: sec.badgeIsolated,
            }}
            resourceKindLabels={sec.resourceKinds}
            roleDisplayLabels={labels.roles}
            subjectPrefixes={{
              ROLE: sec.rolePrefix,
              USER: sec.userPrefix,
              SERVICE_PRINCIPAL: sec.spPrefix,
            }}
            emptyStateText={sec.emptyGrantsText}
            selectAllLabel={sec.selectAllGrantsLabel}
            deleteSelectedCta={sec.deleteSelectedCta}
            deleteSingleLabel={sec.deleteSingleLabel}
            formatTargetScopeLabel={formatTargetScopeLabel}
            onToggleSelectAll={(checked) =>
              setSelectedGrantIds(checked ? rbacGrants.map((g) => g.id) : [])
            }
            onToggleSelectGrant={(grantId, checked) =>
              setSelectedGrantIds((prev) =>
                checked
                  ? prev.includes(grantId)
                    ? prev
                    : [...prev, grantId]
                  : prev.filter((id) => id !== grantId),
              )
            }
            onBulkDeleteSelected={() => {
              onBulkDeleteGrants(selectedGrantIds);
              setSelectedGrantIds([]);
            }}
            onDeleteGrant={(grantId) => {
              onDeleteGrant(grantId);
              setSelectedGrantIds((prev) => prev.filter((id) => id !== grantId));
            }}
          />
        </div>
      ) : null}
    </section>
  );
}
