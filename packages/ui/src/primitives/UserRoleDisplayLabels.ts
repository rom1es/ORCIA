import type { UiLocalePreference } from "./UserAccountDropdownTypes";

export const ROLE_DISPLAY_LABELS_FR: Record<string, string> = {
  PLATFORM_ADMIN: "Administrateur de la plateforme",
  SECOPS: "Responsable Sécurité & Habilitations",
  BU_LEAD: "Responsable de Direction (BU)",
  BU_DIRECTOR: "Responsable de Direction (BU)",
  TEAM_LEAD: "Responsable d'Équipe",
  ONTOLOGY_LEAD: "Référent Glossaire",
  CONTRIBUTOR: "Contributeur",
  OBSERVER: "Observateur (Lecture seule)",
  READ_ONLY_OBSERVER: "Observateur (Lecture seule)",
  ANALYST_PM_PO: "Product Manager / Métier",
  ARCHITECT: "Architecte",
  TECH_LEAD_DEV: "Référent Technique / Développeur",
  SECURITY_COMPLIANCE: "Sécurité & Conformité",
};

export const ROLE_DISPLAY_LABELS_EN: Record<string, string> = {
  PLATFORM_ADMIN: "Platform Administrator",
  SECOPS: "Security & Access Officer",
  BU_LEAD: "Business Unit Lead",
  BU_DIRECTOR: "Business Unit Lead",
  TEAM_LEAD: "Team Lead",
  ONTOLOGY_LEAD: "Glossary Lead",
  CONTRIBUTOR: "Contributor",
  OBSERVER: "Observer (Read-only)",
  READ_ONLY_OBSERVER: "Observer (Read-only)",
  ANALYST_PM_PO: "Product Manager / Business",
  ARCHITECT: "Architect",
  TECH_LEAD_DEV: "Technical Lead / Developer",
  SECURITY_COMPLIANCE: "Security & Compliance",
};

export function resolveUserRoleDisplayLabel(
  roleKey: string,
  locale: UiLocalePreference = "fr",
): string {
  const map = locale === "en" ? ROLE_DISPLAY_LABELS_EN : ROLE_DISPLAY_LABELS_FR;
  return map[roleKey] ?? roleKey;
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
