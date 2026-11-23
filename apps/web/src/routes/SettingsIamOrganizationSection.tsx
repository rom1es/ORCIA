import { createOrciaApiClient, type IamAccountResponse, type RoleMatrixEntryResponse } from "@orcia/api-client";
import { TemporaryPasswordInvitationModal, type ControlCenterWorkspaceGovItem } from "@orcia/ui";
import React, { useCallback, useEffect, useState } from "react";
import type { ConfiguredOrgUnit, ConfiguredRbacGrant } from "../components/platformSetupStore";
import { IamAccountModal } from "../features/admin/iam/IamAccountModal";
import { IamAccountsDirectoryCard } from "../features/admin/iam/IamAccountsDirectoryCard";
import { IamRoleMatrixReferenceModal } from "../features/admin/iam/IamRoleMatrixReferenceModal";
import { IamSecopsExceptionsDrawer } from "../features/admin/iam/IamSecopsExceptionsDrawer";
import {
  fetchIamAccountsFromApi,
  fetchIamGrantsFromApi,
  fetchIamRoleMatrixFromApi,
  resetIamAccountTemporaryPasswordViaApi,
} from "../features/admin/iam/iamApiBridge";
import { resolveLocaleForFlag } from "../i18n";
import type { IamTabDictionarySection } from "../i18n/locales/iam_accounts_labels";
import { useAuthSessionStore } from "../stores/authSessionStore";
import { useIamOrganizationAccountHandlers } from "./useIamOrganizationAccountHandlers";
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
  const locale = resolveLocaleForFlag(isFr);
  const roles = useAuthSessionStore((s) => s.roles);
  const userEmail = useAuthSessionStore((s) => s.email);
  const readOnlyObserver = useAuthSessionStore((s) => s.readOnlyObserver);
  const isAuthenticated = useAuthSessionStore((s) => s.isAuthenticated);
  const isHydrating = useAuthSessionStore((s) => s.isHydrating);
  const accessToken = useAuthSessionStore((s) => s.accessToken);

  const [accounts, setAccounts] = useState<readonly IamAccountResponse[]>([]);
  const [roleMatrix, setRoleMatrix] = useState<readonly RoleMatrixEntryResponse[]>([]);
  const [authMode, setAuthMode] = useState<"LOCAL" | "SSO">("LOCAL");
  const [accountsError, setAccountsError] = useState<string | null>(null);
  const [isRoleMatrixModalOpen, setIsRoleMatrixModalOpen] = useState(false);

  const currentAccount = accounts.find(
    (acc) =>
      acc.status === "ACTIVE" &&
      userEmail &&
      (acc.email?.toLowerCase() === userEmail.toLowerCase() ||
        acc.principal_id?.toLowerCase() === userEmail.toLowerCase()),
  );
  const hasSecopsRole =
    roles.includes("SECOPS") || Boolean(currentAccount?.roles.includes("SECOPS"));
  const isSecopsAuthorized = canMutate && !readOnlyObserver && hasSecopsRole;

  const accountHandlers = useIamOrganizationAccountHandlers({
    locale,
    setAccounts,
    setAccountsError,
    syncOrgUnitsFromServer,
  });

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
    const client = createOrciaApiClient({ baseUrl: "", locale });
    const [accRes, matRes, grantsRes, authCfgRes] = await Promise.allSettled([
      fetchIamAccountsFromApi(locale),
      fetchIamRoleMatrixFromApi(locale),
      fetchIamGrantsFromApi(locale),
      client.getPublicAuthConfig(),
    ]);

    if (accRes.status === "fulfilled") {
      if (accRes.value.ok) setAccounts(accRes.value.accounts);
      else setAccountsError(accRes.value.errorMessage);
    }
    if (matRes.status === "fulfilled" && matRes.value.ok) {
      setRoleMatrix(matRes.value.roles);
    }
    if (grantsRes.status === "fulfilled" && grantsRes.value.ok) {
      syncRbacGrantsFromServer(grantsRes.value.grants);
    }
    if (authCfgRes.status === "fulfilled" && authCfgRes.value?.auth_mode) {
      setAuthMode(authCfgRes.value.auth_mode);
    }
  }, [locale, syncRbacGrantsFromServer]);

  useEffect(() => {
    if (isHydrating || !isAuthenticated) return;
    setAccountsError(null);
    void refreshAccountsAndGrants();
  }, [refreshAccountsAndGrants, isHydrating, isAuthenticated, accessToken]);

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
        authMode={authMode}
        onOpenRoleMatrix={() => setIsRoleMatrixModalOpen(true)}
        onOpenCreateModal={() => {
          accountHandlers.setEditingAccount(null);
          accountHandlers.setModalError(null);
          accountHandlers.setModalOpen(true);
        }}
        onOpenEditModal={(acc) => {
          accountHandlers.setEditingAccount(acc);
          accountHandlers.setModalError(null);
          accountHandlers.setModalOpen(true);
        }}
        onDeleteAccount={(acc) => {
          void accountHandlers.handleDeleteAccount(acc);
        }}
        onResetTemporaryPassword={(acc) => {
          void accountHandlers.handleResetTemporaryPassword(acc);
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
        open={accountHandlers.modalOpen}
        onOpenChange={accountHandlers.setModalOpen}
        canMutate={canMutate && !readOnlyObserver}
        editingAccount={accountHandlers.editingAccount}
        orgUnits={orgUnits}
        labels={iamLabels}
        errorMessage={accountHandlers.modalError}
        isSubmitting={accountHandlers.isSubmittingAccount}
        onOpenRoleMatrix={() => setIsRoleMatrixModalOpen(true)}
        onSubmit={(values) => {
          void accountHandlers.handleAccountModalSubmit(values);
        }}
      />

      {accountHandlers.tempPasswordModalData && (
        <TemporaryPasswordInvitationModal
          isOpen={true}
          isFr={isFr}
          displayName={accountHandlers.tempPasswordModalData.displayName}
          email={accountHandlers.tempPasswordModalData.email}
          temporaryPassword={accountHandlers.tempPasswordModalData.temporaryPassword}
          orciaUrl={
            typeof window !== "undefined"
              ? window.location.origin
              : "http://localhost:3100"
          }
          onClose={() => accountHandlers.setTempPasswordModalData(null)}
          onRegeneratePassword={async () => {
            const payload = accountHandlers.tempPasswordModalData;
            if (!payload) return;
            const resetRes = await resetIamAccountTemporaryPasswordViaApi(payload.accountId, locale);
            if (resetRes.ok) {
              accountHandlers.setTempPasswordModalData((prev) =>
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
