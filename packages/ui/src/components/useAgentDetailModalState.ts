import { useEffect, useRef, useState } from "react";
import {
  createDefaultAgentSixBlocksDraft,
  pickAgentComparableFields,
  resolveAgentLifecycleAndBenchStatus,
  type AgentSixBlocksDraftState,
  type AgentStudioBlockKey,
} from "./AgentGovernanceTypesAndDefaults";
import type {
  AgentsAndSkillsManagerLabels,
  UiAgentLifecycleStatus,
  UiAgentSkillVisibilityScope,
  UiAgentThinkingLevel,
  UiManagedAgentItem,
} from "./AgentsAndSkillsTypes";
import { useUnsavedChangesDialogGuard } from "./RgaaModalDialog";

export interface UseAgentDetailModalStateParams {
  readonly agent: UiManagedAgentItem | null;
  readonly labels: AgentsAndSkillsManagerLabels;
  readonly modalError?: string | null;
  readonly testInputValue: string;
  readonly onChangeTestInput: (agentId: string, nextValue: string) => void;
  readonly onToggleAgentSkill: (
    agentId: string,
    skillId: string,
    nextChecked: boolean,
  ) => Promise<boolean> | boolean | void;
  readonly onExecuteAgent: (agentId: string, prompt: string) => Promise<boolean> | boolean | void;
  readonly onToggleAgentMcpExposure?: (
    agentId: string,
    nextExposed: boolean,
  ) => Promise<boolean> | boolean | void;
  readonly onUpdateAgentLifecycle?: (
    agentId: string,
    nextLifecycle: UiAgentLifecycleStatus,
  ) => Promise<boolean> | boolean | void;
  readonly onUpdateAgentDetails?: (
    agentId: string,
    patch: Partial<AgentSixBlocksDraftState> & {
      name: string;
      roleMission: string;
      instructions: string;
      thinkingLevel: UiAgentThinkingLevel;
      visibilityScope?: UiAgentSkillVisibilityScope;
      mcpExposed?: boolean;
    },
  ) => Promise<boolean> | boolean | void;
  readonly onClearModalError?: () => void;
  readonly onClose: () => void;
}

