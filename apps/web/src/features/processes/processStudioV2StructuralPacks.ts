import { DICTIONARIES, type SupportedWebLocale } from "../../i18n";
import type { DeclarativePackItem } from "./processStudioV2Types";

interface PackStructureSpec {
  readonly id: "orcia-pack-sdlc" | "orcia-pack-docs";
  readonly slug: string;
  readonly version: string;
  readonly rbac_namespace: string;
  readonly bundle_sha256: string;
  readonly agents_count: number;
  readonly skills_count: number;
  readonly gates_count: number;
  readonly vsm_count: number;
  readonly workflows_count: number;
  readonly agents_slugs: readonly string[];
  readonly skills_slugs: readonly string[];
  readonly gates_slugs: readonly string[];
  readonly connectors: ReadonlyArray<{
    readonly connector_type: string;
    readonly required_scopes: readonly string[];
    readonly latency_ms: number;
  }>;
}

const PACK_STRUCTURES: readonly PackStructureSpec[] = [
  {
    id: "orcia-pack-sdlc",
    slug: "sdlc",
    version: "2.0.0",
    rbac_namespace: "pack:sdlc",
    bundle_sha256: "sha256-sdlc-pack-bundle-v2-0000000000000000000000000000000000001",
    agents_count: 4,
    skills_count: 4,
    gates_count: 6,
    vsm_count: 1,
    workflows_count: 4,
    agents_slugs: ["agent-us", "crl-etude-archi", "crl-socle-generateur", "orchestrateur-produit"],
    skills_slugs: ["decoupe-us-invest", "diagrammes-mermaid", "qualification-besoin", "redaction-prd-wsjf"],
    gates_slugs: [
      "det-de-14-points",
      "det-invest-dor",
      "det-prd-fields",
      "hunter-archi-contradicteur",
      "hunter-prd-challenger",
      "hunter-us-controller",
    ],
    connectors: [
      { connector_type: "mcp:atlassian-jira", required_scopes: ["jira:read", "jira:write"], latency_ms: 14 },
      { connector_type: "mcp:atlassian-confluence", required_scopes: ["confluence:read", "confluence:write"], latency_ms: 18 },
      { connector_type: "mcp:git-provider", required_scopes: ["git:read", "git:write"], latency_ms: 11 },
    ],
  },
  {
    id: "orcia-pack-docs",
    slug: "orcia-docs",
    version: "2.0.0",
    rbac_namespace: "pack:orcia-docs",
    bundle_sha256: "sha256-docs-pack-bundle-v2-0000000000000000000000000000000000002",
    agents_count: 1,
    skills_count: 1,
    gates_count: 1,
    vsm_count: 0,
    workflows_count: 1,
    agents_slugs: ["redacteur-documentation-orcia"],
    skills_slugs: ["redaction-aide-bilingue"],
    gates_slugs: ["det-validate-help-article"],
    connectors: [
      { connector_type: "mcp:git-provider", required_scopes: ["git:read", "git:write"], latency_ms: 11 },
    ],
  },
];

export function getInitialDeclarativePacks(locale: SupportedWebLocale = "fr"): DeclarativePackItem[] {
  const dict = DICTIONARIES[locale].processCatalogWorkflows.packs;
  return PACK_STRUCTURES.map((pack) => {
    const copy = dict[pack.id];
    return {
      id: pack.id,
      slug: pack.slug,
      name: copy.name,
      version: pack.version,
      description: copy.description,
      rbac_namespace: pack.rbac_namespace,
      bundle_sha256: pack.bundle_sha256,
      agents_count: pack.agents_count,
      skills_count: pack.skills_count,
      gates_count: pack.gates_count,
      vsm_count: pack.vsm_count,
      workflows_count: pack.workflows_count,
      agents_slugs: [...pack.agents_slugs],
      skills_slugs: [...pack.skills_slugs],
      gates_slugs: [...pack.gates_slugs],
      connector_health: pack.connectors.map((c) => ({
        connector_type: c.connector_type,
        required_scopes: [...c.required_scopes],
        used_for: copy.connectorUsedFor[c.connector_type] ?? c.connector_type,
        health: { connector_type: c.connector_type, ok: true, latency_ms: c.latency_ms },
      })),
    };
  });
}
