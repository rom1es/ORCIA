import { useEffect, useRef, useState } from "react";
import { useUnsavedChangesDialogGuard } from "../components/RgaaModalDialog";
import type {
  AssistantGovernanceModalAndStudioLabels,
  UiAssistantResponseFormat,
  UiAssistantResponseTone,
} from "./AssistantGovernanceTypes";

export interface UseAssistantGovernanceModalStateParams {
  readonly isOpen: boolean;
  readonly canEditWorkspaceLayer: boolean;
  readonly initialUserTone: UiAssistantResponseTone;
  readonly initialUserFormat: UiAssistantResponseFormat;
  readonly initialDefaultHat: string;
  readonly initialPersonalInstructions: string;
  readonly initialWorkspaceInstructions: string;
  readonly initialMcpExposed: boolean;
  readonly mcpFrozenByUpperLayer: boolean;
  readonly saveError: string | null;
  readonly labels: AssistantGovernanceModalAndStudioLabels;
  readonly onSaveUserPreferences?: (payload: {
    responseTone: UiAssistantResponseTone;
    favoriteFormat: UiAssistantResponseFormat;
    defaultHat: string;
    personalInstructions: string;
  }) => Promise<boolean> | boolean | void;
  readonly onSaveWorkspaceSettings?: (payload: {
    workspaceInstructions: string;
    mcpExposeAssistant: boolean;
  }) => Promise<boolean> | boolean | void;
  readonly onClearSaveError?: () => void;
  readonly onClose?: () => void;
}

