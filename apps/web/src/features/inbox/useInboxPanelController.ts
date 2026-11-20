import type { UiAssistantPromptTelemetryRecord } from "@orcia/ui";
import { useEffect, useState } from "react";
import { readAssistantPrefillPrompt } from "../../components/agentsAndSkillsBridgeStore";
import { usePlatformSetup } from "../../components/platformSetupStore";
import { useI18n } from "../../i18n";
import { useReflexiveExecutionController } from "../shared/useReflexiveExecutionController";
import { useSourceLineInspector } from "../shared/useSourceLineInspector";
import { subscribeBgStream } from "./assistantBackgroundStreamStore";
import {
  readSavedActiveConversationId,
  readSavedActiveFolderId,
  readSavedAssistantGovernancePrefs,
  readSavedPromptTelemetryLog,
  writeSavedActiveConversationId,
  writeSavedActiveFolderId,
  type SavedAssistantGovernancePrefs,
} from "./assistantFoldersAndPrefsStore";
import {
  persistCompletedInboxTurn,
  persistInboxTurnFeedback,
} from "./inboxTurnSyncHelpers";
import {
  attachReflexiveTraceToConversationLatestTurn,
  buildAssistantAutocompleteAndRagOptions,
  buildAssistantAutocompleteSuggestions,
  buildAssistantModelOptions,
  consumeAssistantPrefillFromStorage,
  readSavedAssistantConversations,
  writeSavedAssistantConversations,
  type SavedAssistantConversation,
} from "./savedConversationsStore";
import { useActiveEmbeddingModelStatus } from "./useActiveEmbeddingModelStatus";
import { useAssistantStreamingTurn } from "./useAssistantStreamingTurn";
import { useRagReindexStatus } from "./useRagReindexStatus";
import { useServerAssistantFolders } from "./useServerAssistantFolders";

export const ASSISTANT_REFLEXIVE_STORAGE_KEY =
  "orcia.reflexive_exec.assistant.v1";

