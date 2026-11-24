import type { EditOrgUnitFormValues } from "../features/admin/organization/SettingsOrganizationModalsGroup";
import { DICTIONARIES, formatI18nTemplate, type SupportedWebLocale } from "../i18n";

export function resolveEffectiveLeads(
  leadUserIds?: readonly string[],
  leadUserId?: string | null,
): readonly string[] {
  if (Array.isArray(leadUserIds) && leadUserIds.length > 0) return leadUserIds;
  return leadUserId ? [leadUserId] : [];
}

export function buildOrgUnitPatchPayload(
  values: EditOrgUnitFormValues,
  targetLevel: "BU" | "TEAM" | undefined,
  isTeamLeadOnly: boolean,
) {
  const parentPayload =
    values.parentId && values.parentId !== "scope-global" ? values.parentId : null;
  const effectiveLeads =
    Array.isArray(values.leadUserIds) && values.leadUserIds.length > 0
      ? values.leadUserIds
      : values.leadUserId
        ? [values.leadUserId]
        : undefined;
  return {
    name: values.name,
    ...(isTeamLeadOnly
      ? {}
      : { parent_id: parentPayload, billing_enabled: values.billingEnabled }),
    ...(effectiveLeads !== undefined
      ? { lead_user_id: effectiveLeads[0] ?? null, lead_user_ids: effectiveLeads }
      : {}),
    ...(targetLevel === "BU" && values.ontologyLeadUserIds !== undefined
      ? { ontology_lead_user_ids: [...values.ontologyLeadUserIds] }
      : {}),
  };
}

export interface OrgUnitAuditMeta {
  readonly eventType: string;
  readonly summary: string;
  readonly scopeId?: string;
  readonly scopePath?: string;
  readonly scopeLabel?: string;
}

export function buildOrgUnitAuditMeta(params: {
  readonly locale: SupportedWebLocale;
  readonly action: "created" | "updated" | "membersUpdated" | "deleted";
  readonly level: "BU" | "TEAM";
  readonly id: string;
  readonly name: string;
  readonly slug: string;
  readonly count?: number;
}): OrgUnitAuditMeta {
  const { locale, action, level, id, name, slug, count = 0 } = params;
  const copy = DICTIONARIES[locale].routesAndWizards.orgUnitsActions;
  const levelLabel = level === "BU" ? copy.divisionLabel : copy.teamLabel;

  const eventMap = {
    created: { eventType: "OrgUnitCreated", template: copy.createdTemplate },
    updated: { eventType: "SettingsChanged", template: copy.updatedTemplate },
    membersUpdated: { eventType: "PermissionGranted", template: copy.membersUpdatedTemplate },
    deleted: { eventType: "OrgUnitDeleted", template: copy.deletedTemplate },
  } as const;

  const spec = eventMap[action];
  return {
    eventType: spec.eventType,
    summary: formatI18nTemplate(spec.template, { levelLabel, name, slug, count }),
    scopeId: id,
    scopePath: slug,
    scopeLabel: `${levelLabel} · ${name}`,
  };
}
