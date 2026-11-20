const AGENT_HUMAN_LABELS: Record<string, string> = {
  "pack://sdlc/agents/orchestrateur-produit.md":
    "Agent Product Owner (Qualification & PRD)",
  "pack://sdlc/agents/crl-etude-archi.md":
    "Agent Architecte (Dossier d'étude 14 points)",
  "pack://sdlc/agents/agent-us.md":
    "Agent Business Analyst (Découpe Epics & US)",
  "pack://sdlc/agents/crl-socle-generateur.md": "Agent Socle de Connaissance",
  "pack://orcia-docs/agents/redacteur-documentation-orcia.md":
    "Agent Rédacteur Documentaire",
};

export function formatAgentHumanLabel(agentRef: string): string {
  return (
    AGENT_HUMAN_LABELS[agentRef] ??
    agentRef.replace(/^pack:\/\/[^/]+\/agents\//, "").replace(/\.md$/, "")
  );
}

export function extractAgentSlugFromRef(agentRef: string): string {
  return (
    agentRef
      .replace(/^pack:\/\/[^/]+\/agents\//, "")
      .replace(/\.md$/, "")
      .trim() || "assistant"
  );
}

export function simpleHashHex(text: string): string {
  let h = 2166136261;
  for (let i = 0; i < text.length; i += 1) {
    h ^= text.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  const hex = (h >>> 0).toString(16).padStart(8, "0");
  return `${hex}${hex}${hex}${hex}${hex}${hex}${hex}${hex}`;
}

export type InteractiveProcessDrawerStatus =
  | "WAITING_EXTERNAL_GATE"
  | "WAITING_SUBSTEP_HITL"
  | "WAITING_WRITE_PREVIEW"
  | "WAITING_FINAL_ANCHOR"
  | "COMPLETED_APPROVED"
  | "RETURN_LOOP_TRIGGERED"
  | "SLA_SUSPENDED";

export function buildInitialArtifactMarkdown(
  workflowTitle: string,
  stepName: string,
  agentLabel: string,
): string {
  return `# ${workflowTitle}\n\n## Étape en cours : ${stepName}\n\nProposition préparée par ${agentLabel}.\n\n## Synthèse & Critères de valeur\n- Objectif métier clarifié et aligné avec le socle de connaissance.\n- Score de priorité (WSJF) estimé : 8.4 — Prêt pour relecture.`;
}

export function buildSubStepAdvanceMarkdown(
  workflowTitle: string,
  stepName: string,
  outputDescription: string,
): string {
  return `# ${workflowTitle}\n\n## Étape en cours : ${stepName}\n\nLivrable préparé : ${outputDescription}`;
}

export function buildWritePreviewExecutionPayload(
  actorSlug: string,
  workflowId: string,
  workflowTitle: string,
  reflexiveObjective: string | null | undefined,
  isFr: boolean,
) {
  return {
    actor_slug: actorSlug,
    objective: reflexiveObjective || workflowTitle,
    effort_level: "high" as const,
    effort_mode: "approfondi" as const,
    allow_sub_agent_delegation: true,
    available_delegate_agents: ["analyste-metier"],
    initial_resources: ["docs/product/capabilities.yaml"],
    requested_write_preview: {
      connector_type: "confluence",
      action: "publish_page",
      target_resource_uri: "confluence://Architecture/Documentation-ORCIA",
      action_summary: isFr
        ? `Publier le livrable « ${workflowTitle} »`
        : `Publish deliverable "${workflowTitle}"`,
      payload: { workflow_id: workflowId, title: workflowTitle },
    },
  };
}
