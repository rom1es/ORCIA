import type { InstalledBusinessPackItemResponse } from "@orcia/api-client";

export const BUILTIN_INSTALLED_BUSINESS_PACKS: readonly InstalledBusinessPackItemResponse[] = [
  {
    pack_key: "orcia-pack-sdlc",
    pack_slug: "sdlc",
    title: "Ingénierie Logicielle & Cycle de Vie Produit",
    title_en: "Software Engineering & Product Lifecycle",
    version: "0.1.0",
    domain_name: "INGÉNIERIE LOGICIELLE & PRODUIT",
    description:
      "Connecteurs Git, Jira, Confluence et Nexus, processus guidés de spécification et réalisation, revues croisées et suivi de cohérence documentaire.",
    description_en:
      "Git, Jira, Confluence, and Nexus connectors, guided specification and delivery processes, cross-checked reviews, and documentation consistency tracking.",
    workflows_count: 4,
    agents_count: 6,
    is_system_pack: true,
  },
  {
    pack_key: "orcia-pack-builder",
    pack_slug: "pack-builder",
    title: "Atelier de Création & Gouvernance de Packs Métiers",
    title_en: "Business Pack Authoring & Governance Studio",
    version: "0.1.0",
    domain_name: "GOUVERNANCE & MÉTHODOLOGIE",
    description:
      "Conception guidée de nouveaux Packs métiers, simulation d'impact avant évolution, certification des règles métiers et génération de fiches d'aide.",
    description_en:
      "Guided creation of new Business Packs, impact simulation before evolution, business rule certification, and help article generation.",
    workflows_count: 5,
    agents_count: 4,
    is_system_pack: true,
  },
];
