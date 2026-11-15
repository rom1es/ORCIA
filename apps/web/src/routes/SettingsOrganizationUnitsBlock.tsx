import {
  ContextualInfoTriggerButton,
  OrciaAlertBanner,
  OrciaButton,
  type ControlCenterWorkspaceGovItem,
  type KnownUserOption,
} from "@orcia/ui";
import React, { useEffect, useState } from "react";
import type { ConfiguredOrgUnit } from "../components/platformSetupStore";
import { useShellNavigation } from "../components/ShellContainer";
import { useAuthSessionStore } from "../stores/authSessionStore";
import { OrgPedagogicalCallout } from "../features/admin/organization/OrgPedagogicalCallout";
import { buildIndentedOrgTree, type OrgTreeRowItem } from "../features/admin/organization/orgTreeHelpers";
import {
  createOrgUnitViaApi,
  deleteOrgUnitViaApi,
  fetchOrgUnitsFromApi,
  patchOrgUnitViaApi,
} from "../features/admin/organization/orgUnitsApiBridge";
import {
  SettingsOrganizationModalsGroup,
  type CreateOrgUnitFormValues,
  type EditOrgUnitFormValues,
} from "../features/admin/organization/SettingsOrganizationModalsGroup";
import { useI18n } from "../i18n";
import { SettingsOrganizationUnitRow } from "./SettingsOrganizationUnitRow";

export interface SettingsOrganizationUnitsBlockProps {
  readonly isFr: boolean;
  readonly canMutate?: boolean;
  readonly orgUnits: readonly ConfiguredOrgUnit[];
  readonly workspaces?: readonly ControlCenterWorkspaceGovItem[];
  readonly openHelpSection: (sectionId: string) => void;
  readonly syncOrgUnitsFromServer: (
    units: readonly ConfiguredOrgUnit[],
    auditMeta?: {
      readonly eventType: string;
      readonly summary: string;
      readonly scopeId?: string;
      readonly scopePath?: string;
      readonly scopeLabel?: string;
    },
  ) => void;
}

