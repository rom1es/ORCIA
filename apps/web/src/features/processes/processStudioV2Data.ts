// Auto-generated & synchronized declarative data for ORCIA Process Studio v2 (Epics 14 & 15)
// Zero raw hex colors (uses Direction C semantic CSS variables exclusively).

export interface ConnectorHealthItem {
  connector_type: string;
  required_scopes: string[];
  used_for: string;
  health: {
    connector_type: string;
    ok: boolean;
    latency_ms: number;
    error_message?: string | null;
  };
}

export interface DeclarativePackItem {
  id: string;
  slug: string;
  name: string;
  version: string;
  description: string;
  rbac_namespace: string;
  bundle_sha256: string;
  agents_count: number;
  skills_count: number;
  gates_count: number;
  vsm_count: number;
  workflows_count: number;
  agents_slugs: string[];
  skills_slugs: string[];
  gates_slugs: string[];
  connector_health: ConnectorHealthItem[];
}

export interface DeterministicSubStepItem {
  id: string;
  name: string;
  short_label: string;
  trigger_condition_label: string;
  role_description: string;
  instruction_prompt_or_ref: string;
  output_description: string;
  mcp_tools_allowed: string[];
  write_preview_required: boolean;
  requires_human_checkpoint: boolean;
  checkpoint_question?: string | null;
  enabled: boolean;
}

export interface WorkflowDefinitionV2Item {
  id: string;
  slug: string;
  title: string;
  pack_id: string;
  vsm_step_num?: string | null;
  version: string;
  status: "draft" | "published" | "archived";
  execution_mode: "native_orcia" | "external_delegated";
  external_tool_label?: string | null;
  external_completion_event?: string | null;
  agent_ref: string;
  skills_refs: string[];
  knowledge_base_refs: string[];
  triggers: Array<{ trigger_type: string; source_label: string; condition_expression?: string | null }>;
  contract: {
    inputs: string[];
    outputs: string[];
    exit_criteria: string[];
    expected_format?: string;
  };
  sub_steps: DeterministicSubStepItem[];
  controls: {
    deterministic_gates: Array<{
      id: string;
      name: string;
      runner: "markdown_contract_runner" | "json_schema_runner" | "cli_sandbox_runner" | "catalog_invariant_runner";
      config: Record<string, unknown>;
      blocking: boolean;
      max_self_heal_retries: number;
    }>;
    probabilistic_evaluations: Array<{
      id: string;
      name: string;
      agent_ref: string;
      rubric_ref: string;
      blocking: boolean;
      trigger_condition: string;
    }>;
  };
  guardrails: string[];
}

export const INITIAL_DECLARATIVE_PACKS: DeclarativePackItem[] = [
  {
    id: "orcia-pack-sdlc",
    slug: "sdlc",
    name: "Pack SDLC — Mon Compte (De l'idée à la production)",
    version: "2.0.0",
    description:
      "Chaîne de valeur complète en 11 étapes et 4 phases avec 4 workflows DBOS bornés, 4 agents spécialisés, 4 skills et 6 gates.",
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
    connector_health: [
      {
        connector_type: "mcp:atlassian-jira",
        required_scopes: ["jira:read", "jira:write"],
        used_for: "Lecture demandes/Epics/US et écriture sous WritePreviewCard",
        health: { connector_type: "mcp:atlassian-jira", ok: true, latency_ms: 14 },
      },
      {
        connector_type: "mcp:atlassian-confluence",
        required_scopes: ["confluence:read", "confluence:write"],
        used_for: "Socle de connaissance, PRD, Dossiers d'étude et fiches de MEP",
        health: { connector_type: "mcp:atlassian-confluence", ok: true, latency_ms: 18 },
      },
      {
        connector_type: "mcp:git-provider",
        required_scopes: ["git:read", "git:write"],
        used_for: "Arborescence du dépôt, branches, Pull Requests et Sas Externe (Étape 08)",
        health: { connector_type: "mcp:git-provider", ok: true, latency_ms: 11 },
      },
    ],
  },
  {
    id: "orcia-pack-docs",
    slug: "orcia-docs",
    name: "Pack Documentation & Aide Contextuelle ORCIA",
    version: "2.0.0",
    description: "Pack déclaratif de génération et validation déterministe de l'aide bilingue FR/EN.",
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
    connector_health: [
      {
        connector_type: "mcp:git-provider",
        required_scopes: ["git:read", "git:write"],
        used_for: "Lecture de l'arborescence et export documentaire",
        health: { connector_type: "mcp:git-provider", ok: true, latency_ms: 11 },
      },
    ],
  },
];

