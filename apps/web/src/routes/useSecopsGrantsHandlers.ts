import { useState } from "react";
import type { ConfiguredRbacGrant } from "../components/platformSetupStore";
import {
  createIamGrantsViaApi,
  deleteIamGrantViaApi,
  fetchIamGrantsFromApi,
} from "../features/admin/iam/iamApiBridge";
import type { CreateSecopsExceptionInput } from "../features/admin/iam/IamSecopsExceptionsDrawer";
import { DICTIONARIES, formatI18nTemplate } from "../i18n";

export function useSecopsGrantsHandlers(params: {
  readonly locale: "fr" | "en";
  readonly rbacGrants: readonly ConfiguredRbacGrant[];
  readonly syncRbacGrantsFromServer: (
    grants: readonly ConfiguredRbacGrant[],
    auditMeta?: {
      readonly eventType: string;
      readonly summary: string;
      readonly scopePath?: string;
      readonly scopeLabel?: string;
    },
  ) => void;
}) {
  const { locale, rbacGrants, syncRbacGrantsFromServer } = params;
  const copy = DICTIONARIES[locale].routesAndWizards.orgUnitsActions;
  const [grantsError, setGrantsError] = useState<string | null>(null);
  const [isSubmittingGrant, setIsSubmittingGrant] = useState(false);

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
    const nextGrants = fresh.ok ? fresh.grants : [...rbacGrants, ...res.grants];
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
      summary: formatI18nTemplate(copy.secopsDeletedTemplate, { grantId }),
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
      summary: formatI18nTemplate(copy.secopsBulkDeletedTemplate, { count: grantIds.length }),
    });
  };

  return {
    grantsError,
    isSubmittingGrant,
    handleCreateException,
    handleDeleteSingleGrant,
    handleBulkDeleteGrants,
  };
}
