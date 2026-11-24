import type { ControlCenterWorkspaceGovItem } from "@orcia/ui";
import { DICTIONARIES, formatI18nTemplate, type SupportedWebLocale } from "../i18n";
import { computeRemoveOrgUnitOutcome, type AppendAuditFn } from "./platformSetupOrgAndGovernance";
import {
  formatHumanReadableScopePath,
  writeCachedPlatformAdmin,
  writeCachedPlatformSetupState,
  type CachedPlatformSetupState,
  type ConfiguredAuditEvent,
  type ConfiguredOrgUnit,
  type ConfiguredPlatformAdmin,
  type ConfiguredRbacGrant,
} from "./platformSetupStorageHelpers";

export interface OrgAndRbacActionsDeps {
  readonly locale: SupportedWebLocale;
  readonly platformAdmin: ConfiguredPlatformAdmin | null;
  readonly orgUnits: readonly ConfiguredOrgUnit[];
  readonly rbacGrants: readonly ConfiguredRbacGrant[];
  readonly workspaces: readonly ControlCenterWorkspaceGovItem[];
  readonly setPlatformAdmin: (admin: ConfiguredPlatformAdmin | null) => void;
  readonly setOrgUnits: (units: readonly ConfiguredOrgUnit[]) => void;
  readonly setRbacGrants: (grants: readonly ConfiguredRbacGrant[]) => void;
  readonly setAuditEvents: (events: readonly ConfiguredAuditEvent[]) => void;
  readonly markMutated: () => void;
  readonly appendAudit: AppendAuditFn;
  readonly buildSnapshot: (
    overrides: Partial<CachedPlatformSetupState>,
  ) => CachedPlatformSetupState;
  readonly persistSnapshot: (next: CachedPlatformSetupState) => void;
}