export const INITIAL_VSM_SPEC = {
  "id": "vsm-mon-compte-idea-to-prod",
  "slug": "mon-compte-idea-to-prod",
  "title": "De l’idée à la production",
  "subtitle": "Le workflow agentique de Mon Compte",
  "version": "2.0.0",
  "knowledge_base": {
    "title": "Socle de connaissance",
    "description": "Une source unique, tenue à jour, projetée selon celui qui la lit, humain ou agent. Aujourd’hui la connaissance est éclatée entre huit endroits, dont un seul fait autorité : le code.",
    "feeds_steps": [
      "01",
      "02",
      "03",
      "06",
      "08",
      "09",
      "11"
    ]
  },
  "phases": [
    {
      "num": "01",
      "name": "Émergence & cadrage",
      "goal": "Du besoin aux spécifications",
      "steps_range": "01–04",
      "deliverables_summary": "4 étapes",
      "steps": [
        {
          "num": "01",
          "title": "Funnel",
          "actor_type": "agent",
          "actor_label": "Rovo",
          "status_badge": "Agentifié",
          "summary": "Le sous-agent **Qualification** définit le qui, le quoi, le pourquoi et le périmètre du besoin.",
          "deliverable": "Un besoin qualifié : qui, quoi, pourquoi, périmètre, validé par le PO / PM",
          "attention_point": "Le titre est le seul champ obligatoire. Le rattachement à un epic est recommandé, il dit dans quel chantier le sujet s’inscrit, mais rien ne l’impose. Ni architecte, ni PI cible à ce stade.",
          "linked_workflow_id": "wf-01-qualification-prd",
          "today": {
            "actors": "Le PO / PM, à la main",
            "activities": "Le PO / PM crée le ticket dans Jira. Le titre est le seul champ obligatoire. · Le rattachement à un epic est recommandé, mais rien ne l’impose.",
            "deliverable": "Un ticket avec son titre, une coquille",
            "pain_points": "Aucune, le ticket peut rester une coquille"
          },
          "tomorrow": {
            "actors": "Le sous-agent **Qualification** définit le qui, le quoi, le pourquoi et le périmètre, en allant chercher le contexte dans Confluence, Jira ou sur le web. Le PO / PM valide le bloc STATUT : QUALIFIÉ.",
            "activities": "Le PO / PM décrit son besoin à l’Orchestrateur Produit. · L’orchestrateur confie la qualification au sous-agent, qui cherche le contexte dans Confluence, Jira ou sur le web, lit les documents fournis et repère les parties prenantes. · Le sous-agent formule le qui, le quoi, le pourquoi et le périmètre. L’orchestrateur restitue sa réponse sans la modifier. · Le PO / PM corrige ou complète, tant que le bloc n’est pas validé. · Le PO / PM valide le bloc STATUT : QUALIFIÉ. Sans cette validation, l’orchestrateur ne passe pas à la suite.",
            "deliverable": "Un besoin qualifié : qui, quoi, pourquoi, périmètre, validé par le PO / PM",
            "gains": "Le PO / PM valide le bloc STATUT : QUALIFIÉ"
          },
          "passage_point": null,
          "detail_tabs": {
            "agent_sub_steps": [
              {
                "id": "qualification",
                "name": "Qualification du besoin",
                "shortLabel": "Qualification",
                "trigger": "Départ systématique",
                "role": "Définit le qui, le quoi, le pourquoi et le périmètre.",
                "output": "Le besoin qualifié",
                "humanCheck": "STATUT : QUALIFIÉ"
              }
            ],
            "human_ai_interactions": {
              "initiative": "Un besoin exploré, issu de la discovery",
              "humanValidation": "Le PO / PM valide le bloc STATUT : QUALIFIÉ ; sans cette validation, l’agent ne passe pas à la rédaction du PRD"
            },
            "controls_and_gates": {
              "delegated_to_step_num": "02",
              "delegation_note": "Les contrôles du recueil du besoin portent sur le PRD : ils sont décrits à l’étape 02.",
              "deterministic": [],
              "non_deterministic": []
            },
            "complements_and_missing": [
              "Le titre est le seul champ obligatoire. Le rattachement à un epic est recommandé, il dit dans quel chantier le sujet s’inscrit, mais rien ne l’impose. Ni architecte, ni PI cible à ce stade."
            ],
            "guardrails": [
              "L’IA est un outil de réflexion et un assistant. L’humain est le maître de chacune des actions.",
              "Le PO / PM valide le bloc STATUT : QUALIFIÉ ; sans cette validation, l’agent ne passe pas à la rédaction du PRD"
            ]
          }
        },
        {
          "num": "02",
          "title": "En revue",
          "actor_type": "agent",
          "actor_label": "Rovo",
          "status_badge": "Étape 1 du POC",
          "summary": "**Rédaction PRD** rédige le PRD, puis **Création Jira** crée le ticket Feature dans MCIA.",
          "deliverable": "Le ticket Feature, qui est le PRD : au gabarit, avec KPI, critères d’acceptation, WSJF et effort, sans doublon et prêt pour le comité d’accueil",
          "attention_point": "**Le ticket Feature est le PRD** : c’est ici qu’il se rédige, au niveau suffisant pour décider en comité, le reste étant finalisé à l’étape 04. Les trois champs sont distincts dans Jira, donc extractibles. C’est aussi ici que le périmètre a tendance à gonfler sans que rien ne le signale, et que le PI cible se pose au plus tôt.",
          "linked_workflow_id": "wf-01-qualification-prd",
          "today": {
            "actors": "Le PO / PM. Format libre.",
            "activities": "Le PO / PM rédige la description, les hypothèses de bénéfices et les critères d’acceptation, en format libre. · Il va chercher les inputs UX, juridiques et métier. · Le sujet passe ensuite au comité d’accueil des demandes.",
            "deliverable": "Le ticket Feature, qui est le PRD : description, hypothèses de bénéfices, critères d’acceptation",
            "pain_points": "Comité d’accueil des demandes : métier, technique, managers build et run, PO, architectes"
          },
          "tomorrow": {
            "actors": "Le sous-agent **Rédaction PRD** rédige le PRD Light : KPI, critères d’acceptation, WSJF, effort. Une fois le bloc STATUT : PRD VALIDÉ, le sous-agent **Création Jira** cherche les doublons et crée la Feature dans MCIA, après prévisualisation.",
            "activities": "Après la validation du bloc QUALIFIÉ, l’orchestrateur confie la rédaction au sous-agent. Il cherche des modèles de PRD et des KPI existants, lit la qualification validée et rédige le PRD Light : KPI, critères d’acceptation, WSJF, effort. · L’orchestrateur restitue le PRD sans le modifier. · Le PO / PM valide le bloc STATUT : PRD VALIDÉ. · Le sous-agent cherche les doublons, cible le projet MCIA et les champs requis par le comité, puis prépare le ticket Feature. · Le PO / PM valide la prévisualisation : le ticket Feature est créé. · Le sujet passe ensuite au comité d’accueil des demandes.",
            "deliverable": "Le ticket Feature, qui est le PRD : au gabarit, avec KPI, critères d’acceptation, WSJF et effort, sans doublon et prêt pour le comité d’accueil",
            "gains": "Le PO / PM valide le PRD et la Feature, puis le comité d’accueil décide"
          },
          "passage_point": {
            "decision": "Comité d’accueil des demandes",
            "question": "Le besoin rédigé est pitché devant métier, technique, managers build et run, PO et architectes. En sortie, les architectes prennent le relais, ou le sujet retourne en revue.",
            "actors": "sdlc:committee, sdlc:architect, sdlc:po",
            "possible_outcomes": [
              "Retour vers Étape 02 (corrections)",
              "Retour vers Étape 01 (corrections)",
              "Validation & passage à l'étape suivante"
            ]
          },
          "detail_tabs": {
            "agent_sub_steps": [
              {
                "id": "prd",
                "name": "Rédaction PRD",
                "shortLabel": "PRD",
                "trigger": "Après validation du bloc STATUT : QUALIFIÉ",
                "role": "Rédige le PRD Light : KPI, critères d’acceptation, WSJF, effort.",
                "output": "Le contenu du PRD, validé par le PO / PM",
                "humanCheck": "STATUT : PRD VALIDÉ"
              },
              {
                "id": "jira",
                "name": "Création Jira",
                "shortLabel": "Jira",
                "trigger": "Après validation du bloc STATUT : PRD VALIDÉ",
                "role": "Recherche les doublons et crée la Feature dans le projet MCIA.",
                "output": "Le ticket Feature, qui est le PRD, créé dans le projet MCIA",
                "humanCheck": "Prévisualisation validée, puis création du ticket"
              }
            ],
            "human_ai_interactions": {
              "initiative": "Le ticket, et les inputs à aller chercher : UX, juridique, métier",
              "humanValidation": "Le PO / PM valide le bloc STATUT : PRD VALIDÉ, puis la prévisualisation de la Feature ; le comité d’accueil des demandes décide ensuite"
            },
            "controls_and_gates": {
              "strategy": "fail_fast",
              "sandbox_dry_run": true,
              "deterministic": [
                {
                  "id": "det-02-1",
                  "name": "Script de contrôle des champs",
                  "short_label": "Script : caractères par champ",
                  "status": "hypothese",
                  "runner_plugin_id": "markdown_contract_runner",
                  "verifies_description": "Contrôle le nombre de caractères de chaque champ du ticket Feature.",
                  "on_ko_behavior": "À préciser.",
                  "max_self_heal_retries": 3,
                  "config": {
                    "required_headings": [
                      "# "
                    ],
                    "min_chars_per_section": 20
                  }
                }
              ],
              "non_deterministic": [
                {
                  "id": "ndet-02-1",
                  "name": "Agent challenger du PRD",
                  "short_label": "Agent challenger du PRD",
                  "status": "hypothese",
                  "evaluator_type": "adversarial_agent",
                  "agent_ref": "pack://sdlc/gates/hunter-archi-contradicteur",
                  "risk_threshold": 0.7,
                  "verifies_description": "Vient challenger le PRD sur le fond.",
                  "hypothesis_note": "Hypothèse à confirmer : s’appuyer sur les questions métier que pose l’agent d’étude d’architecture pour améliorer le besoin.",
                  "on_ko_behavior": "À préciser."
                }
              ]
            },
            "complements_and_missing": [
              "**Le ticket Feature est le PRD** : c’est ici qu’il se rédige, au niveau suffisant pour décider en comité, le reste étant finalisé à l’étape 04. Les trois champs sont distincts dans Jira, donc extractibles. C’est aussi ici que le périmètre a tendance à gonfler sans que rien ne le signale, et que le PI cible se pose au plus tôt."
            ],
            "guardrails": [
              "L’IA est un outil de réflexion et un assistant. L’humain est le maître de chacune des actions.",
              "Le PO / PM valide le bloc STATUT : PRD VALIDÉ, puis la prévisualisation de la Feature ; le comité d’accueil des demandes décide ensuite"
            ]
          }
        },
        {
          "num": "03",
          "title": "Cadrage d’architecture",
          "actor_type": "agent",
          "actor_label": "GitHub Copilot",
          "status_badge": "Étape 3 du POC",
          "summary": "L’architecte construit l’étude avec l’agent, outil de réflexion : l’agent questionne, propose et rédige, l’architecte arbitre.",
          "deliverable": "Le dossier d’étude (DE) au gabarit, construit avec l’architecte : solution, relevé de décisions, diagrammes Mermaid, impacts en taille T-shirt, questions encore ouvertes",
          "attention_point": "« Cadrage » désigne ici **le cadrage d’architecture**, et rien d’autre : le terme est connoté dans l’équipe. En sortie, deux instances distinctes : la restitution à l’équipe, systématique, et le comité d’architecture, dont le déclenchement dépend de l’impact du changement.",
          "linked_workflow_id": "wf-03-etude-architecture",
          "today": {
            "actors": "L’architecte référent. Rendu variable selon l’archi, sans estimation.",
            "activities": "L’architecte référent rédige le dossier d’étude dans Confluence. Le rendu varie selon l’architecte, sans estimation. · Il restitue l’étude à l’équipe, puis la porte en comité d’architecture si l’impact le demande.",
            "deliverable": "Le dossier d’étude, dans Confluence",
            "pain_points": "Restitution d’équipe systématique, puis comité d’architecture selon l’impact du changement. RSSI si le sujet est sensible."
          },
          "tomorrow": {
            "actors": "L’architecte construit l’étude avec l’agent **CRL Étude d’architecture**, qui lui sert d’outil de réflexion : l’agent rassemble l’existant, pose les questions que les sources ne tranchent pas, propose des options et rédige. L’architecte arbitre à chaque étape et reste l’auteur de l’étude.",
            "activities": "L’architecte lance l’agent avec la clé du ticket Feature. · L’agent lit le ticket et le socle de connaissance, vérifie dans le code, Confluence et les études existantes, puis analyse l’impact. · Il pose en un seul questionnaire ce que les sources ne disent pas, en commençant par les éléments hors socle. · L’architecte répond au questionnaire. · Point de validation 1 : l’architecte confirme ou corrige la compréhension du besoin et de l’existant. · L’agent conçoit la solution. Si le choix n’est pas tranché, il propose 2 ou 3 options et une recommandation. · Point de validation 2 : l’architecte choisit la solution. · L’agent rédige le dossier d’étude bloc par bloc, et s’arrête après chacun. · Après chaque bloc, l’architecte valide, corrige ou complète. Un bloc validé est figé. · L’agent contrôle le dossier en 14 points et rend compte. · L’architecte relit et complète : l’étude reste la sienne.",
            "deliverable": "Le dossier d’étude (DE) au gabarit, construit avec l’architecte : solution, relevé de décisions, diagrammes Mermaid, impacts en taille T-shirt, questions encore ouvertes",
            "gains": "L’architecte arbitre à chaque point d’étape, puis restitution et comité"
          },
          "passage_point": null,
          "detail_tabs": {
            "agent_sub_steps": [
              {
                "id": "comprendre",
                "name": "Comprendre le besoin et l’existant",
                "shortLabel": "Comprendre",
                "trigger": "Mode « générer », avec une clé ou une URL de ticket",
                "role": "Lit le ticket et le socle en entier, analyse l’impact, vérifie dans le code, puis pose en un seul questionnaire ce que les sources ne disent pas.",
                "output": "Sa compréhension du besoin, de l’existant impacté et des lacunes",
                "humanCheck": "Point de validation 1"
              },
              {
                "id": "concevoir",
                "name": "Concevoir la solution",
                "shortLabel": "Concevoir",
                "trigger": "Après accord sur la compréhension",
                "role": "Conçoit à partir de l’existant. Si le choix n’est pas tranché, propose 2 ou 3 options et une recommandation. Décide et justifie la stack.",
                "output": "La solution retenue, ou les options et la recommandation",
                "humanCheck": "Point de validation 2"
              },
              {
                "id": "rediger",
                "name": "Rédiger par blocs",
                "shortLabel": "Rédiger",
                "trigger": "Après le choix de la solution",
                "role": "Rédige le DE en six blocs, du contexte aux impacts, et s’arrête après chacun.",
                "output": "Le DE, bloc par bloc",
                "humanCheck": "Validation de chaque bloc"
              },
              {
                "id": "controler",
                "name": "Contrôler et rendre compte",
                "shortLabel": "Contrôler",
                "trigger": "Après le dernier bloc",
                "role": "Vérifie le fichier en 14 points (sources, décisions, stack, diagrammes, sommaire, impacts), puis rend compte.",
                "output": "Le DE et le compte rendu : choix de stack, décisions à justifier, questions ouvertes",
                "humanCheck": "L’architecte relit et complète : l’étude reste la sienne"
              }
            ],
            "human_ai_interactions": {
              "initiative": "Le ticket Feature (le PRD), le socle de connaissance CRL, le code de crl-back et crl-front, les études existantes",
              "humanValidation": "L’architecte arbitre à chaque point d’étape : sa compréhension du besoin, le choix de la solution, chaque bloc rédigé. Viennent ensuite la restitution d’équipe et le comité d’architecture."
            },
            "controls_and_gates": {
              "strategy": "fail_fast",
              "sandbox_dry_run": true,
              "deterministic": [],
              "non_deterministic": [
                {
                  "id": "ndet-03-1",
                  "name": "Agent contradicteur",
                  "short_label": "Agent contradicteur",
                  "status": "ajouter",
                  "evaluator_type": "adversarial_agent",
                  "agent_ref": "pack://sdlc/gates/hunter-archi-contradicteur",
                  "risk_threshold": 0.7,
                  "verifies_description": "Relit l’étude générée en position contradictoire et en relève les faiblesses.",
                  "hypothesis_note": null,
                  "on_ko_behavior": "Ses objections reviennent à l’agent CRL Étude d’architecture, qui améliore l’étude ; l’architecte arbitre."
                },
                {
                  "id": "ndet-03-2",
                  "name": "Contrôle final en 14 points",
                  "short_label": "Contrôle final de l’agent",
                  "status": "place",
                  "evaluator_type": "adversarial_agent",
                  "agent_ref": "pack://sdlc/gates/hunter-archi-contradicteur",
                  "risk_threshold": 0.7,
                  "verifies_description": "L’agent vérifie lui-même le DE : sources, décisions, stack, diagrammes, sommaire, impacts.",
                  "hypothesis_note": null,
                  "on_ko_behavior": "L’agent corrige ; une correction qui touche un bloc déjà validé est soumise à l’architecte."
                }
              ]
            },
            "complements_and_missing": [
              "« Cadrage » désigne ici **le cadrage d’architecture**, et rien d’autre : le terme est connoté dans l’équipe. En sortie, deux instances distinctes : la restitution à l’équipe, systématique, et le comité d’architecture, dont le déclenchement dépend de l’impact du changement."
            ],
            "guardrails": [
              "L’IA est un outil de réflexion et un assistant. L’humain est le maître de chacune des actions.",
              "L’architecte arbitre à chaque point d’étape : sa compréhension du besoin, le choix de la solution, chaque bloc rédigé. Viennent ensuite la restitution d’équipe et le comité d’architecture."
            ]
          }
        },
        {
          "num": "04",
          "title": "Finalisation des exigences produit",
          "actor_type": "human",
          "actor_label": "Rovo",
          "status_badge": "Gouvernance Humaine",
          "summary": "Le PRD complet, les maquettes finalisées et les KPI d’observabilité",
          "deliverable": "Le PRD complet, les maquettes finalisées et les KPI d’observabilité",
          "attention_point": "Cette étape et le cadrage d’architecture s’alimentent mutuellement : l’architecte challenge le besoin, le métier le réexprime à la lumière de l’architecture. Les maquettes sont produites par l’équipe UX transverse, deux à trois jours par semaine pour Mon Compte, et doivent être finalisées avant « À prioriser ».",
          "linked_workflow_id": null,
          "today": {
            "actors": "Le PM, le PO et l’architecte, en ateliers. Beaucoup d’allers-retours, sans livrable normé.",
            "activities": "",
            "deliverable": "Les livrables de spécification, à des niveaux de finition variables",
            "pain_points": "À définir : le comité d’architecture valide l’étude, aucune instance ne valide aujourd’hui les exigences produit"
          },
          "tomorrow": {
            "actors": "Il complète le PRD au gabarit et signale ce qui manque, observabilité comprise ; l’équipe tranche.",
            "activities": "",
            "deliverable": "Le PRD complet, les maquettes finalisées et les KPI d’observabilité",
            "gains": "À définir : le comité d’architecture valide l’étude, aucune instance ne valide aujourd’hui les exigences produit"
          },
          "passage_point": {
            "decision": "Restitution d’équipe, comité d’architecture, RSSI",
            "question": "Deux instances distinctes. La restitution d’équipe est systématique côté Mon Compte : l’architecte présente son étude à l’ensemble de l’équipe impliquée. Le comité d’architecture réunit les architectes de la branche, sans l’équipe produit, et n’est pas systématique : sans changement d’architecture il n’y a qu’une information, un changement mineur se traite en peer review, un changement impactant l’écosystème passe en comité et son no-go est bloquant. Le RSSI intervient selon la sensibilité.",
            "actors": "sdlc:committee, sdlc:architect, sdlc:po",
            "possible_outcomes": [
              "Retour vers Étape 03 (corrections)",
              "Retour vers Étape 04 (corrections)",
              "Retour vers Étape 02 (corrections)",
              "Validation & passage à l'étape suivante"
            ]
          },
          "detail_tabs": {
            "agent_sub_steps": [],
            "human_ai_interactions": {
              "initiative": "Le PRD validé au comité d’accueil, et le dossier d’étude d’architecture",
              "humanValidation": "À définir : le comité d’architecture valide l’étude, aucune instance ne valide aujourd’hui les exigences produit"
            },
            "controls_and_gates": {
              "deterministic": [],
              "non_deterministic": []
            },
            "complements_and_missing": [
              "Cette étape et le cadrage d’architecture s’alimentent mutuellement : l’architecte challenge le besoin, le métier le réexprime à la lumière de l’architecture. Les maquettes sont produites par l’équipe UX transverse, deux à trois jours par semaine pour Mon Compte, et doivent être finalisées avant « À prioriser »."
            ],
            "guardrails": [
              "L’IA est un outil de réflexion et un assistant. L’humain est le maître de chacune des actions.",
              "À définir : le comité d’architecture valide l’étude, aucune instance ne valide aujourd’hui les exigences produit"
            ]
          }
        }
      ]
    },
    {
      "num": "02",
      "name": "Priorisation & engagement",
      "goal": "De l’étude au PI engagé",
      "steps_range": "05–06",
      "deliverables_summary": "2 étapes",
      "steps": [
        {
          "num": "05",
          "title": "Éléments de priorisation",
          "actor_type": "human",
          "actor_label": "Humain / Équipe",
          "status_badge": "Gouvernance Humaine",
          "summary": "La valeur et l’effort déjà renseignés dans le ticket Feature, avec le WSJF calculé en 02, à confirmer",
          "deliverable": "La valeur et l’effort déjà renseignés dans le ticket Feature, avec le WSJF calculé en 02, à confirmer",
          "attention_point": "L’étape ne produit pas un ordre de passage, elle produit **les éléments qui permettent de prioriser**. La priorisation arbitre un rang, must, should ou could, et non un go. Une priorisation implicite existe déjà en amont : les architectes étudient pendant un PI ce qui sera réalisé au suivant. Les champs de scoring et leur formule existent déjà dans Jira.",
          "linked_workflow_id": null,
          "today": {
            "actors": "De proche en proche, sans instance dédiée. Champs de scoring inutilisés.",
            "activities": "",
            "deliverable": "La complexité et la valeur, inégalement renseignées",
            "pain_points": "La priorisation elle-même est processée par le train"
          },
          "tomorrow": {
            "actors": "Pas d’agent à cette étape. Le WSJF et l’effort arrivent déjà renseignés dans le ticket Feature, calculés par l’Orchestrateur Produit en 02 ; l’équipe les confirme et la priorisation reste humaine.",
            "activities": "",
            "deliverable": "La valeur et l’effort déjà renseignés dans le ticket Feature, avec le WSJF calculé en 02, à confirmer",
            "gains": "La priorisation elle-même est processée par le train"
          },
          "passage_point": null,
          "detail_tabs": {
            "agent_sub_steps": [],
            "human_ai_interactions": {
              "initiative": "Les sujets actés, et leur estimation macro",
              "humanValidation": "La priorisation elle-même est processée par le train"
            },
            "controls_and_gates": {
              "deterministic": [],
              "non_deterministic": []
            },
            "complements_and_missing": [
              "L’étape ne produit pas un ordre de passage, elle produit **les éléments qui permettent de prioriser**. La priorisation arbitre un rang, must, should ou could, et non un go. Une priorisation implicite existe déjà en amont : les architectes étudient pendant un PI ce qui sera réalisé au suivant. Les champs de scoring et leur formule existent déjà dans Jira."
            ],
            "guardrails": [
              "L’IA est un outil de réflexion et un assistant. L’humain est le maître de chacune des actions.",
              "La priorisation elle-même est processée par le train"
            ]
          }
        },
        {
          "num": "06",
          "title": "Découpage en User Stories",
          "actor_type": "agent",
          "actor_label": "Rovo",
          "status_badge": "Étape 4 du POC",
          "summary": "L’agent analyse, prépare l’Epic, découpe, contrôle puis crée les US ; le PO valide chaque transition.",
          "deliverable": "Un Epic lié à la Feature, et des Stories au gabarit DoR / INVEST, contrôlées puis créées dans Jira sous l’Epic, avec leurs dépendances",
          "attention_point": "Le découpage avant le PIP est conforme à SAFe : sans US, les équipes planifient des sorties de features. Il peut être perdu si la feature ne passe pas, mais c’est exceptionnel.",
          "linked_workflow_id": "wf-06-decoupe-us",
          "today": {
            "actors": "PO et développeurs en refinement, en amont du PIP",
            "activities": "Le PO et les développeurs découpent la feature en US en refinement, avant le PIP. · Les US sont rédigées, parfois estimées. · Le PIP engage ensuite les équipes.",
            "deliverable": "Des US rédigées, parfois estimées",
            "pain_points": "PIP : engagement des équipes du train, au deuxième jour"
          },
          "tomorrow": {
            "actors": "L’**Agent US** analyse la Feature, le PRD et l’étude, retrouve ou prépare l’Epic, propose un plan de découpage puis rédige les US au gabarit DoR / INVEST, les contrôle et les crée dans Jira. Le PO valide chaque transition.",
            "activities": "Le PO donne à l’Agent US la clé de la Feature à découper. · Le sous-agent lit la Feature, le PRD et l’étude d’architecture, en fait la synthèse et relève les questions. · Le PO répond aux questions. · Le PO valide l’analyse. · Le sous-agent cherche un Epic existant pour la Feature. Sinon, il prépare sa création et le lie à la Feature. · Le PO confirme la création de l’Epic (« fait », « ok »). · Le sous-agent propose un plan de découpage, la liste des US. · Le PO valide le plan. · Le sous-agent rédige chaque US au gabarit DoR / INVEST. Le sous-agent Contrôle les évalue aussitôt et rend un verdict OK ou KO, avec un tableau d’écarts. · Après un contrôle OK, le PO valide explicitement (« je valide »). · Le sous-agent crée les Stories sous l’Epic et lie leurs dépendances. · Le PO confirme la création (« fait », « ok »).",
            "deliverable": "Un Epic lié à la Feature, et des Stories au gabarit DoR / INVEST, contrôlées puis créées dans Jira sous l’Epic, avec leurs dépendances",
            "gains": "Le PO valide chaque transition de l’agent, puis le PIP engage les équipes"
          },
          "passage_point": {
            "decision": "PIP, deux jours",
            "question": "Une centaine de personnes, deux jours. Les dépendances entre équipes sont traitées, les US positionnées dans les itérations, et les features retenues passent à « Prêt » au deuxième jour.",
            "actors": "sdlc:committee, sdlc:architect, sdlc:po",
            "possible_outcomes": [
              "Retour vers Étape 06 (corrections)",
              "Retour vers Étape 04 (corrections)",
              "Validation & passage à l'étape suivante"
            ]
          },
          "detail_tabs": {
            "agent_sub_steps": [
              {
                "id": "analyse",
                "name": "Analyse",
                "shortLabel": "Analyse",
                "trigger": "Dès qu’on lui donne la clé d’une Feature, ou pour reprendre l’analyse après des retours",
                "role": "Lit la Feature, le PRD et l’étude d’architecture, en fait la synthèse et relève les zones d’ombre et les questions (R, C, Q).",
                "output": "La synthèse et les questions",
                "humanCheck": "Analyse validée"
              },
              {
                "id": "epic",
                "name": "Créateur d’Epic",
                "shortLabel": "Epic",
                "trigger": "Une fois l’analyse validée et les réponses obtenues",
                "role": "Cherche si un Epic existe déjà pour la Feature. Sinon, prépare sa création, sans parent, et le lie à la Feature.",
                "output": "L’Epic prêt, lié à la Feature",
                "humanCheck": "Epic créé"
              },
              {
                "id": "decoupe",
                "name": "Découpe US",
                "shortLabel": "Découpe",
                "trigger": "Dès que l’Epic est prêt, ou pour réviser le plan ou les US",
                "role": "Propose d’abord un plan de découpage, la liste des US. Après accord sur le plan, rédige chaque US selon le gabarit DoR / INVEST.",
                "output": "Les US détaillées",
                "humanCheck": "Contrôle lancé"
              },
              {
                "id": "controle",
                "name": "Contrôle",
                "shortLabel": "Contrôle",
                "trigger": "Automatiquement après la rédaction des US, ou sur demande",
                "role": "Évalue la qualité des US : INVEST, DoR, couverture du PRD. Rend un verdict OK ou KO, avec un tableau d’écarts si des corrections sont nécessaires.",
                "output": "Le verdict et le tableau d’écarts",
                "humanCheck": "Contrôle OK, puis « je valide »"
              },
              {
                "id": "creation",
                "name": "Création",
                "shortLabel": "Création",
                "trigger": "Uniquement après validation explicite, suite à un contrôle OK",
                "role": "Crée les Stories dans Jira avec l’Epic pour parent, puis lie les dépendances entre elles.",
                "output": "Les Stories créées sous l’Epic, avec leurs dépendances",
                "humanCheck": "Le PO confirme la création (« fait », « ok »)"
              }
            ],
            "human_ai_interactions": {
              "initiative": "La clé de la Feature : le ticket Feature (le PRD) et l’étude d’architecture",
              "humanValidation": "Le PO valide l’analyse, le plan de découpage et le contrôle avant toute création dans Jira ; le PIP engage ensuite les équipes, au deuxième jour"
            },
            "controls_and_gates": {
              "strategy": "fail_fast",
              "sandbox_dry_run": true,
              "deterministic": [],
              "non_deterministic": [
                {
                  "id": "ndet-06-1",
                  "name": "Sous-agent Contrôle",
                  "short_label": "Sous-agent Contrôle",
                  "status": "place",
                  "evaluator_type": "adversarial_agent",
                  "agent_ref": "pack://sdlc/gates/hunter-archi-contradicteur",
                  "risk_threshold": 0.7,
                  "verifies_description": "Évalue les US : INVEST, DoR, couverture du PRD. Rend un verdict OK ou KO, avec un tableau d’écarts.",
                  "hypothesis_note": null,
                  "on_ko_behavior": "Le tableau d’écarts sert à réviser les US avec la Découpe US ; rien n’est créé sans contrôle OK et validation du PO."
                }
              ]
            },
            "complements_and_missing": [
              "Le découpage avant le PIP est conforme à SAFe : sans US, les équipes planifient des sorties de features. Il peut être perdu si la feature ne passe pas, mais c’est exceptionnel."
            ],
            "guardrails": [
              "L’IA est un outil de réflexion et un assistant. L’humain est le maître de chacune des actions.",
              "Le PO valide l’analyse, le plan de découpage et le contrôle avant toute création dans Jira ; le PIP engage ensuite les équipes, au deuxième jour"
            ]
          }
        }
      ]
    },
    {
      "num": "03",
      "name": "Réalisation",
      "goal": "Du code à l’US validée",
      "steps_range": "07–09",
      "deliverables_summary": "3 étapes",
      "steps": [
        {
          "num": "07",
          "title": "Refinement US",
          "actor_type": "human",
          "actor_label": "Humain / Équipe",
          "status_badge": "Gouvernance Humaine",
          "summary": "Règles de gestion, scénarios de test, découpage en sous-tâches",
          "deliverable": "Règles de gestion, scénarios de test, découpage en sous-tâches",
          "attention_point": "C’est ici que se pose la question laissée ouverte par l’atelier : jusqu’où va l’UAT fonctionnelle du PO, et où commencent les cas limites de la QA. **Le rôle QA doit être présent à cette étape**, même lorsqu’il est porté par le PO : c’est là que la charge d’automatisation s’estime.",
          "linked_workflow_id": null,
          "today": {
            "actors": "PO et développeurs, en itération",
            "activities": "",
            "deliverable": "Règles de gestion, scénarios de test, découpage en sous-tâches",
            "pain_points": "Le PO et les développeurs, sur les statuts « à valider » et « à corriger ». Le rôle QA devrait y être : c’est ici que les scénarios se construisent."
          },
          "tomorrow": {
            "actors": "Pas d’agent à cette étape. Les US arrivent déjà rédigées au gabarit DoR / INVEST par l’Agent US en 06 ; PO et développeurs les affinent en itération.",
            "activities": "",
            "deliverable": "Règles de gestion, scénarios de test, découpage en sous-tâches",
            "gains": "Le PO et les développeurs, sur les statuts « à valider » et « à corriger ». Le rôle QA devrait y être : c’est ici que les scénarios se construisent."
          },
          "passage_point": null,
          "detail_tabs": {
            "agent_sub_steps": [],
            "human_ai_interactions": {
              "initiative": "L’US issue du découpage, déjà au gabarit DoR / INVEST avec ses critères d’acceptation",
              "humanValidation": "Le PO et les développeurs, sur les statuts « à valider » et « à corriger ». Le rôle QA devrait y être : c’est ici que les scénarios se construisent."
            },
            "controls_and_gates": {
              "deterministic": [],
              "non_deterministic": []
            },
            "complements_and_missing": [
              "C’est ici que se pose la question laissée ouverte par l’atelier : jusqu’où va l’UAT fonctionnelle du PO, et où commencent les cas limites de la QA. **Le rôle QA doit être présent à cette étape**, même lorsqu’il est porté par le PO : c’est là que la charge d’automatisation s’estime."
            ],
            "guardrails": [
              "L’IA est un outil de réflexion et un assistant. L’humain est le maître de chacune des actions.",
              "Le PO et les développeurs, sur les statuts « à valider » et « à corriger ». Le rôle QA devrait y être : c’est ici que les scénarios se construisent."
            ]
          }
        },
        {
          "num": "08",
          "title": "Développement",
          "actor_type": "human",
          "actor_label": "GitHub Copilot",
          "status_badge": "Étape 5 du POC",
          "summary": "Le code, puis une pull request, même sortie, même exigence",
          "deliverable": "Le code, puis une pull request, même sortie, même exigence",
          "attention_point": "Certaines tâches resteront hors de portée (provisionner une base, ouvrir un topic) et le POC met ces limites en exergue : **c’est un résultat attendu**.",
          "linked_workflow_id": "wf-08-dev-external-gate",
          "today": {
            "actors": "Le développeur assigné, en local",
            "activities": "",
            "deliverable": "Le code, puis une pull request",
            "pain_points": "Revue du Dev : un développeur qui n’a pas codé la tâche relit, jamais déléguée"
          },
          "tomorrow": {
            "actors": "Il développe ; le développeur pilote, corrige et assume.",
            "activities": "",
            "deliverable": "Le code, puis une pull request, même sortie, même exigence",
            "gains": "Revue du Dev : un développeur qui n’a pas codé la tâche relit, jamais déléguée"
          },
          "passage_point": {
            "decision": "Revue du Dev",
            "question": "Un développeur qui n’a pas codé la tâche relit et autorise le merge. C’est la seule gate que le POC ne cherche pas à déplacer.",
            "actors": "sdlc:committee, sdlc:architect, sdlc:po",
            "possible_outcomes": [
              "Retour vers Étape 08 (corrections)",
              "Validation & passage à l'étape suivante"
            ]
          },
          "detail_tabs": {
            "agent_sub_steps": [],
            "human_ai_interactions": {
              "initiative": "Les US, l’étude, et les standards de l’équipe",
              "humanValidation": "Revue du Dev : un développeur qui n’a pas codé la tâche relit, jamais déléguée"
            },
            "controls_and_gates": {
              "deterministic": [],
              "non_deterministic": []
            },
            "complements_and_missing": [
              "Certaines tâches resteront hors de portée (provisionner une base, ouvrir un topic) et le POC met ces limites en exergue : **c’est un résultat attendu**."
            ],
            "guardrails": [
              "L’IA est un outil de réflexion et un assistant. L’humain est le maître de chacune des actions.",
              "Revue du Dev : un développeur qui n’a pas codé la tâche relit, jamais déléguée"
            ]
          }
        },
        {
          "num": "09",
          "title": "Recette",
          "actor_type": "human",
          "actor_label": "GitHub Copilot",
          "status_badge": "Cas d’usage du POC",
          "summary": "L’US validée, et une bibliothèque de tests qui s’enrichit d’elle-même",
          "deliverable": "L’US validée, et une bibliothèque de tests qui s’enrichit d’elle-même",
          "attention_point": "Le merge précède la validation métier : une US mergée entre dans la release avant que le QA et le PO ne l’aient validée. **Ce n’est pas un défaut d’outil, c’est un choix de flux**, mais il détermine où une gate a un effet réel. La génération des scénarios est un cas d’usage du POC.",
          "linked_workflow_id": null,
          "today": {
            "actors": "L’équipe QA, transverse aux équipes, déroule les scénarios",
            "activities": "",
            "deliverable": "L’US validée, puis passée en attente de MEP",
            "pain_points": "Test QA par l’équipe QA transverse, revue fonctionnelle par l’architecte, démo validée en comité BO & PM, puis PO review"
          },
          "tomorrow": {
            "actors": "Il génère les scénarios et, après chaque bug non couvert, le scénario manquant ; le QA exécute et arbitre.",
            "activities": "",
            "deliverable": "L’US validée, et une bibliothèque de tests qui s’enrichit d’elle-même",
            "gains": "Test QA par l’équipe QA transverse, revue fonctionnelle par l’architecte, démo validée en comité BO & PM, puis PO review"
          },
          "passage_point": {
            "decision": "PO review",
            "question": "Validation fonctionnelle sur les critères d’acceptation, après le test QA sur l’environnement de recette.",
            "actors": "sdlc:committee, sdlc:architect, sdlc:po",
            "possible_outcomes": [
              "Retour vers Étape 08 (corrections)",
              "Retour vers Étape 07 (corrections)",
              "Validation & passage à l'étape suivante"
            ]
          },
          "detail_tabs": {
            "agent_sub_steps": [],
            "human_ai_interactions": {
              "initiative": "Le package déployé en recette, et les scénarios de test",
              "humanValidation": "Test QA par l’équipe QA transverse, revue fonctionnelle par l’architecte, démo validée en comité BO & PM, puis PO review"
            },
            "controls_and_gates": {
              "deterministic": [],
              "non_deterministic": []
            },
            "complements_and_missing": [
              "Le merge précède la validation métier : une US mergée entre dans la release avant que le QA et le PO ne l’aient validée. **Ce n’est pas un défaut d’outil, c’est un choix de flux**, mais il détermine où une gate a un effet réel. La génération des scénarios est un cas d’usage du POC."
            ],
            "guardrails": [
              "L’IA est un outil de réflexion et un assistant. L’humain est le maître de chacune des actions.",
              "Test QA par l’équipe QA transverse, revue fonctionnelle par l’architecte, démo validée en comité BO & PM, puis PO review"
            ]
          }
        }
      ]
    },
    {
      "num": "04",
      "name": "Livraison",
      "goal": "De la release à la mise en service",
      "steps_range": "10–11",
      "deliverables_summary": "2 étapes",
      "steps": [
        {
          "num": "10",
          "title": "Déploiement",
          "actor_type": "human",
          "actor_label": "Rovo",
          "status_badge": "Gouvernance Humaine",
          "summary": "La même page, pré-remplie et contrôlée, en une fraction du temps",
          "deliverable": "La même page, pré-remplie et contrôlée, en une fraction du temps",
          "attention_point": "Tout ce qu’on y recopie (US, composants impactés, versions) **existe déjà dans Jira**. Le code freeze intervient environ trois semaines avant la MEP, et la recette est figée deux jours.",
          "linked_workflow_id": null,
          "today": {
            "actors": "Écrite à plusieurs mains dans Confluence, complétude vérifiée à l’œil",
            "activities": "",
            "deliverable": "La page de déploiement, et la release figée au code freeze",
            "pain_points": "Release manager et Ops : complétude de la page, puis code freeze"
          },
          "tomorrow": {
            "actors": "Il initialise la page depuis Jira ; l’humain ne complète que ce qui demande un jugement.",
            "activities": "",
            "deliverable": "La même page, pré-remplie et contrôlée, en une fraction du temps",
            "gains": "Release manager et Ops : complétude de la page, puis code freeze"
          },
          "passage_point": {
            "decision": "TNR, perf, intégration, pré-production",
            "question": "Quatre environnements, un go/no-go à chaque passage. Tests de non-régression sur recette figée, tirs de charge, mise à disposition des SI partenaires, puis test de rollback.",
            "actors": "sdlc:committee, sdlc:architect, sdlc:po",
            "possible_outcomes": [
              "Retour vers Étape 08 (corrections)",
              "Retour vers Étape 10 (corrections)",
              "Validation & passage à l'étape suivante"
            ]
          },
          "detail_tabs": {
            "agent_sub_steps": [],
            "human_ai_interactions": {
              "initiative": "Les US de la release, leurs composants, leurs versions",
              "humanValidation": "Release manager et Ops : complétude de la page, puis code freeze"
            },
            "controls_and_gates": {
              "deterministic": [],
              "non_deterministic": []
            },
            "complements_and_missing": [
              "Tout ce qu’on y recopie (US, composants impactés, versions) **existe déjà dans Jira**. Le code freeze intervient environ trois semaines avant la MEP, et la recette est figée deux jours."
            ],
            "guardrails": [
              "L’IA est un outil de réflexion et un assistant. L’humain est le maître de chacune des actions.",
              "Release manager et Ops : complétude de la page, puis code freeze"
            ]
          }
        },
        {
          "num": "11",
          "title": "MEP & mise en service",
          "actor_type": "human",
          "actor_label": "Humain / Équipe",
          "status_badge": "Gouvernance Humaine",
          "summary": "La fonctionnalité en production, puis la restitution de ce qu’elle a produit",
          "deliverable": "La fonctionnalité en production, puis la restitution de ce qu’elle a produit",
          "attention_point": "Une fonctionnalité peut être déployée désactivée puis activée par simple configuration à la date voulue, cela évite une mise en production dédiée. Une restitution suit la mise en service : c’est le moment où l’on regarde ce que la fonctionnalité a réellement produit, et **il n’existe aujourd’hui aucun temps de restitution des KPI au sein du train**.",
          "linked_workflow_id": null,
          "today": {
            "actors": "La system team, sur procédure fournie par les développeurs",
            "activities": "",
            "deliverable": "La fonctionnalité en production, puis la restitution de ce qu’elle a produit",
            "pain_points": "Go/no-go à chaque passage d’environnement : Ops, QA, SI partenaires"
          },
          "tomorrow": {
            "actors": "La system team, sur procédure fournie par les développeurs",
            "activities": "",
            "deliverable": "La fonctionnalité en production, puis la restitution de ce qu’elle a produit",
            "gains": "Go/no-go à chaque passage d’environnement : Ops, QA, SI partenaires"
          },
          "passage_point": null,
          "detail_tabs": {
            "agent_sub_steps": [],
            "human_ai_interactions": {
              "initiative": "Le package validé, et la procédure d’activation",
              "humanValidation": "Go/no-go à chaque passage d’environnement : Ops, QA, SI partenaires"
            },
            "controls_and_gates": {
              "deterministic": [],
              "non_deterministic": []
            },
            "complements_and_missing": [
              "Une fonctionnalité peut être déployée désactivée puis activée par simple configuration à la date voulue, cela évite une mise en production dédiée. Une restitution suit la mise en service : c’est le moment où l’on regarde ce que la fonctionnalité a réellement produit, et **il n’existe aujourd’hui aucun temps de restitution des KPI au sein du train**."
            ],
            "guardrails": [
              "L’IA est un outil de réflexion et un assistant. L’humain est le maître de chacune des actions.",
              "Go/no-go à chaque passage d’environnement : Ops, QA, SI partenaires"
            ]
          }
        }
      ]
    }
  ],
  "return_loops": [
    {
      "id": "loop-02-to-02-0",
      "from_step_num": "02",
      "to_step_num": "02",
      "tier": "primary",
      "reentry_mode": "corrections",
      "trigger_condition": "La demande n’est pas jugée prête : besoin flou, bénéfices non étayés, périmètre trop large.",
      "reason": "Les questions du comité, les informations manquantes, les hypothèses de bénéfices à étayer, un éventuel redécoupage.",
      "impact_summary": "Les remarques sont consignées dans la Feature. L’Orchestrateur Produit reprend au sous-agent Rédaction PRD, qui produit un PRD révisé répondant à chaque remarque et signale celles qui restent ouvertes. Le PO / PM valide de nouveau le bloc STATUT : PRD VALIDÉ avant de re-présenter."
    },
    {
      "id": "loop-02-to-01-1",
      "from_step_num": "02",
      "to_step_num": "01",
      "tier": "secondary",
      "reentry_mode": "corrections",
      "trigger_condition": "La remarque remet en cause la qualification : qui, quoi, pourquoi ou périmètre. L’orchestrateur reprend alors au sous-agent Qualification.",
      "reason": "La remarque remet en cause la qualification : qui, quoi, pourquoi ou périmètre. L’orchestrateur reprend alors au sous-agent Qualification.",
      "impact_summary": ""
    },
    {
      "id": "loop-04-to-03-0",
      "from_step_num": "04",
      "to_step_num": "03",
      "tier": "primary",
      "reentry_mode": "corrections",
      "trigger_condition": "L’étude fait émerger une problématique bloquante, ou le comité d’architecture rend un no-go.",
      "reason": "Les points bloquants, les questions restées ouvertes, les scénarios à approfondir, les exigences du RSSI le cas échéant.",
      "impact_summary": "Les remarques de la restitution et du comité sont rattachées au DE. L’architecte reprend l’étude avec l’agent en mode « corrections » : l’agent intègre chaque remarque, incrémente la version et liste les sections dépendantes à revoir, sans les modifier sans accord. Une section à repenser entièrement passe par le mode « section ». L’architecte arbitre chaque reprise avant le nouveau passage."
    },
    {
      "id": "loop-04-to-04-1",
      "from_step_num": "04",
      "to_step_num": "04",
      "tier": "secondary",
      "reentry_mode": "corrections",
      "trigger_condition": "La remarque porte sur les exigences produit, pas sur l’architecture.",
      "reason": "La remarque porte sur les exigences produit, pas sur l’architecture.",
      "impact_summary": ""
    },
    {
      "id": "loop-04-to-02-2",
      "from_step_num": "04",
      "to_step_num": "02",
      "tier": "secondary",
      "reentry_mode": "corrections",
      "trigger_condition": "La remarque remet en cause le besoin lui-même.",
      "reason": "La remarque remet en cause le besoin lui-même.",
      "impact_summary": ""
    },
    {
      "id": "loop-06-to-06-0",
      "from_step_num": "06",
      "to_step_num": "06",
      "tier": "primary",
      "reentry_mode": "corrections",
      "trigger_condition": "Les équipes ne s’engagent pas : découpage incomplet, dépendances non traitées.",
      "reason": "Les dépendances relevées entre équipes, les US manquantes ou trop larges, les questions des équipes.",
      "impact_summary": "Les remarques du PIP sont rattachées à la Feature. Le PO relance l’Agent US : la Découpe US révise le plan ou les US à partir des remarques, le Contrôle les vérifie de nouveau, et rien n’est créé sans validation. Le découpage révisé est prêt pour le PI suivant."
    },
    {
      "id": "loop-06-to-04-1",
      "from_step_num": "06",
      "to_step_num": "04",
      "tier": "secondary",
      "reentry_mode": "corrections",
      "trigger_condition": "Les exigences ne suffisent pas pour découper.",
      "reason": "Les exigences ne suffisent pas pour découper.",
      "impact_summary": ""
    },
    {
      "id": "loop-08-to-08-0",
      "from_step_num": "08",
      "to_step_num": "08",
      "tier": "primary",
      "reentry_mode": "corrections",
      "trigger_condition": "La revue demande des corrections.",
      "reason": "Les commentaires de revue, ligne par ligne.",
      "impact_summary": "Les commentaires de la pull request deviennent l’entrée de l’itération suivante de l’agent de développement. Le développeur pilote la correction, la revue reste humaine."
    },
    {
      "id": "loop-09-to-08-0",
      "from_step_num": "09",
      "to_step_num": "08",
      "tier": "primary",
      "reentry_mode": "corrections",
      "trigger_condition": "Le résultat ne répond pas aux critères d’acceptation.",
      "reason": "Les écarts constatés, critère par critère.",
      "impact_summary": "L’agent confronte le résultat aux critères et rédige les écarts. Selon leur nature, il propose de renvoyer vers le développement ou vers le refinement ; le PO confirme."
    },
    {
      "id": "loop-09-to-07-1",
      "from_step_num": "09",
      "to_step_num": "07",
      "tier": "secondary",
      "reentry_mode": "corrections",
      "trigger_condition": "Le critère d’acceptation lui-même est ambigu ou incomplet.",
      "reason": "Le critère d’acceptation lui-même est ambigu ou incomplet.",
      "impact_summary": ""
    },
    {
      "id": "loop-10-to-08-0",
      "from_step_num": "10",
      "to_step_num": "08",
      "tier": "primary",
      "reentry_mode": "corrections",
      "trigger_condition": "Une anomalie bloquante apparaît en non-régression, en charge, en intégration ou en pré-production.",
      "reason": "L’anomalie, l’environnement concerné, le scénario qui l’a révélée.",
      "impact_summary": "Le scénario qui a révélé l’anomalie rejoint la bibliothèque de tests ; la correction repart du développement avec ce scénario en entrée."
    },
    {
      "id": "loop-10-to-10-1",
      "from_step_num": "10",
      "to_step_num": "10",
      "tier": "secondary",
      "reentry_mode": "corrections",
      "trigger_condition": "Le problème vient de la page de déploiement ou de la procédure, pas du code.",
      "reason": "Le problème vient de la page de déploiement ou de la procédure, pas du code.",
      "impact_summary": ""
    }
  ],
  "opportunities": [
    {
      "priority": "P1",
      "target_steps": "O2, O18",
      "title": "Affiner le contenu d’une feature",
      "description": "Normer ce qu’on attend d’une revue : description, hypothèses de bénéfices, critères d’acceptation. Les trois champs existent déjà dans Jira et sont extractibles, il manque un gabarit et un ordre de grandeur de ce qu’est une feature acceptable. — Débloque : La priorisation en aval, et l’entrée de toute la chaîne agentique : c’est le premier texte que l’agent lira."
    },
    {
      "priority": "P2",
      "target_steps": "O12, O13, C10",
      "title": "Affiner le contenu d’une User Story",
      "description": "Structurer les critères d’acceptation dans un format lisible par un agent, du type « étant donné, quand, alors », et en dériver les scénarios de recette. Concerne le refinement et la recette. — Débloque : La génération des scénarios de recette, le scénario manquant après un bug de production, et une PO review outillable."
    },
    {
      "priority": "P3",
      "target_steps": "O9",
      "title": "Écrire automatiquement les User Stories",
      "description": "Générer les US au gabarit à partir de l’étude d’architecture et du besoin, pour que le refinement devienne une relecture. — Débloque : La création directe des tickets sans copier-coller, et un contexte déjà branché (epics, Confluence, maquettes) qui évite de recharger le prompt à chaque fois."
    }
  ]
};

