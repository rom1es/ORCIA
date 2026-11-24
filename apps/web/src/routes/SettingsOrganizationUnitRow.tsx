import { OrciaButton, OrciaIcon, StatusBadge, type KnownUserOption } from "@orcia/ui";
import React from "react";
import type { ConfiguredOrgUnit } from "../components/platformSetupStore";
import type { OrgTreeRowItem } from "../features/admin/organization/orgTreeHelpers";
import type { OrgUnitServerCapabilities } from "../features/admin/organization/orgUnitsApiBridge";
import type { AdminAndStudioDictionarySection } from "../i18n/locales/admin_and_studio_labels";
import { resolveLocaleForFlag } from "../i18n";
import { formatCountNoun } from "../stores/authSessionStore";

export interface SettingsOrganizationUnitRowProps {
  readonly rowItem: OrgTreeRowItem;
  readonly isFr: boolean;
  readonly canMutate: boolean;
  readonly capabilities?: OrgUnitServerCapabilities;
  readonly knownUsers?: readonly KnownUserOption[];
  readonly labels: AdminAndStudioDictionarySection["settingsHub"]["organizationTab"];
  readonly onEdit: (unit: ConfiguredOrgUnit) => void;
  readonly onManageMembers: (unit: ConfiguredOrgUnit) => void;
  readonly onRequestDelete: (rowItem: OrgTreeRowItem) => void;
}

