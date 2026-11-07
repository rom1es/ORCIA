import type {
  UiAssistantAttachedFileItem,
  UiAssistantSpeedMode,
  UiInferenceEffort,
  UiInferenceTier,
  UiThreeSpeedStepProgress,
} from "@orcia/ui";
import type { SavedAssistantConversation } from "./savedConversationsStore";

export interface CompletedAssistantTurnPayload {
  readonly turnId?: string;
  readonly userPrompt: string;
  readonly assistantReply: string;
  readonly assembledSystemPrompt?: string;
  readonly thinkingText?: string;
  readonly conversationHistoryCount?: number;
  readonly folderTitle?: string | null;
  readonly folderPinnedNotes?: string | null;
  readonly requestedTier: UiInferenceTier;
  readonly thinkingEffort: UiInferenceEffort;
  readonly attachedFiles?: readonly UiAssistantAttachedFileItem[];
  readonly stepProgress?: readonly UiThreeSpeedStepProgress[];
  readonly thinkingElapsedSeconds?: number;
}

export interface BackgroundAssistantStreamSnapshot {
  streamedText: string;
  activeUserPrompt: string;
  stepProgress: readonly UiThreeSpeedStepProgress[];
  cacheHit: boolean;
  cacheLookupMs: number;
  nodes1To4Ms: number;
  ttftMs: number;
  isGenerating: boolean;
  thinkingStartedAtMs: number | null;
  generationStopped: boolean;
  errorMessage: string | null;
}

const bgListeners = new Set<() => void>();
let bgAbortController: AbortController | null = null;
let bgTimers: ReturnType<typeof setTimeout>[] = [];
let bgOnTurnCompletedCallback: ((params: CompletedAssistantTurnPayload) => void) | null = null;

export let bgSnapshot: BackgroundAssistantStreamSnapshot = {
  streamedText: "",
  activeUserPrompt: "",
  stepProgress: [],
  cacheHit: false,
  cacheLookupMs: 0,
  nodes1To4Ms: 0,
  ttftMs: 0,
  isGenerating: false,
  thinkingStartedAtMs: null,
  generationStopped: false,
  errorMessage: null,
};

export function subscribeBgStream(listener: () => void): () => void {
  bgListeners.add(listener);
  return () => {
    bgListeners.delete(listener);
  };
}

export function setBgOnTurnCompletedCallback(
  cb: ((params: CompletedAssistantTurnPayload) => void) | null,
): void {
  bgOnTurnCompletedCallback = cb;
}

export function invokeBgOnTurnCompleted(params: CompletedAssistantTurnPayload): void {
  bgOnTurnCompletedCallback?.(params);
}

export function getBgAbortController(): AbortController | null {
  return bgAbortController;
}

export function setBgAbortController(controller: AbortController | null): void {
  bgAbortController = controller;
}

export function clearBgTimers(): void {
  for (const t of bgTimers) clearTimeout(t);
  bgTimers = [];
}

export function addBgTimer(timer: ReturnType<typeof setTimeout>): void {
  bgTimers.push(timer);
}

export function updateBgSnapshot(patch: Partial<BackgroundAssistantStreamSnapshot>): void {
  bgSnapshot = { ...bgSnapshot, ...patch };
  for (const listener of bgListeners) listener();
}

export function resetBackgroundAssistantStreamForTests(): void {
  bgAbortController?.abort();
  bgAbortController = null;
  clearBgTimers();
  bgSnapshot = {
    streamedText: "",
    activeUserPrompt: "",
    stepProgress: [],
    cacheHit: false,
    cacheLookupMs: 0,
    nodes1To4Ms: 0,
    ttftMs: 0,
    isGenerating: false,
    thinkingStartedAtMs: null,
    generationStopped: false,
    errorMessage: null,
  };
}

