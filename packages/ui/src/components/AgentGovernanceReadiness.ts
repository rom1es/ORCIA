import type {
  AgentGovernanceStudioLabels,
  AgentReadinessConditionItem,
  AgentSixBlocksDraftState,
} from "./AgentGovernanceTypesAndDefaults";

function formatChecklistTemplate(
  template: string,
  vars: Readonly<Record<string, string | number>>,
): string {
  return template.replace(/\{([a-zA-Z0-9_]+)\}/g, (_m, k: string) =>
    vars[k] !== undefined ? String(vars[k]) : `{${k}}`,
  );
}

export function computeAgentReadinessChecklist(
  draft: AgentSixBlocksDraftState,
  studio: AgentGovernanceStudioLabels,
): readonly AgentReadinessConditionItem[] {
  const hasIdentity =
    draft.name.trim().length > 0 && draft.roleMission.trim().length > 0;
  const hasInstructions =
    draft.instructions.trim().length > 0 || draft.promptRef.trim().length > 0;
  const hasModelAndBudget =
    Boolean(draft.llmModelTier) && draft.maxTokens >= 256;
  const hasCitationsPolicy = draft.guardrails.includes("citations_obligatoires");
  const hasRagAndOntologyScope =
    draft.allowedRagSources.length > 0 && draft.ontologyViews.length > 0;
  const hasWriteTools = Object.values(draft.mcpToolPermissions).some(
    (m) => m === "WRITE_PREVIEW",
  );
  const writePreviewOk = !hasWriteTools || draft.writePreviewRequired;
  const rc = studio.readinessConditions;

  return [
    {
      index: 1,
      code: "IDENTITY_AND_HANDLE",
      label: rc.identityLabel,
      satisfied: hasIdentity,
      detail: hasIdentity
        ? formatChecklistTemplate(rc.identityOkTemplate, {
            posture:
              draft.posture === "EVALUATOR_GATE"
                ? rc.postureEvaluatorShort
                : rc.postureProducerShort,
            partner: draft.humanPartnerRole,
          })
        : rc.identityMissing,
    },
    {
      index: 2,
      code: "SYSTEM_INSTRUCTIONS",
      label: rc.instructionsLabel,
      satisfied: hasInstructions,
      detail: hasInstructions
        ? formatChecklistTemplate(rc.instructionsOkTemplate, {
            count: draft.invocationModes.length,
          })
        : rc.instructionsMissing,
    },
    {
      index: 3,
      code: "COGNITIVE_ENGINE",
      label: rc.engineLabel,
      satisfied: hasModelAndBudget,
      detail: formatChecklistTemplate(rc.engineTemplate, {
        tier: studio.llmModelTiers[draft.llmModelTier],
        temperature: draft.temperature,
        maxTokens: draft.maxTokens,
      }),
    },
    {
      index: 4,
      code: "CITATIONS_POLICY",
      label: rc.citationsLabel,
      satisfied: hasCitationsPolicy,
      detail: hasCitationsPolicy
        ? formatChecklistTemplate(rc.citationsOkTemplate, {
            format: studio.outputContractFormats[draft.outputContractFormat],
          })
        : rc.citationsMissing,
    },
    {
      index: 5,
      code: "RAG_AND_RBAC_SCOPE",
      label: rc.ragScopeLabel,
      satisfied: hasRagAndOntologyScope,
      detail: formatChecklistTemplate(rc.ragScopeTemplate, {
        ragCount: draft.allowedRagSources.length,
        ontologyCount: draft.ontologyViews.length,
      }),
    },
    {
      index: 6,
      code: "WRITE_PREVIEW_AND_BENCH",
      label: rc.writePreviewLabel,
      satisfied: writePreviewOk,
      detail: draft.testBenchValidated
        ? rc.writePreviewValidated
        : rc.writePreviewReady,
    },
  ];
}
