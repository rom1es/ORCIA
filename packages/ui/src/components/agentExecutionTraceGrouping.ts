import type { UiAgentTraceEventItem } from "./AgentExecutionTraceTypes";

export interface TraceGroupSection {
  readonly key: string;
  readonly title: string;
  readonly items: readonly UiAgentTraceEventItem[];
  readonly delegatedChildrenByParentId: ReadonlyMap<
    string,
    readonly UiAgentTraceEventItem[]
  >;
}

function isThoughtEvent(ev: UiAgentTraceEventItem): boolean {
  return ev.kind === "THOUGHT_DELTA" || ev.kind === "THOUGHT_COMPLETED";
}

function resolveThoughtText(ev: UiAgentTraceEventItem): string {
  if (ev.thoughtContent !== undefined && ev.thoughtContent !== null) {
    return ev.thoughtContent;
  }
  return ev.kind === "THOUGHT_DELTA" ? ev.label : "";
}

export function coalesceConsecutiveThoughts(
  events: readonly UiAgentTraceEventItem[],
): readonly UiAgentTraceEventItem[] {
  const coalesced: UiAgentTraceEventItem[] = [];
  let seenSynthesisReady = false;

  for (const ev of events) {
    if (ev.kind === "SYNTHESIS_READY") {
      if (seenSynthesisReady) {
        continue;
      }
      seenSynthesisReady = true;
      coalesced.push(ev);
      continue;
    }

    if (!isThoughtEvent(ev)) {
      coalesced.push(ev);
      continue;
    }

    const prev = coalesced[coalesced.length - 1];
    if (!prev || !isThoughtEvent(prev)) {
      coalesced.push({
        ...ev,
        thoughtContent: resolveThoughtText(ev),
      });
      continue;
    }

    const prevText = resolveThoughtText(prev);
    const currText = resolveThoughtText(ev);
    const needsNewline =
      prev.kind === "THOUGHT_COMPLETED" &&
      ev.kind === "THOUGHT_COMPLETED" &&
      prevText.length > 0 &&
      currText.length > 0 &&
      !prevText.endsWith("\n");
    const mergedText = needsNewline
      ? `${prevText}\n${currText}`
      : `${prevText}${currText}`;

    coalesced[coalesced.length - 1] = {
      ...prev,
      kind: ev.kind === "THOUGHT_COMPLETED" ? "THOUGHT_COMPLETED" : prev.kind,
      durationSeconds: ev.durationSeconds ?? prev.durationSeconds ?? null,
      thoughtContent: mergedText,
      label: prevText ? prev.label : ev.label,
    };
  }

  return coalesced;
}

export function groupTraceEvents(
  events: readonly UiAgentTraceEventItem[],
  defaultTitle: string,
): readonly TraceGroupSection[] {
  const sorted = [...events].sort((a, b) => a.sequence - b.sequence);
  const groups: Array<{
    key: string;
    title: string;
    items: UiAgentTraceEventItem[];
    delegatedChildrenByParentId: Map<string, UiAgentTraceEventItem[]>;
  }> = [];

  let activeGroup: (typeof groups)[number] | null = null;
  let activeDelegationParent: { eventId: string; agentSlug: string } | null = null;

  for (const ev of sorted) {
    if (ev.kind === "EXECUTION_FINISHED") {
      continue;
    }
    if (ev.kind === "GROUP_HEADER") {
      const key = ev.groupKey || ev.eventId || `group-${groups.length + 1}`;
      activeGroup = {
        key,
        title: ev.label || defaultTitle,
        items: [],
        delegatedChildrenByParentId: new Map(),
      };
      groups.push(activeGroup);
      activeDelegationParent = null;
      continue;
    }

    if (!activeGroup) {
      activeGroup = {
        key: ev.groupKey || "default-group",
        title: defaultTitle,
        items: [],
        delegatedChildrenByParentId: new Map(),
      };
      groups.push(activeGroup);
    }

    if (ev.kind === "AGENT_DELEGATED") {
      activeGroup.items.push(ev);
      const slug = (ev.delegatedAgentSlug || "").replace(/^@/, "");
      activeDelegationParent = slug ? { eventId: ev.eventId, agentSlug: slug } : null;
      continue;
    }

    if (ev.kind === "WRITE_PREVIEW_REQUESTED") {
      continue;
    }

    const cleanActor = (ev.actorSlug || "").replace(/^@/, "");
    if (
      activeDelegationParent &&
      cleanActor &&
      cleanActor === activeDelegationParent.agentSlug
    ) {
      const existing =
        activeGroup.delegatedChildrenByParentId.get(activeDelegationParent.eventId) ?? [];
      activeGroup.delegatedChildrenByParentId.set(activeDelegationParent.eventId, [
        ...existing,
        ev,
      ]);
      continue;
    }

    activeDelegationParent = null;
    activeGroup.items.push(ev);
  }

  return groups.map((grp) => {
    const coalescedChildren = new Map<string, readonly UiAgentTraceEventItem[]>();
    for (const [parentId, children] of grp.delegatedChildrenByParentId.entries()) {
      coalescedChildren.set(parentId, coalesceConsecutiveThoughts(children));
    }
    return {
      key: grp.key,
      title: grp.title,
      items: coalesceConsecutiveThoughts(grp.items),
      delegatedChildrenByParentId: coalescedChildren,
    };
  });
}
