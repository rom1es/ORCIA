import type { IamAccountResponse, RoleMatrixEntryResponse } from "@orcia/api-client";
import type { ControlCenterWorkspaceGovItem } from "@orcia/ui";
import React, { useCallback, useEffect, useState } from "react";
import type {
  ConfiguredOrgUnit,
  ConfiguredRbacGrant,
} from "../components/platformSetupStore";
import {
  IamAccountModal,
  type IamAccountModalSubmitValues,
} from "../features/admin/iam/IamAccountModal";
import { IamAccountsDirectoryCard } from "../features/admin/iam/IamAccountsDirectoryCard";
import { IamNativeRoleMatrixCard } from "../features/admin/iam/IamNativeRoleMatrixCard";
import {
  IamSecopsExceptionsDrawer,
  type CreateSecopsExceptionInput,
} from "../features/admin/iam/IamSecopsExceptionsDrawer";
import {
  createIamAccountViaApi,
  createIamGrantsViaApi,
  deleteIamAccountViaApi,
  deleteIamGrantViaApi,
  fetchIamAccountsFromApi,
  fetchIamGrantsFromApi,
  fetchIamRoleMatrixFromApi,
  updateIamAccountViaApi,
} from "../features/admin/iam/iamApiBridge";
import { fetchOrgUnitsFromApi } from "../features/admin/organization/orgUnitsApiBridge";
import type { IamTabDictionarySection } from "../i18n/locales/iam_accounts_labels";
import { useAuthSessionStore } from "../stores/authSessionStore";

export interface SettingsIamOrganizationSectionProps {
  readonly isFr: boolean;
  readonly canMutate?: boolean;
  readonly iamLabels: IamTabDictionarySection;
  readonly orgUnits: readonly ConfiguredOrgUnit[];
  readonly workspaces: readonly ControlCenterWorkspaceGovItem[];
  readonly rbacGrants: readonly ConfiguredRbacGrant[];
  readonly openHelpSection: (sectionId: string) => void;
  readonly syncOrgUnitsFromServer: (
    units: readonly ConfiguredOrgUnit[],
    auditMeta?: {
      readonly eventType: string;
      readonly summary: string;
      readonly scopePath?: string;
      readonly scopeLabel?: string;
    },
  ) => void;
  readonly syncRbacGrantsFromServer: (
    grants: readonly ConfiguredRbacGrant[],
    auditMeta?: {
      readonly eventType: string;
      readonly summary: string;
      readonly scopePath?: string;
      readonly scopeLabel?: string;
    },
  ) => void;
}

