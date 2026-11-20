import type { IamAccountResponse } from "@orcia/api-client";
import {
  ContextualInfoTriggerButton,
  type ControlCenterWorkspaceGovItem,
} from "@orcia/ui";
import React from "react";
import type { ConfiguredOrgUnit } from "../../../components/platformSetupStorageHelpers";
import type { IamTabDictionarySection } from "../../../i18n/locales/iam_accounts_labels";
import {
  GRANT_RESOURCE_KINDS,
  OFFICIAL_IAM_ROLES,
  type GrantResourceKindKey,
  type OfficialIamRoleKey,
} from "./iamApiBridge";

const selectStyle: React.CSSProperties = {
  padding: "7px 10px",
  borderRadius: "var(--radius-sm)",
  border: "1px solid var(--color-border)",
  backgroundColor: "var(--color-surface-card)",
  color: "var(--color-foreground)",
  width: "100%",
};

export interface IamSecopsScopeAndTargetFieldsProps {
  readonly controlsLocked: boolean;
  readonly beneficiaryKind: "ROLE" | "USER";
  readonly selectedRole: OfficialIamRoleKey;
  readonly effectivePrincipal: string;
  readonly scopePath: string;
  readonly resourceKind: GrantResourceKindKey;
  readonly effect: "ALLOW" | "DENY" | "INHERITANCE_BLOCK";
  readonly accounts: readonly IamAccountResponse[];
  readonly orgUnits: readonly ConfiguredOrgUnit[];
  readonly workspaces: readonly ControlCenterWorkspaceGovItem[];
  readonly labels: IamTabDictionarySection;
  readonly openHelpSection: (sectionId: string) => void;
  readonly onChangeBeneficiaryKind: (kind: "ROLE" | "USER") => void;
  readonly onChangeSelectedRole: (role: OfficialIamRoleKey) => void;
  readonly onChangeAccountPrincipal: (principal: string) => void;
  readonly onChangeScopePath: (scope: string) => void;
  readonly onChangeResourceKind: (kind: GrantResourceKindKey) => void;
  readonly onChangeEffect: (effect: "ALLOW" | "DENY" | "INHERITANCE_BLOCK") => void;
}

