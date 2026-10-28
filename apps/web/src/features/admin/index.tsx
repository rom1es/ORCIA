import { BootstrapOnboardingPanel, type UiBootstrapWorkflowView } from "@orcia/ui";
import React from "react";
import { usePersonaContext } from "../../components/ShellContainer";
import { useI18n } from "../../i18n";

export const DEFAULT_BOOTSTRAP_WORKFLOWS: UiBootstrapWorkflowView[] = [
  { uri: "orcia://system/bootstrap/init-organization", title: "init-organization", requiredRole: "PLATFORM_ADMIN", scopeLevel: "GLOBAL", gateRules: ["GATE-LLM-ORTHOGONALITY-MIN-2-FAMILIES"] },
  { uri: "orcia://system/bootstrap/init-workspace", title: "init-workspace", requiredRole: "TEAM_LEAD", scopeLevel: "TEAM", gateRules: ["GATE-ONTOLOGY-L3-NO-UPSTREAM-CONFLICT"] },
  { uri: "orcia://system/bootstrap/init-datasource", title: "init-datasource", requiredRole: "TEAM_LEAD", scopeLevel: "WORKSPACE", gateRules: ["GATE-PERMISSION-BROKER-HUMAN-ANCHOR-SIGNED"] },
  { uri: "orcia://system/bootstrap/init-existing-project", title: "init-existing-project", requiredRole: "TEAM_LEAD", scopeLevel: "WORKSPACE", gateRules: ["GATE-BROWNFIELD-SCAN-VERIFIED"] },
  { uri: "orcia://system/bootstrap/init-skill", title: "init-skill", requiredRole: "CONTRIBUTOR", scopeLevel: "WORKSPACE", gateRules: ["GATE-SKILL-SCHEMA-VALID"] },
  { uri: "orcia://system/bootstrap/init-user", title: "init-user", requiredRole: "CONTRIBUTOR", scopeLevel: "WORKSPACE", gateRules: ["GATE-PASSTHROUGH-AES256GCM-ENCRYPTED"] },
];

export function AdminFeaturePanel() {
  const { dictionary } = useI18n();
  const { activePersona } = usePersonaContext();

  return (
    <div className="orcia-bento-card">
      <BootstrapOnboardingPanel
        activePersona={activePersona}
        workflows={DEFAULT_BOOTSTRAP_WORKFLOWS}
        labels={dictionary.bootstrapOnboarding}
      />
    </div>
  );
}