export const INITIAL_WORKFLOWS_V2: WorkflowDefinitionV2Item[] = [
  {
    "id": "wf-01-qualification-prd",
    "slug": "wf-01-qualification-prd",
    "title": "Qualification de demande, Rédaction PRD & Création Feature Jira",
    "pack_id": "orcia-pack-sdlc",
    "vsm_step_num": "01",
    "version": "1.0.0",
    "status": "published",
    "execution_mode": "native_orcia",
    "external_tool_label": null,
    "external_completion_event": null,
    "agent_ref": "pack://sdlc/agents/orchestrateur-produit.md",
    "skills_refs": [
      "pack://sdlc/skills/qualification-besoin",
      "pack://sdlc/skills/redaction-prd-wsjf"
    ],
    "knowledge_base_refs": [
      "pack://sdlc/agents/crl-socle-generateur.md"
    ],
    "triggers": [
      {
        "trigger_type": "vsm_step_entry",
        "source_label": "Entrée Étape VSM 01, 02",
        "condition_expression": "STATUT_PRECEDENT == VALIDE"
      }
    ],
    "contract": {
      "inputs": [
        "demande_source (Expression initiale du besoin ou ticket d'entrée)"
      ],
      "outputs": [
        "# PRD",
        "## Contexte",
        "## Objectifs & KPI",
        "## Critères d'acceptation",
        "## WSJF"
      ],
      "exit_criteria": [
        "Gates déterministes PASS (auto-heal <= 3)",
        "Signature Anchor Card"
      ],
      "expected_format": "markdown"
    },
    "sub_steps": [
      {
        "id": "qualification",
        "name": "Qualification du besoin",
        "short_label": "Qualification",
        "trigger_condition_label": "Départ systématique",
        "role_description": "Définit le qui, le quoi, le pourquoi et le périmètre.",
        "instruction_prompt_or_ref": "pack://sdlc/agents/orchestrateurProduit#qualification",
        "output_description": "Le besoin qualifié",
        "mcp_tools_allowed": [
          "mcp:atlassian-confluence (read)"
        ],
        "write_preview_required": false,
        "requires_human_checkpoint": true,
        "checkpoint_question": "validé par le PO / PM",
        "enabled": true
      },
      {
        "id": "prd",
        "name": "Rédaction PRD",
        "short_label": "PRD",
        "trigger_condition_label": "Après validation du bloc STATUT : QUALIFIÉ",
        "role_description": "Rédige le PRD Light : KPI, critères d’acceptation, WSJF, effort.",
        "instruction_prompt_or_ref": "pack://sdlc/agents/orchestrateurProduit#prd",
        "output_description": "Le contenu du PRD, validé par le PO / PM",
        "mcp_tools_allowed": [
          "mcp:atlassian-confluence (read)"
        ],
        "write_preview_required": false,
        "requires_human_checkpoint": true,
        "checkpoint_question": "validé par le PO / PM",
        "enabled": true
      },
      {
        "id": "jira",
        "name": "Création Jira",
        "short_label": "Jira",
        "trigger_condition_label": "Après validation du bloc STATUT : PRD VALIDÉ",
        "role_description": "Recherche les doublons et crée la Feature dans le projet MCIA.",
        "instruction_prompt_or_ref": "pack://sdlc/agents/orchestrateurProduit#jira",
        "output_description": "Le ticket Feature, qui est le PRD, créé dans le projet MCIA",
        "mcp_tools_allowed": [
          "mcp:atlassian-jira (write_preview)"
        ],
        "write_preview_required": true,
        "requires_human_checkpoint": true,
        "checkpoint_question": "Prévisualisation validée, puis création du ticket",
        "enabled": true
      }
    ],
    "controls": {
      "deterministic_gates": [
        {
          "id": "det-02-1",
          "name": "Script de contrôle des champs",
          "runner": "markdown_contract_runner",
          "config": {
            "required_headings": [
              "# "
            ],
            "min_chars_per_section": 20
          },
          "blocking": true,
          "max_self_heal_retries": 3
        }
      ],
      "probabilistic_evaluations": [
        {
          "id": "ndet-02-1",
          "name": "Agent challenger du PRD",
          "agent_ref": "pack://sdlc/gates/hunter-archi-contradicteur",
          "rubric_ref": "Vient challenger le PRD sur le fond.",
          "blocking": false,
          "trigger_condition": "after_deterministic_pass"
        }
      ]
    },
    "guardrails": [
      "Ne jamais sauter une sous-étape sans validation humaine du bloc STATUT.",
      "Toujours exiger une prévisualisation avant création du ticket Feature dans Jira."
    ]
  },
  {
    "id": "wf-03-etude-architecture",
    "slug": "wf-03-etude-architecture",
    "title": "Étude de Cadrage d'Architecture (CRL-Étude-Archi — 4 sous-étapes)",
    "pack_id": "orcia-pack-sdlc",
    "vsm_step_num": "03",
    "version": "1.0.0",
    "status": "published",
    "execution_mode": "native_orcia",
    "external_tool_label": null,
    "external_completion_event": null,
    "agent_ref": "pack://sdlc/agents/crl-etude-archi.md",
    "skills_refs": [
      "pack://sdlc/skills/qualification-besoin",
      "pack://sdlc/skills/redaction-prd-wsjf"
    ],
    "knowledge_base_refs": [
      "pack://sdlc/agents/crl-socle-generateur.md"
    ],
    "triggers": [
      {
        "trigger_type": "vsm_step_entry",
        "source_label": "Entrée Étape VSM 03",
        "condition_expression": "STATUT_PRECEDENT == VALIDE"
      }
    ],
    "contract": {
      "inputs": [
        "prd_valide_uri (PRD validé en Comité d'accueil)"
      ],
      "outputs": [
        "# Dossier d'Étude Architecture",
        "## Contexte & Exigences",
        "## Scénarios d'Architecture",
        "## Impacts Applicatifs",
        "## Sécurité & Résilience"
      ],
      "exit_criteria": [
        "Gates déterministes PASS (auto-heal <= 3)",
        "Signature Anchor Card"
      ],
      "expected_format": "markdown"
    },
    "sub_steps": [
      {
        "id": "comprendre",
        "name": "Comprendre le besoin et l’existant",
        "short_label": "Comprendre",
        "trigger_condition_label": "Mode « générer », avec une clé ou une URL de ticket",
        "role_description": "Lit le ticket et le socle en entier, analyse l’impact, vérifie dans le code, puis pose en un seul questionnaire ce que les sources ne disent pas.",
        "instruction_prompt_or_ref": "pack://sdlc/agents/etudeArchi#comprendre",
        "output_description": "Sa compréhension du besoin, de l’existant impacté et des lacunes",
        "mcp_tools_allowed": [
          "mcp:atlassian-confluence (read)"
        ],
        "write_preview_required": false,
        "requires_human_checkpoint": true,
        "checkpoint_question": "l’architecte confirme ou corrige la compréhension",
        "enabled": true
      },
      {
        "id": "concevoir",
        "name": "Concevoir la solution",
        "short_label": "Concevoir",
        "trigger_condition_label": "Après accord sur la compréhension",
        "role_description": "Conçoit à partir de l’existant. Si le choix n’est pas tranché, propose 2 ou 3 options et une recommandation. Décide et justifie la stack.",
        "instruction_prompt_or_ref": "pack://sdlc/agents/etudeArchi#concevoir",
        "output_description": "La solution retenue, ou les options et la recommandation",
        "mcp_tools_allowed": [
          "mcp:atlassian-confluence (read)"
        ],
        "write_preview_required": false,
        "requires_human_checkpoint": true,
        "checkpoint_question": "l’architecte choisit la solution",
        "enabled": true
      },
      {
        "id": "rediger",
        "name": "Rédiger par blocs",
        "short_label": "Rédiger",
        "trigger_condition_label": "Après le choix de la solution",
        "role_description": "Rédige le DE en six blocs, du contexte aux impacts, et s’arrête après chacun.",
        "instruction_prompt_or_ref": "pack://sdlc/agents/etudeArchi#rediger",
        "output_description": "Le DE, bloc par bloc",
        "mcp_tools_allowed": [
          "mcp:atlassian-confluence (read)"
        ],
        "write_preview_required": false,
        "requires_human_checkpoint": true,
        "checkpoint_question": "l’architecte valide, corrige ou complète",
        "enabled": true
      },
      {
        "id": "controler",
        "name": "Contrôler et rendre compte",
        "short_label": "Contrôler",
        "trigger_condition_label": "Après le dernier bloc",
        "role_description": "Vérifie le fichier en 14 points (sources, décisions, stack, diagrammes, sommaire, impacts), puis rend compte.",
        "instruction_prompt_or_ref": "pack://sdlc/agents/etudeArchi#controler",
        "output_description": "Le DE et le compte rendu : choix de stack, décisions à justifier, questions ouvertes",
        "mcp_tools_allowed": [
          "mcp:atlassian-confluence (read)"
        ],
        "write_preview_required": false,
        "requires_human_checkpoint": true,
        "checkpoint_question": "L’architecte relit et complète : l’étude reste la sienne",
        "enabled": true
      }
    ],
    "controls": {
      "deterministic_gates": [],
      "probabilistic_evaluations": [
        {
          "id": "ndet-03-1",
          "name": "Agent contradicteur",
          "agent_ref": "pack://sdlc/gates/hunter-archi-contradicteur",
          "rubric_ref": "Relit l’étude générée en position contradictoire et en relève les faiblesses.",
          "blocking": false,
          "trigger_condition": "after_deterministic_pass"
        },
        {
          "id": "ndet-03-2",
          "name": "Contrôle final en 14 points",
          "agent_ref": "pack://sdlc/gates/hunter-archi-contradicteur",
          "rubric_ref": "L’agent vérifie lui-même le DE : sources, décisions, stack, diagrammes, sommaire, impacts.",
          "blocking": false,
          "trigger_condition": "after_deterministic_pass"
        }
      ]
    },
    "guardrails": [
      "L'architecte reste l'auteur souverain du Dossier d'Étude (DE).",
      "Toute affirmation sur l'existant est vérifiée dans le socle et le code."
    ]
  },
  {
    "id": "wf-06-decoupe-us",
    "slug": "wf-06-decoupe-us",
    "title": "Découpage en Epic & User Stories INVEST (5 sous-étapes)",
    "pack_id": "orcia-pack-sdlc",
    "vsm_step_num": "06",
    "version": "1.0.0",
    "status": "published",
    "execution_mode": "native_orcia",
    "external_tool_label": null,
    "external_completion_event": null,
    "agent_ref": "pack://sdlc/agents/agent-us.md",
    "skills_refs": [
      "pack://sdlc/skills/qualification-besoin",
      "pack://sdlc/skills/redaction-prd-wsjf"
    ],
    "knowledge_base_refs": [
      "pack://sdlc/agents/crl-socle-generateur.md"
    ],
    "triggers": [
      {
        "trigger_type": "vsm_step_entry",
        "source_label": "Entrée Étape VSM 06",
        "condition_expression": "STATUT_PRECEDENT == VALIDE"
      }
    ],
    "contract": {
      "inputs": [
        "feature_key (Clé de la Feature validée (PRD + DA))"
      ],
      "outputs": [
        "# Découpage en User Stories",
        "## Epic",
        "## User Stories",
        "## Critères d'acceptation"
      ],
      "exit_criteria": [
        "Gates déterministes PASS (auto-heal <= 3)",
        "Signature Anchor Card"
      ],
      "expected_format": "markdown"
    },
    "sub_steps": [
      {
        "id": "analyse",
        "name": "Analyse",
        "short_label": "Analyse",
        "trigger_condition_label": "Dès qu’on lui donne la clé d’une Feature, ou pour reprendre l’analyse après des retours",
        "role_description": "Lit la Feature, le PRD et l’étude d’architecture, en fait la synthèse et relève les zones d’ombre et les questions (R, C, Q).",
        "instruction_prompt_or_ref": "pack://sdlc/agents/agentUS#analyse",
        "output_description": "La synthèse et les questions",
        "mcp_tools_allowed": [
          "mcp:atlassian-confluence (read)"
        ],
        "write_preview_required": false,
        "requires_human_checkpoint": true,
        "checkpoint_question": "le PO répond aux questions",
        "enabled": true
      },
      {
        "id": "epic",
        "name": "Créateur d’Epic",
        "short_label": "Epic",
        "trigger_condition_label": "Une fois l’analyse validée et les réponses obtenues",
        "role_description": "Cherche si un Epic existe déjà pour la Feature. Sinon, prépare sa création, sans parent, et le lie à la Feature.",
        "instruction_prompt_or_ref": "pack://sdlc/agents/agentUS#epic",
        "output_description": "L’Epic prêt, lié à la Feature",
        "mcp_tools_allowed": [
          "mcp:atlassian-confluence (read)"
        ],
        "write_preview_required": false,
        "requires_human_checkpoint": true,
        "checkpoint_question": "le PO confirme (« fait », « ok »)",
        "enabled": true
      },
      {
        "id": "decoupe",
        "name": "Découpe US",
        "short_label": "Découpe",
        "trigger_condition_label": "Dès que l’Epic est prêt, ou pour réviser le plan ou les US",
        "role_description": "Propose d’abord un plan de découpage, la liste des US. Après accord sur le plan, rédige chaque US selon le gabarit DoR / INVEST.",
        "instruction_prompt_or_ref": "pack://sdlc/agents/agentUS#decoupe",
        "output_description": "Les US détaillées",
        "mcp_tools_allowed": [
          "mcp:atlassian-confluence (read)"
        ],
        "write_preview_required": false,
        "requires_human_checkpoint": true,
        "checkpoint_question": "automatiquement, sans attendre",
        "enabled": true
      },
      {
        "id": "controle",
        "name": "Contrôle",
        "short_label": "Contrôle",
        "trigger_condition_label": "Automatiquement après la rédaction des US, ou sur demande",
        "role_description": "Évalue la qualité des US : INVEST, DoR, couverture du PRD. Rend un verdict OK ou KO, avec un tableau d’écarts si des corrections sont nécessaires.",
        "instruction_prompt_or_ref": "pack://sdlc/agents/agentUS#controle",
        "output_description": "Le verdict et le tableau d’écarts",
        "mcp_tools_allowed": [
          "mcp:atlassian-confluence (read)"
        ],
        "write_preview_required": false,
        "requires_human_checkpoint": true,
        "checkpoint_question": "validation explicite du PO",
        "enabled": true
      },
      {
        "id": "creation",
        "name": "Création",
        "short_label": "Création",
        "trigger_condition_label": "Uniquement après validation explicite, suite à un contrôle OK",
        "role_description": "Crée les Stories dans Jira avec l’Epic pour parent, puis lie les dépendances entre elles.",
        "instruction_prompt_or_ref": "pack://sdlc/agents/agentUS#creation",
        "output_description": "Les Stories créées sous l’Epic, avec leurs dépendances",
        "mcp_tools_allowed": [
          "mcp:atlassian-jira (write_preview)"
        ],
        "write_preview_required": true,
        "requires_human_checkpoint": true,
        "checkpoint_question": "Le PO confirme la création (« fait », « ok »)",
        "enabled": true
      }
    ],
    "controls": {
      "deterministic_gates": [],
      "probabilistic_evaluations": [
        {
          "id": "ndet-06-1",
          "name": "Sous-agent Contrôle",
          "agent_ref": "pack://sdlc/gates/hunter-archi-contradicteur",
          "rubric_ref": "Évalue les US : INVEST, DoR, couverture du PRD. Rend un verdict OK ou KO, avec un tableau d’écarts.",
          "blocking": false,
          "trigger_condition": "after_deterministic_pass"
        }
      ]
    },
    "guardrails": [
      "Chaque User Story doit respecter la Definition of Ready (DoR) et le format Gherkin.",
      "Prévisualisation obligatoire avant création par lot dans Jira."
    ]
  },
  {
    "id": "wf-08-dev-external-gate",
    "slug": "wf-08-dev-external-gate",
    "title": "Développement Assisté IDE & Sas de Contrôle Externe avant Revue du Dev",
    "pack_id": "orcia-pack-sdlc",
    "vsm_step_num": "08",
    "version": "1.0.0",
    "status": "published",
    "execution_mode": "external_delegated",
    "external_tool_label": "GitHub Copilot / Claude Code dans l'IDE",
    "external_completion_event": "git:pr_opened",
    "agent_ref": "pack://sdlc/agents/crl-socle-generateur.md",
    "skills_refs": [
      "pack://sdlc/skills/decoupe-us-invest"
    ],
    "knowledge_base_refs": [
      "confluence://mon-compte/socle-architecture"
    ],
    "triggers": [
      {
        "trigger_type": "vsm_step_entry",
        "source_label": "Entrée Étape VSM 08",
        "condition_expression": "STATUT_PRECEDENT == VALIDE"
      }
    ],
    "contract": {
      "inputs": [
        "us_key (User Story prête (DoR) engagée dans le sprint)"
      ],
      "outputs": [
        "# Rapport de Sas Externe PR"
      ],
      "exit_criteria": [
        "Gates déterministes PASS (auto-heal <= 3)",
        "Signature Anchor Card"
      ],
      "expected_format": "markdown"
    },
    "sub_steps": [
      {
        "id": "expose-mcp-context",
        "name": "Exposition du Paquet de Contexte MCP à l'IDE",
        "short_label": "Contexte MCP",
        "trigger_condition_label": "Sélection de l'US par le développeur",
        "role_description": "Assembler l'US, le DA, le PRD et les conventions d'équipe en bundle MCP.",
        "instruction_prompt_or_ref": "Expose MCP context bundle for IDE assistant.",
        "output_description": "Paquet de contexte MCP prêt pour l'IDE",
        "mcp_tools_allowed": [
          "mcp:git-provider (read)"
        ],
        "write_preview_required": false,
        "requires_human_checkpoint": false,
        "checkpoint_question": "Contexte exposé",
        "enabled": true
      },
      {
        "id": "external-pr-gatekeeper",
        "name": "Sas de Contrôle ORCIA sur la Pull Request soumise",
        "short_label": "Sas PR",
        "trigger_condition_label": "Réception du webhook git:pr_opened",
        "role_description": "Exécuter les contrôles déterministes et contradictoires sur le diff de la PR.",
        "instruction_prompt_or_ref": "Vérifier l'alignement du diff PR avec les critères d'acceptation de l'US et le DA.",
        "output_description": "Rapport d'audit pré-Revue du Dev",
        "mcp_tools_allowed": [
          "mcp:git-provider (read)"
        ],
        "write_preview_required": false,
        "requires_human_checkpoint": true,
        "checkpoint_question": "Passage en Revue du Dev",
        "enabled": true
      }
    ],
    "controls": {
      "deterministic_gates": [
        {
          "id": "det-08-pr-contract",
          "name": "Contrat de conformité Pull Request & Tests",
          "runner": "markdown_contract_runner",
          "config": {
            "required_headings": [
              "# Rapport de Sas Externe PR"
            ],
            "min_chars_per_section": 15,
            "forbid_patterns": [
              "TODO"
            ]
          },
          "blocking": true,
          "max_self_heal_retries": 3
        }
      ],
      "probabilistic_evaluations": [
        {
          "id": "ndet-08-pr-hunter",
          "name": "Revue contradictoire d'alignement US / DA",
          "agent_ref": "pack://sdlc/gates/hunter-archi-contradicteur",
          "rubric_ref": "Vérifie que l'implémentation respecte les scénarios retenus dans le DA et les critères Gherkin de l'US.",
          "blocking": false,
          "trigger_condition": "after_deterministic_pass"
        }
      ]
    },
    "guardrails": [
      "Aucun merge automatique sans validation humaine en Revue du Dev.",
      "Exécution obligatoire des Gates déterministes et contradictoires à l'ouverture de la PR."
    ]
  },
  {
    "id": "wf-generate-orcia-documentation",
    "slug": "wf-generate-orcia-documentation",
    "title": "Génération & Validation d'Article d'Aide Contextuelle ORCIA",
    "pack_id": "orcia-pack-docs",
    "vsm_step_num": null,
    "version": "2.0.0",
    "status": "published",
    "execution_mode": "native_orcia",
    "external_tool_label": null,
    "external_completion_event": null,
    "agent_ref": "pack://orcia-docs/agents/redacteur-documentation-orcia.md",
    "skills_refs": [
      "pack://orcia-docs/skills/redaction-aide-bilingue"
    ],
    "knowledge_base_refs": [
      "confluence://mon-compte/socle-architecture"
    ],
    "triggers": [
      {
        "trigger_type": "vsm_step_entry",
        "source_label": "Déclenchement manuel / API",
        "condition_expression": "STATUT_PRECEDENT == VALIDE"
      }
    ],
    "contract": {
      "inputs": [
        "help_key (Clé d'aide contextuelle cible (ex: studio.five-blocks))"
      ],
      "outputs": [
        "# ",
        "## Objectif",
        "## Étapes clés"
      ],
      "exit_criteria": [
        "Gates déterministes PASS (auto-heal <= 3)",
        "Signature Anchor Card"
      ],
      "expected_format": "markdown"
    },
    "sub_steps": [
      {
        "id": "draft-bilingual-help",
        "name": "Rédaction bilingue FR/EN par @Redacteur-Documentation-Orcia",
        "short_label": "Rédaction",
        "trigger_condition_label": "Demande de génération d'aide",
        "role_description": "Rédiger la fiche d'aide contextuelle structurée.",
        "instruction_prompt_or_ref": "pack://orcia-docs/agents/redacteur-documentation-orcia.md",
        "output_description": "Fiche Markdown FR/EN",
        "mcp_tools_allowed": [],
        "write_preview_required": false,
        "requires_human_checkpoint": true,
        "checkpoint_question": "Validation éditoriale & rattachement",
        "enabled": true
      }
    ],
    "controls": {
      "deterministic_gates": [
        {
          "id": "det-docs-markdown",
          "name": "Contrat de structure d'aide contextuelle",
          "runner": "markdown_contract_runner",
          "config": {
            "required_headings": [
              "# ",
              "## Objectif",
              "## Étapes clés"
            ],
            "min_chars_per_section": 20,
            "forbid_patterns": [
              "TODO",
              "TBD"
            ]
          },
          "blocking": true,
          "max_self_heal_retries": 3
        }
      ],
      "probabilistic_evaluations": []
    },
    "guardrails": [
      "Toujours produire une version française et une version anglaise alignées.",
      "Ne jamais exposer de secret ou d'URL interne non gouvernée."
    ]
  }
];

