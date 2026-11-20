import type { KnownUserOption } from "@orcia/ui";
import { useEffect, useState } from "react";
import type { ConfiguredOrgUnit } from "../components/platformSetupStore";
import { type OrgTreeRowItem } from "../features/admin/organization/orgTreeHelpers";
import {
  createOrgUnitViaApi,
  deleteOrgUnitViaApi,
  fetchOrgUnitsFromApi,
  inviteOrgUnitUserViaApi,
  patchOrgUnitViaApi,
  type OrgUnitServerCapabilities,
} from "../features/admin/organization/orgUnitsApiBridge";
import type {
  CreateOrgUnitFormValues,
  EditOrgUnitFormValues,
  InviteOrganizationUserFormValues,
} from "../features/admin/organization/SettingsOrganizationModalsGroup";
import { isPlatformAdministratorSession, useAuthSessionStore } from "../stores/authSessionStore";

export type OrgUnitAuditMeta = {
  readonly eventType: string;
  readonly summary: string;
  readonly scopeId?: string;
  readonly scopePath?: string;
  readonly scopeLabel?: string;
};

export function useOrgUnitsBlockActions({
  locale,
  orgUnits,
  syncOrgUnitsFromServer,
}: {
  readonly locale: "fr" | "en";
  readonly orgUnits: readonly ConfiguredOrgUnit[];
  readonly syncOrgUnitsFromServer: (
    units: readonly ConfiguredOrgUnit[],
    auditMeta?: OrgUnitAuditMeta,
  ) => void;
}) {
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [inviteModalOpen, setInviteModalOpen] = useState(false);
  const [editingUnit, setEditingUnit] = useState<ConfiguredOrgUnit | null>(null);
  const [managingMembersUnit, setManagingMembersUnit] = useState<ConfiguredOrgUnit | null>(null);
  const [deletingRowItem, setDeletingRowItem] = useState<OrgTreeRowItem | null>(null);
  const [capabilitiesById, setCapabilitiesById] = useState<
    Record<string, OrgUnitServerCapabilities>
  >({});
  const [inviteTempPasswordData, setInviteTempPasswordData] = useState<{
    readonly displayName: string;
    readonly email: string;
    readonly temporaryPassword: string;
  } | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [modalError, setModalError] = useState<string | null>(null);
  const [orgDeleteFeedback, setOrgDeleteFeedback] = useState<string | null>(null);
  const [knownUsers, setKnownUsers] = useState<readonly KnownUserOption[]>([]);

  const isHydrating = useAuthSessionStore((s) => s.isHydrating);
  const isAuthenticated = useAuthSessionStore((s) => s.isAuthenticated);
  const accessToken = useAuthSessionStore((s) => s.accessToken);
  const roles = useAuthSessionStore((s) => s.roles);
  const activeHat = useAuthSessionStore((s) => s.activeHat);
  const readOnlyObserver = useAuthSessionStore((s) => s.readOnlyObserver);
  const isPlatformAdmin = isPlatformAdministratorSession({ roles, activeHat, readOnlyObserver });

  useEffect(() => {
    if (isHydrating || !isAuthenticated) {
      return;
    }
    let cancelled = false;
    void fetchOrgUnitsFromApi(locale).then((res) => {
      if (cancelled) return;
      if (res.ok) {
        setOrgDeleteFeedback(null);
        setCapabilitiesById(res.capabilitiesById);
        if (res.units.length > 0) {
          syncOrgUnitsFromServer(res.units);
        }
        if (res.knownUsers) {
          setKnownUsers(res.knownUsers);
        }
      } else {
        setOrgDeleteFeedback(res.errorMessage);
      }
    });
    return () => {
      cancelled = true;
    };
  }, [locale, isHydrating, isAuthenticated, accessToken]);

  const handleCreateSubmit = async (values: CreateOrgUnitFormValues) => {
    setIsSubmitting(true);
    setModalError(null);
    setOrgDeleteFeedback(null);
    const parentPayload =
      values.parentId && values.parentId !== "scope-global" ? values.parentId : null;
    const effectiveLeads =
      Array.isArray(values.leadUserIds) && values.leadUserIds.length > 0
        ? values.leadUserIds
        : values.leadUserId
          ? [values.leadUserId]
          : [];
    const res = await createOrgUnitViaApi(
      {
        name: values.name,
        kind: values.kind,
        slug: values.slug || null,
        parent_id: parentPayload,
        billing_enabled: values.billingEnabled,
        lead_user_id: effectiveLeads[0] ?? null,
        lead_user_ids: effectiveLeads,
        ontology_lead_user_ids:
          values.kind === "BU" ? [...(values.ontologyLeadUserIds ?? [])] : [],
        member_user_ids: [],
      },
      locale,
    );
    setIsSubmitting(false);
    if (!res.ok) {
      setModalError(res.errorMessage);
      return;
    }
    if (res.capabilities) {
      setCapabilitiesById((prev) => ({ ...prev, [res.unit.id]: res.capabilities! }));
    }
    const nextUnits = [...orgUnits.filter((u) => u.id !== res.unit.id), res.unit];
    const levelLabel = values.kind === "BU" ? "Direction (BU)" : "Équipe";
    syncOrgUnitsFromServer(nextUnits, {
      eventType: "OrgUnitCreated",
      summary: `${levelLabel} "${res.unit.name}" (${res.unit.slug}) créée`,
      scopeId: res.unit.id,
      scopePath: res.unit.slug,
      scopeLabel: `${levelLabel} · ${res.unit.name}`,
    });
    void useAuthSessionStore.getState().hydrateSession({ force: true });
    setCreateModalOpen(false);
  };

  const handleEditSave = async (orgUnitId: string, values: EditOrgUnitFormValues) => {
    setIsSubmitting(true);
    setModalError(null);
    const targetUnit = orgUnits.find((u) => u.id === orgUnitId);
    const caps = capabilitiesById[orgUnitId];
    const parentPayload =
      values.parentId && values.parentId !== "scope-global" ? values.parentId : null;
    const effectiveLeads =
      Array.isArray(values.leadUserIds) && values.leadUserIds.length > 0
        ? values.leadUserIds
        : values.leadUserId
          ? [values.leadUserId]
          : undefined;
    const isTeamLeadOnly =
      targetUnit?.level === "TEAM" && caps && caps.canEdit && !caps.canInviteUsers;
    const res = await patchOrgUnitViaApi(
      orgUnitId,
      {
        name: values.name,
        ...(isTeamLeadOnly
          ? {}
          : { parent_id: parentPayload, billing_enabled: values.billingEnabled }),
        ...(effectiveLeads !== undefined
          ? { lead_user_id: effectiveLeads[0] ?? null, lead_user_ids: effectiveLeads }
          : {}),
        ...(targetUnit?.level === "BU" && values.ontologyLeadUserIds !== undefined
          ? { ontology_lead_user_ids: [...values.ontologyLeadUserIds] }
          : {}),
      },
      locale,
    );
    setIsSubmitting(false);
    if (!res.ok) {
      setModalError(res.errorMessage);
      return;
    }
    if (res.capabilities) {
      setCapabilitiesById((prev) => ({ ...prev, [res.unit.id]: res.capabilities! }));
    }
    const nextUnits = orgUnits.map((u) => (u.id === orgUnitId ? res.unit : u));
    const levelLabel = res.unit.level === "BU" ? "Direction (BU)" : "Équipe";
    syncOrgUnitsFromServer(nextUnits, {
      eventType: "SettingsChanged",
      summary: `${levelLabel} "${res.unit.name}" mise à jour`,
      scopeId: res.unit.id,
      scopePath: res.unit.slug,
      scopeLabel: `${levelLabel} · ${res.unit.name}`,
    });
    void useAuthSessionStore.getState().hydrateSession({ force: true });
    setEditingUnit(null);
  };

  const handleInviteSubmit = async (values: InviteOrganizationUserFormValues) => {
    setIsSubmitting(true);
    setModalError(null);
    const res = await inviteOrgUnitUserViaApi(
      {
        target_org_unit_id: values.targetOrgUnitId,
        email: values.email,
        display_name: values.displayName,
        assignment_role: values.assignmentRole,
      },
      locale,
    );
    setIsSubmitting(false);
    if (!res.ok) {
      setModalError(res.errorMessage);
      return;
    }
    setCapabilitiesById((prev) => ({ ...prev, [res.unit.id]: res.capabilities }));
    const refreshed = await fetchOrgUnitsFromApi(locale);
    if (refreshed.ok) {
      setCapabilitiesById(refreshed.capabilitiesById);
      syncOrgUnitsFromServer(refreshed.units);
      setKnownUsers(refreshed.knownUsers);
    } else {
      syncOrgUnitsFromServer(orgUnits.map((u) => (u.id === res.unit.id ? res.unit : u)));
    }
    setInviteModalOpen(false);
    if (res.invitation.temporary_password) {
      setInviteTempPasswordData({
        displayName: res.invitation.display_name,
        email: res.invitation.email,
        temporaryPassword: res.invitation.temporary_password,
      });
    }
    void useAuthSessionStore.getState().hydrateSession({ force: true });
  };

  const handleMembersSave = async (
    orgUnitId: string,
    values: {
      readonly leadUserId: string | null;
      readonly leadUserIds?: readonly string[];
      readonly memberUserIds: readonly string[];
    },
  ) => {
    setIsSubmitting(true);
    setModalError(null);
    const effectiveLeads =
      Array.isArray(values.leadUserIds) && values.leadUserIds.length > 0
        ? values.leadUserIds
        : values.leadUserId
          ? [values.leadUserId]
          : [];
    const res = await patchOrgUnitViaApi(
      orgUnitId,
      {
        lead_user_id: effectiveLeads[0] ?? null,
        lead_user_ids: effectiveLeads,
        member_user_ids: [...values.memberUserIds],
      },
      locale,
    );
    setIsSubmitting(false);
    if (!res.ok) {
      setModalError(res.errorMessage);
      return;
    }
    const nextUnits = orgUnits.map((u) => (u.id === orgUnitId ? res.unit : u));
    const levelLabel = res.unit.level === "BU" ? "Direction (BU)" : "Équipe";
    syncOrgUnitsFromServer(nextUnits, {
      eventType: "PermissionGranted",
      summary: `Membres de ${levelLabel} "${res.unit.name}" mis à jour (${res.unit.memberUserIds?.length ?? 0})`,
      scopeId: res.unit.id,
      scopePath: res.unit.slug,
      scopeLabel: `${levelLabel} · ${res.unit.name}`,
    });
    void useAuthSessionStore.getState().hydrateSession({ force: true });
    setManagingMembersUnit(null);
  };

  const handleConfirmDelete = async (orgUnitId: string) => {
    setIsSubmitting(true);
    setModalError(null);
    const target = orgUnits.find((u) => u.id === orgUnitId);
    const res = await deleteOrgUnitViaApi(orgUnitId, locale);
    setIsSubmitting(false);
    if (!res.ok) {
      setOrgDeleteFeedback(res.errorMessage);
      setDeletingRowItem(null);
      return;
    }
    const nextUnits = orgUnits.filter((u) => u.id !== orgUnitId);
    const levelLabel = target?.level === "BU" ? "Direction (BU)" : "Équipe";
    syncOrgUnitsFromServer(
      nextUnits,
      target
        ? {
            eventType: "OrgUnitDeleted",
            summary: `${levelLabel} "${target.name}" (${target.slug}) supprimée`,
            scopeId: target.id,
            scopePath: target.slug,
            scopeLabel: `${levelLabel} · ${target.name}`,
          }
        : undefined,
    );
    void useAuthSessionStore.getState().hydrateSession({ force: true });
    setOrgDeleteFeedback(null);
    setDeletingRowItem(null);
  };

  return {
    createModalOpen,
    setCreateModalOpen,
    inviteModalOpen,
    setInviteModalOpen,
    editingUnit,
    setEditingUnit,
    managingMembersUnit,
    setManagingMembersUnit,
    deletingRowItem,
    setDeletingRowItem,
    capabilitiesById,
    inviteTempPasswordData,
    setInviteTempPasswordData,
    isSubmitting,
    modalError,
    setModalError,
    orgDeleteFeedback,
    setOrgDeleteFeedback,
    knownUsers,
    isPlatformAdmin,
    handleCreateSubmit,
    handleEditSave,
    handleInviteSubmit,
    handleMembersSave,
    handleConfirmDelete,
  };
}
