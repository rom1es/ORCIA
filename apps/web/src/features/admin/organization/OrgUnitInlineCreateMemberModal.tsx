import { TemporaryPasswordInvitationModal, type KnownUserOption } from "@orcia/ui";
import React, { useMemo, useState } from "react";
import type { ConfiguredOrgUnit } from "../../../components/platformSetupStorageHelpers";
import { useI18n } from "../../../i18n";
import {
  IamAccountModal,
  type IamAccountModalSubmitValues,
} from "../iam/IamAccountModal";
import { IamRoleMatrixReferenceModal } from "../iam/IamRoleMatrixReferenceModal";
import {
  createIamAccountViaApi,
  resetIamAccountTemporaryPasswordViaApi,
} from "../iam/iamApiBridge";

export interface OrgUnitInlineCreateMemberModalProps {
  readonly unit: ConfiguredOrgUnit;
  readonly open: boolean;
  readonly onOpenChange: (open: boolean) => void;
  readonly canMutate: boolean;
  readonly draftInput: string;
  readonly orgUnits?: readonly ConfiguredOrgUnit[];
  readonly onMemberCreated: (user: KnownUserOption) => void;
}

export function OrgUnitInlineCreateMemberModal({
  unit,
  open,
  onOpenChange,
  canMutate,
  draftInput,
  orgUnits = [],
  onMemberCreated,
}: OrgUnitInlineCreateMemberModalProps): React.ReactElement {
  const { dictionary, isFr, locale } = useI18n();
  const iamLabels = dictionary.settingsHub.iamTab;

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isRoleMatrixOpen, setIsRoleMatrixOpen] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [tempPasswordModalData, setTempPasswordModalData] = useState<{
    displayName: string;
    email: string;
    temporaryPassword: string;
    accountId: string;
  } | null>(null);

  const initialCreateDefaults = useMemo(() => {
    const trimmed = draftInput.trim();
    const isEmail = trimmed.includes("@");
    const prefix = trimmed.split("@")[0] ?? "";
    return {
      displayName: isEmail ? prefix.replace(/[._-]/g, " ") : trimmed,
      emailOrPrincipal: isEmail ? trimmed : "",
      teamIds: unit.level === "TEAM" ? [unit.id] : [],
    };
  }, [draftInput, unit]);

  const handleSubmit = async (values: IamAccountModalSubmitValues) => {
    setIsSubmitting(true);
    setErrorMessage(null);
    const res = await createIamAccountViaApi(
      {
        account_kind: values.accountKind,
        display_name: values.displayName.trim(),
        email: values.accountKind === "HUMAN" ? values.emailOrPrincipal.trim() : null,
        principal_id: values.emailOrPrincipal.trim(),
        roles: [...values.roles],
        team_ids: [...values.teamIds],
        status: values.status,
      },
      locale,
    );
    setIsSubmitting(false);
    if (!res.ok) {
      setErrorMessage(res.errorMessage);
      return;
    }
    onOpenChange(false);
    const resolvedPrincipal =
      res.account.principal_id ??
      (res.account as unknown as { principalId?: string }).principalId ??
      values.emailOrPrincipal;
    const resolvedDisplayName =
      res.account.display_name ??
      (res.account as unknown as { displayName?: string }).displayName ??
      values.displayName;
    const resolvedEmail =
      res.account.email ??
      (res.account as unknown as { email?: string }).email ??
      (values.accountKind === "HUMAN" ? values.emailOrPrincipal : null);
    onMemberCreated({
      principalId: resolvedPrincipal,
      displayName: resolvedDisplayName,
      email: resolvedEmail,
    });
    if (res.temporaryPassword) {
      setTempPasswordModalData({
        displayName: resolvedDisplayName,
        email: resolvedEmail ?? resolvedPrincipal,
        temporaryPassword: res.temporaryPassword,
        accountId: res.account.id,
      });
    }
  };

  const handleRegenerate = async (): Promise<string | void> => {
    if (!tempPasswordModalData) return;
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
  };

  const effectiveUnits = orgUnits.length > 0 ? orgUnits : [unit];

  return (
    <>
      <IamAccountModal
        open={open}
        onOpenChange={(nextOpen) => {
          if (!nextOpen) setErrorMessage(null);
          onOpenChange(nextOpen);
        }}
        canMutate={canMutate}
        editingAccount={null}
        orgUnits={effectiveUnits}
        labels={iamLabels}
        errorMessage={errorMessage}
        isSubmitting={isSubmitting}
        initialCreateDefaults={initialCreateDefaults}
        onOpenRoleMatrix={() => setIsRoleMatrixOpen(true)}
        onSubmit={(values) => void handleSubmit(values)}
      />

      <IamRoleMatrixReferenceModal
        isOpen={isRoleMatrixOpen}
        onClose={() => setIsRoleMatrixOpen(false)}
        roleMatrix={[]}
        labels={iamLabels}
        openHelpSection={() => undefined}
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
          onRegeneratePassword={handleRegenerate}
        />
      )}
    </>
  );
}