const WORKFLOWS_STORAGE_KEY = "orcia.processStudioV2.workflows.v1";
let memoryFallbackWorkflows: WorkflowDefinitionV2Item[] | null = null;

export function resetPersistedWorkflowsV2(): void {
  memoryFallbackWorkflows = null;
  if (typeof window !== "undefined" && typeof window.localStorage?.removeItem === "function") {
    window.localStorage.removeItem(WORKFLOWS_STORAGE_KEY);
  }
}

export function loadPersistedWorkflowsV2(): WorkflowDefinitionV2Item[] {
  if (typeof window !== "undefined" && typeof window.localStorage?.getItem === "function") {
    try {
      const raw = window.localStorage.getItem(WORKFLOWS_STORAGE_KEY);
      if (raw) {
        const parsed = JSON.parse(raw) as WorkflowDefinitionV2Item[];
        if (Array.isArray(parsed) && parsed.length > 0) {
          return parsed;
        }
      }
    } catch {
      // Fallback to memory or initial
    }
  }
  return memoryFallbackWorkflows ?? INITIAL_WORKFLOWS_V2;
}

export function savePersistedWorkflowV2(updated: WorkflowDefinitionV2Item): WorkflowDefinitionV2Item[] {
  const current = loadPersistedWorkflowsV2();
  const idx = current.findIndex((w) => w.id === updated.id || w.slug === updated.slug);
  const next =
    idx >= 0
      ? current.map((w, i) => (i === idx ? updated : w))
      : [...current, updated];
  memoryFallbackWorkflows = next;
  if (typeof window !== "undefined" && typeof window.localStorage?.setItem === "function") {
    try {
      window.localStorage.setItem(WORKFLOWS_STORAGE_KEY, JSON.stringify(next));
    } catch {
      // Memory fallback already updated
    }
  }
  return next;
}
