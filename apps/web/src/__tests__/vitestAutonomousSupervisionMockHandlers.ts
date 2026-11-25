export interface MockAutonomousRunRecord {
  run_id: string;
  workspace_id: string;
  workflow_id: string;
  workflow_title: string;
  trigger_id: string | null;
  trigger_label: string;
  trigger_type: string;
  trigger_status: string;
  run_status: string;
  post_hoc_status: string;
  contract_id: string;
  cost_usd: number;
  created_at_iso: string;
  help_resource_id?: string | null;
  previous_version_available?: boolean;
}

export interface MockContextualHelpResolveState {
  route: string;
  active_article: {
    resource_id: string;
    uri: string;
    title: string;
    version: string;
    lang: string;
    layer: "BASE" | "PACK" | "WORKSPACE" | "PERSONAL";
    pack_name?: string | null;
    bound_routes: string[];
    summary_what_for: string;
    step_by_step_items: string[];
    key_terms_items: string[];
    faq_items: string[];
    cas_key: string;
    sha256: string;
    previous_version?: string | null;
  };
  merged_layers: Array<"BASE" | "PACK" | "WORKSPACE" | "PERSONAL">;
  redis_cache_key: string;
  rollback_available: boolean;
  is_autonomous_generated: boolean;
  run_id: string | null;
  contract_label: string | null;
  trigger_label: string | null;
  previous_version_available: boolean;
}

const mockAutonomousRuns: MockAutonomousRunRecord[] = [];
const mockHelpByRoute = new Map<string, MockContextualHelpResolveState>();

export function resetVitestAutonomousSupervisionMockState(): void {
  mockAutonomousRuns.length = 0;
  mockHelpByRoute.clear();
}

export function seedVitestAutonomousSupervisionRuns(
  runs: readonly MockAutonomousRunRecord[],
): void {
  mockAutonomousRuns.length = 0;
  for (const r of runs) {
    mockAutonomousRuns.push({ ...r });
  }
}

export function seedVitestContextualHelpResolve(state: MockContextualHelpResolveState): void {
  mockHelpByRoute.set(state.route, structuredClone(state));
}

export function getVitestAutonomousSupervisionRuns(): MockAutonomousRunRecord[] {
  return mockAutonomousRuns;
}

function restoreHelpRecordsForRunOrResource(
  runId: string,
  helpResourceId: string | null,
): string {
  let restoredVersion = "1.0.0";
  for (const [route, help] of mockHelpByRoute.entries()) {
    const matchesRun = help.run_id === runId;
    const matchesRes =
      helpResourceId !== null && help.active_article.resource_id === helpResourceId;
    if (matchesRun || matchesRes) {
      restoredVersion = help.active_article.previous_version ?? "1.0.0";
      mockHelpByRoute.set(route, {
        ...help,
        active_article: {
          ...help.active_article,
          version: restoredVersion,
          previous_version: null,
        },
        rollback_available: false,
        is_autonomous_generated: false,
        run_id: null,
        contract_label: null,
        trigger_label: null,
        previous_version_available: false,
      });
    }
  }
  return restoredVersion;
}