export function SettingsIamOrganizationSection({
  isFr,
  canMutate = true,
  iamLabels,
  orgUnits,
  workspaces,
  rbacGrants,
  openHelpSection,
  syncOrgUnitsFromServer,
  syncRbacGrantsFromServer,
}: SettingsIamOrganizationSectionProps): React.ReactElement {
  const locale: "fr" | "en" = isFr ? "fr" : "en";
  const roles = useAuthSessionStore((s) => s.roles);
  const activeHat = useAuthSessionStore((s) => s.activeHat);
  const readOnlyObserver = useAuthSessionStore((s) => s.readOnlyObserver);

  const hasSecopsRole = roles.includes("SECOPS") || activeHat === "SECOPS";
  const isSecopsAuthorized = canMutate && !readOnlyObserver && hasSecopsRole;

  const [accounts, setAccounts] = useState<readonly IamAccountResponse[]>([]);
  const [roleMatrix, setRoleMatrix] = useState<readonly RoleMatrixEntryResponse[]>([]);
  const [accountsError, setAccountsError] = useState<string | null>(null);
  const [modalError, setModalError] = useState<string | null>(null);
  const [grantsError, setGrantsError] = useState<string | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [editingAccount, setEditingAccount] = useState<IamAccountResponse | null>(null);
  const [isSubmittingAccount, setIsSubmittingAccount] = useState(false);
  const [isSubmittingGrant, setIsSubmittingGrant] = useState(false);

  const refreshAccountsAndGrants = useCallback(async () => {
    const [accRes, matRes, grantsRes] = await Promise.all([
      fetchIamAccountsFromApi(locale),
      fetchIamRoleMatrixFromApi(locale),
      fetchIamGrantsFromApi(locale),
    ]);
    if (accRes.ok) {
      setAccounts(accRes.accounts);
    } else {
      setAccountsError(accRes.errorMessage);
    }
    if (matRes.ok) {
      setRoleMatrix(matRes.roles);
    }
    if (grantsRes.ok) {
      syncRbacGrantsFromServer(grantsRes.grants);
    }
  }, [locale, syncRbacGrantsFromServer]);

  useEffect(() => {
    void refreshAccountsAndGrants();
  }, [refreshAccountsAndGrants]);

  const syncOrgUnitsAfterAccountTeamChange = async () => {
    const orgRes = await fetchOrgUnitsFromApi(locale);
    if (orgRes.ok) {
      syncOrgUnitsFromServer(orgRes.units);
    }
  };

  const handleAccountModalSubmit = async (values: IamAccountModalSubmitValues) => {
    setIsSubmittingAccount(true);
    setModalError(null);
    setAccountsError(null);
    if (editingAccount) {
      const res = await updateIamAccountViaApi(
        editingAccount.id,
        {
          display_name: values.displayName,
          email:
            values.accountKind === "HUMAN" ? values.emailOrPrincipal : editingAccount.email,
          roles: [...values.roles],
          team_ids: [...values.teamIds],
          status: values.status,
        },
        locale,
      );
      setIsSubmittingAccount(false);
      if (!res.ok) {
        setModalError(res.errorMessage);
        return;
      }
      setModalOpen(false);
      setEditingAccount(null);
      const listRes = await fetchIamAccountsFromApi(locale);
      if (listRes.ok) setAccounts(listRes.accounts);
      await syncOrgUnitsAfterAccountTeamChange();
    } else {
      const res = await createIamAccountViaApi(
        {
          account_kind: values.accountKind,
          display_name: values.displayName,
          email: values.accountKind === "HUMAN" ? values.emailOrPrincipal : null,
          principal_id: values.emailOrPrincipal,
          roles: [...values.roles],
          team_ids: [...values.teamIds],
          status: values.status,
        },
        locale,
      );
      setIsSubmittingAccount(false);
      if (!res.ok) {
        setModalError(res.errorMessage);
        return;
      }
      setModalOpen(false);
      const listRes = await fetchIamAccountsFromApi(locale);
      if (listRes.ok) setAccounts(listRes.accounts);
      await syncOrgUnitsAfterAccountTeamChange();
    }
  };

  const handleDeleteAccount = async (account: IamAccountResponse) => {
    setAccountsError(null);
    const res = await deleteIamAccountViaApi(account.id, locale);
    if (!res.ok) {
      setAccountsError(res.errorMessage);
      return;
    }
    const listRes = await fetchIamAccountsFromApi(locale);
    if (listRes.ok) setAccounts(listRes.accounts);
    await syncOrgUnitsAfterAccountTeamChange();
  };

  const handleCreateException = async (input: CreateSecopsExceptionInput) => {
    setIsSubmittingGrant(true);
    setGrantsError(null);
    const res = await createIamGrantsViaApi(
      {
        subject_type: input.subjectType,
        subject_id: input.subjectId,
        scope_path: input.scopePath,
        verbs: [...input.verbs],
        effect: input.effect,
        inheritance_block: input.effect === "INHERITANCE_BLOCK",
        resource_kind: input.resourceKind,
      },
      locale,
    );
    setIsSubmittingGrant(false);
    if (!res.ok) {
      setGrantsError(res.errorMessage);
      return;
    }
    const fresh = await fetchIamGrantsFromApi(locale);
    const nextGrants = fresh.ok
      ? fresh.grants
      : [...rbacGrants, ...res.grants];
    syncRbacGrantsFromServer(nextGrants, {
      eventType: "PermissionGranted",
      summary: `${input.subjectId} → ${input.verbs.join(", ")} (${input.scopePath})`,
      scopePath: input.scopePath,
    });
  };

  const handleDeleteSingleGrant = async (grantId: string) => {
    setGrantsError(null);
    const res = await deleteIamGrantViaApi(grantId, locale);
    if (!res.ok) {
      setGrantsError(res.errorMessage);
      return;
    }
    const nextGrants = rbacGrants.filter((g) => g.id !== grantId);
    syncRbacGrantsFromServer(nextGrants, {
      eventType: "PermissionRevoked",
      summary: `Exception ${grantId} supprimée`,
    });
  };

  const handleBulkDeleteGrants = async (grantIds: readonly string[]) => {
    setGrantsError(null);
    for (const gid of grantIds) {
      const res = await deleteIamGrantViaApi(gid, locale);
      if (!res.ok) {
        setGrantsError(res.errorMessage);
        return;
      }
    }
    const removedSet = new Set(grantIds);
    const nextGrants = rbacGrants.filter((g) => !removedSet.has(g.id));
    syncRbacGrantsFromServer(nextGrants, {
      eventType: "PermissionRevoked",
      summary: `${grantIds.length} exceptions supprimées`,
    });
  };

  return (
    <div
      data-testid="settings-iam-section"
      style={{ display: "flex", flexDirection: "column", gap: "16px" }}
    >
      <IamAccountsDirectoryCard
        canMutate={canMutate && !readOnlyObserver}
        accounts={accounts}
        orgUnits={orgUnits}
        labels={iamLabels}
        errorMessage={accountsError}
        onOpenCreateModal={() => {
          setEditingAccount(null);
          setModalError(null);
          setModalOpen(true);
        }}
        onOpenEditModal={(acc) => {
          setEditingAccount(acc);
          setModalError(null);
          setModalOpen(true);
        }}
        onDeleteAccount={(acc) => {
          void handleDeleteAccount(acc);
        }}
      />

      <IamNativeRoleMatrixCard
        roleMatrix={roleMatrix}
        labels={iamLabels}
        openHelpSection={openHelpSection}
      />

      <IamSecopsExceptionsDrawer
        isFr={isFr}
        isSecopsAuthorized={isSecopsAuthorized}
        accounts={accounts}
        orgUnits={orgUnits}
        workspaces={workspaces}
        rbacGrants={rbacGrants}
        labels={iamLabels}
        errorMessage={grantsError}
        isSubmitting={isSubmittingGrant}
        openHelpSection={openHelpSection}
        onCreateException={(input) => {
          void handleCreateException(input);
        }}
        onDeleteGrant={(grantId) => {
          void handleDeleteSingleGrant(grantId);
        }}
        onBulkDeleteGrants={(grantIds) => {
          void handleBulkDeleteGrants(grantIds);
        }}
      />

      <IamAccountModal
        open={modalOpen}
        onOpenChange={setModalOpen}
        canMutate={canMutate && !readOnlyObserver}
        editingAccount={editingAccount}
        orgUnits={orgUnits}
        labels={iamLabels}
        errorMessage={modalError}
        isSubmitting={isSubmittingAccount}
        onSubmit={(values) => {
          void handleAccountModalSubmit(values);
        }}
      />
    </div>
  );
}
