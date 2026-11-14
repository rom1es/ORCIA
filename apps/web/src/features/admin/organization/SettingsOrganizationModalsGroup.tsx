import type { KnownUserOption } from "@orcia/ui";
import React from "react";
import type { ConfiguredOrgUnit } from "../../../components/platformSetupStorageHelpers";
import type { OrganizationTabDictionarySection } from "../../../i18n/locales/organization_tab_labels";
import { ConfirmDeleteOrgUnitModal } from "./ConfirmDeleteOrgUnitModal";
import { CreateOrgUnitModal, type CreateOrgUnitFormValues } from "./CreateOrgUnitModal";
import { EditOrgUnitModal, type EditOrgUnitFormValues } from "./EditOrgUnitModal";
import { ManageOrgUnitMembersModal } from "./ManageOrgUnitMembersModal";
import type { OrgTreeRowItem } from "./orgTreeHelpers";

export type { CreateOrgUnitFormValues, EditOrgUnitFormValues };

export interface SettingsOrganizationModalsGroupProps {
  readonly isFr: boolean;
  readonly canMutate: boolean;
  readonly orgUnits: readonly ConfiguredOrgUnit[];
  readonly knownUsers: readonly KnownUserOption[];
  readonly labels: OrganizationTabDictionarySection;
  readonly modalError: string | null;
  readonly isSubmitting: boolean;
  readonly createModalOpen: boolean;
  readonly onOpenChangeCreate: (open: boolean) => void;
  readonly onCreateSubmit: (values: CreateOrgUnitFormValues) => void;
  readonly editingUnit: ConfiguredOrgUnit | null;
  readonly onOpenChangeEdit: (open: boolean) => void;
  readonly onEditSave: (orgUnitId: string, values: EditOrgUnitFormValues) => void;
  readonly managingMembersUnit: ConfiguredOrgUnit | null;
  readonly onOpenChangeMembers: (open: boolean) => void;
  readonly onMembersSave: (
    orgUnitId: string,
    values: { readonly leadUserId: string | null; readonly memberUserIds: readonly string[] },
  ) => void;
  readonly deletingRowItem: OrgTreeRowItem | null;
  readonly onOpenChangeDelete: (open: boolean) => void;
  readonly onOpenWorkspaces: () => void;
  readonly onConfirmDelete: (orgUnitId: string) => void;
}

export function SettingsOrganizationModalsGroup({
  isFr,
  canMutate,
  orgUnits,
  knownUsers,
  labels,
  modalError,
  isSubmitting,
  createModalOpen,
  onOpenChangeCreate,
  onCreateSubmit,
  editingUnit,
  onOpenChangeEdit,
  onEditSave,
  managingMembersUnit,
  onOpenChangeMembers,
  onMembersSave,
  deletingRowItem,
  onOpenChangeDelete,
  onOpenWorkspaces,
  onConfirmDelete,
}: SettingsOrganizationModalsGroupProps): React.ReactElement {
  return (
    <>
      <CreateOrgUnitModal
        open={createModalOpen}
        onOpenChange={onOpenChangeCreate}
        canMutate={canMutate}
        orgUnits={orgUnits}
        knownUsers={knownUsers}
        unknownUserErrorLabel={labels.unknownUserError}
        labels={labels.createModal}
        errorMessage={modalError}
        isSubmitting={isSubmitting}
        onSubmit={onCreateSubmit}
      />

      <EditOrgUnitModal
        unit={editingUnit}
        open={editingUnit !== null}
        onOpenChange={onOpenChangeEdit}
        canMutate={canMutate}
        orgUnits={orgUnits}
        labels={labels.editModal}
        parentPrefixLabel={labels.createModal.parentBuOptionPrefix}
        errorMessage={modalError}
        isSubmitting={isSubmitting}
        onSave={onEditSave}
      />

      <ManageOrgUnitMembersModal
        unit={managingMembersUnit}
        open={managingMembersUnit !== null}
        onOpenChange={onOpenChangeMembers}
        canMutate={canMutate}
        labels={labels.membersModal}
        knownUsers={knownUsers}
        unknownUserErrorLabel={labels.unknownUserError}
        errorMessage={modalError}
        isSubmitting={isSubmitting}
        onSave={onMembersSave}
      />

      <ConfirmDeleteOrgUnitModal
        rowItem={deletingRowItem}
        open={deletingRowItem !== null}
        onOpenChange={onOpenChangeDelete}
        isFr={isFr}
        canMutate={canMutate}
        labels={labels.deleteModal}
        errorMessage={modalError}
        isSubmitting={isSubmitting}
        onOpenWorkspaces={onOpenWorkspaces}
        onConfirmDelete={onConfirmDelete}
      />
    </>
  );
}
