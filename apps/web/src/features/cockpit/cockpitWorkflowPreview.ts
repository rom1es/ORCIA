import type { Edge, Node } from "@xyflow/react";
import { resolveDictionaryForFlag, type SupportedWebLocale } from "../../i18n";

export function buildCockpitWorkflowPreviewGraph(locale: SupportedWebLocale = "fr"): {
  nodes: Node[];
  edges: Edge[];
} {
  const labels = resolveDictionaryForFlag(undefined, locale).featureCockpitGates.cockpit.workflowPreviewNodes;
  return {
    nodes: [
      { id: "intent-router", position: { x: 0, y: 0 }, data: { label: labels.intentRouter } },
      { id: "query-planner", position: { x: 200, y: 0 }, data: { label: labels.queryPlanner } },
      { id: "parallel-fan-out", position: { x: 400, y: 0 }, data: { label: labels.parallelFanOut } },
      { id: "critical-triage", position: { x: 600, y: 0 }, data: { label: labels.criticalTriage } },
      { id: "profile-synthesizer", position: { x: 800, y: 0 }, data: { label: labels.profileSynthesizer } },
    ],
    edges: [
      { id: "e-intent-planner", source: "intent-router", target: "query-planner" },
      { id: "e-planner-fanout", source: "query-planner", target: "parallel-fan-out" },
      { id: "e-fanout-triage", source: "parallel-fan-out", target: "critical-triage" },
      { id: "e-triage-synthesizer", source: "critical-triage", target: "profile-synthesizer" },
    ],
  };
}
