import {
  ContextualInfoTriggerButton,
  OrciaAlertBanner,
  OrciaButton,
  TemporaryPasswordInvitationModal,
  type ControlCenterWorkspaceGovItem,
} from "@orcia/ui";
import React from "react";
import type { ConfiguredOrgUnit } from "../components/platformSetupStore";
import { useShellNavigation } from "../components/ShellContainer";
import { OrgPedagogicalCallout } from "../features/admin/organization/OrgPedagogicalCallout";
import { buildIndentedOrgTree } from "../features/admin/organization/orgTreeHelpers";
import { SettingsOrganizationModalsGroup } from "../features/admin/organization/SettingsOrganizationModalsGroup";
import { useI18n } from "../i18n";
import { SettingsOrganizationUnitRow } from "./SettingsOrganizationUnitRow";
import { type OrgUnitAuditMeta, useOrgUnitsBlockActions } from "./useOrgUnitsBlockActions";

export interface SettingsOrganizationUnitsBlockProps {
  readonly isFr: boolean;
  readonly canMutate?: boolean;
  readonly orgUnits: readonly ConfiguredOrgUnit[];
  readonly workspaces?: readonly ControlCenterWorkspaceGovItem[];
  readonly openHelpSection: (sectionId: string) => void;
  readonly syncOrgUnitsFromServer: (
    units: readonly ConfiguredOrgUnit[],
    auditMeta?: OrgUnitAuditMeta,
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
  const typedLocale = locale === "en" ? "en" : "fr";

  const s = useOrgUnitsBlockActions({
    locale: typedLocale,
    orgUnits,
    syncOrgUnitsFromServer,
  });

  const treeRows = buildIndentedOrgTree(orgUnits, workspaces);
  const hasServerCaps = Object.keys(s.capabilitiesById).length > 0;
  const creatableParentUnits = orgUnits.filter((u) =>
    hasServerCaps ? Boolean(s.capabilitiesById[u.id]?.canCreateChild) : u.level === "BU",
  );
  const canCreateUnit =
    canMutate && (s.isPlatformAdmin || creatableParentUnits.length > 0 || !hasServerCaps);
  const invitableUnits = orgUnits.filter((u) =>
    hasServerCaps ? Boolean(s.capabilitiesById[u.id]?.canInviteUsers) : s.isPlatformAdmin,
  );
  const hasReadOnlyAncestor = orgUnits.some((u) => s.capabilitiesById[u.id]?.canEdit === false);

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

        <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
          {invitableUnits.length > 0 ? (
            <OrciaButton
              variant="secondary"
              testId="open-invite-org-user-modal-btn"
              disabled={!canMutate}
              onClick={() => {
                s.setModalError(null);
                s.setOrgDeleteFeedback(null);
                s.setInviteModalOpen(true);
              }}
            >
              {labels.openInviteModalCta}
            </OrciaButton>
          ) : null}

          <OrciaButton
            variant="primary"
            testId="open-create-org-unit-modal-btn"
            disabled={!canCreateUnit}
            onClick={() => {
              s.setModalError(null);
              s.setOrgDeleteFeedback(null);
              s.setCreateModalOpen(true);
            }}
          >
            {labels.openCreateModalCta}
          </OrciaButton>
        </div>
      </div>

      {hasReadOnlyAncestor ? (
        <OrciaAlertBanner tone="cobalt" testId="org-scoped-view-notice">
          {labels.scopedViewNotice}
        </OrciaAlertBanner>
      ) : null}

      <OrgPedagogicalCallout
        labels={labels}
        onOpenWorkspaces={() => navigateToRoute("/workspaces")}
      />

      {s.orgDeleteFeedback ? (
        <OrciaAlertBanner tone="crimson" role="alert" testId="org-unit-delete-feedback">
          {s.orgDeleteFeedback}
        </OrciaAlertBanner>
      ) : null}

      {treeRows.length === 0 ? (
        <p
          data-testid="iam-org-units-empty-state"
          style={{ margin: 0, fontSize: "13px", color: "var(--color-muted-foreground)" }}
        >
          {labels.emptyStateText}
        </p>
      ) : (
        <div data-testid="settings-organization-tree" style={{ display: "grid", gap: "6px" }}>
          {treeRows.map((rowItem) => (
            <SettingsOrganizationUnitRow
              key={rowItem.unit.id}
              rowItem={rowItem}
              isFr={isFr}
              canMutate={canMutate}
              capabilities={s.capabilitiesById[rowItem.unit.id]}
              labels={labels}
              knownUsers={s.knownUsers}
              onEdit={(unit) => {
                s.setModalError(null);
                s.setEditingUnit(unit);
              }}
              onManageMembers={(unit) => {
                s.setModalError(null);
                s.setManagingMembersUnit(unit);
              }}
              onRequestDelete={(item) => {
                s.setModalError(null);
                s.setOrgDeleteFeedback(null);
                s.setDeletingRowItem(item);
              }}
            />
          ))}
        </div>
      )}

      <SettingsOrganizationModalsGroup
        isFr={isFr}
        canMutate={canMutate}
        canCreateAtRoot={s.isPlatformAdmin}
        creatableParentUnits={creatableParentUnits}
        invitableUnits={invitableUnits}
        capabilitiesById={s.capabilitiesById}
        orgUnits={orgUnits}
        knownUsers={s.knownUsers}
        labels={labels}
        modalError={s.modalError}
        isSubmitting={s.isSubmitting}
        createModalOpen={s.createModalOpen}
        onOpenChangeCreate={s.setCreateModalOpen}
        onCreateSubmit={(values) => void s.handleCreateSubmit(values)}
        inviteModalOpen={s.inviteModalOpen}
        onOpenChangeInvite={s.setInviteModalOpen}
        onInviteSubmit={(values) => void s.handleInviteSubmit(values)}
        editingUnit={s.editingUnit}
        onOpenChangeEdit={(open) => !open && s.setEditingUnit(null)}
        onEditSave={(orgUnitId, values) => void s.handleEditSave(orgUnitId, values)}
        managingMembersUnit={s.managingMembersUnit}
        onOpenChangeMembers={(open) => !open && s.setManagingMembersUnit(null)}
        onMembersSave={(orgUnitId, values) => void s.handleMembersSave(orgUnitId, values)}
        deletingRowItem={s.deletingRowItem}
        onOpenChangeDelete={(open) => !open && s.setDeletingRowItem(null)}
        onOpenWorkspaces={() => navigateToRoute("/workspaces")}
        onConfirmDelete={(orgUnitId) => void s.handleConfirmDelete(orgUnitId)}
      />

      {s.inviteTempPasswordData ? (
        <TemporaryPasswordInvitationModal
          isOpen={true}
          isFr={isFr}
          displayName={s.inviteTempPasswordData.displayName}
          email={s.inviteTempPasswordData.email}
          temporaryPassword={s.inviteTempPasswordData.temporaryPassword}
          orciaUrl={
            typeof window !== "undefined" ? window.location.origin : "http://localhost:3100"
          }
          onClose={() => s.setInviteTempPasswordData(null)}
        />
      ) : null}
    </section>
  );
}
