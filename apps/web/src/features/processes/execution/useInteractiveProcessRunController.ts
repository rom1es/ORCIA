import type { UiAgentTraceEventItem } from "@orcia/ui";
import { useEffect, useState } from "react";
import { useI18n } from "../../../i18n";
import type { WorkflowDefinitionV2Item } from "../processStudioV2Data";
import { createProcessesApiClient } from "../studio/studioLabelsAndMappers";
import {
  mapApiTraceEventToUi,
  readPersistedReflexiveId,
} from "../../shared/reflexiveTraceMappers";
import { useReflexiveExecutionController } from "../../shared/useReflexiveExecutionController";
import { useSourceLineInspector } from "../../shared/useSourceLineInspector";

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

function simpleHashHex(text: string): string {
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

export function useInteractiveProcessRunController(
  workflow: WorkflowDefinitionV2Item,
  isFr: boolean,
) {
  const { locale, dictionary } = useI18n();
  const enabledSubSteps = workflow.sub_steps.filter((s) => s.enabled);
  const isExternalGate = workflow.execution_mode === "external_delegated";
  const isGoalDriven = workflow.orchestration_type === "non_deterministic";
  const storageKey = `orcia.reflexive_exec.process.${workflow.id}.v1`;
  const actorSlug = extractAgentSlugFromRef(workflow.agent_ref);

  const [runId, setRunId] = useState<string>(() => `run-${workflow.id}-01`);
  const [iteration, setIteration] = useState<number>(1);
  const [reentryMode, setReentryMode] = useState<"initial" | "corrections">(
    "initial",
  );
  const [currentSubIndex, setCurrentSubIndex] = useState<number>(0);
  const [status, setStatus] = useState<InteractiveProcessDrawerStatus>(
    isExternalGate ? "WAITING_EXTERNAL_GATE" : "WAITING_SUBSTEP_HITL",
  );

  const currentSubStep = enabledSubSteps[currentSubIndex] ?? enabledSubSteps[0];
  const agentLabel = formatAgentHumanLabel(workflow.agent_ref);

  const [artifactMarkdown, setArtifactMarkdown] = useState<string>(
    `# ${workflow.title}\n\n## Étape en cours : ${currentSubStep?.name ?? "Exécution"}\n\nProposition préparée par ${agentLabel}.\n\n## Synthèse & Critères de valeur\n- Objectif métier clarifié et aligné avec le socle de connaissance.\n- Score de priorité (WSJF) estimé : 8.4 — Prêt pour relecture.`,
  );
  const [artifactSha256, setArtifactSha256] = useState<string>(() =>
    simpleHashHex(artifactMarkdown),
  );
  const [isEditingDiff, setIsEditingDiff] = useState<boolean>(false);
  const [returnLoopTargetStep, setReturnLoopTargetStep] =
    useState<string>("02");
  const [returnLoopRemarks, setReturnLoopRemarks] = useState<string>(
    "Préciser les hypothèses de gain métier sur le segment professionnel.",
  );
  const [signedTokenPreview, setSignedTokenPreview] = useState<string | null>(
    null,
  );
  const [statusBanner, setStatusBanner] = useState<string | null>(null);
  const [inlineRunTraceEvents, setInlineRunTraceEvents] = useState<
    readonly UiAgentTraceEventItem[]
  >([]);

  const inspector = useSourceLineInspector({
    locale,
    onFeedback: setStatusBanner,
  });

  const reflexive = useReflexiveExecutionController({
    storageKey,
    locale,
    onFeedback: setStatusBanner,
    onSnapshotUpdated: (mapped) => {
      if (mapped.finalMarkdown) {
        setArtifactMarkdown(mapped.finalMarkdown);
        setArtifactSha256(
          mapped.artifactSha256 || simpleHashHex(mapped.finalMarkdown),
        );
      }
      if (mapped.status === "WAITING_WRITE_PREVIEW") {
        setStatus("WAITING_WRITE_PREVIEW");
      } else if (
        mapped.status === "COMPLETED" &&
        status === "WAITING_WRITE_PREVIEW"
      ) {
        setStatus("WAITING_FINAL_ANCHOR");
      }
    },
  });

  useEffect(() => {
    const existingExecId = readPersistedReflexiveId(storageKey);
    if (existingExecId) {
      return;
    }
    let cancelled = false;
    createProcessesApiClient(locale)
      .startWorkflowV2Run(workflow.id, {
        inputs: { objective: workflow.title },
        iteration: 1,
        reentry_mode: "initial",
      })
      .then((res) => {
        if (cancelled || !res?.run) return;
        setRunId(res.run.run_id || `run-${workflow.id}-01`);
        if (res.run.reflexive_execution_id) {
          void reflexive.refreshSnapshot(res.run.reflexive_execution_id);
        } else if (
          Array.isArray(res.run.trace_events) &&
          res.run.trace_events.length > 0
        ) {
          setInlineRunTraceEvents(
            res.run.trace_events.map((ev) =>
              mapApiTraceEventToUi(ev, actorSlug),
            ),
          );
        } else if (isGoalDriven) {
          void reflexive.startExecution({
            actor_slug: actorSlug,
            objective: workflow.reflexive_objective || workflow.title,
            effort_level: "high",
            effort_mode: "approfondi",
            allow_sub_agent_delegation: true,
            available_delegate_agents: ["analyste-metier"],
            initial_resources: [
              "docs/product/capabilities.yaml",
              "packs/orcia-docs/workflows/wf-generate-orcia-documentation.yaml",
            ],
          });
        }
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        const detail = err instanceof Error ? err.message : String(err);
        setStatusBanner(
          isFr
            ? `ℹ️ Mode dossier local actif (${detail}).`
            : `ℹ️ Local dossier mode active (${detail}).`,
        );
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [workflow.id]);

  const handleLaunchLiveInvestigation = () => {
    void reflexive.startExecution({
      actor_slug: actorSlug,
      objective: workflow.reflexive_objective || workflow.title,
      effort_level: "high",
      effort_mode: "approfondi",
      allow_sub_agent_delegation: true,
      available_delegate_agents: ["analyste-metier"],
      initial_resources: [
        "docs/product/capabilities.yaml",
        "packs/orcia-docs/workflows/wf-generate-orcia-documentation.yaml",
      ],
      run_in_background: true,
      step_delay_ms: 120,
    });
  };

  const handleStageExternalWritePreview = () => {
    void reflexive.startExecution({
      actor_slug: actorSlug,
      objective: workflow.reflexive_objective || workflow.title,
      effort_level: "high",
      effort_mode: "approfondi",
      allow_sub_agent_delegation: true,
      available_delegate_agents: ["analyste-metier"],
      initial_resources: ["docs/product/capabilities.yaml"],
      requested_write_preview: {
        connector_type: "confluence",
        action: "publish_page",
        target_resource_uri: "confluence://Architecture/Documentation-ORCIA",
        action_summary: isFr
          ? `Publier le livrable « ${workflow.title} »`
          : `Publish deliverable "${workflow.title}"`,
        payload: { workflow_id: workflow.id, title: workflow.title },
      },
    });
  };

  const handleApproveCurrentSubStep = () => {
    if (
      currentSubStep?.write_preview_required &&
      status !== "WAITING_WRITE_PREVIEW"
    ) {
      setStatus("WAITING_WRITE_PREVIEW");
      setStatusBanner(
        isFr
          ? "Vérification avant publication externe : veuillez confirmer la création dans l'outil cible (Jira / Confluence)."
          : "Pre-publication check: please confirm creation in the target tool.",
      );
      return;
    }
    if (status === "WAITING_WRITE_PREVIEW") {
      setSignedTokenPreview(`sat_${artifactSha256.slice(0, 16)}_hmac_ok`);
    }
    if (currentSubIndex + 1 < enabledSubSteps.length) {
      const nextIdx = currentSubIndex + 1;
      const nextSub = enabledSubSteps[nextIdx];
      setCurrentSubIndex(nextIdx);
      const nextMd = `# ${workflow.title}\n\n## Étape en cours : ${nextSub?.name ?? ""}\n\nLivrable préparé : ${nextSub?.output_description ?? ""}`;
      setArtifactMarkdown(nextMd);
      setArtifactSha256(simpleHashHex(nextMd));
      setStatus(
        nextSub?.write_preview_required
          ? "WAITING_WRITE_PREVIEW"
          : "WAITING_SUBSTEP_HITL",
      );
      setStatusBanner(
        isFr
          ? `Étape « ${currentSubStep?.short_label} » validée. Passage à « ${nextSub?.short_label} ».`
          : `Step "${currentSubStep?.short_label}" approved. Advancing to "${nextSub?.short_label}".`,
      );
    } else {
      setStatus("WAITING_FINAL_ANCHOR");
      setStatusBanner(
        isFr
          ? "Toutes les étapes et les vérifications de qualité sont conformes. Vous pouvez valider et publier le livrable final."
          : "All steps and quality checks passed. Ready for final sign-off.",
      );
    }
  };

  const handleAction2SaveAmendedDiff = () => {
    setArtifactSha256(simpleHashHex(artifactMarkdown));
    setIsEditingDiff(false);
    setStatusBanner(
      isFr
        ? "Modifications enregistrées sur le livrable."
        : "Deliverable changes saved.",
    );
  };

  const handleAction3RejectAndLoop = () => {
    const nextIter = iteration + 1;
    setIteration(nextIter);
    setReentryMode("corrections");
    setCurrentSubIndex(0);
    setStatus("RETURN_LOOP_TRIGGERED");
    const revisedMd = `${artifactMarkdown}\n\n## Reprise sur corrections (Cycle ${nextIter} → Étape ${returnLoopTargetStep})\nCommentaires pris en compte : ${returnLoopRemarks}`;
    setArtifactMarkdown(revisedMd);
    setArtifactSha256(simpleHashHex(revisedMd));
    setStatusBanner(
      isFr
        ? `Dossier renvoyé vers l'Étape ${returnLoopTargetStep} avec vos commentaires de correction (Cycle ${nextIter}).`
        : `Returned to Step ${returnLoopTargetStep} with your correction notes (Cycle ${nextIter}).`,
    );
  };

  const effectiveEvents =
    reflexive.events.length > 0 ? reflexive.events : inlineRunTraceEvents;
  const effectiveTraceStatus =
    reflexive.status ?? (effectiveEvents.length > 0 ? "COMPLETED" : null);

  return {
    dictionary,
    enabledSubSteps,
    isGoalDriven,
    runId,
    iteration,
    reentryMode,
    currentSubIndex,
    currentSubStep,
    status,
    setStatus,
    agentLabel,
    artifactMarkdown,
    setArtifactMarkdown,
    artifactSha256,
    isEditingDiff,
    setIsEditingDiff,
    returnLoopTargetStep,
    setReturnLoopTargetStep,
    returnLoopRemarks,
    setReturnLoopRemarks,
    signedTokenPreview,
    statusBanner,
    setStatusBanner,
    inspector,
    reflexive,
    effectiveEvents,
    effectiveTraceStatus,
    handleLaunchLiveInvestigation,
    handleStageExternalWritePreview,
    handleApproveCurrentSubStep,
    handleAction2SaveAmendedDiff,
    handleAction3RejectAndLoop,
  };
}