export function IamSecopsScopeAndTargetFields({
  controlsLocked,
  beneficiaryKind,
  selectedRole,
  effectivePrincipal,
  scopePath,
  resourceKind,
  effect,
  accounts,
  orgUnits,
  workspaces,
  labels,
  openHelpSection,
  onChangeBeneficiaryKind,
  onChangeSelectedRole,
  onChangeAccountPrincipal,
  onChangeScopePath,
  onChangeResourceKind,
  onChangeEffect,
}: IamSecopsScopeAndTargetFieldsProps): React.ReactElement {
  const sec = labels.secopsDrawer;
  const buUnits = orgUnits.filter((u) => u.level === "BU");
  const teamUnits = orgUnits.filter((u) => u.level === "TEAM");
  const standaloneWorkspaces = workspaces.filter(
    (ws) => !orgUnits.some((u) => u.name === ws.name || u.slug === ws.name),
  );

  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: "10px", alignItems: "flex-end" }}>
      <label style={{ display: "flex", flexDirection: "column", gap: "4px", fontSize: "12px", minWidth: "150px" }}>
        <span style={{ fontWeight: 600 }}>{sec.beneficiaryTypeLabel}</span>
        <select
          data-testid="rbac-subject-type-select"
          disabled={controlsLocked}
          value={beneficiaryKind}
          onChange={(e) => onChangeBeneficiaryKind(e.target.value as "ROLE" | "USER")}
          style={selectStyle}
        >
          <option value="ROLE">{sec.beneficiaryTypeRole}</option>
          <option value="USER">{sec.beneficiaryTypeAccount}</option>
        </select>
      </label>

      <label
        style={{
          display: "flex",
          flexDirection: "column",
          gap: "4px",
          fontSize: "12px",
          flex: "1 1 200px",
          minWidth: "200px",
        }}
      >
        <span data-testid="rbac-subject-dynamic-label" style={{ fontWeight: 600 }}>
          {beneficiaryKind === "ROLE" ? sec.targetRoleLabel : sec.targetAccountLabel}
        </span>
        {beneficiaryKind === "ROLE" ? (
          <select
            data-testid="rbac-subject-select"
            disabled={controlsLocked}
            value={selectedRole}
            onChange={(e) => onChangeSelectedRole(e.target.value as OfficialIamRoleKey)}
            style={selectStyle}
          >
            {OFFICIAL_IAM_ROLES.map((roleKey) => (
              <option key={roleKey} value={roleKey}>
                {labels.roles[roleKey]}
              </option>
            ))}
          </select>
        ) : (
          <select
            data-testid="rbac-subject-select"
            disabled={controlsLocked || accounts.length === 0}
            value={effectivePrincipal}
            onChange={(e) => onChangeAccountPrincipal(e.target.value)}
            style={selectStyle}
          >
            {accounts.map((acc) => (
              <option key={acc.id} value={acc.principal_id}>
                {`${acc.display_name} (${acc.principal_id})`}
              </option>
            ))}
          </select>
        )}
      </label>

      <div
        style={{
          display: "flex",
          flexDirection: "column",
          gap: "4px",
          fontSize: "12px",
          flex: "1.2 1 240px",
          minWidth: "240px",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
          <label htmlFor="rbac-scope-preset-select" style={{ fontWeight: 600 }}>
            {sec.targetScopeLabel}
          </label>
          <ContextualInfoTriggerButton
            sectionId="iam-target-scope"
            label={sec.targetScopeLabel}
            onOpenHelpSection={openHelpSection}
          />
        </div>
        <select
          id="rbac-scope-preset-select"
          data-testid="rbac-scope-preset-select"
          aria-label={sec.targetScopeLabel}
          disabled={controlsLocked}
          value={scopePath}
          onChange={(e) => onChangeScopePath(e.target.value)}
          style={selectStyle}
        >
          {buUnits.length > 0 ? (
            <optgroup label={sec.buOptgroupLabel}>
              {buUnits.map((u) => (
                <option key={u.id} value={u.slug}>
                  {`${sec.buScopePrefix} ${u.name} (${u.slug})`}
                </option>
              ))}
            </optgroup>
          ) : null}
          {teamUnits.length > 0 ? (
            <optgroup label={sec.teamOptgroupLabel}>
              {teamUnits.map((u) => (
                <option key={u.id} value={u.slug}>
                  {`${sec.teamScopePrefix} ${u.name} (${u.slug})`}
                </option>
              ))}
            </optgroup>
          ) : null}
          {standaloneWorkspaces.length > 0 ? (
            <optgroup label={sec.workspaceOptgroupLabel}>
              {standaloneWorkspaces.map((ws) => (
                <option key={ws.name} value={ws.name}>
                  {`${sec.workspaceScopePrefix} ${ws.name}`}
                </option>
              ))}
            </optgroup>
          ) : null}
          <option value="GLOBAL">{sec.globalScopeOption}</option>
        </select>
      </div>

      <label style={{ display: "flex", flexDirection: "column", gap: "4px", fontSize: "12px", minWidth: "180px", flex: "1 1 180px" }}>
        <span style={{ fontWeight: 600 }}>{sec.resourceKindLabel}</span>
        <select
          data-testid="rbac-resource-kind-select"
          disabled={controlsLocked}
          value={resourceKind}
          onChange={(e) => onChangeResourceKind(e.target.value as GrantResourceKindKey)}
          style={selectStyle}
        >
          {GRANT_RESOURCE_KINDS.map((rk) => (
            <option key={rk} value={rk}>
              {sec.resourceKinds[rk]}
            </option>
          ))}
        </select>
      </label>

      <label style={{ display: "flex", flexDirection: "column", gap: "4px", fontSize: "12px", minWidth: "180px", flex: "1 1 180px" }}>
        <span style={{ fontWeight: 600 }}>{sec.effectLabel}</span>
        <select
          data-testid="rbac-effect-select"
          disabled={controlsLocked}
          value={effect}
          onChange={(e) =>
            onChangeEffect(e.target.value as "ALLOW" | "DENY" | "INHERITANCE_BLOCK")
          }
          style={selectStyle}
        >
          <option value="ALLOW">{sec.effectAllow}</option>
          <option value="DENY">{sec.effectDeny}</option>
          <option value="INHERITANCE_BLOCK">{sec.effectIsolate}</option>
        </select>
      </label>
    </div>
  );
}