export function useAgentDetailModalState(params: UseAgentDetailModalStateParams) {
  const {
    agent,
    labels,
    modalError,
    testInputValue,
    onChangeTestInput,
    onToggleAgentSkill,
    onExecuteAgent,
    onToggleAgentMcpExposure,
    onUpdateAgentLifecycle,
    onUpdateAgentDetails,
    onClearModalError,
    onClose,
  } = params;
  const studio = labels.studio;

  const [baseline, setBaseline] = useState<AgentSixBlocksDraftState>(() =>
    createDefaultAgentSixBlocksDraft(agent),
  );
  const [draft, setDraft] = useState<AgentSixBlocksDraftState>(() =>
    createDefaultAgentSixBlocksDraft(agent),
  );
  const [mcpExposed, setMcpExposed] = useState<boolean>(() => Boolean(agent?.mcpExposed));
  const [activeBlock, setActiveBlock] = useState<AgentStudioBlockKey>("A");
  const [showAllBlocks, setShowAllBlocks] = useState<boolean>(true);
  const [savedFeedback, setSavedFeedback] = useState<boolean>(false);
  const [localError, setLocalError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState<boolean>(false);
  const [isUpdatingMcp, setIsUpdatingMcp] = useState<boolean>(false);
  const [isUpdatingLifecycle, setIsUpdatingLifecycle] = useState<boolean>(false);

  const isDirty =
    Boolean(agent) && pickAgentComparableFields(draft) !== pickAgentComparableFields(baseline);
  const isDirtyOrSavingRef = useRef<boolean>(false);
  isDirtyOrSavingRef.current = isDirty || isSaving;
  const lastAgentIdRef = useRef<string | null>(agent?.agentId ?? null);

  useEffect(() => {
    const nextId = agent?.agentId ?? null;
    if (nextId !== lastAgentIdRef.current) {
      lastAgentIdRef.current = nextId;
      const fresh = createDefaultAgentSixBlocksDraft(agent);
      setBaseline(fresh);
      setDraft(fresh);
      setMcpExposed(Boolean(agent?.mcpExposed));
      setSavedFeedback(false);
      setLocalError(null);
      setIsSaving(false);
      setIsUpdatingMcp(false);
      setIsUpdatingLifecycle(false);
      return;
    }
    if (!agent) return;
    if (!isUpdatingMcp) {
      setMcpExposed(Boolean(agent.mcpExposed));
    }
    const resolved = resolveAgentLifecycleAndBenchStatus(agent);
    if (!isDirtyOrSavingRef.current) {
      const fresh = createDefaultAgentSixBlocksDraft(agent);
      setBaseline(fresh);
      setDraft(fresh);
    } else {
      setDraft((prev) => ({
        ...prev,
        skillIds: agent.skillIds,
        lifecycleStatus: resolved.lifecycleStatus,
        testBenchStatus: resolved.testBenchStatus,
        testBenchValidated: resolved.testBenchStatus === "PASSED",
      }));
      setBaseline((prev) => ({
        ...prev,
        skillIds: agent.skillIds,
        lifecycleStatus: resolved.lifecycleStatus,
        testBenchStatus: resolved.testBenchStatus,
        testBenchValidated: resolved.testBenchStatus === "PASSED",
      }));
    }
  }, [agent, isUpdatingMcp]);

  const resetDraftToBaseline = (): void => {
    setDraft(baseline);
    setLocalError(null);
    onClearModalError?.();
  };

  const handleCloseClean = (): void => {
    setLocalError(null);
    setSavedFeedback(false);
    onClearModalError?.();
    onClose();
  };

  const guard = useUnsavedChangesDialogGuard({
    isOpen: Boolean(agent),
    isDirty,
    onClose: handleCloseClean,
    onDiscardChanges: resetDraftToBaseline,
  });

  const handleChangeDraft = (patch: Partial<AgentSixBlocksDraftState>): void => {
    setDraft((prev) => ({ ...prev, ...patch }));
    setSavedFeedback(false);
    setLocalError(null);
    onClearModalError?.();
  };

  const resolveFallbackError = (): string => studio.saveErrorFallback;

  const runAsyncModalMutation = async (opts: {
    readonly execute: () => Promise<boolean | void> | boolean | void;
    readonly onSuccess?: () => void;
    readonly onRollback?: () => void;
    readonly setBusy?: (busy: boolean) => void;
  }): Promise<boolean> => {
    opts.setBusy?.(true);
    setSavedFeedback(false);
    setLocalError(null);
    onClearModalError?.();
    const fallbackMsg = resolveFallbackError();
    try {
      const res = await opts.execute();
      if (res === false) {
        opts.onRollback?.();
        setLocalError(fallbackMsg);
        return false;
      }
      opts.onSuccess?.();
      setSavedFeedback(true);
      return true;
    } catch (err: unknown) {
      opts.onRollback?.();
      setLocalError(err instanceof Error && err.message.trim() ? err.message : fallbackMsg);
      return false;
    } finally {
      opts.setBusy?.(false);
    }
  };

  const handleSaveDetails = async (): Promise<void> => {
    if (!agent || agent.visibilityScope === "PACK" || !isDirty || isSaving) return;
    const savedDraft: AgentSixBlocksDraftState = {
      ...draft,
      name: draft.name.trim() || agent.name,
      roleMission: draft.roleMission.trim() || agent.roleMission,
      instructions: draft.instructions.trim() || agent.instructions,
    };
    await runAsyncModalMutation({
      setBusy: setIsSaving,
      execute: () =>
        onUpdateAgentDetails?.(agent.agentId, {
          ...savedDraft,
          thinkingLevel: savedDraft.thinkingLevel,
          visibilityScope: savedDraft.visibilityScope,
          mcpExposed,
        }),
      onSuccess: () => {
        setDraft(savedDraft);
        setBaseline(savedDraft);
      },
    });
  };

  const handleToggleMcp = async (nextChecked: boolean): Promise<void> => {
    if (!agent || isUpdatingMcp) return;
    const prev = mcpExposed;
    setMcpExposed(nextChecked);
    await runAsyncModalMutation({
      setBusy: setIsUpdatingMcp,
      execute: () => onToggleAgentMcpExposure?.(agent.agentId, nextChecked),
      onRollback: () => setMcpExposed(prev),
    });
  };

  const handleToggleSkill = async (skillId: string, nextChecked: boolean): Promise<void> => {
    if (!agent) return;
    const prevIds = draft.skillIds;
    const nextIds = nextChecked
      ? Array.from(new Set([...prevIds, skillId]))
      : prevIds.filter((id) => id !== skillId);
    setDraft((prev) => ({ ...prev, skillIds: nextIds }));
    await runAsyncModalMutation({
      execute: () => onToggleAgentSkill(agent.agentId, skillId, nextChecked),
      onRollback: () => setDraft((prev) => ({ ...prev, skillIds: prevIds })),
      onSuccess: () => setBaseline((prev) => ({ ...prev, skillIds: nextIds })),
    });
  };

  const handleToggleLifecycle = async (nextLifecycle: UiAgentLifecycleStatus): Promise<void> => {
    if (!agent || isUpdatingLifecycle) return;
    await runAsyncModalMutation({
      setBusy: setIsUpdatingLifecycle,
      execute: () => onUpdateAgentLifecycle?.(agent.agentId, nextLifecycle),
      onSuccess: () => {
        if (nextLifecycle === "DRAFT") setMcpExposed(false);
      },
    });
  };

  const handleRunAgent = async (): Promise<void> => {
    if (!agent || agent.visibilityScope === "PACK") return;
    const raw = testInputValue.trim();
    const prompt =
      raw ||
      studio.defaultTestPromptTemplate
        .replace("{name}", agent.name)
        .replace("{role}", agent.roleMission);
    if (!raw) onChangeTestInput(agent.agentId, prompt);
    setLocalError(null);
    onClearModalError?.();
    try {
      await onExecuteAgent(agent.agentId, prompt);
    } catch (err: unknown) {
      setLocalError(
        err instanceof Error && err.message.trim() ? err.message : resolveFallbackError(),
      );
    }
  };

  return {
    draft,
    mcpExposed,
    activeBlock,
    setActiveBlock,
    showAllBlocks,
    setShowAllBlocks,
    savedFeedback,
    displayedError: modalError || localError,
    isDirty,
    isSaving,
    isUpdatingMcp,
    isUpdatingLifecycle,
    guard,
    handleChangeDraft,
    handleSaveDetails,
    handleToggleMcp,
    handleToggleSkill,
    handleToggleLifecycle,
    handleRunAgent,
  };
}
