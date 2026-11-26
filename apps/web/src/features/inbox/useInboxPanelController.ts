import type { UiAssistantPromptTelemetryRecord } from "@orcia/ui";
import { useEffect, useMemo, useState } from "react";
import { readAssistantPrefillPrompt } from "../../components/agentsAndSkillsBridgeStore";
import { usePlatformSetup } from "../../components/platformSetupStore";
import { useShellNavigation } from "../../components/ShellContainer";
import { resolveEffectiveWorkspaceId } from "../../components/shellScopeOptions";
import { useI18n } from "../../i18n";
import { isPlatformAdministratorSession, useAuthSessionStore } from "../../stores/authSessionStore";
import { useSyncManagedAgentsCache } from "../../components/useSyncManagedAgentsCache";
import { useSourceLineInspector } from "../shared/useSourceLineInspector";
import { readSavedActiveFolderId, writeSavedActiveFolderId } from "./assistantFoldersAndPrefsStore";
import { persistCompletedInboxTurn, persistInboxTurnFeedback } from "./inboxTurnSyncHelpers";
import { buildAssistantAutocompleteAndRagOptions, buildAssistantAutocompleteSuggestions, buildAssistantModelOptions, consumeAssistantPrefillFromStorage, type SavedConversationTurnItem } from "./savedConversationsStore";
import { useActiveEmbeddingModelStatus } from "./useActiveEmbeddingModelStatus";
import { useAssistantStreamingTurn } from "./useAssistantStreamingTurn";
import { useRagReindexStatus } from "./useRagReindexStatus";
import { useServerAssistantFolders } from "./useServerAssistantFolders";
import { useServerAssistantGovernance } from "./useServerAssistantGovernance";
import { useServerAssistantThreads } from "./useServerAssistantThreads";

export const ASSISTANT_REFLEXIVE_STORAGE_KEY =
  "orcia.reflexive_exec.assistant.v1";

