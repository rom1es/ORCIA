import type { KnownUserOption } from "@orcia/ui";
import React, { useMemo, useState } from "react";
import type { ConfiguredOrgUnit } from "../../../components/platformSetupStorageHelpers";
import { useI18n } from "../../../i18n";
import {
  IamAccountModal,
  type IamAccountModalSubmitValues,
} from "../iam/IamAccountModal";
import { createIamAccountViaApi } from "../iam/iamApiBridge";

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
  const { dictionary, locale } = useI18n();
  const iamLabels = dictionary.settingsHub.iamTab;

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

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
    onMemberCreated({
      principalId: res.account.principal_id,
      displayName: res.account.display_name,
      email: res.account.email ?? null,
    });
  };

  const effectiveUnits = orgUnits.length > 0 ? orgUnits : [unit];

  return (
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
      onSubmit={(values) => void handleSubmit(values)}
    />
  );
}