export function useInboxPanelController() {
  const { dictionary, locale } = useI18n();
  const {
    platformAdmin,
    workspaces,
    llmTiers,
    datasources,
    catalogItems,
    packs,
  } = usePlatformSetup();
  const isFr = locale === "fr";

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
  const [governancePrefs, setGovernancePrefs] =
    useState<SavedAssistantGovernancePrefs>(() =>
      readSavedAssistantGovernancePrefs(),
    );
  const [foldersPanelOpen, setFoldersPanelOpen] = useState<boolean>(false);
  const [savedConversationsOpen, setSavedConversationsOpen] =
    useState<boolean>(false);
  const [savedConversations, setSavedConversations] = useState<
    readonly SavedAssistantConversation[]
  >(() => readSavedAssistantConversations());
  const [activeConversationId, setActiveConversationId] = useState<
    string | null
  >(() => {
    const savedId = readSavedActiveConversationId();
    const convs = readSavedAssistantConversations();
    return savedId && convs.some((c) => c.id === savedId)
      ? savedId
      : (convs[0]?.id ?? null);
  });
  const [promptTelemetryLog, setPromptTelemetryLog] = useState<
    readonly UiAssistantPromptTelemetryRecord[]
  >(() => readSavedPromptTelemetryLog());
  const [governanceOpen, setGovernanceOpen] = useState<boolean>(false);
  const [governanceFeedback, setGovernanceFeedback] = useState<string | null>(
    null,
  );

  const activeWorkspaceId = workspaces[0]?.workspaceId ?? "";
  const { hasActiveEmbeddingModel } = useActiveEmbeddingModelStatus();
  const ragReindex = useRagReindexStatus();
  const assistantInputBlocked =
    !hasActiveEmbeddingModel || ragReindex.isReindexing || ragReindex.isReindexFailed;
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

  const reflexive = useReflexiveExecutionController({
    storageKey: ASSISTANT_REFLEXIVE_STORAGE_KEY,
    locale,
    onFeedback: setGovernanceFeedback,
    onSnapshotUpdated: (mapped) => {
      if (mapped.events.length === 0) return;
      const targetConvId =
        readSavedActiveConversationId() ?? activeConversationId;
      if (targetConvId) {
        setSavedConversations(
          attachReflexiveTraceToConversationLatestTurn(
            targetConvId,
            mapped.executionId,
            mapped.events,
          ),
        );
      }
    },
  });

  const modelOptions = buildAssistantModelOptions(llmTiers, isFr);
  const activeConversation =
    savedConversations.find((c) => c.id === activeConversationId) ?? null;
  const activeFolder =
    foldersController.folders.find((f) => f.folderId === activeFolderId) ??
    null;
  const { agentOptions, skillOptions, orciaDocuments, ragCitations } =
    buildAssistantAutocompleteAndRagOptions({ catalogItems, datasources });
  const autocompleteSuggestions = buildAssistantAutocompleteSuggestions(packs);

  const selectActiveConversationAndPersist = (nextConvId: string | null) => {
    setActiveConversationId(nextConvId);
    writeSavedActiveConversationId(nextConvId);
  };

  useEffect(() => {
    const onPrefill = () => {
      const next = consumeAssistantPrefillFromStorage();
      if (next) {
        setPrefillPrompt(next);
      }
    };
    window.addEventListener("orcia:assistant-prefill", onPrefill);
    return () => window.removeEventListener("orcia:assistant-prefill", onPrefill);
  }, []);

  useEffect(() => {
    return subscribeBgStream(() => {
      const latestConvs = readSavedAssistantConversations();
      if (latestConvs.length !== savedConversations.length) {
        setSavedConversations(latestConvs);
      }
      const latestActiveId = readSavedActiveConversationId();
      if (
        latestActiveId &&
        latestActiveId !== activeConversationId &&
        latestConvs.some((c) => c.id === latestActiveId)
      ) {
        setActiveConversationId(latestActiveId);
      }
      setPromptTelemetryLog(readSavedPromptTelemetryLog());
    });
  }, [savedConversations.length, activeConversationId]);

  const selectActiveFolderAndPersist = (nextFolderId: string) => {
    setActiveFolderId(nextFolderId);
    writeSavedActiveFolderId(nextFolderId);
  };

  const firstConv = savedConversations[0];
  const initialLastReply =
    firstConv?.turns[firstConv.turns.length - 1]?.assistantReply ?? "";
  const streaming = useAssistantStreamingTurn({
    activeWorkspaceId,
    isFr,
    initialStreamedText: initialLastReply,
    activeConversation,
    activeFolder,
    governancePrefs,
    streamErrorLabels: dictionary.assistantStreamErrors,
    onTurnCompleted: (completed) => {
      const res = persistCompletedInboxTurn({
        completed,
        savedConversations,
        activeConversationId,
        activeWorkspaceId,
        activeFolderId,
        activeFolder,
        modelOptions,
        datasources,
        isFr,
        reflexiveExecutionId: reflexive.executionId,
        reflexiveEvents: reflexive.events,
        onFeedbackBanner: setGovernanceFeedback,
      });
      setSavedConversations(res.nextConversations);
      selectActiveConversationAndPersist(res.resolvedConversationId);
      setPromptTelemetryLog(res.nextTelemetryLog);
    },
  });

  const handleFeedbackTurn = (
    turnId: string,
    feedback: "LIKE" | "DISLIKE" | null,
  ) => {
    const res = persistInboxTurnFeedback({
      turnId,
      feedback,
      activeWorkspaceId,
      isFr,
      onFeedbackBanner: setGovernanceFeedback,
    });
    setSavedConversations(res.nextConversations);
    setPromptTelemetryLog(res.nextTelemetryLog);
  };

  const handleSendTurnWithReflexive = (
    payload: Parameters<typeof streaming.sendTurn>[0],
  ) => {
    if (assistantInputBlocked) return;
    const agentMatch = /(?:^|\s)@([a-zA-Z0-9_-]+)/.exec(payload.userPrompt);
    const isDeepOrDelegated =
      payload.thinkingEffort === "deep" ||
      payload.deepAuditPillActive ||
      Boolean(agentMatch);
    if (isDeepOrDelegated) {
      void reflexive.startExecution({
        actor_slug: agentMatch?.[1] ?? "assistant",
        objective: payload.userPrompt,
        effort_level:
          payload.thinkingEffort === "deep" || payload.deepAuditPillActive
            ? "high"
            : "medium",
        effort_mode:
          payload.thinkingEffort === "deep" || payload.deepAuditPillActive
            ? "approfondi"
            : "standard",
        allow_sub_agent_delegation: true,
        available_delegate_agents: agentOptions.slice(0, 3).map((a) => a.slug),
        initial_resources: ["docs/product/capabilities.yaml"],
        ...(activeWorkspaceId ? { workspace_id: activeWorkspaceId } : {}),
      });
    } else if (reflexive.executionId) {
      reflexive.clearExecution();
    }
    streaming.sendTurn(payload);
  };

  const handleStopAll = () => {
    streaming.stopGeneration();
    if (
      reflexive.executionId &&
      (reflexive.status === "RUNNING" || reflexive.status === "SYNTHESIZING")
    ) {
      void reflexive.cancelExecution();
    }
  };

  const handleDeleteConversation = (convId: string) => {
    const next = savedConversations.filter((c) => c.id !== convId);
    setSavedConversations(next);
    writeSavedAssistantConversations(next);
    if (activeConversationId === convId) {
      selectActiveConversationAndPersist(null);
      streaming.resetStreamState("");
    }
  };

  return {
    dictionary,
    isFr,
    authorEmail: platformAdmin?.email ?? "",
    activeWorkspaceId,
    hasActiveEmbeddingModel,
    ragReindex,
    assistantInputBlocked,
    prefillPrompt,
    setPrefillPrompt,
    activeFolderId,
    activeFolder,
    governancePrefs,
    setGovernancePrefs,
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
    inspector,
    reflexive,
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
    handleStopAll,
    handleDeleteConversation,
  };
}