export function useInboxPanelController() {
  const { dictionary, locale, isFr } = useI18n();
  const { activeScopeId } = useShellNavigation();
  const authEmail = useAuthSessionStore((s) => s.email);
  const authRoles = useAuthSessionStore((s) => s.roles);
  const authReadOnlyObserver = useAuthSessionStore((s) => s.readOnlyObserver);
  const sessionActiveHat = useAuthSessionStore((s) => s.activeHat);
  const canConfigureAiModels = isPlatformAdministratorSession({
    roles: authRoles,
    readOnlyObserver: authReadOnlyObserver,
  });
  const {
    platformAdmin,
    workspaces,
    llmTiers,
    datasources,
    catalogItems,
    packs,
  } = usePlatformSetup();

  const [prefillPrompt, setPrefillPrompt] = useState<string | null>(null);
  useEffect(() => {
    const next = readAssistantPrefillPrompt();
    if (!next) return;
    setPrefillPrompt(next);
    const timer = window.setTimeout(() => {
      consumeAssistantPrefillFromStorage();
    }, 0);
    return () => window.clearTimeout(timer);
  }, []);

  const [activeFolderId, setActiveFolderId] = useState<string>(() =>
    readSavedActiveFolderId(),
  );
  const [foldersPanelOpen, setFoldersPanelOpen] = useState<boolean>(false);
  const [savedConversationsOpen, setSavedConversationsOpen] =
    useState<boolean>(false);
  const [governanceOpen, setGovernanceOpen] = useState<boolean>(false);
  const [governanceFeedback, setGovernanceFeedback] = useState<string | null>(null);

  const activeWorkspaceId = resolveEffectiveWorkspaceId(
    activeScopeId,
    workspaces,
    authEmail ?? platformAdmin?.email,
  );
  const {
    hasActiveEmbeddingModel,
    hasActiveChatModel: hasHubChatModel,
    hasSupportsTools: hasHubSupportsTools,
  } = useActiveEmbeddingModelStatus();
  const hasActiveChatModel =
    hasHubChatModel || llmTiers.some((t) => Boolean(t.primaryModel?.trim()));
  const ragReindex = useRagReindexStatus();
  const assistantInputBlocked = !hasActiveChatModel;

  const modelOptions = buildAssistantModelOptions(llmTiers, isFr);
  const threads = useServerAssistantThreads({
    workspaceId: activeWorkspaceId,
    locale,
    modelOptions,
    onFeedback: setGovernanceFeedback,
  });
  const governance = useServerAssistantGovernance({
    workspaceId: activeWorkspaceId,
    locale,
    onFeedback: setGovernanceFeedback,
  });
  const foldersController = useServerAssistantFolders({
    workspaceId: activeWorkspaceId,
    messages: dictionary.assistantFoldersSync,
    onFeedback: setGovernanceFeedback,
  });
  const inspector = useSourceLineInspector({
    locale,
    workspaceId: activeWorkspaceId,
    onFeedback: setGovernanceFeedback,
  });

  useEffect(() => {
    if (governance.governanceSaveMessage) {
      setGovernanceFeedback(governance.governanceSaveMessage);
    }
  }, [governance.governanceSaveMessage]);

  const savedConversations = threads.conversations;
  const activeConversationId = threads.activeConversationId;
  const activeConversation =
    savedConversations.find((c) => c.id === activeConversationId) ?? null;
  const activeFolder =
    foldersController.folders.find((f) => f.folderId === activeFolderId) ?? null;
  const promptTelemetryLog = useMemo<readonly UiAssistantPromptTelemetryRecord[]>(() => {
    const foldersById = new Map(foldersController.folders.map((f) => [f.folderId, f]));
    const rows: UiAssistantPromptTelemetryRecord[] = [];
    for (const conv of savedConversations) {
      const folder = conv.folderId ? foldersById.get(conv.folderId) : undefined;
      conv.turns.forEach((turn, idx) => {
        rows.push({
          turnId: turn.turnId,
          timestampIso: turn.timestampIso,
          userPrompt: turn.userPrompt,
          assembledSystemPrompt: turn.assembledSystemPrompt ?? "",
          conversationHistoryCount: idx * 2,
          folderTitle: folder?.title ?? null,
          folderPinnedNotes: folder?.pinnedNotesMarkdown ?? null,
          assistantReply: turn.assistantReply,
          modelLabel: turn.modelLabel,
          thinkingEffort: turn.thinkingEffort,
          thinkingElapsedSeconds: turn.thinkingElapsedSeconds ?? 1,
          userFeedback: turn.userFeedback ?? null,
        });
      });
    }
    return rows.slice(-100).reverse();
  }, [savedConversations, foldersController.folders]);
  const [agentsSyncTick] = useSyncManagedAgentsCache(
    locale,
    dictionary.featureAdminCatalogSettings.catalog.defaultSkillOutputFormat,
  );
  const { agentOptions, skillOptions, orciaDocuments, ragCitations } = useMemo(
    () => buildAssistantAutocompleteAndRagOptions({ catalogItems, datasources, isFr }),
    [catalogItems, datasources, isFr, agentsSyncTick],
  );
  const autocompleteSuggestions = useMemo(
    () => buildAssistantAutocompleteSuggestions(packs, isFr),
    [packs, isFr, agentsSyncTick],
  );
  const selectActiveConversationAndPersist = (nextConvId: string | null) =>
    threads.setActiveConversationId(nextConvId);

  useEffect(() => {
    const onPrefill = () => {
      const next = consumeAssistantPrefillFromStorage();
      if (next) setPrefillPrompt(next);
    };
    window.addEventListener("orcia:assistant-prefill", onPrefill);
    return () => window.removeEventListener("orcia:assistant-prefill", onPrefill);
  }, []);

  const selectActiveFolderAndPersist = (nextFolderId: string) => {
    setActiveFolderId(nextFolderId);
    writeSavedActiveFolderId(nextFolderId);
  };

  const initialLastReply =
    activeConversation?.turns[activeConversation.turns.length - 1]?.assistantReply ?? "";
  const streaming = useAssistantStreamingTurn({
    activeWorkspaceId,
    isFr,
    initialStreamedText: initialLastReply,
    activeThreadId: activeConversationId,
    ensureThreadForTurn: (promptSeed) =>
      threads.ensureThreadForTurn(promptSeed, activeFolderId || null),
    activeFolder,
    governancePrefs: governance.governancePrefs,
    sessionActiveHat,
    streamErrorLabels: dictionary.assistantStreamErrors,
    onTurnCompleted: (completed) => {
      const res = persistCompletedInboxTurn({
        completed,
        savedConversations: threads.conversations,
        activeConversationId: threads.activeConversationId,
        activeWorkspaceId,
        activeFolderId,
        activeFolder,
        modelOptions,
        isFr,
        reflexiveExecutionId: completed.turnId ?? null,
        reflexiveEvents: completed.traceEvents ?? [],
      });
      threads.setConversations(res.nextConversations);
      threads.setActiveConversationId(res.resolvedConversationId);
    },
  });

  const supportsTools = hasHubSupportsTools && streaming.supportsTools;

  const handleFeedbackTurn = (
    turnId: string,
    feedback: "LIKE" | "DISLIKE" | null,
  ) => {
    const res = persistInboxTurnFeedback({
      conversations: threads.conversations,
      turnId,
      feedback,
      activeWorkspaceId,
      isFr,
      onFeedbackBanner: setGovernanceFeedback,
    });
    threads.setConversations(res.nextConversations);
  };

  const handleSendTurnWithReflexive = (
    payload: Parameters<typeof streaming.sendTurn>[0],
  ) => {
    if (assistantInputBlocked) return;
    streaming.sendTurn(payload);
  };

  const handleDeepenTurn = (turn: SavedConversationTurnItem) => {
    if (assistantInputBlocked || !supportsTools) return;
    streaming.sendTurn({
      userPrompt: turn.userPrompt,
      requestedSpeed: "SPEED_2_AGENT_TOOLS",
      deepAuditPillActive: false,
      parentTurnId: turn.turnId,
    });
  };

  const handleStopAll = () => {
    streaming.stopGeneration();
  };

  const handleDeleteConversation = (convId: string) => {
    threads.setConversations((prev) => prev.filter((c) => c.id !== convId));
    if (activeConversationId === convId) {
      threads.startNewThread();
      streaming.resetStreamState("");
    }
  };

  return {
    dictionary,
    isFr,
    authorEmail: platformAdmin?.email ?? "",
    canConfigureAiModels,
    sessionActiveHat,
    activeWorkspaceId,
    hasActiveEmbeddingModel,
    hasActiveChatModel,
    supportsTools,
    ragReindex,
    assistantInputBlocked,
    prefillPrompt,
    setPrefillPrompt,
    activeFolderId,
    activeFolder,
    governancePrefs: governance.governancePrefs,
    governance,
    foldersPanelOpen,
    setFoldersPanelOpen,
    savedConversationsOpen,
    setSavedConversationsOpen,
    savedConversations,
    activeConversationId,
    activeConversation,
    promptTelemetryLog,
    governanceOpen,
    setGovernanceOpen,
    governanceFeedback,
    setGovernanceFeedback,
    foldersController,
    threads,
    inspector,
    streaming,
    modelOptions,
    agentOptions,
    skillOptions,
    orciaDocuments,
    ragCitations,
    autocompleteSuggestions,
    selectActiveConversationAndPersist,
    selectActiveFolderAndPersist,
    handleFeedbackTurn,
    handleSendTurnWithReflexive,
    handleDeepenTurn,
    handleStopAll,
    handleDeleteConversation,
  };
}