export function handleVitestAutonomousSupervisionRoute(
  path: string,
  method: string,
  body: Record<string, unknown>,
  jsonResponse: (data: unknown, status?: number) => Response,
  searchParams?: URLSearchParams,
): Response | null {
  if (path === "/api/v1/autonomous-runs" && method === "GET") {
    const scopeId = searchParams?.get("scope_id");
    const runs = scopeId
      ? mockAutonomousRuns.filter((r) => r.workspace_id === scopeId || mockAutonomousRuns.length > 0)
      : [...mockAutonomousRuns];
    return jsonResponse({
      workspace_id: null,
      runs,
      trace_id: "0195f000000070008000000000007401",
    });
  }

  const listMatch = /^\/api\/v1\/workspaces\/([^/]+)\/autonomous-runs$/.exec(path);
  if (listMatch && method === "GET") {
    const wsId = decodeURIComponent(listMatch[1] ?? "");
    return jsonResponse({
      workspace_id: wsId,
      runs: mockAutonomousRuns.filter((r) => r.workspace_id === wsId),
      trace_id: "0195f000000070008000000000007401",
    });
  }

  const stopMatch = /^\/api\/v1\/runs\/([^/]+)\/emergency-stop$/.exec(path);
  if (stopMatch && method === "POST") {
    const runId = decodeURIComponent(stopMatch[1] ?? "");
    const target = mockAutonomousRuns.find((r) => r.run_id === runId);
    if (!target) {
      return jsonResponse({ error_code: "ERR_RESOURCE_NOT_FOUND", detail: "Not found" }, 404);
    }
    target.run_status = "KILL_SWITCH_STOPPED";
    const suspend = body.suspend_trigger !== false && target.trigger_id !== null;
    if (suspend) {
      target.trigger_status = "CIRCUIT_OPEN";
    }
    return jsonResponse({
      run_id: target.run_id,
      workspace_id: target.workspace_id,
      status: "KILL_SWITCH_STOPPED",
      trigger_suspended: suspend,
      sse_dispatch_latency_ms: 4.5,
      trace_id: "0195f000000070008000000000007402",
    });
  }

  const rollbackMatch = /^\/api\/v1\/runs\/([^/]+)\/invalidate-and-restore$/.exec(path);
  if (rollbackMatch && method === "POST") {
    const runId = decodeURIComponent(rollbackMatch[1] ?? "");
    const target = mockAutonomousRuns.find((r) => r.run_id === runId);
    const helpId =
      typeof body.help_resource_id === "string"
        ? body.help_resource_id
        : (target?.help_resource_id ?? null);
    if (!target && !helpId) {
      return jsonResponse({ error_code: "ERR_RESOURCE_NOT_FOUND", detail: "Not found" }, 404);
    }
    if (target) {
      target.run_status = "ROLLED_BACK";
      target.post_hoc_status = "INVALIDATED_ROLLED_BACK";
      target.previous_version_available = false;
    }
    const restoredVersion = restoreHelpRecordsForRunOrResource(runId, helpId);
    return jsonResponse({
      run_id: runId,
      workspace_id: target?.workspace_id ?? "0195f000-0000-7000-8000-000000000301",
      status: "ROLLED_BACK",
      restored_version: restoredVersion,
      help_resource_id: helpId,
      redis_cache_invalidated_ms: 1.2,
      sse_dispatch_latency_ms: 3.4,
      trace_id: "0195f000000070008000000000007403",
    });
  }

  const reviewMatch = /^\/api\/v1\/runs\/([^/]+)\/post-hoc-review$/.exec(path);
  if (reviewMatch && method === "POST") {
    const runId = decodeURIComponent(reviewMatch[1] ?? "");
    const target = mockAutonomousRuns.find((r) => r.run_id === runId);
    if (!target) {
      return jsonResponse({ error_code: "ERR_RESOURCE_NOT_FOUND", detail: "Not found" }, 404);
    }
    const decision = String(body.decision ?? "VALIDATED");
    target.post_hoc_status = decision;
    let restoredVersion: string | null = null;
    if (decision === "INVALIDATED_ROLLED_BACK") {
      target.run_status = "ROLLED_BACK";
      target.previous_version_available = false;
      restoredVersion = restoreHelpRecordsForRunOrResource(runId, target.help_resource_id ?? null);
    }
    return jsonResponse({
      run_id: runId,
      review_status: decision,
      run_status: target.run_status,
      restored_version: restoredVersion,
      trace_id: "0195f000000070008000000000007404",
    });
  }

  if (path === "/api/v1/help/resolve" && method === "GET") {
    const route = searchParams?.get("route") ?? "/cockpit";
    const lang = searchParams?.get("lang") === "en" ? "en" : "fr";
    const pack = searchParams?.get("pack") ?? "core";
    const seeded = mockHelpByRoute.get(route);
    if (seeded) {
      return jsonResponse(seeded);
    }
    const slug = route.replace(/^\/+|\/+$/g, "").replace(/[^a-z0-9]+/gi, "-") || "cockpit";
    const isConfigRoute =
      route.startsWith("/settings") ||
      route.startsWith("/configuration") ||
      route.startsWith("/organization");
    const isAssistantRoute = route.startsWith("/assistant") || route.startsWith("/inbox");
    const isSpacesRoute = route.startsWith("/spaces") || route.startsWith("/workspaces");
    const isCockpitRoute = route === "/" || route.startsWith("/cockpit");

    const titleByRoute = isAssistantRoute
      ? lang === "fr"
        ? "Aide contextuelle — /assistant : questions et dossiers"
        : "Contextual Help — /assistant: questions and folders"
      : isSpacesRoute
        ? lang === "fr"
          ? "Aide contextuelle — /spaces : Mes Espaces et sources"
          : "Contextual Help — /spaces: My Spaces and sources"
        : isCockpitRoute
          ? lang === "fr"
            ? "Aide contextuelle — /cockpit : décisions et démarrage"
            : "Contextual Help — /cockpit: decisions and onboarding"
          : lang === "fr"
            ? `Aide contextuelle — ${route}`
            : `Contextual Help — ${route}`;

    const summaryByRoute = isAssistantRoute
      ? lang === "fr"
        ? "Mon Assistant répond à vos questions à partir des documents de votre Espace actif avec citations vérifiées."
        : "My Assistant answers questions grounded in your active Space documents with verified citations."
      : isSpacesRoute
        ? lang === "fr"
          ? "Mes Espaces regroupe vos Espaces de travail rattachés à une unité d'organisation et leurs sources documentaires."
          : "My Spaces groups your Workspaces linked to an organizational unit and their document sources."
        : isCockpitRoute
          ? lang === "fr"
            ? "Le Cockpit regroupe les décisions en attente de validation humaine et l'avancement du démarrage."
            : "The Cockpit gathers decisions awaiting human approval and onboarding progress."
          : lang === "fr"
            ? `Présentation de l'écran ${route}.`
            : `Overview for screen ${route}.`;

    const stepsByRoute = isAssistantRoute
      ? lang === "fr"
        ? [
            "Choisissez votre modèle (Rapide, Polyvalent ou Raisonnement avancé) et votre mode de réflexion (Standard ou Approfondi — ex. « Polyvalent · Standard »).",
            "Rédigez votre question avec @ pour appeler un agent ou / pour une compétence.",
            "Classez vos échanges dans un dossier avec notes permanentes.",
          ]
        : [
            "Choose your model (Fast, Versatile, or Advanced Reasoning) and thinking mode (Standard or In-Depth — e.g. \"Versatile · Standard\").",
            "Write your question using @ for agents or / for skills.",
            "Organize threads into a folder with permanent notes.",
          ]
      : isSpacesRoute
        ? lang === "fr"
          ? [
              "Filtrez ou créez un Espace rattaché à une unité d'organisation.",
              "Ajustez le niveau de confidentialité de l'Espace.",
              "Connectez vos sources documentaires et enrichissez le glossaire.",
            ]
          : [
              "Filter or create a Space linked to an organizational unit.",
              "Adjust the Workspace confidentiality level.",
              "Connect document sources and enrich the glossary.",
            ]
        : [
            lang === "fr" ? `Consultez les éléments de ${route}` : `Review ${route} items`,
          ];

    const realExampleByRoute = isAssistantRoute
      ? lang === "fr"
        ? "Marc sélectionne son Espace produit, ouvre le dossier Conformité et obtient une synthèse avec pastilles de citations vérifiées."
        : "Marc selects his product Space, opens the Compliance folder, and gets a summary with verified citation pills."
      : isSpacesRoute
        ? lang === "fr"
          ? "L'équipe Sinistres crée un Espace confidentiel rattaché à son unité d'organisation puis y connecte ses documents."
          : "The Claims team creates a confidential Space linked to its organizational unit and connects its documents."
        : lang === "fr"
          ? `Exemple pratique d'utilisation sur l'écran ${route}.`
          : `Practical usage example on screen ${route}.`;

    const commonPitfallsByRoute = isAssistantRoute
      ? lang === "fr"
        ? [
            "Zone de saisie verrouillée : vérifiez qu'un modèle d'analyse documentaire et un modèle de dialogue sont configurés.",
          ]
        : [
            "Locked input: verify both an indexing model and a chat model are configured.",
          ]
      : isSpacesRoute
        ? lang === "fr"
          ? [
              "Unité d'organisation vs Espace de travail : l'unité d'organisation porte les membres et le budget, l'Espace porte les sources.",
            ]
          : [
              "Org unit vs Workspace: the organizational unit carries members and budget, the Workspace carries sources.",
            ]
        : [
            lang === "fr"
              ? "Vérifiez votre périmètre actif dans la barre latérale gauche."
              : "Check your active scope in the left sidebar.",
          ];

    const defaultKeyTerms =
      isConfigRoute && lang === "fr"
        ? [
            "BU vs Équipe vs Espace de travail : Une Direction (BU) regroupe plusieurs Équipes.",
            "Qui ? (Bénéficiaire) vs Sur quoi ? (Périmètre cible) : « Rôle : Responsable Produit → Équipe Paiement ».",
            "Isoler ce périmètre (INHERITANCE_BLOCK) : Coupe l'héritage parent sur cette Équipe ou cet Espace.",
          ]
        : [];
    return jsonResponse({
      route,
      pack,
      lang,
      redis_cache_key: `help:route:${route}:${pack}:${lang}`,
      cache_hit: false,
      merged_layers: ["BASE"],
      active_article: {
        resource_id: `help-base-${slug}-${lang}`,
        uri: `orcia://system/help/${slug}`,
        title: titleByRoute,
        version: "1.0.0",
        lang,
        layer: "BASE",
        pack_name: pack,
        bound_routes: [route],
        summary_what_for: summaryByRoute,
        step_by_step_items: stepsByRoute,
        key_terms_items: defaultKeyTerms,
        faq_items: [],
        real_example_text: realExampleByRoute,
        common_pitfalls_items: commonPitfallsByRoute,
        cas_key: `cas/${slug}`,
        sha256: "b".repeat(64),
        markdown_body: `# ${route}`,
        item_type: "HELP_ARTICLE",
        previous_version: null,
        previous_cas_key: null,
      },
      rollback_available: false,
      ask_assistant_prefill:
        lang === "fr"
          ? `Explique-moi comment utiliser l'écran ${route}`
          : `Explain how to use screen ${route}`,
      is_autonomous_generated: false,
      run_id: null,
      contract_label: null,
      trigger_label: null,
      previous_version_available: false,
      trace_id: "0195f000000070008000000000007405",
    });
  }

  if (path === "/api/v1/help/rollback" && method === "POST") {
    const resourceId = String(body.resource_id ?? "");
    const restoredVersion = restoreHelpRecordsForRunOrResource("", resourceId || null);
    return jsonResponse({
      resource_id: resourceId,
      uri: `orcia://system/help/${resourceId}`,
      title: "Aide restaurée",
      version: restoredVersion,
      lang: "fr",
      layer: "WORKSPACE",
      pack_name: "core",
      bound_routes: ["/cockpit"],
      summary_what_for: "Restored",
      step_by_step_items: [],
      key_terms_items: [],
      faq_items: [],
      cas_key: "cas/restored",
      sha256: "a".repeat(64),
      previous_version: null,
      is_autonomous_generated: false,
    });
  }

  const wfV2Match = /^\/api\/v1\/workflows\/v2\/([^/]+)$/.exec(path);
  if (wfV2Match && method === "PUT") {
    return jsonResponse({
      workflow: body.workflow ?? { id: decodeURIComponent(wfV2Match[1] ?? ""), status: "published" },
      forked_as_draft: false,
    });
  }

  return null;
}
