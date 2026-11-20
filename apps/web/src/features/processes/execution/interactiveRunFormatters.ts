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
