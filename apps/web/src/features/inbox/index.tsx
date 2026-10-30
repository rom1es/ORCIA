import { PresenceClaimPill, StatusBadge, type UiClaimPresenceState } from "@orcia/ui";
import React, { useState } from "react";
import { useI18n } from "../../i18n";

interface InboxTaskSeed {
  id: string;
  stepExecutionId: string;
  scopeKind: "PERSONAL" | "TEAM";
  typeLabel: string;
  title: string;
  summary: string;
  presenceState: UiClaimPresenceState;
  claimedByDisplayName?: string;
  canForceUnclaim?: boolean;
  sseLatencyMs: number;
}

const INITIAL_TASKS: InboxTaskSeed[] = [
  {
    id: "task-notif-1",
    stepExecutionId: "stepexec-0801",
    scopeKind: "TEAM",
    typeLabel: "⚖️ HUMAN_ARBITRATION",
    title: "⚖️ Arbitrage IA requis — Choix de topologie d'isolation",
    summary: "Deux options d'architecture présentent un score équivalent ; décision d'équipe requise.",
    presenceState: "UNCLAIMED",
    sseLatencyMs: 38.4,
  },
  {
    id: "task-notif-2",
    stepExecutionId: "stepexec-0802",
    scopeKind: "PERSONAL",
    typeLabel: "🛡️ HUMAN_GATE",
    title: "🛡️ Gate Humaine Adaptative — Revue du Briefing 4 blocs",
    summary: "Validation par découpage attendue sur le livrable de sécurité.",
    presenceState: "CLAIMED_BY_ME",
    claimedByDisplayName: "Nadia",
    sseLatencyMs: 24.1,
  },
  {
    id: "task-notif-3",
    stepExecutionId: "stepexec-0803",
    scopeKind: "TEAM",
    typeLabel: "✍️ HUMAN_ANCHOR",
    title: "✍️ Ancrage Humain — Périmètre réglementaire SEPA",
    summary: "Rédaction obligatoire de la section réglementaire avant exécution de l'agent.",
    presenceState: "CLAIMED_BY_PEER",
    claimedByDisplayName: "Thomas",
    canForceUnclaim: true,
    sseLatencyMs: 41.2,
  },
];

export function InboxFeaturePanel() {
  const { dictionary } = useI18n();
  const copy = dictionary.modulePages.inbox;
  const inboxCopy = dictionary.inboxAndClaims;
  const [scopeFilter, setScopeFilter] = useState<"ALL" | "PERSONAL" | "TEAM">("ALL");
  const [tasks, setTasks] = useState<InboxTaskSeed[]>(INITIAL_TASKS);
  const [liveAnnouncement, setLiveAnnouncement] = useState<string>("");

  const visibleTasks = tasks.filter((t) => {
    if (scopeFilter === "ALL") return true;
    return t.scopeKind === scopeFilter;
  });

  const handleClaim = (taskId: string) => {
    setTasks((prev) =>
      prev.map((t) =>
        t.id === taskId
          ? {
              ...t,
              presenceState: "CLAIMED_BY_ME",
              claimedByDisplayName: "Nadia",
              sseLatencyMs: 19.8,
            }
          : t
      )
    );
    setLiveAnnouncement(`task.claim.locked: ${taskId}`);
  };

  const handleRelease = (taskId: string, _force: boolean) => {
    setTasks((prev) =>
      prev.map((t) =>
        t.id === taskId
          ? {
              ...t,
              presenceState: "UNCLAIMED",
              claimedByDisplayName: undefined,
            }
          : t
      )
    );
    setLiveAnnouncement(`task.claim.released: ${taskId}`);
  };

  return (
    <div className="orcia-bento-card" data-testid="inbox-feature-panel">
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: "8px",
          marginBottom: "14px",
          flexWrap: "wrap",
        }}
      >
        <span>{copy.subtitle}</span>
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <StatusBadge
            testId="inbox-amber-counter"
            label={`${inboxCopy.amberCounterPrefix} ${visibleTasks.length}`}
            tone="amber"
            pill
          />
          <StatusBadge testId="inbox-uri-badge" label={copy.uriBadgeExample} tone="cobalt" monospace />
        </div>
      </div>

      <div
        role="group"
        aria-label="Scope filters"
        style={{ display: "flex", gap: "8px", marginBottom: "16px", flexWrap: "wrap" }}
      >
        {(["ALL", "PERSONAL", "TEAM"] as const).map((scopeKey) => {
          const label =
            scopeKey === "ALL"
              ? inboxCopy.filterAllLabel
              : scopeKey === "PERSONAL"
                ? inboxCopy.filterPersonalLabel
                : inboxCopy.filterTeamLabel;
          const active = scopeFilter === scopeKey;
          return (
            <button
              key={scopeKey}
              type="button"
              data-testid={`inbox-filter-${scopeKey.toLowerCase()}`}
              onClick={() => setScopeFilter(scopeKey)}
              style={{
                padding: "4px 12px",
                borderRadius: "var(--radius-full)",
                border: active
                  ? "1px solid var(--color-primary-cobalt)"
                  : "1px solid var(--color-border)",
                backgroundColor: active
                  ? "var(--color-sidebar-active-bg)"
                  : "var(--color-surface-card)",
                color: active ? "var(--color-primary-cobalt)" : "var(--color-foreground)",
                fontFamily: "var(--font-sans)",
                fontSize: "var(--font-size-mono)",
                fontWeight: active ? 600 : 500,
                cursor: "pointer",
              }}
            >
              {label}
            </button>
          );
        })}
      </div>

      <div aria-live="polite" data-testid="inbox-aria-live-region" style={{ fontSize: "12px", marginBottom: "8px", color: "var(--color-muted-foreground)" }}>
        {liveAnnouncement}
      </div>

      <div style={{ display: "grid", gap: "12px" }}>
        {visibleTasks.map((task) => (
          <div
            key={task.id}
            data-testid={`inbox-task-card-${task.id}`}
            style={{
              padding: "12px 14px",
              borderRadius: "var(--radius-md)",
              border: "1px solid var(--color-border)",
              backgroundColor: "var(--color-surface-hover)",
              opacity: task.presenceState === "CLAIMED_BY_PEER" ? 0.85 : 1,
              display: "flex",
              flexDirection: "column",
              gap: "8px",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
              <strong style={{ fontSize: "var(--font-size-body)" }}>{task.title}</strong>
              <StatusBadge
                label={task.typeLabel}
                tone={task.scopeKind === "TEAM" ? "amber" : "cobalt"}
                monospace
              />
            </div>
            <p style={{ margin: 0, color: "var(--color-muted-foreground)", fontSize: "12.5px" }}>
              {task.summary}
            </p>
            <PresenceClaimPill
              taskId={task.id}
              stepExecutionId={task.stepExecutionId}
              presenceState={task.presenceState}
              claimedByDisplayName={task.claimedByDisplayName}
              canForceUnclaim={task.canForceUnclaim}
              sseLatencyMs={task.sseLatencyMs}
              labels={inboxCopy.presencePill}
              onClaim={handleClaim}
              onRelease={handleRelease}
            />
          </div>
        ))}
      </div>
    </div>
  );
}
