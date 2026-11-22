import {
  createOrciaApiClient,
  type AssistantThreadMessageSchemaItem,
  type AssistantThreadSchemaItem,
} from "@orcia/api-client";
import { sanitizeAssistantDisplayReply, type UiAssistantModelOption } from "@orcia/ui";
import { useCallback, useEffect, useRef, useState } from "react";
import { formatRfc9457ErrorToBanner } from "../../lib/formatRfc9457ErrorToBanner";
import { citationMapToRagItems, parseServerCitationMap } from "./inboxCitationHelpers";
import type { SavedAssistantConversation, SavedConversationTurnItem } from "./savedConversationsStore";

function errorDetail(err: unknown, locale: string): string {
  return formatRfc9457ErrorToBanner(err, locale === "en" ? "en" : "fr", "Mon Assistant").fullText;
}

export function mapServerMessagesToConversationTurns(
  messages: readonly AssistantThreadMessageSchemaItem[],
  modelLabel: string,
): readonly SavedConversationTurnItem[] {
  const grouped = new Map<
    string,
    { user?: AssistantThreadMessageSchemaItem; assistant?: AssistantThreadMessageSchemaItem }
  >();
  const orderedTurnIds: string[] = [];

  for (const msg of messages) {
    let slot = grouped.get(msg.turn_id);
    if (!slot) {
      slot = {};
      grouped.set(msg.turn_id, slot);
      orderedTurnIds.push(msg.turn_id);
    }
    if (msg.role === "user") slot.user = msg;
    else slot.assistant = msg;
  }

  return orderedTurnIds
    .map((turnId): SavedConversationTurnItem | null => {
      const pair = grouped.get(turnId);
      if (!pair) return null;
      const userPrompt = pair.user?.content ?? "";
      const assistantReply = sanitizeAssistantDisplayReply(pair.assistant?.content ?? "");
      const citationMap = pair.assistant?.citation_map;
      const parsedCitations = parseServerCitationMap(citationMap);
      const usedSources = citationMapToRagItems(citationMap);
      const parentTurnId = pair.assistant?.parent_turn_id ?? pair.user?.parent_turn_id ?? null;
      const timestampIso =
        pair.assistant?.created_at ?? pair.user?.created_at ?? new Date().toISOString();

      return {
        turnId,
        userPrompt,
        assistantReply,
        modelTier: "medium",
        modelLabel,
        thinkingEffort: "balanced",
        effortLabel: "Standard",
        timestampIso,
        ...(parentTurnId ? { parentTurnId } : {}),
        ...(citationMap ? { citationMap } : {}),
        ...(usedSources.length > 0 ? { usedSources } : {}),
        ...(parsedCitations.sources.length === 0 && parsedCitations.glossaryItems.length === 0
          ? { lowEvidence: false }
          : {}),
      };
    })
    .filter((item): item is SavedConversationTurnItem => item !== null);
}