export function createPlatformOrgAndRbacActions(deps: OrgAndRbacActionsDeps) {
  const {
    locale,
    platformAdmin,
    orgUnits,
    rbacGrants,
    workspaces,
    setPlatformAdmin,
    setOrgUnits,
    setRbacGrants,
    setAuditEvents,
    markMutated,
    appendAudit,
    buildSnapshot,
    persistSnapshot,
  } = deps;
  const copy = DICTIONARIES[locale].shellChrome.platformSetupGovernance;

  const toggleAdminTeamMembership = (teamId: string) => {
    const targetTeam = orgUnits.find((u) => u.id === teamId && u.level === "TEAM");
    if (!targetTeam) return;
    const baseAdmin: ConfiguredPlatformAdmin = platformAdmin ?? {
      displayName: copy.defaultAdminDisplayName,
      email: "admin@orcia.local",
      role: "PLATFORM_ADMIN",
      memberTeamIds: [],
    };
    const currentTeamIds = baseAdmin.memberTeamIds ?? [];
    const isMember = currentTeamIds.includes(teamId);
    const nextTeamIds = isMember
      ? currentTeamIds.filter((id) => id !== teamId)
      : [...currentTeamIds, teamId];
    const updatedAdmin: ConfiguredPlatformAdmin = { ...baseAdmin, memberTeamIds: nextTeamIds };
    writeCachedPlatformAdmin(updatedAdmin);
    setPlatformAdmin(updatedAdmin);
    const nextAudit = appendAudit(
      isMember ? "PermissionRevoked" : "PermissionGranted",
      formatI18nTemplate(
        isMember ? copy.teamDetachedTemplate : copy.teamAttachedTemplate,
        { teamName: targetTeam.name, displayName: updatedAdmin.displayName },
      ),
      {
        scopeId: targetTeam.id,
        scopePath: targetTeam.slug,
        scopeLabel: formatI18nTemplate(copy.teamScopePrefix, { name: targetTeam.name }),
      },
    );
    setAuditEvents(nextAudit);
    persistSnapshot(buildSnapshot({ auditEvents: nextAudit }));
  };

  const addOrgUnit = (
    input: Omit<ConfiguredOrgUnit, "id"> & { readonly attachCurrentAdmin?: boolean },
  ) => {
    const id = orgUnits.length === 0 ? "org-1" : `org-${orgUnits.length + 1}`;
    const newUnit: ConfiguredOrgUnit = {
      id,
      name: input.name,
      slug: input.slug,
      level: input.level,
      parentId: input.parentId,
      billingEnabled: input.billingEnabled ?? true,
      leadUserId: input.leadUserId ?? null,
      memberUserIds: input.memberUserIds ?? [],
      attachedWorkspacesCount: input.attachedWorkspacesCount ?? 0,
    };
    const nextOrgUnits = [...orgUnits, newUnit];
    if (input.level === "TEAM" && input.attachCurrentAdmin !== false && platformAdmin) {
      const currentTeamIds = platformAdmin.memberTeamIds ?? [];
      if (!currentTeamIds.includes(id)) {
        const updatedAdmin = { ...platformAdmin, memberTeamIds: [...currentTeamIds, id] };
        writeCachedPlatformAdmin(updatedAdmin);
        setPlatformAdmin(updatedAdmin);
      }
    }
    const levelLabel = input.level === "BU" ? copy.divisionLabel : copy.teamLabel;
    const nextAudit = appendAudit(
      "OrgUnitCreated",
      formatI18nTemplate(copy.orgUnitCreatedTemplate, {
        levelLabel,
        name: input.name,
        slug: input.slug,
      }),
      { scopeId: id, scopePath: input.slug, scopeLabel: `${levelLabel} · ${input.name}` },
    );
    setOrgUnits(nextOrgUnits);
    setAuditEvents(nextAudit);
    persistSnapshot(buildSnapshot({ orgUnits: nextOrgUnits, auditEvents: nextAudit }));
  };

  const syncOrgUnitsFromServer = (
    units: readonly ConfiguredOrgUnit[],
    auditMeta?: {
      readonly eventType: string;
      readonly summary: string;
      readonly scopeId?: string;
      readonly scopePath?: string;
      readonly scopeLabel?: string;
    },
  ) => {
    setOrgUnits(units);
    if (auditMeta) {
      const nextAudit = appendAudit(auditMeta.eventType, auditMeta.summary, auditMeta);
      setAuditEvents(nextAudit);
      persistSnapshot(buildSnapshot({ orgUnits: units, auditEvents: nextAudit }));
    } else {
      markMutated();
      writeCachedPlatformSetupState(buildSnapshot({ orgUnits: units }));
    }
  };

  const removeOrgUnit = (orgUnitId: string) => {
    const outcome = computeRemoveOrgUnitOutcome({
      orgUnitId,
      orgUnits,
      workspaces,
      rbacGrants,
      platformAdmin,
      appendAudit,
    });
    if (!outcome.deleted || !outcome.nextOrgUnits || !outcome.nextAudit) {
      return { deleted: outcome.deleted, blockedReason: outcome.blockedReason };
    }
    if (outcome.updatedAdmin) {
      writeCachedPlatformAdmin(outcome.updatedAdmin);
      setPlatformAdmin(outcome.updatedAdmin);
    }
    setOrgUnits(outcome.nextOrgUnits);
    setAuditEvents(outcome.nextAudit);
    persistSnapshot(
      buildSnapshot({ orgUnits: outcome.nextOrgUnits, auditEvents: outcome.nextAudit }),
    );
    return { deleted: true, blockedReason: null };
  };

  const addRbacGrant = (input: Omit<ConfiguredRbacGrant, "id">) => {
    const id = rbacGrants.length === 0 ? "grant-1" : `grant-${rbacGrants.length + 1}`;
    const nextRbacGrants = [...rbacGrants, { ...input, id }];
    const readableScope = formatHumanReadableScopePath(input.scopePath, locale);
    const subjectKind = input.subjectType === "ROLE" ? copy.roleLabel : copy.userLabel;
    const nextAudit = appendAudit(
      "PermissionGranted",
      formatI18nTemplate(copy.grantCreatedTemplate, {
        subjectKind,
        subjectId: input.subjectId,
        verb: input.verb,
        scope: readableScope,
      }),
      { scopePath: input.scopePath, scopeLabel: readableScope },
    );
    setRbacGrants(nextRbacGrants);
    setAuditEvents(nextAudit);
    persistSnapshot(buildSnapshot({ rbacGrants: nextRbacGrants, auditEvents: nextAudit }));
  };

  const removeRbacGrant = (grantId: string) => {
    const target = rbacGrants.find((g) => g.id === grantId);
    if (!target) return;
    const nextRbacGrants = rbacGrants.filter((g) => g.id !== grantId);
    const readableScope = formatHumanReadableScopePath(target.scopePath, locale);
    const subjectKind = target.subjectType === "ROLE" ? copy.roleLabel : copy.userLabel;
    const nextAudit = appendAudit(
      "PermissionRevoked",
      formatI18nTemplate(copy.grantRevokedTemplate, {
        subjectKind,
        subjectId: target.subjectId,
        verb: target.verb,
        scope: readableScope,
      }),
      { scopePath: target.scopePath, scopeLabel: readableScope },
    );
    setRbacGrants(nextRbacGrants);
    setAuditEvents(nextAudit);
    persistSnapshot(buildSnapshot({ rbacGrants: nextRbacGrants, auditEvents: nextAudit }));
  };

  const syncRbacGrantsFromServer = (
    grants: readonly ConfiguredRbacGrant[],
    auditMeta?: {
      readonly eventType: string;
      readonly summary: string;
      readonly scopePath?: string;
      readonly scopeLabel?: string;
    },
  ) => {
    setRbacGrants(grants);
    if (auditMeta) {
      const nextAudit = appendAudit(auditMeta.eventType, auditMeta.summary, auditMeta);
      setAuditEvents(nextAudit);
      persistSnapshot(buildSnapshot({ rbacGrants: grants, auditEvents: nextAudit }));
    } else {
      markMutated();
      writeCachedPlatformSetupState(buildSnapshot({ rbacGrants: grants }));
    }
  };

  return {
    toggleAdminTeamMembership,
    addOrgUnit,
    removeOrgUnit,
    syncOrgUnitsFromServer,
    addRbacGrant,
    removeRbacGrant,
    syncRbacGrantsFromServer,
  };
}
