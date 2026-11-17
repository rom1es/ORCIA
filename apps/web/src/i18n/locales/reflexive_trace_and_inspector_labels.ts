import type {
  AgentExecutionTraceLabels,
  SourceLineInspectorLabels,
} from "@orcia/ui";

export interface ReflexiveTraceFeedbackCopy {
  readonly loadInspectorFailed: (detail: string) => string;
  readonly executionStartFailed: (detail: string) => string;
  readonly synthesizeRequestedBanner: string;
  readonly executionCancelledBanner: string;
  readonly writeApprovedBanner: string;
  readonly writeRejectedBanner: string;
  readonly actionFailed: (detail: string) => string;
}

export interface ReflexiveTraceAndInspectorDictionarySection {
  readonly executionTrace: AgentExecutionTraceLabels;
  readonly sourceLineInspector: SourceLineInspectorLabels;
  readonly reflexiveTraceFeedback: ReflexiveTraceFeedbackCopy;
}

export const REFLEXIVE_TRACE_AND_INSPECTOR_FR_LABELS: ReflexiveTraceAndInspectorDictionarySection = {
  executionTrace: {
    heading: "Déroulement de l'investigation",
    defaultGroupTitle: "Analyse et consultation de vos sources",
    runningStatus: "En cours d'analyse...",
    synthesizingStatus: "Rédaction de la synthèse...",
    completedStatus: "Analyse terminée",
    pausedWriteStatus: "En attente de votre confirmation avant publication",
    cancelledStatus: "Analyse interrompue",
    failedStatus: "Analyse interrompue sur anomalie",
    stepsCountLabel: (count: number) => `${count} action${count > 1 ? "s" : ""}`,
    thoughtSummaryLabel: (seconds: number) => `Réflexion (${seconds}s)`,
    thoughtInProgressLabel: "Réflexion en cours",
    analyzedPrefix: "Analysé",
    linesRangeShort: (start: number, end: number) => `#L${start}-${end}`,
    redactedPillSuffix: "Accès requis",
    delegatedPrefix: (agentHandle: string) => `Délégation à ${agentHandle}`,
    synthesizeNowButtonLabel: "Synthétiser maintenant",
    synthesizeNowButtonHint:
      "Conclure immédiatement avec les éléments déjà consultés sans poursuivre les recherches.",
    writePreviewHeading: "Confirmation requise avant action externe",
    writePreviewTargetPrefix: "Outil cible :",
    approveWriteButtonLabel: "Approuver la publication",
    rejectWriteButtonLabel: "Refuser",
    expandGroupAriaLabel: "Déplier l'étape",
    collapseGroupAriaLabel: "Replier l'étape",
  },
  sourceLineInspector: {
    dialogAriaLabel: "Inspecteur d'extrait source",
    linesSliceSummary: (startLine: number, endLine: number, totalLines: number) =>
      `Lignes ${startLine} – ${endLine} sur ${totalLines}`,
    copySliceButtonLabel: (startLine: number, endLine: number) =>
      `Copier l'extrait #L${startLine}-${endLine}`,
    copiedSliceFeedbackLabel: "Extrait copié",
    closeButtonLabel: "Fermer",
    loadingLabel: "Chargement de l'extrait vérifié...",
    redactedTitle: "Extrait protégé (habilitation requise)",
    redactedBody:
      "Votre compte ne dispose pas du droit de lecture sur cette source. Pour protéger la confidentialité, aucune ligne du document n'est affichée.",
    redactedHintPrefix: "Demande d'accès :",
    emptySliceLabel: "Aucune ligne disponible pour cet extrait.",
  },
  reflexiveTraceFeedback: {
    loadInspectorFailed: (detail: string) =>
      `Impossible d'ouvrir l'extrait source (${detail}).`,
    executionStartFailed: (detail: string) =>
      `L'analyse n'a pas pu démarrer (${detail}).`,
    synthesizeRequestedBanner:
      "Synthèse immédiate demandée : rédaction de la réponse à partir des éléments déjà recueillis.",
    executionCancelledBanner: "Exécution arrêtée à votre demande.",
    writeApprovedBanner:
      "Publication externe approuvée : reprise et finalisation du dossier.",
    writeRejectedBanner:
      "Publication externe refusée : aucune modification n'a été envoyée à l'outil cible.",
    actionFailed: (detail: string) =>
      `L'action n'a pas pu aboutir (${detail}).`,
  },
};

export const REFLEXIVE_TRACE_AND_INSPECTOR_EN_LABELS: ReflexiveTraceAndInspectorDictionarySection = {
  executionTrace: {
    heading: "Investigation progress",
    defaultGroupTitle: "Source analysis and verification",
    runningStatus: "Working...",
    synthesizingStatus: "Drafting synthesis...",
    completedStatus: "Analysis completed",
    pausedWriteStatus: "Waiting for your confirmation before publishing",
    cancelledStatus: "Analysis stopped",
    failedStatus: "Analysis interrupted",
    stepsCountLabel: (count: number) => `${count} action${count > 1 ? "s" : ""}`,
    thoughtSummaryLabel: (seconds: number) => `Thought for ${seconds}s`,
    thoughtInProgressLabel: "Thinking",
    analyzedPrefix: "Analyzed",
    linesRangeShort: (start: number, end: number) => `#L${start}-${end}`,
    redactedPillSuffix: "Access required",
    delegatedPrefix: (agentHandle: string) => `Delegated to ${agentHandle}`,
    synthesizeNowButtonLabel: "Synthesize now",
    synthesizeNowButtonHint:
      "Wrap up immediately using the findings gathered so far.",
    writePreviewHeading: "Confirmation required before external action",
    writePreviewTargetPrefix: "Target tool:",
    approveWriteButtonLabel: "Approve publication",
    rejectWriteButtonLabel: "Decline",
    expandGroupAriaLabel: "Expand step",
    collapseGroupAriaLabel: "Collapse step",
  },
  sourceLineInspector: {
    dialogAriaLabel: "Source excerpt inspector",
    linesSliceSummary: (startLine: number, endLine: number, totalLines: number) =>
      `Lines ${startLine} – ${endLine} of ${totalLines}`,
    copySliceButtonLabel: (startLine: number, endLine: number) =>
      `Copy excerpt #L${startLine}-${endLine}`,
    copiedSliceFeedbackLabel: "Excerpt copied",
    closeButtonLabel: "Close",
    loadingLabel: "Loading verified excerpt...",
    redactedTitle: "Protected excerpt (permission required)",
    redactedBody:
      "Your account does not have read permission for this source. No document lines are exposed.",
    redactedHintPrefix: "Access request:",
    emptySliceLabel: "No lines available in the requested range.",
  },
  reflexiveTraceFeedback: {
    loadInspectorFailed: (detail: string) =>
      `Unable to load source excerpt (${detail}).`,
    executionStartFailed: (detail: string) =>
      `Unable to start analysis (${detail}).`,
    synthesizeRequestedBanner:
      "Immediate synthesis requested: drafting response from gathered findings.",
    executionCancelledBanner: "Execution stopped at your request.",
    writeApprovedBanner:
      "External publication approved: resuming and completing deliverable.",
    writeRejectedBanner:
      "External publication declined: no changes were sent to the target tool.",
    actionFailed: (detail: string) =>
      `Action could not be completed (${detail}).`,
  },
};
