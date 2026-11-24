export interface RoleDisplayLabels {
  readonly platformAdmin: string;
  readonly secops: string;
  readonly buLead: string;
  readonly teamLead: string;
  readonly ontologyLead: string;
  readonly contributor: string;
  readonly observer: string;
  readonly analystPmPo: string;
  readonly architect: string;
  readonly techLeadDev: string;
  readonly securityCompliance: string;
}

export function resolveUserRoleDisplayLabel(
  roleKey: string,
  roleLabels?: RoleDisplayLabels | Readonly<Record<string, string>>,
): string {
  if (!roleLabels) return roleKey;
  if (roleKey in roleLabels) {
    return (roleLabels as Readonly<Record<string, string>>)[roleKey] ?? roleKey;
  }
  const typed = roleLabels as Partial<RoleDisplayLabels>;
  switch (roleKey) {
    case "PLATFORM_ADMIN":
      return typed.platformAdmin ?? roleKey;
    case "SECOPS":
      return typed.secops ?? roleKey;
    case "BU_LEAD":
    case "BU_DIRECTOR":
      return typed.buLead ?? roleKey;
    case "TEAM_LEAD":
      return typed.teamLead ?? roleKey;
    case "ONTOLOGY_LEAD":
      return typed.ontologyLead ?? roleKey;
    case "CONTRIBUTOR":
      return typed.contributor ?? roleKey;
    case "OBSERVER":
    case "READ_ONLY_OBSERVER":
      return typed.observer ?? roleKey;
    case "ANALYST_PM_PO":
      return typed.analystPmPo ?? roleKey;
    case "ARCHITECT":
      return typed.architect ?? roleKey;
    case "TECH_LEAD_DEV":
      return typed.techLeadDev ?? roleKey;
    case "SECURITY_COMPLIANCE":
      return typed.securityCompliance ?? roleKey;
    default:
      return roleKey;
  }
}

export function computeUserInitials(displayName: string): string {
  const parts = displayName
    .trim()
    .split(/\s+/)
    .filter((p) => p.length > 0);
  if (parts.length === 0) return "OR";
  if (parts.length === 1) return parts[0]!.slice(0, 2).toUpperCase();
  return `${parts[0]![0] ?? ""}${parts[parts.length - 1]![0] ?? ""}`.toUpperCase();
}
