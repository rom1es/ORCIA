import type { IamAccountResponse } from "@orcia/api-client";
import {
  ContextualInfoTriggerButton,
  DisabledButtonAlertIndicator,
  OrciaAlertBanner,
  type ControlCenterWorkspaceGovItem,
  type UiPermissionVerb,
} from "@orcia/ui";
import React, { useEffect, useRef, useState } from "react";
import type { ConfiguredOrgUnit } from "../../../components/platformSetupStorageHelpers";
import type { IamTabDictionarySection } from "../../../i18n/locales/iam_accounts_labels";
import {
  GRANT_RESOURCE_KINDS,
  OFFICIAL_IAM_ROLES,
  type GrantResourceKindKey,
  type OfficialIamRoleKey,
} from "./iamApiBridge";

const IMPLIED_READ_VERBS: readonly UiPermissionVerb[] = [
  "create",
  "update",
  "delete",
  "execute",
];

const ALL_SIX_VERBS: readonly UiPermissionVerb[] = [
  "create",
  "read",
  "update",
  "delete",
  "execute",
  "grant",
];

export interface CreateSecopsExceptionInput {
  readonly subjectType: "ROLE" | "USER" | "SERVICE_PRINCIPAL";
  readonly subjectId: string;
  readonly scopePath: string;
  readonly resourceKind: GrantResourceKindKey;
  readonly effect: "ALLOW" | "DENY" | "INHERITANCE_BLOCK";
  readonly verbs: readonly UiPermissionVerb[];
}

export interface IamSecopsExceptionFormProps {
  readonly isSecopsAuthorized: boolean;
  readonly isSubmitting: boolean;
  readonly accounts: readonly IamAccountResponse[];
  readonly orgUnits: readonly ConfiguredOrgUnit[];
  readonly workspaces: readonly ControlCenterWorkspaceGovItem[];
  readonly labels: IamTabDictionarySection;
  readonly openHelpSection: (sectionId: string) => void;
  readonly onCreateException: (input: CreateSecopsExceptionInput) => void;
}

const selectStyle: React.CSSProperties = {
  padding: "7px 10px",
  borderRadius: "var(--radius-sm)",
  border: "1px solid var(--color-border)",
  backgroundColor: "var(--color-surface-card)",
  color: "var(--color-foreground)",
};