export function SettingsOrganizationUnitsBlock({
  isFr,
  canMutate = true,
  orgUnits,
  workspaces = [],
  openHelpSection,
  syncOrgUnitsFromServer,
}: SettingsOrganizationUnitsBlockProps): React.ReactElement {
  const { dictionary, locale } = useI18n();
  const { navigateToRoute } = useShellNavigation();
  const labels = dictionary.settingsHub.organizationTab;

  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [editingUnit, setEditingUnit] = useState<ConfiguredOrgUnit | null>(null);
  const [managingMembersUnit, setManagingMembersUnit] = useState<ConfiguredOrgUnit | null>(null);
  const [deletingRowItem, setDeletingRowItem] = useState<OrgTreeRowItem | null>(null);

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [modalError, setModalError] = useState<string | null>(null);
  const [orgDeleteFeedback, setOrgDeleteFeedback] = useState<string | null>(null);
  const [knownUsers, setKnownUsers] = useState<readonly KnownUserOption[]>([]);

  const isHydrating = useAuthSessionStore((s) => s.isHydrating);
  const accessToken = useAuthSessionStore((s) => s.accessToken);

  useEffect(() => {
    if (isHydrating) {
      return;
    }
    let cancelled = false;
    void fetchOrgUnitsFromApi(locale).then((res) => {
      if (cancelled) return;
      if (res.ok) {
        setOrgDeleteFeedback(null);
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
  }, [locale, isHydrating, accessToken]);

  const treeRows = buildIndentedOrgTree(orgUnits, workspaces);

  const handleCreateSubmit = async (values: CreateOrgUnitFormValues) => {
    setIsSubmitting(true);
    setModalError(null);
    setOrgDeleteFeedback(null);
    const parentPayload = values.parentId && values.parentId !== "scope-global" ? values.parentId : null;
    const res = await createOrgUnitViaApi(
      {
        name: values.name,
        kind: values.kind,
        slug: values.slug || null,
        parent_id: parentPayload,
        billing_enabled: values.billingEnabled,
        lead_user_id: values.leadUserId || null,
        member_user_ids: [],
      },
      locale,
    );
    setIsSubmitting(false);
    if (!res.ok) {
      setModalError(res.errorMessage);
      return;
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
    setCreateModalOpen(false);
  };

  const handleEditSave = async (orgUnitId: string, values: EditOrgUnitFormValues) => {
    setIsSubmitting(true);
    setModalError(null);
    const parentPayload = values.parentId && values.parentId !== "scope-global" ? values.parentId : null;
    const res = await patchOrgUnitViaApi(
      orgUnitId,
      { name: values.name, parent_id: parentPayload, billing_enabled: values.billingEnabled },
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
      eventType: "SettingsChanged",
      summary: `${levelLabel} "${res.unit.name}" mise à jour`,
      scopeId: res.unit.id,
      scopePath: res.unit.slug,
      scopeLabel: `${levelLabel} · ${res.unit.name}`,
    });
    setEditingUnit(null);
  };

  const handleMembersSave = async (
    orgUnitId: string,
    values: { readonly leadUserId: string | null; readonly memberUserIds: readonly string[] },
  ) => {
    setIsSubmitting(true);
    setModalError(null);
    const res = await patchOrgUnitViaApi(
      orgUnitId,
      { lead_user_id: values.leadUserId, member_user_ids: [...values.memberUserIds] },
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
    setOrgDeleteFeedback(null);
    setDeletingRowItem(null);
  };

  return (
    <section
      data-testid="settings-organization-section"
      className="orcia-bento-card"
      style={{ display: "flex", flexDirection: "column", gap: "14px" }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "8px",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <h2 style={{ margin: 0, fontSize: "15px" }}>{labels.sectionTitle}</h2>
          <ContextualInfoTriggerButton
            sectionId="iam-org-tree"
            label={labels.helpTriggerLabel}
            onOpenHelpSection={openHelpSection}
          />
        </div>

        <OrciaButton
          variant="primary"
          testId="open-create-org-unit-modal-btn"
          disabled={!canMutate}
          onClick={() => {
            setModalError(null);
            setOrgDeleteFeedback(null);
            setCreateModalOpen(true);
          }}
        >
          {labels.openCreateModalCta}
        </OrciaButton>
      </div>

      <OrgPedagogicalCallout
        labels={labels}
        onOpenWorkspaces={() => navigateToRoute("/workspaces")}
      />

      {orgDeleteFeedback ? (
        <OrciaAlertBanner tone="crimson" role="alert" testId="org-unit-delete-feedback">
          {orgDeleteFeedback}
        </OrciaAlertBanner>
      ) : null}

      {treeRows.length === 0 ? (
        <p
          data-testid="iam-org-units-empty-state"
          style={{
            margin: 0,
            fontSize: "13px",
            color: "var(--color-muted-foreground)",
          }}
        >
          {labels.emptyStateText}
        </p>
      ) : (
        <div
          data-testid="settings-organization-tree"
          style={{ display: "grid", gap: "6px" }}
        >
          {treeRows.map((rowItem) => (
            <SettingsOrganizationUnitRow
              key={rowItem.unit.id}
              rowItem={rowItem}
              isFr={isFr}
              canMutate={canMutate}
              labels={labels}
              knownUsers={knownUsers}
              onEdit={(unit) => { setModalError(null); setEditingUnit(unit); }}
              onManageMembers={(unit) => { setModalError(null); setManagingMembersUnit(unit); }}
              onRequestDelete={(item) => {
                setModalError(null);
                setOrgDeleteFeedback(null);
                setDeletingRowItem(item);
              }}
            />
          ))}
        </div>
      )}

      <SettingsOrganizationModalsGroup
        isFr={isFr}
        canMutate={canMutate}
        orgUnits={orgUnits}
        knownUsers={knownUsers}
        labels={labels}
        modalError={modalError}
        isSubmitting={isSubmitting}
        createModalOpen={createModalOpen}
        onOpenChangeCreate={setCreateModalOpen}
        onCreateSubmit={(values) => void handleCreateSubmit(values)}
        editingUnit={editingUnit}
        onOpenChangeEdit={(open) => !open && setEditingUnit(null)}
        onEditSave={(orgUnitId, values) => void handleEditSave(orgUnitId, values)}
        managingMembersUnit={managingMembersUnit}
        onOpenChangeMembers={(open) => !open && setManagingMembersUnit(null)}
        onMembersSave={(orgUnitId, values) => void handleMembersSave(orgUnitId, values)}
        deletingRowItem={deletingRowItem}
        onOpenChangeDelete={(open) => !open && setDeletingRowItem(null)}
        onOpenWorkspaces={() => navigateToRoute("/workspaces")}
        onConfirmDelete={(orgUnitId) => void handleConfirmDelete(orgUnitId)}
      />
    </section>
  );
}