export function SettingsOrganizationUnitRow({
  rowItem,
  isFr,
  canMutate,
  capabilities,
  knownUsers = [],
  labels,
  onEdit,
  onManageMembers,
  onRequestDelete,
}: SettingsOrganizationUnitRowProps): React.ReactElement {
  const {
    unit,
    depth,
    isSubBu,
    parentNode,
    attachedTeamsCount,
    attachedWorkspacesCount,
  } = rowItem;
  const locale = resolveLocaleForFlag(isFr);

  const kindLabel =
    unit.level === "TEAM"
      ? labels.badges.team
      : isSubBu
        ? labels.badges.subBu
        : labels.badges.rootBu;

  const kindTone = unit.level === "TEAM" ? "emerald" : "cobalt";
  const membersCount = (unit.memberUserIds ?? []).length;
  const membersBadgeText = formatCountNoun(
    membersCount,
    labels.nouns.memberSingular,
    labels.nouns.memberPlural,
    locale,
  );
  const workspacesBadgeText = formatCountNoun(
    attachedWorkspacesCount,
    labels.nouns.workspaceSingular,
    labels.nouns.workspacePlural,
    locale,
  );
  const attachedTeamsLabel = formatCountNoun(
    attachedTeamsCount,
    labels.nouns.childTeamSingular,
    labels.nouns.childTeamPlural,
    locale,
  );
  const billingActive = unit.billingEnabled !== false;
  const isReadOnlyContext = Boolean(capabilities && !capabilities.canEdit);
  const rowCanEdit = canMutate && (capabilities ? capabilities.canEdit : true);
  const rowCanManageMembers = canMutate && (capabilities ? capabilities.canManageMembers : true);
  const rowCanDelete = canMutate && (capabilities ? capabilities.canDelete : true);

  return (
    <div
      data-testid={`org-unit-row-${unit.id}`}
      data-depth={String(depth)}
      style={{
        padding: "10px 12px",
        paddingLeft: `${12 + depth * 28}px`,
        borderRadius: "var(--radius-sm)",
        border: "1px solid var(--color-border)",
        backgroundColor:
          depth === 0 ? "var(--color-surface-card)" : "var(--color-surface-secondary)",
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        flexWrap: "wrap",
        gap: "10px",
      }}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "8px",
          flexWrap: "wrap",
        }}
      >
        {depth > 0 ? (
          <span
            data-testid={`org-unit-tree-connector-${unit.id}`}
            role="presentation"
            style={{
              fontFamily: "var(--font-mono)",
              fontSize: "13px",
              fontWeight: 700,
              color: "var(--color-primary-cobalt)",
            }}
          >
            └─
          </span>
        ) : null}

        <OrciaIcon
          name={unit.level === "TEAM" ? "team" : "organizationBu"}
          size={15}
        />

        <strong
          data-testid={`org-unit-name-${unit.id}`}
          className="text-base font-semibold tracking-tight"
          style={{ color: "var(--color-foreground)" }}
        >
          {unit.name}
        </strong>

        <StatusBadge
          testId={`org-unit-kind-badge-${unit.id}`}
          label={kindLabel}
          tone={kindTone}
        />

        <StatusBadge
          testId={`org-unit-slug-badge-${unit.id}`}
          label={unit.slug}
          tone="neutral"
          monospace
        />

        <span style={{ fontSize: "12px", color: "var(--color-muted-foreground)" }}>
          {parentNode
            ? `↳ ${labels.badges.parentAttachmentPrefix} ${parentNode.name}`
            : `↳ ${labels.badges.rootAttachment}`}
        </span>

        {attachedTeamsCount > 0 ? (
          <span style={{ fontSize: "11px", color: "var(--color-muted-foreground)" }}>
            {`(${attachedTeamsLabel})`}
          </span>
        ) : null}
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: "6px", flexWrap: "wrap" }}>
        {(() => {
          const effectiveLeads = Array.isArray(unit.leadUserIds) && unit.leadUserIds.length > 0
            ? unit.leadUserIds
            : (unit.leadUserId ? [unit.leadUserId] : []);
          if (effectiveLeads.length === 0) return null;
          if (effectiveLeads.length === 1) {
            const leadId = effectiveLeads[0];
            const leadUser = knownUsers.find(
              (u) =>
                u.principalId.toLowerCase() === leadId.toLowerCase() ||
                (u.email && u.email.toLowerCase() === leadId.toLowerCase()),
            );
            const leadLabelText =
              leadUser && leadUser.displayName && leadUser.displayName !== leadId
                ? `${labels.badges.leadPrefix} ${leadUser.displayName} (${leadId})`
                : `${labels.badges.leadPrefix} ${leadId}`;
            return (
              <StatusBadge
                testId={`org-unit-lead-badge-${unit.id}`}
                label={leadLabelText}
                tone="neutral"
              />
            );
          }
          const leadNames = effectiveLeads.map((lid) => {
            const u = knownUsers.find(
              (k) =>
                k.principalId.toLowerCase() === lid.toLowerCase() ||
                (k.email && k.email.toLowerCase() === lid.toLowerCase()),
            );
            return u?.displayName || lid;
          });
          const pluralPrefix = labels.badges.leadsPluralPrefix;
          return (
            <StatusBadge
              testId={`org-unit-lead-badge-${unit.id}`}
              label={`${pluralPrefix} ${leadNames.join(", ")}`}
              tone="neutral"
            />
          );
        })()}

        {isReadOnlyContext ? (
          <StatusBadge
            testId={`org-unit-readonly-badge-${unit.id}`}
            label={labels.badges.readOnlyAncestor}
            tone="neutral"
          />
        ) : null}

        {(() => {
          const ontoLeads =
            unit.level === "BU" && Array.isArray(unit.ontologyLeadUserIds)
              ? unit.ontologyLeadUserIds
              : [];
          if (ontoLeads.length === 0) return null;
          const names = ontoLeads.map((lid) => {
            const u = knownUsers.find(
              (k) =>
                k.principalId.toLowerCase() === lid.toLowerCase() ||
                (k.email && k.email.toLowerCase() === lid.toLowerCase()),
            );
            return u?.displayName || lid;
          });
          const prefix =
            ontoLeads.length === 1
              ? labels.badges.ontologyLeadPrefix
              : labels.badges.ontologyLeadsPluralPrefix;
          return (
            <StatusBadge
              testId={`org-unit-ontology-lead-badge-${unit.id}`}
              label={`${prefix} ${names.join(", ")}`}
              tone="cobalt"
            />
          );
        })()}

        {unit.level === "TEAM" ? (
          <StatusBadge
            testId={`org-unit-members-count-${unit.id}`}
            label={membersBadgeText}
            tone="neutral"
          />
        ) : null}

        <StatusBadge
          testId={`org-unit-workspaces-count-${unit.id}`}
          label={workspacesBadgeText}
          tone="neutral"
        />

        <StatusBadge
          testId={`org-unit-billing-badge-${unit.id}`}
          label={billingActive ? labels.badges.billingActive : labels.badges.billingDisabled}
          tone={billingActive ? "emerald" : "neutral"}
        />

        <OrciaButton
          variant="secondary"
          testId={`edit-org-unit-btn-${unit.id}`}
          disabled={!rowCanEdit}
          onClick={() => onEdit(unit)}
          style={{ padding: "5px 10px", fontSize: "12px" }}
        >
          {labels.rowActions.edit}
        </OrciaButton>

        {unit.level === "TEAM" ? (
          <OrciaButton
            variant="secondary"
            testId={`manage-members-org-unit-btn-${unit.id}`}
            disabled={!rowCanManageMembers}
            onClick={() => onManageMembers(unit)}
            style={{ padding: "5px 10px", fontSize: "12px" }}
          >
            {labels.rowActions.members}
          </OrciaButton>
        ) : null}

        <OrciaButton
          variant="danger"
          testId={`delete-org-unit-btn-${unit.id}`}
          disabled={!rowCanDelete}
          onClick={() => onRequestDelete(rowItem)}
          style={{ padding: "5px 10px", fontSize: "12px" }}
        >
          {labels.rowActions.delete}
        </OrciaButton>
      </div>
    </div>
  );
}
