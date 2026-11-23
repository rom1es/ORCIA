import type { ConfiguredWorkflowItem } from "../../components/platformSetupStore";
import { resolveDictionaryForFlag } from "../../i18n";

export function buildOrciaDocumentationWorkflowSpec(
  isFr: boolean,
  status: "DRAFT" | "PUBLISHED" = "PUBLISHED",
): ConfiguredWorkflowItem {
  const docCopy = resolveDictionaryForFlag(isFr).featureCockpitGates.gates.docProcess;
  return {
    workflowKey: "generate-orcia-documentation",
    title: docCopy.workflowTitle,
    version: "1.0.0",
    status,
    prePrompt: docCopy.workflowPrePrompt,
    prePromptSha256:
      "a4b9c2f18d7e6034521983746501928374650192837465019283746501928374", // pragma: allowlist secret
    requiredParams: ["langues", "perimetre_routes", "inclure_faq_architecture"],
    requiredMarkdownSections: [
      "Objectif",
      "Guide Fonctionnel par Écran",
      "Architecture & Modèle Métier",
      "Questions Fréquentes (FAQ)",
    ],
    triggers: ["manual"],
    layers: [...docCopy.workflowLayers],
  };
}

export function buildGeneratedDocumentationMarkdown(isFr: boolean): string {
  return resolveDictionaryForFlag(isFr).featureCockpitGates.gates.docProcess.generatedMarkdown;
}