export function useAssistantGovernanceModalState({
  isOpen,
  canEditWorkspaceLayer,
  initialUserTone,
  initialUserFormat,
  initialDefaultHat,
  initialPersonalInstructions,
  initialWorkspaceInstructions,
  initialMcpExposed,
  mcpFrozenByUpperLayer,
  saveError,
  labels,
  onSaveUserPreferences,
  onSaveWorkspaceSettings,
  onClearSaveError,
  onClose,
}: UseAssistantGovernanceModalStateParams) {
  const normalizedInitialMcp = mcpFrozenByUpperLayer ? false : initialMcpExposed;
  const [internalOpen, setInternalOpen] = useState<boolean>(true);
  const [activeTab, setActiveTab] = useState<
    "USER_PREFS" | "WORKSPACE_SETTINGS" | "FULL_ASSEMBLY"
  >("USER_PREFS");

  const [baselineUserTone, setBaselineUserTone] = useState<UiAssistantResponseTone>(initialUserTone);
  const [baselineUserFormat, setBaselineUserFormat] =
    useState<UiAssistantResponseFormat>(initialUserFormat);
  const [baselineDefaultHat, setBaselineDefaultHat] = useState<string>(initialDefaultHat);
  const [baselinePersonalInstructions, setBaselinePersonalInstructions] = useState<string>(
    initialPersonalInstructions,
  );
  const [baselineWorkspaceInstructions, setBaselineWorkspaceInstructions] = useState<string>(
    initialWorkspaceInstructions,
  );
  const [baselineMcpExposed, setBaselineMcpExposed] = useState<boolean>(normalizedInitialMcp);

  const [userTone, setUserTone] = useState<UiAssistantResponseTone>(initialUserTone);
  const [userFormat, setUserFormat] = useState<UiAssistantResponseFormat>(initialUserFormat);
  const [defaultHat, setDefaultHat] = useState<string>(initialDefaultHat);
  const [personalInstructions, setPersonalInstructions] = useState<string>(
    initialPersonalInstructions,
  );
  const [workspaceInstructions, setWorkspaceInstructions] = useState<string>(
    initialWorkspaceInstructions,
  );
  const [mcpExposed, setMcpExposed] = useState<boolean>(normalizedInitialMcp);
  const [copiedMcp, setCopiedMcp] = useState<boolean>(false);
  const [isSaving, setIsSaving] = useState<boolean>(false);
  const [autosavedBadgeVisible, setAutosavedBadgeVisible] = useState<boolean>(false);
  const [localSaveError, setLocalSaveError] = useState<string | null>(null);

  const isUserDirty =
    userTone !== baselineUserTone ||
    userFormat !== baselineUserFormat ||
    defaultHat !== baselineDefaultHat ||
    personalInstructions !== baselinePersonalInstructions;
  const isWorkspaceDirty =
    canEditWorkspaceLayer &&
    (workspaceInstructions !== baselineWorkspaceInstructions ||
      mcpExposed !== baselineMcpExposed);
  const isDirty = isUserDirty || isWorkspaceDirty;

  const isDirtyOrSavingRef = useRef<boolean>(false);
  isDirtyOrSavingRef.current = isDirty || isSaving;

  useEffect(() => {
    if (isDirtyOrSavingRef.current) return;
    setBaselineUserTone(initialUserTone);
    setBaselineUserFormat(initialUserFormat);
    setBaselineDefaultHat(initialDefaultHat);
    setBaselinePersonalInstructions(initialPersonalInstructions);
    setBaselineWorkspaceInstructions(initialWorkspaceInstructions);
    setBaselineMcpExposed(normalizedInitialMcp);
    setUserTone(initialUserTone);
    setUserFormat(initialUserFormat);
    setDefaultHat(initialDefaultHat);
    setPersonalInstructions(initialPersonalInstructions);
    setWorkspaceInstructions(initialWorkspaceInstructions);
    setMcpExposed(normalizedInitialMcp);
  }, [
    initialUserTone,
    initialUserFormat,
    initialDefaultHat,
    initialPersonalInstructions,
    initialWorkspaceInstructions,
    normalizedInitialMcp,
  ]);

  useEffect(() => {
    if (!autosavedBadgeVisible) return;
    const timer = setTimeout(() => setAutosavedBadgeVisible(false), 3000);
    return () => clearTimeout(timer);
  }, [autosavedBadgeVisible]);

  const effectiveOpen = isOpen && internalOpen;

  const resetUnsavedChanges = (): void => {
    setUserTone(baselineUserTone);
    setUserFormat(baselineUserFormat);
    setDefaultHat(baselineDefaultHat);
    setPersonalInstructions(baselinePersonalInstructions);
    setWorkspaceInstructions(baselineWorkspaceInstructions);
    setMcpExposed(baselineMcpExposed);
    setLocalSaveError(null);
    onClearSaveError?.();
  };

  const handleCloseAction = (): void => {
    setLocalSaveError(null);
    onClearSaveError?.();
    if (onClose) onClose();
    else setInternalOpen(false);
  };

  const guard = useUnsavedChangesDialogGuard({
    isOpen: effectiveOpen,
    isDirty,
    onClose: handleCloseAction,
    onDiscardChanges: resetUnsavedChanges,
  });

  const clearFeedbackOnEdit = (): void => {
    setAutosavedBadgeVisible(false);
    setLocalSaveError(null);
    onClearSaveError?.();
  };

  const handleSaveChanges = async (): Promise<void> => {
    if (!isDirty || isSaving) return;
    setIsSaving(true);
    setAutosavedBadgeVisible(false);
    setLocalSaveError(null);
    onClearSaveError?.();
    try {
      let userOk = true;
      let workspaceOk = true;
      if (isUserDirty) {
        const res = await onSaveUserPreferences?.({
          responseTone: userTone,
          favoriteFormat: userFormat,
          defaultHat,
          personalInstructions,
        });
        userOk = res !== false;
        if (userOk) {
          setBaselineUserTone(userTone);
          setBaselineUserFormat(userFormat);
          setBaselineDefaultHat(defaultHat);
          setBaselinePersonalInstructions(personalInstructions);
        }
      }
      if (isWorkspaceDirty) {
        const res = await onSaveWorkspaceSettings?.({
          workspaceInstructions,
          mcpExposeAssistant: mcpExposed,
        });
        workspaceOk = res !== false;
        if (workspaceOk) {
          setBaselineWorkspaceInstructions(workspaceInstructions);
          setBaselineMcpExposed(mcpExposed);
        }
      }
      if (userOk && workspaceOk) {
        setAutosavedBadgeVisible(true);
      } else {
        setAutosavedBadgeVisible(false);
        setLocalSaveError(labels.saveErrorFallback ?? labels.unsavedAlertMessage ?? "");
      }
    } catch (err: unknown) {
      setAutosavedBadgeVisible(false);
      setLocalSaveError(
        err instanceof Error && err.message.trim()
          ? err.message
          : (labels.saveErrorFallback ?? labels.unsavedAlertMessage ?? ""),
      );
    } finally {
      setIsSaving(false);
    }
  };

  return {
    effectiveOpen,
    activeTab,
    setActiveTab,
    userTone,
    setUserTone,
    userFormat,
    setUserFormat,
    defaultHat,
    setDefaultHat,
    personalInstructions,
    setPersonalInstructions,
    workspaceInstructions,
    setWorkspaceInstructions,
    mcpExposed,
    setMcpExposed,
    copiedMcp,
    setCopiedMcp,
    isDirty,
    isSaving,
    autosavedBadgeVisible,
    displayedError: saveError || localSaveError,
    guard,
    clearFeedbackOnEdit,
    handleSaveChanges,
  };
}
