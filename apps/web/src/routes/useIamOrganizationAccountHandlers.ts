import type { IamAccountResponse } from "@orcia/api-client";
import { useState } from "react";
import type { ConfiguredOrgUnit } from "../components/platformSetupStore";
import type { IamAccountModalSubmitValues } from "../features/admin/iam/IamAccountModal";
import {
  createIamAccountViaApi,
  deleteIamAccountViaApi,
  fetchIamAccountsFromApi,
  resetIamAccountTemporaryPasswordViaApi,
  updateIamAccountViaApi,
} from "../features/admin/iam/iamApiBridge";
import { fetchOrgUnitsFromApi } from "../features/admin/organization/orgUnitsApiBridge";
import { useAuthSessionStore } from "../stores/authSessionStore";

export interface TempPasswordModalPayload {
  readonly displayName: string;
  readonly email: string;
  readonly temporaryPassword: string;
  readonly accountId: string;
}

export function useIamOrganizationAccountHandlers(params: {
  readonly locale: "fr" | "en";
  readonly setAccounts: (accounts: readonly IamAccountResponse[]) => void;
  readonly setAccountsError: (err: string | null) => void;
  readonly syncOrgUnitsFromServer: (units: readonly ConfiguredOrgUnit[]) => void;
}) {
  const { locale, setAccounts, setAccountsError, syncOrgUnitsFromServer } = params;
  const [modalError, setModalError] = useState<string | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [editingAccount, setEditingAccount] = useState<IamAccountResponse | null>(null);
  const [isSubmittingAccount, setIsSubmittingAccount] = useState(false);
  const [tempPasswordModalData, setTempPasswordModalData] =
    useState<TempPasswordModalPayload | null>(null);

  const syncOrgUnitsAfterAccountTeamChange = async () => {
    const orgRes = await fetchOrgUnitsFromApi(locale);
    if (orgRes.ok) syncOrgUnitsFromServer(orgRes.units);
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
          email: values.accountKind === "HUMAN" ? values.emailOrPrincipal : editingAccount.email,
          roles: [...values.roles],
          team_ids: [...values.teamIds],
          led_bu_ids: values.ledBuIds ? [...values.ledBuIds] : [],
          led_team_ids: values.ledTeamIds ? [...values.ledTeamIds] : [],
          ontology_led_bu_ids: values.ontologyLedBuIds ? [...values.ontologyLedBuIds] : [],
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
    } else {
      const res = await createIamAccountViaApi(
        {
          account_kind: values.accountKind,
          display_name: values.displayName,
          email: values.accountKind === "HUMAN" ? values.emailOrPrincipal : null,
          principal_id: values.emailOrPrincipal,
          roles: [...values.roles],
          team_ids: [...values.teamIds],
          led_bu_ids: values.ledBuIds ? [...values.ledBuIds] : [],
          led_team_ids: values.ledTeamIds ? [...values.ledTeamIds] : [],
          ontology_led_bu_ids: values.ontologyLedBuIds ? [...values.ontologyLedBuIds] : [],
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
    }
    const listRes = await fetchIamAccountsFromApi(locale);
    if (listRes.ok) setAccounts(listRes.accounts);
    await syncOrgUnitsAfterAccountTeamChange();
    await useAuthSessionStore.getState().hydrateSession({ force: true });
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

  return {
    modalError,
    setModalError,
    modalOpen,
    setModalOpen,
    editingAccount,
    setEditingAccount,
    isSubmittingAccount,
    tempPasswordModalData,
    setTempPasswordModalData,
    handleAccountModalSubmit,
    handleResetTemporaryPassword,
    handleDeleteAccount,
  };
}
