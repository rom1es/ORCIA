export function buildGoalDrivenExecutionPayload(params: {
  readonly actorSlug: string;
  readonly objective: string;
  readonly workspaceId?: string;
  readonly runInBackground?: boolean;
}) {
  return {
    actor_slug: params.actorSlug,
    objective: params.objective,
    effort_level: "high" as const,
    effort_mode: "approfondi" as const,
    allow_sub_agent_delegation: true,
    available_delegate_agents: ["analyste-metier"],
    initial_resources: [
      "docs/product/capabilities.yaml",
      "packs/orcia-docs/workflows/wf-generate-orcia-documentation.yaml",
    ],
    ...(params.workspaceId ? { workspace_id: params.workspaceId } : {}),
    ...(params.runInBackground ? { run_in_background: true, step_delay_ms: 120 } : {}),
  };
}