export function detectAdaptiveThinkingStepsForQuestion(
  userPrompt: string,
  isFr = true,
): readonly UiThreeSpeedStepProgress[] {
  const lower = userPrompt.toLowerCase();
  const buildStep = (
    stepCode: string,
    label: string,
    durationMs: number,
    intermediateOutput: string,
  ): UiThreeSpeedStepProgress => ({
    stepCode,
    label,
    durationMs,
    status: "COMPLETED",
    intermediateOutput,
  });

  if (/\b(code|coder|fonction|python|sql|bug|script|algorithme|api|test|typescript|react|classe|boucle|erreur)\b/i.test(lower)) {
    return [
      buildStep("STEP_1_SPEC_EDGE_CASES", isFr ? "Spécification et cas limites" : "Specification and edge cases", 1100, isFr ? "Cadrage des entrées/sorties, complexité et cas particuliers pour la demande." : "Framing inputs/outputs, complexity, and edge cases for the request."),
      buildStep("STEP_2_IMPLEMENTATION_DESIGN", isFr ? "Conception de l'implémentation" : "Implementation design", 1400, isFr ? "Structuration du code et choix techniques adaptés." : "Code structuring and technical choices."),
      buildStep("STEP_3_VERIFICATION_EXAMPLE", isFr ? "Vérification et exemple d'usage" : "Verification and usage example", 900, isFr ? "Contrôle de validité et préparation d'un cas de test." : "Validity check and test case preparation."),
    ];
  }
  if (/\b(explique|expliquer|résume|résumer|document|contrat|texte|synthèse|rapport|note|dossier|extrait)\b/i.test(lower)) {
    return [
      buildStep("STEP_1_KEY_POINTS_EXTRACTION", isFr ? "Extraction des points clés" : "Extracting key points", 1100, isFr ? "Repérage des idées principales et de la structure." : "Identifying main ideas and structure."),
      buildStep("STEP_2_WORKSPACE_CONTEXT_CROSS", isFr ? "Croisement avec le contexte de l'espace" : "Cross-referencing workspace context", 1300, isFr ? "Mise en regard avec le glossaire et les règles métiers." : "Aligning with glossary and business rules."),
      buildStep("STEP_3_PEDAGOGICAL_STRUCTURING", isFr ? "Structuration pédagogique" : "Pedagogical structuring", 900, isFr ? "Organisation claire de l'explication." : "Clear organization of the explanation."),
    ];
  }
  if (/\b(choisir|comparer|comparaison|option|options|avantage|avantages|risque|risques|pourquoi|quel|quelle|quels|quelles|arbitrage|versus)\b/i.test(lower)) {
    return [
      buildStep("STEP_1_EVALUATION_CRITERIA", isFr ? "Critères d'évaluation" : "Evaluation criteria", 1000, isFr ? "Définition des axes de comparaison pertinents." : "Defining relevant comparison axes."),
      buildStep("STEP_2_OPTIONS_AND_RISKS", isFr ? "Analyse des options et points de vigilance" : "Analyzing options and watchpoints", 1400, isFr ? "Pesée des avantages et limites de chaque piste." : "Weighing pros and limitations of each option."),
      buildStep("STEP_3_ARGUED_RECOMMENDATION", isFr ? "Recommandation argumentée" : "Reasoned recommendation", 900, isFr ? "Synthèse décisionnelle structurée." : "Structured decision summary."),
    ];
  }
  return [
    buildStep("STEP_1_REQUEST_FRAMING", isFr ? "Cadrage de la demande" : "Framing the request", 1000, isFr ? "Identification des objectifs et du périmètre de la question." : "Identifying objectives and scope of the question."),
    buildStep("STEP_2_DEEP_ANALYSIS_SOURCES", isFr ? "Analyse approfondie et sources" : "In-depth analysis and sources", 1400, isFr ? "Exploration détaillée des éléments de réponse et références." : "Detailed exploration of answer elements and references."),
    buildStep("STEP_3_RESPONSE_CONSOLIDATION", isFr ? "Consolidation de la réponse" : "Response consolidation", 900, isFr ? "Mise en forme structurée et synthétique." : "Structured and concise formatting."),
  ];
}

export function shouldUseProgressiveStepThinking(params: {
  readonly userPrompt: string;
  readonly requestedSpeed: UiAssistantSpeedMode;
  readonly deepAuditPillActive: boolean;
  readonly thinkingEffort?: UiInferenceEffort;
}): boolean {
  if (
    params.deepAuditPillActive ||
    params.thinkingEffort === "deep" ||
    params.requestedSpeed === "SPEED_3_DEEP_AUDIT" ||
    params.requestedSpeed === "SPEED_2_AGENT_TOOLS"
  ) {
    return true;
  }
  return /(?:^|\s)(@[a-zA-Z0-9_-]+|\/[a-zA-Z0-9_-]+)/.test(params.userPrompt);
}

export function buildConversationHistoryPayload(
  conversation?: SavedAssistantConversation | null,
): Array<{ role: "user" | "assistant"; content: string }> {
  if (!conversation || !conversation.turns.length) return [];
  const history: Array<{ role: "user" | "assistant"; content: string }> = [];
  for (const turn of conversation.turns) {
    if (turn.userPrompt.trim()) history.push({ role: "user", content: turn.userPrompt.trim() });
    if (turn.assistantReply.trim()) {
      history.push({ role: "assistant", content: turn.assistantReply.trim() });
    }
  }
  return history;
}