export function IamSecopsExceptionForm({
  isSecopsAuthorized,
  isSubmitting,
  accounts,
  orgUnits,
  workspaces,
  labels,
  openHelpSection,
  onCreateException,
}: IamSecopsExceptionFormProps): React.ReactElement {
  const sec = labels.secopsDrawer;
  const [beneficiaryKind, setBeneficiaryKind] = useState<"ROLE" | "USER">("ROLE");
  const [selectedRole, setSelectedRole] = useState<OfficialIamRoleKey>("TEAM_LEAD");
  const [selectedAccountPrincipal, setSelectedAccountPrincipal] = useState<string>("");
  const firstRestrictedScope = orgUnits[0]?.slug ?? workspaces[0]?.name ?? "GLOBAL";
  const [scopePath, setScopePath] = useState<string>(firstRestrictedScope);
  const userPickedScopeRef = useRef(false);
  const [resourceKind, setResourceKind] = useState<GrantResourceKindKey>("ALL");
  const [effect, setEffect] = useState<"ALLOW" | "DENY" | "INHERITANCE_BLOCK">("ALLOW");
  const [selectedVerbs, setSelectedVerbs] = useState<readonly UiPermissionVerb[]>([
    "read",
    "execute",
  ]);

  useEffect(() => {
    if (!userPickedScopeRef.current && scopePath === "GLOBAL" && firstRestrictedScope !== "GLOBAL") {
      setScopePath(firstRestrictedScope);
    }
  }, [firstRestrictedScope, scopePath]);

  useEffect(() => {
    if (!selectedAccountPrincipal && accounts[0]) {
      setSelectedAccountPrincipal(accounts[0].principal_id);
    }
  }, [accounts, selectedAccountPrincipal]);

  const hasImpliedRead = selectedVerbs.some((v) => IMPLIED_READ_VERBS.includes(v));
  const effectiveVerbs: readonly UiPermissionVerb[] =
    hasImpliedRead && !selectedVerbs.includes("read")
      ? ["read", ...selectedVerbs]
      : selectedVerbs;

  const effectivePrincipal =
    beneficiaryKind === "ROLE"
      ? selectedRole
      : selectedAccountPrincipal || accounts[0]?.principal_id || "";

  const controlsLocked = !isSecopsAuthorized || isSubmitting;
  const submitDisabled =
    controlsLocked || !effectivePrincipal.trim() || effectiveVerbs.length === 0;
  const submitDisabledReason = !isSecopsAuthorized
    ? sec.nonSecopsLockedNotice
    : effectiveVerbs.length === 0
      ? sec.verbsFieldsetLabel
      : sec.targetAccountLabel;

  const buUnits = orgUnits.filter((u) => u.level === "BU");
  const teamUnits = orgUnits.filter((u) => u.level === "TEAM");
  const standaloneWorkspaces = workspaces.filter(
    (ws) => !orgUnits.some((u) => u.name === ws.name || u.slug === ws.name),
  );

  return (
    <form
      data-testid="create-rbac-grant-form"
      autoComplete="off"
      data-lpignore="true"
      data-1p-ignore="true"
      data-bwignore="true"
      data-form-type="other"
      aria-disabled={controlsLocked}
      onSubmit={(e) => {
        e.preventDefault();
        if (submitDisabled) return;
        const matchedAcc = accounts.find((a) => a.principal_id === effectivePrincipal);
        const resolvedSubjectType: "ROLE" | "USER" | "SERVICE_PRINCIPAL" =
          beneficiaryKind === "ROLE"
            ? "ROLE"
            : matchedAcc?.account_kind === "SERVICE_PRINCIPAL"
              ? "SERVICE_PRINCIPAL"
              : "USER";
        onCreateException({
          subjectType: resolvedSubjectType,
          subjectId: effectivePrincipal,
          scopePath,
          resourceKind,
          effect,
          verbs: effectiveVerbs,
        });
      }}
      style={{
        display: "flex",
        flexDirection: "column",
        gap: "10px",
        opacity: !isSecopsAuthorized ? 0.6 : 1,
      }}
    >
      <div style={{ display: "flex", flexWrap: "wrap", gap: "10px", alignItems: "flex-end" }}>
        <label style={{ display: "flex", flexDirection: "column", gap: "4px", fontSize: "12px" }}>
          <span style={{ fontWeight: 600 }}>{sec.beneficiaryTypeLabel}</span>
          <select
            data-testid="rbac-subject-type-select"
            disabled={controlsLocked}
            value={beneficiaryKind}
            onChange={(e) => setBeneficiaryKind(e.target.value as "ROLE" | "USER")}
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
            flex: 1,
            minWidth: "210px",
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
              onChange={(e) => setSelectedRole(e.target.value as OfficialIamRoleKey)}
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
              onChange={(e) => setSelectedAccountPrincipal(e.target.value)}
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
            flex: 1,
            minWidth: "220px",
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
            onChange={(e) => {
              userPickedScopeRef.current = true;
              setScopePath(e.target.value);
            }}
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

        <label style={{ display: "flex", flexDirection: "column", gap: "4px", fontSize: "12px" }}>
          <span style={{ fontWeight: 600 }}>{sec.resourceKindLabel}</span>
          <select
            data-testid="rbac-resource-kind-select"
            disabled={controlsLocked}
            value={resourceKind}
            onChange={(e) => setResourceKind(e.target.value as GrantResourceKindKey)}
            style={selectStyle}
          >
            {GRANT_RESOURCE_KINDS.map((rk) => (
              <option key={rk} value={rk}>
                {sec.resourceKinds[rk]}
              </option>
            ))}
          </select>
        </label>

        <label style={{ display: "flex", flexDirection: "column", gap: "4px", fontSize: "12px" }}>
          <span style={{ fontWeight: 600 }}>{sec.effectLabel}</span>
          <select
            data-testid="rbac-effect-select"
            disabled={controlsLocked}
            value={effect}
            onChange={(e) =>
              setEffect(e.target.value as "ALLOW" | "DENY" | "INHERITANCE_BLOCK")
            }
            style={selectStyle}
          >
            <option value="ALLOW">{sec.effectAllow}</option>
            <option value="DENY">{sec.effectDeny}</option>
            <option value="INHERITANCE_BLOCK">{sec.effectIsolate}</option>
          </select>
        </label>
      </div>

      {scopePath === "GLOBAL" ? (
        <OrciaAlertBanner tone="amber" testId="iam-global-scope-amber-warning">
          {sec.globalScopeAmberWarning}
        </OrciaAlertBanner>
      ) : null}

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
                    setSelectedVerbs((prev) =>
                      e.target.checked
                        ? prev.includes(v)
                          ? prev
                          : [...prev, v]
                        : prev.filter((item) => item !== v),
                    );
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

      <div
        data-testid="rbac-submit-footer"
        style={{ display: "flex", justifyContent: "flex-end" }}
      >
        <button
          type="submit"
          data-testid="create-rbac-grant-btn"
          disabled={submitDisabled}
          title={submitDisabled ? submitDisabledReason : undefined}
          className="orcia-ds-btn orcia-ds-btn-primary"
        >
          <span>{sec.submitExceptionCta}</span>
          <DisabledButtonAlertIndicator
            disabled={submitDisabled}
            reason={submitDisabledReason}
            testIdSuffix="create-rbac-grant-btn"
          />
        </button>
      </div>
    </form>
  );
}
