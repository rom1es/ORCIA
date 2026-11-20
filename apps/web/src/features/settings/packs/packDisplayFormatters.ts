export function formatPackCounterLabel(
  count: number,
  singularFr: string,
  pluralFr: string,
  singularEn: string,
  pluralEn: string,
  isFr: boolean,
): string {
  if (isFr) {
    return count <= 1 ? singularFr : pluralFr;
  }
  return count === 1 ? singularEn : pluralEn;
}

const KNOWN_CONNECTOR_NAMES: Readonly<Record<string, { fr: string; en: string }>> = {
  "mcp:atlassian-jira": { fr: "Atlassian Jira", en: "Atlassian Jira" },
  "mcp:atlassian-confluence": { fr: "Atlassian Confluence", en: "Atlassian Confluence" },
  "mcp:git-provider": { fr: "Dépôt Git", en: "Git Provider" },
  "mcp:slack": { fr: "Slack", en: "Slack" },
  "mcp:postgresql": { fr: "Base de données", en: "Database" },
  "mcp:email": { fr: "Messagerie SMTP", en: "SMTP Mail" },
};

export function formatConnectorDisplayName(connectorType: string, isFr: boolean): string {
  const normalized = connectorType.trim().toLowerCase();
  const known = KNOWN_CONNECTOR_NAMES[normalized];
  if (known) {
    return isFr ? known.fr : known.en;
  }
  const stripped = normalized
    .replace(/^mcp:/, "")
    .replace(/^atlassian-/, "Atlassian ");
  return stripped
    .split(/[-_]+/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

const SCOPE_LABELS_FR: Readonly<Record<string, string>> = {
  read: "Lecture",
  write_preview: "Écriture sous validation",
  write: "Écriture",
  execute: "Exécution",
};

const SCOPE_LABELS_EN: Readonly<Record<string, string>> = {
  read: "Read",
  write_preview: "Write (with approval)",
  write: "Write",
  execute: "Execute",
};

export function formatConnectorScopes(
  scopes: readonly string[],
  isFr: boolean,
): string {
  const dict = isFr ? SCOPE_LABELS_FR : SCOPE_LABELS_EN;
  return scopes
    .map((scope) => dict[scope.trim().toLowerCase()] ?? scope)
    .join(", ");
}

const KNOWN_PACK_AGENTS: Readonly<Record<string, { fr: string; en: string }>> = {
  "crl-etude-archi": { fr: "Analyste Étude Architecture", en: "Architecture Study Analyst" },
  "crl-dev-backend": { fr: "Développeur Backend", en: "Backend Developer" },
  "crl-qa-audit": { fr: "Auditeur Qualité", en: "Quality Auditor" },
  "sdlc-pm": { fr: "Chef de Produit", en: "Product Manager" },
  "sdlc-architect": { fr: "Architecte Solution", en: "Solution Architect" },
  "sdlc-tech-lead": { fr: "Référent Technique", en: "Tech Lead" },
  "sdlc-qa": { fr: "Responsable Qualité", en: "QA Lead" },
  "doc-writer": { fr: "Rédacteur Guides Utilisateurs", en: "User Guide Author" },
  "doc-reviewer": { fr: "Relecteur Documentation", en: "Documentation Reviewer" },
};

export function formatPackAgentDisplayName(slug: string, isFr: boolean): string {
  const clean = slug.trim();
  const known = KNOWN_PACK_AGENTS[clean];
  if (known) {
    return isFr ? known.fr : known.en;
  }
  const stripped = clean.replace(/^(?:crl|sdlc|orcia)-/, "");
  return stripped
    .split(/[-_]+/)
    .filter(Boolean)
    .map((part) => (part.toLowerCase() === "ia" ? "IA" : part.charAt(0).toUpperCase() + part.slice(1)))
    .join(" ");
}