export function useServerAssistantThreads(params: {
  readonly workspaceId: string;
  readonly locale: string;
  readonly modelOptions: readonly UiAssistantModelOption[];
  readonly onFeedback: (message: string) => void;
}) {
  const { workspaceId, locale, modelOptions, onFeedback } = params;
  const [conversations, setConversations] = useState<readonly SavedAssistantConversation[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null);
  const [isLoadingThreads, setIsLoadingThreads] = useState<boolean>(false);
  const activeIdRef = useRef<string | null>(null);
  activeIdRef.current = activeConversationId;

  const defaultModelLabel =
    modelOptions.find((m) => m.tier === "medium")?.configuredModelName ??
    modelOptions[1]?.title ??
    "Mon Assistant";

  const refreshThreadsOverview = useCallback(async (): Promise<readonly AssistantThreadSchemaItem[]> => {
    if (!workspaceId) {
      setConversations([]);
      setActiveConversationId(null);
      return [];
    }
    setIsLoadingThreads(true);
    try {
      const overview = await createOrciaApiClient({ baseUrl: "" }).listAssistantFolders(workspaceId);
      const serverThreads = overview.threads ?? [];
      setConversations((prev) => {
        const prevMap = new Map(prev.map((c) => [c.id, c]));
        return serverThreads.map((t) => {
          const existing = prevMap.get(t.thread_id);
          return {
            id: t.thread_id,
            workspaceId: t.workspace_id,
            ...(t.folder_id ? { folderId: t.folder_id } : {}),
            title: t.title,
            createdAtIso: existing?.createdAtIso ?? new Date().toISOString(),
            updatedAtIso: new Date().toISOString(),
            modelTier: existing?.modelTier ?? "medium",
            modelLabel: existing?.modelLabel ?? defaultModelLabel,
            thinkingEffort: existing?.thinkingEffort ?? "balanced",
            turns: existing?.turns ?? [],
          };
        });
      });
      setActiveConversationId((prevId) => {
        if (prevId && serverThreads.some((t) => t.thread_id === prevId)) return prevId;
        return serverThreads[0]?.thread_id ?? null;
      });
      return serverThreads;
    } catch (err: unknown) {
      onFeedback(errorDetail(err, locale));
      return [];
    } finally {
      setIsLoadingThreads(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [workspaceId, defaultModelLabel]);

  const loadThreadMessages = useCallback(
    async (threadId: string): Promise<void> => {
      if (!workspaceId || !threadId) return;
      try {
        const client = createOrciaApiClient({ baseUrl: "" });
        const resp = await client.listAssistantThreadMessages(
          threadId,
          workspaceId,
        );
        const mappedTurns = mapServerMessagesToConversationTurns(
          resp.messages ?? [],
          defaultModelLabel,
        );
        setConversations((prev) =>
          prev.map((conv) =>
            conv.id === threadId ? { ...conv, turns: mappedTurns } : conv,
          ),
        );
      } catch (err: unknown) {
        onFeedback(errorDetail(err, locale));
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [workspaceId, defaultModelLabel],
  );

  useEffect(() => {
    void refreshThreadsOverview();
  }, [refreshThreadsOverview]);

  useEffect(() => {
    if (!workspaceId || !activeConversationId) return;
    void loadThreadMessages(activeConversationId);
  }, [workspaceId, activeConversationId, loadThreadMessages]);

  const ensureThreadForTurn = useCallback(
    async (titleSeed: string, folderId?: string | null): Promise<string> => {
      if (activeIdRef.current) return activeIdRef.current;
      const client = createOrciaApiClient({ baseUrl: "" });
      const title = titleSeed.trim().slice(0, 72) || "Nouvelle discussion";
      const created = await client.createAssistantThread({
        workspace_id: workspaceId,
        title,
        ...(folderId ? { folder_id: folderId } : {}),
      });
      const nextConv: SavedAssistantConversation = {
        id: created.thread_id,
        workspaceId: created.workspace_id,
        ...(created.folder_id ? { folderId: created.folder_id } : {}),
        title: created.title,
        createdAtIso: new Date().toISOString(),
        updatedAtIso: new Date().toISOString(),
        modelTier: "medium",
        modelLabel: defaultModelLabel,
        thinkingEffort: "balanced",
        turns: [],
      };
      setConversations((prev) => [nextConv, ...prev.filter((c) => c.id !== created.thread_id)]);
      setActiveConversationId(created.thread_id);
      activeIdRef.current = created.thread_id;
      return created.thread_id;
    },
    [workspaceId, defaultModelLabel],
  );

  const startNewThread = useCallback(() => {
    setActiveConversationId(null);
    activeIdRef.current = null;
  }, []);

  return {
    conversations,
    setConversations,
    activeConversationId,
    setActiveConversationId,
    isLoadingThreads,
    refreshThreadsOverview,
    loadThreadMessages,
    ensureThreadForTurn,
    startNewThread,
  };
}
