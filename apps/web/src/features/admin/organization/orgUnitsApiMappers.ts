import type { OrgUnitResponse } from "@orcia/api-client";
import type { KnownUserOption } from "@orcia/ui";
import type { ConfiguredOrgUnit } from "../../../components/platformSetupStorageHelpers";

export interface OrgUnitServerCapabilities {
  readonly canEdit: boolean;
  readonly canCreateChild: boolean;
  readonly canDelete: boolean;
  readonly canManageMembers: boolean;
  readonly canManageOntologyLeads: boolean;
  readonly canInviteUsers: boolean;
}

export function extractOrgUnitCapabilities(
  dto: OrgUnitResponse,
): OrgUnitServerCapabilities {
  return {
    canEdit: dto.can_edit ?? true,
    canCreateChild: dto.can_create_child ?? dto.kind === "BU",
    canDelete: dto.can_delete ?? true,
    canManageMembers: dto.can_manage_members ?? dto.kind === "TEAM",
    canManageOntologyLeads: dto.can_manage_ontology_leads ?? dto.kind === "BU",
    canInviteUsers: dto.can_invite_users ?? true,
  };
}

export function mapOrgUnitDtoToConfigured(dto: OrgUnitResponse): ConfiguredOrgUnit {
  const rawLeads = Array.isArray(dto.lead_user_ids) ? dto.lead_user_ids : [];
  const leadUserIds =
    rawLeads.length > 0 ? rawLeads : dto.lead_user_id ? [dto.lead_user_id] : [];
  const ontologyLeadUserIds =
    dto.kind === "BU" && Array.isArray(dto.ontology_lead_user_ids)
      ? dto.ontology_lead_user_ids
      : [];
  return {
    id: dto.id,
    name: dto.name,
    slug: dto.slug,
    level: dto.kind,
    parentId: dto.parent_id ?? "scope-global",
    billingEnabled: dto.billing_enabled ?? true,
    leadUserId: leadUserIds[0] ?? dto.lead_user_id ?? null,
    leadUserIds,
    ontologyLeadUserIds,
    memberUserIds: dto.kind === "BU" ? [] : (dto.member_user_ids ?? []),
    attachedWorkspacesCount: dto.attached_workspaces_count ?? 0,
    attachedWorkspaces: dto.attached_workspaces
      ? dto.attached_workspaces.map((w) => ({ id: w.id, slug: w.slug, name: w.name }))
      : [],
  };
}

export function isKnownUserIdentifier(
  identifier: string,
  knownUsers: readonly KnownUserOption[],
): boolean {
  const trimmed = identifier.trim().toLowerCase();
  if (!trimmed) return true;
  return knownUsers.some(
    (u) =>
      u.principalId.trim().toLowerCase() === trimmed ||
      (u.email ? u.email.trim().toLowerCase() === trimmed : false),
  );
}
