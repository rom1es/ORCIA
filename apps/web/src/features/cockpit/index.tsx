import { HumanLedAnchorCard } from "@orcia/ui";
import type { Edge, Node } from "@xyflow/react";
import React, { useState } from "react";
import { useI18n } from "../../i18n";

export function buildCockpitWorkflowPreviewGraph(): {
  nodes: Node[];
  edges: Edge[];
} {
  return {
    nodes: [
      { id: "intent-router", position: { x: 0, y: 0 }, data: { label: "1. Intent Router" } },
      { id: "query-planner", position: { x: 200, y: 0 }, data: { label: "2. Query Planner" } },
    ],
    edges: [
      { id: "e-intent-planner", source: "intent-router", target: "query-planner" },
    ],
  };
}

export function CockpitFeaturePanel() {
  const { dictionary } = useI18n();
  const [customAnchorText, setCustomAnchorText] = useState<string | null>(null);
  const anchorText = customAnchorText ?? dictionary.humanAnchor.defaultValue;

  return (
    <div className="orcia-bento-card">
      <HumanLedAnchorCard
        sectionKey="architecture-intent"
        sectionTitle={dictionary.humanAnchor.defaultSectionTitle}
        authorName={dictionary.humanAnchor.defaultAuthorName}
        value={anchorText}
        labels={dictionary.humanAnchor}
        onChange={setCustomAnchorText}
      />
    </div>
  );
}
