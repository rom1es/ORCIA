import type { KnownUserOption } from "@orcia/ui";
import React from "react";
import type { ConfiguredOrgUnit } from "../../../components/platformSetupStorageHelpers";
import type { OrganizationTabDictionarySection } from "../../../i18n/locales/organization_tab_labels";
import { ConfirmDeleteOrgUnitModal } from "./ConfirmDeleteOrgUnitModal";
import { CreateOrgUnitModal, type CreateOrgUnitFormValues } from "./CreateOrgUnitModal";
import { EditOrgUnitModal, type EditOrgUnitFormValues } from "./EditOrgUnitModal";
import {
  InviteOrganizationUserModal,
  type InviteOrganizationUserFormValues,
} from "./InviteOrganizationUserModal";
import { ManageOrgUnitMembersModal } from "./ManageOrgUnitMembersModal";
import type { OrgTreeRowItem } from "./orgTreeHelpers";
import type { OrgUnitServerCapabilities } from "./orgUnitsApiBridge";

export type { CreateOrgUnitFormValues, EditOrgUnitFormValues, InviteOrganizationUserFormValues };

export interface SettingsOrganizationModalsGroupProps {
  readonly isFr: boolean;
  readonly canMutate: boolean;
  readonly canCreateAtRoot?: boolean;
  readonly creatableParentUnits?: readonly ConfiguredOrgUnit[];
  readonly invitableUnits?: readonly ConfiguredOrgUnit[];
  readonly capabilitiesById?: Record<string, OrgUnitServerCapabilities>;
  readonly orgUnits: readonly ConfiguredOrgUnit[];
  readonly knownUsers: readonly KnownUserOption[];
  readonly labels: OrganizationTabDictionarySection;
  readonly modalError: string | null;
  readonly isSubmitting: boolean;
  readonly createModalOpen: boolean;
  readonly onOpenChangeCreate: (open: boolean) => void;
  readonly onCreateSubmit: (values: CreateOrgUnitFormValues) => void;
  readonly inviteModalOpen: boolean;
  readonly onOpenChangeInvite: (open: boolean) => void;
  readonly onInviteSubmit: (values: InviteOrganizationUserFormValues) => void;
  readonly editingUnit: ConfiguredOrgUnit | null;
  readonly onOpenChangeEdit: (open: boolean) => void;
  readonly onEditSave: (orgUnitId: string, values: EditOrgUnitFormValues) => void;
  readonly managingMembersUnit: ConfiguredOrgUnit | null;
  readonly onOpenChangeMembers: (open: boolean) => void;
  readonly onMembersSave: (
    orgUnitId: string,
    values: {
      readonly leadUserId: string | null;
      readonly leadUserIds?: readonly string[];
      readonly memberUserIds: readonly string[];
    },
  ) => void;
  readonly deletingRowItem: OrgTreeRowItem | null;
  readonly onOpenChangeDelete: (open: boolean) => void;
  readonly onOpenWorkspaces: () => void;
  readonly onConfirmDelete: (orgUnitId: string) => void;
}

export function SettingsOrganizationModalsGroup({
  isFr,
  canMutate,
  canCreateAtRoot = true,
  creatableParentUnits,
  invitableUnits = [],
  capabilitiesById = {},
  orgUnits,
  knownUsers,
  labels,
  modalError,
  isSubmitting,
  createModalOpen,
  onOpenChangeCreate,
  onCreateSubmit,
  inviteModalOpen,
  onOpenChangeInvite,
  onInviteSubmit,
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
  const editingCapabilities = editingUnit ? capabilitiesById[editingUnit.id] : undefined;
  const allowParentAndBillingEdit = !(
    editingUnit?.level === "TEAM" &&
    editingCapabilities &&
    editingCapabilities.canEdit &&
    !editingCapabilities.canInviteUsers
  );

  return (
    <>
      <CreateOrgUnitModal
        open={createModalOpen}
        onOpenChange={onOpenChangeCreate}
        canMutate={canMutate}
        canCreateAtRoot={canCreateAtRoot}
        creatableParentUnits={creatableParentUnits}
        orgUnits={orgUnits}
        knownUsers={knownUsers}
        unknownUserErrorLabel={labels.unknownUserError}
        labels={labels.createModal}
        errorMessage={modalError}
        isSubmitting={isSubmitting}
        onSubmit={onCreateSubmit}
      />

      <InviteOrganizationUserModal
        open={inviteModalOpen}
        onOpenChange={onOpenChangeInvite}
        invitableUnits={invitableUnits}
        labels={labels.inviteModal}
        errorMessage={modalError}
        isSubmitting={isSubmitting}
        onSubmit={onInviteSubmit}
      />

      <EditOrgUnitModal
        unit={editingUnit}
        unitCapabilities={editingCapabilities}
        open={editingUnit !== null}
        onOpenChange={onOpenChangeEdit}
        canMutate={canMutate}
        allowParentAndBillingEdit={allowParentAndBillingEdit}
        orgUnits={orgUnits}
        knownUsers={knownUsers}
        unknownUserErrorLabel={labels.unknownUserError}
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
