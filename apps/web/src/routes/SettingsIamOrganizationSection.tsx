import type { IamAccountResponse, RoleMatrixEntryResponse } from "@orcia/api-client";
import {
  TemporaryPasswordInvitationModal,
  type ControlCenterWorkspaceGovItem,
} from "@orcia/ui";
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
import { IamRoleMatrixReferenceModal } from "../features/admin/iam/IamRoleMatrixReferenceModal";
import {
  IamSecopsExceptionsDrawer,
  type CreateSecopsExceptionInput,
} from "../features/admin/iam/IamSecopsExceptionsDrawer";
import {
  createIamAccountViaApi,
  deleteIamAccountViaApi,
  fetchIamAccountsFromApi,
  fetchIamGrantsFromApi,
  fetchIamRoleMatrixFromApi,
  resetIamAccountTemporaryPasswordViaApi,
  updateIamAccountViaApi,
} from "../features/admin/iam/iamApiBridge";
import { fetchOrgUnitsFromApi } from "../features/admin/organization/orgUnitsApiBridge";
import type { IamTabDictionarySection } from "../i18n/locales/iam_accounts_labels";
import { useAuthSessionStore } from "../stores/authSessionStore";
import { useSecopsGrantsHandlers } from "./useSecopsGrantsHandlers";

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
  const userEmail = useAuthSessionStore((s) => s.email);
  const readOnlyObserver = useAuthSessionStore((s) => s.readOnlyObserver);
  const isHydrating = useAuthSessionStore((s) => s.isHydrating);
  const accessToken = useAuthSessionStore((s) => s.accessToken);

  const [accounts, setAccounts] = useState<readonly IamAccountResponse[]>([]);
  const [roleMatrix, setRoleMatrix] = useState<readonly RoleMatrixEntryResponse[]>([]);
  const [accountsError, setAccountsError] = useState<string | null>(null);
  const [modalError, setModalError] = useState<string | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [isRoleMatrixModalOpen, setIsRoleMatrixModalOpen] = useState(false);
  const [editingAccount, setEditingAccount] = useState<IamAccountResponse | null>(null);
  const [isSubmittingAccount, setIsSubmittingAccount] = useState(false);

  const currentAccount = accounts.find(
    (acc) =>
      acc.status === "ACTIVE" &&
      userEmail &&
      (acc.email?.toLowerCase() === userEmail.toLowerCase() ||
        acc.principal_id?.toLowerCase() === userEmail.toLowerCase()),
  );
  const currentAccountRoles = currentAccount?.roles ?? [];
  const hasSecopsRole =
    roles.includes("SECOPS") ||
    activeHat === "SECOPS" ||
    currentAccountRoles.includes("SECOPS");
  const isSecopsAuthorized = canMutate && !readOnlyObserver && hasSecopsRole;
  const [tempPasswordModalData, setTempPasswordModalData] = useState<{
    displayName: string;
    email: string;
    temporaryPassword: string;
    accountId: string;
  } | null>(null);

  const {
    grantsError,
    isSubmittingGrant,
    handleCreateException,
    handleDeleteSingleGrant,
    handleBulkDeleteGrants,
  } = useSecopsGrantsHandlers({
    locale,
    rbacGrants,
    syncRbacGrantsFromServer,
  });

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
    if (isHydrating) {
      return;
    }
    setAccountsError(null);
    void refreshAccountsAndGrants();
  }, [refreshAccountsAndGrants, isHydrating, accessToken]);

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
      await useAuthSessionStore.getState().hydrateSession({ force: true });
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
      if (res.temporaryPassword) {
        setTempPasswordModalData({
          displayName: values.displayName,
          email: values.emailOrPrincipal,
          temporaryPassword: res.temporaryPassword,
          accountId: res.account.id,
        });
      }
      const listRes = await fetchIamAccountsFromApi(locale);
      if (listRes.ok) setAccounts(listRes.accounts);
      await syncOrgUnitsAfterAccountTeamChange();
      await useAuthSessionStore.getState().hydrateSession({ force: true });
    }
  };

  const handleResetTemporaryPassword = async (account: IamAccountResponse) => {
    setAccountsError(null);
    const res = await resetIamAccountTemporaryPasswordViaApi(account.id, locale);
    if (!res.ok) {
      setAccountsError(res.errorMessage);
      return;
    }
    setTempPasswordModalData({
      displayName: account.display_name,
      email: account.email ?? account.principal_id,
      temporaryPassword: res.temporaryPassword,
      accountId: account.id,
    });
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
    await useAuthSessionStore.getState().hydrateSession({ force: true });
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
        onOpenRoleMatrix={() => setIsRoleMatrixModalOpen(true)}
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
        onResetTemporaryPassword={(acc) => {
          void handleResetTemporaryPassword(acc);
        }}
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

      <IamRoleMatrixReferenceModal
        isOpen={isRoleMatrixModalOpen}
        onClose={() => setIsRoleMatrixModalOpen(false)}
        roleMatrix={roleMatrix}
        labels={iamLabels}
        openHelpSection={openHelpSection}
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
        onOpenRoleMatrix={() => setIsRoleMatrixModalOpen(true)}
        onSubmit={(values) => {
          void handleAccountModalSubmit(values);
        }}
      />

      {tempPasswordModalData && (
        <TemporaryPasswordInvitationModal
          isOpen={true}
          isFr={isFr}
          displayName={tempPasswordModalData.displayName}
          email={tempPasswordModalData.email}
          temporaryPassword={tempPasswordModalData.temporaryPassword}
          orciaUrl={
            typeof window !== "undefined"
              ? window.location.origin
              : "http://localhost:3100"
          }
          onClose={() => setTempPasswordModalData(null)}
          onRegeneratePassword={async () => {
            const resetRes = await resetIamAccountTemporaryPasswordViaApi(
              tempPasswordModalData.accountId,
              locale,
            );
            if (resetRes.ok) {
              setTempPasswordModalData((prev) =>
                prev ? { ...prev, temporaryPassword: resetRes.temporaryPassword } : null,
              );
              return resetRes.temporaryPassword;
            }
          }}
        />
      )}
    </div>
  );
}
