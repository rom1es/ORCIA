export const HUMAN_TOOL_LABELS: Record<string, { fr: string; en: string }> = {
  "mcp:atlassian-jira (read)": {
    fr: "Jira — Consultation des demandes & tickets",
    en: "Jira — Read requests & issues",
  },
  "mcp:atlassian-jira (write_preview)": {
    fr: "Jira — Création / mise à jour (avec confirmation)",
    en: "Jira — Create / update (with confirmation)",
  },
  "mcp:atlassian-confluence (read)": {
    fr: "Confluence — Lecture du socle documentaire",
    en: "Confluence — Read knowledge base",
  },
  "mcp:atlassian-confluence (write_preview)": {
    fr: "Confluence — Publication de page (avec confirmation)",
    en: "Confluence — Publish page (with confirmation)",
  },
  "mcp:git-provider (read)": {
    fr: "Git — Lecture du code & des Pull Requests",
    en: "Git — Read code & Pull Requests",
  },
  "mcp:git-provider (write_preview)": {
    fr: "Git — Préparation de branche / Pull Request",
    en: "Git — Prepare branch / Pull Request",
  },
};

export const HUMAN_SKILL_LABELS: Record<string, { fr: string; en: string }> = {
  "pack://sdlc/skills/qualification-besoin": {
    fr: "Qualification structurée du besoin",
    en: "Structured Need Qualification",
  },
  "pack://sdlc/skills/redaction-prd-wsjf": {
    fr: "Rédaction du PRD & calcul de priorité (WSJF)",
    en: "PRD Authoring & Priority Scoring (WSJF)",
  },
  "pack://sdlc/skills/diagrammes-mermaid": {
    fr: "Schémas d'architecture & parcours",
    en: "Architecture & Flow Diagrams",
  },
  "pack://sdlc/skills/decoupe-us-invest": {
    fr: "Découpage en User Stories (INVEST & Gherkin)",
    en: "INVEST & Gherkin User Story Splitting",
  },
  "pack://orcia-docs/skills/redaction-aide-bilingue": {
    fr: "Rédaction de guides utilisateurs FR/EN",
    en: "Bilingual FR/EN User Guide Authoring",
  },
};

export const HUMAN_KB_LABELS: Record<string, { fr: string; en: string }> = {
  "pack://sdlc/agents/crl-socle-generateur.md": {
    fr: "Socle de connaissance produit & architecture (Confluence)",
    en: "Product & Architecture Knowledge Base (Confluence)",
  },
  "pack://orcia-docs/agents/redacteur-documentation-orcia.md": {
    fr: "Référentiel documentaire ORCIA",
    en: "ORCIA Documentation Reference",
  },
  "confluence://mon-compte/socle-architecture": {
    fr: "Socle d'architecture Mon Compte",
    en: "My Account Architecture Reference",
  },
};

export interface DelegateAgentOption {
  readonly slug: string;
  readonly labelFr: string;
  readonly labelEn: string;
  readonly roleFr: string;
  readonly roleEn: string;
}

export const AVAILABLE_DELEGATE_AGENTS: readonly DelegateAgentOption[] = [
  {
    slug: "redacteur-documentation-orcia",
    labelFr: "Rédacteur Documentaire ORCIA",
    labelEn: "ORCIA Documentation Writer",
    roleFr: "Rédaction bilingue FR/EN et structuration des guides d'aide",
    roleEn: "Bilingual FR/EN authoring and help guide structuring",
  },
  {
    slug: "orchestrateur-produit",
    labelFr: "Agent Product Owner",
    labelEn: "Product Owner Agent",
    roleFr: "Qualification du besoin, indicateurs de valeur et cadrage produit",
    roleEn: "Need qualification, value metrics, and product framing",
  },
  {
    slug: "crl-etude-archi",
    labelFr: "Agent Architecte d'Étude",
    labelEn: "Architecture Study Agent",
    roleFr: "Analyse d'impacts applicatifs, scénarios et sécurité",
    roleEn: "Application impact analysis, scenarios, and security",
  },
  {
    slug: "agent-us",
    labelFr: "Agent Business Analyst",
    labelEn: "Business Analyst Agent",
    roleFr: "Découpage en User Stories et critères d'acceptation",
    roleEn: "User Story splitting and acceptance criteria",
  },
  {
    slug: "crl-socle-generateur",
    labelFr: "Agent Socle de Connaissance",
    labelEn: "Knowledge Base Agent",
    roleFr: "Synthèse documentaire et consolidation du référentiel",
    roleEn: "Documentation synthesis and reference consolidation",
  },
];
