import type { IamAccountResponse } from "@orcia/api-client";
import {
  DisabledButtonAlertIndicator,
  OrciaAlertBanner,
  type ControlCenterWorkspaceGovItem,
  type UiPermissionVerb,
} from "@orcia/ui";
import React, { useEffect, useRef, useState } from "react";
import type { ConfiguredOrgUnit } from "../../../components/platformSetupStorageHelpers";
import type { IamTabDictionarySection } from "../../../i18n/locales/iam_accounts_labels";
import {
  type GrantResourceKindKey,
  type OfficialIamRoleKey,
} from "./iamApiBridge";
import { IamSecopsScopeAndTargetFields } from "./IamSecopsScopeAndTargetFields";
import { IamSecopsVerbsCheckboxes } from "./IamSecopsVerbsCheckboxes";

const IMPLIED_READ_VERBS: readonly UiPermissionVerb[] = [
  "create",
  "update",
  "delete",
  "execute",
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
      <IamSecopsScopeAndTargetFields
        controlsLocked={controlsLocked}
        beneficiaryKind={beneficiaryKind}
        selectedRole={selectedRole}
        effectivePrincipal={effectivePrincipal}
        scopePath={scopePath}
        resourceKind={resourceKind}
        effect={effect}
        accounts={accounts}
        orgUnits={orgUnits}
        workspaces={workspaces}
        labels={labels}
        openHelpSection={openHelpSection}
        onChangeBeneficiaryKind={setBeneficiaryKind}
        onChangeSelectedRole={setSelectedRole}
        onChangeAccountPrincipal={setSelectedAccountPrincipal}
        onChangeScopePath={(nextScope) => {
          userPickedScopeRef.current = true;
          setScopePath(nextScope);
        }}
        onChangeResourceKind={setResourceKind}
        onChangeEffect={setEffect}
      />

      {scopePath === "GLOBAL" ? (
        <OrciaAlertBanner tone="amber" testId="iam-global-scope-amber-warning">
          {sec.globalScopeAmberWarning}
        </OrciaAlertBanner>
      ) : null}

      <IamSecopsVerbsCheckboxes
        controlsLocked={controlsLocked}
        hasImpliedRead={hasImpliedRead}
        effectiveVerbs={effectiveVerbs}
        labels={labels}
        onToggleVerb={(v, checked) => {
          setSelectedVerbs((prev) =>
            checked
              ? prev.includes(v)
                ? prev
                : [...prev, v]
              : prev.filter((item) => item !== v),
          );
        }}
      />

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
