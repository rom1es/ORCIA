import {
  createOrciaApiClient,
  type AutonomyContractStateResponse,
} from "@orcia/api-client";
import type {
  SignAutonomyContractDraft,
  UiActiveAutonomyContractView,
  UiEligibleServiceAccountOption,
} from "@orcia/ui";
import { useCallback, useEffect, useMemo, useState } from "react";
import type { AutonomyContractStudioCopy } from "../../../i18n/locales/autonomy_contract_labels";

interface UseWorkflowAutonomyContractParams {
  readonly workspaceId: string;
  readonly workflowId: string;
  readonly workflowVersion: string;
  readonly knowledgeBaseRefs: readonly string[];
  readonly contractLabels: AutonomyContractStudioCopy;
  readonly onBanner: (banner: string) => void;
}

export function useWorkflowAutonomyContract({
  workspaceId,
  workflowId,
  workflowVersion,
  knowledgeBaseRefs,
  contractLabels,
  onBanner,
}: UseWorkflowAutonomyContractParams) {
  const [showContractModal, setShowContractModal] = useState<boolean>(false);
  const [contractState, setContractState] = useState<AutonomyContractStateResponse | null>(null);
  const [contractError, setContractError] = useState<string | null>(null);
  const [contractSubmitting, setContractSubmitting] = useState<boolean>(false);

  const apiClient = useMemo(() => createOrciaApiClient({ baseUrl: "" }), []);

  const refreshAutonomyContractState = useCallback(async () => {
    try {
      const state = await apiClient.getAutonomyContractState(workspaceId, workflowId);
      setContractState(state);
      setContractError(null);
    } catch (err) {
      setContractError(err instanceof Error ? err.message : contractLabels.loadErrorBanner);
    }
  }, [apiClient, workspaceId, workflowId, contractLabels.loadErrorBanner]);

  useEffect(() => {
    void refreshAutonomyContractState();
  }, [refreshAutonomyContractState]);

  const handleSignAutonomyContract = async (draft: SignAutonomyContractDraft) => {
    setContractSubmitting(true);
    setContractError(null);
    try {
      await apiClient.signAutonomyContract(workspaceId, workflowId, {
        workflow_version: workflowVersion,
        workflow_sha256: `sha256-${workflowId}-${workflowVersion}`,
        criticality: workflowId.includes("help") ? "LOW_NON_CRITICAL" : "STANDARD",
        service_principal_id: draft.servicePrincipalId,
        allowed_read_sources: [...draft.allowedReadSources],
        allowed_write_actions: [...draft.allowedWriteActions],
        max_cost_per_run_usd: draft.maxCostPerRunUsd,
        tie_break_policy: draft.tieBreakPolicy,
        post_hoc_sampling_rate: 0.15,
        scope_path: "GLOBAL",
      });
      await refreshAutonomyContractState();
      onBanner(contractLabels.signedSuccessBanner);
      setShowContractModal(false);
    } catch (err) {
      setContractError(err instanceof Error ? err.message : contractLabels.loadErrorBanner);
    } finally {
      setContractSubmitting(false);
    }
  };

  const handleRevokeAutonomyContract = async () => {
    setContractSubmitting(true);
    setContractError(null);
    try {
      await apiClient.revokeAutonomyContract(workspaceId, workflowId, {
        scope_path: "GLOBAL",
      });
      await refreshAutonomyContractState();
      onBanner(contractLabels.revokedSuccessBanner);
    } catch (err) {
      setContractError(err instanceof Error ? err.message : contractLabels.loadErrorBanner);
    } finally {
      setContractSubmitting(false);
    }
  };

  const eligibleServiceAccounts: UiEligibleServiceAccountOption[] = useMemo(
    () =>
      (contractState?.eligible_service_principals ?? []).map((sp) => ({
        id: sp.id,
        displayName: sp.display_name,
        principalId: sp.principal_id,
      })),
    [contractState],
  );

  const activeContractView: UiActiveAutonomyContractView | null = useMemo(() => {
    const active = contractState?.active_contract;
    if (!active) return null;
    return {
      id: active.id,
      servicePrincipalId: active.service_principal_id,
      allowedReadSources: active.allowed_read_sources ?? [],
      allowedWriteActions: active.allowed_write_actions ?? [],
      maxCostPerRunUsd: active.max_cost_per_run_usd,
      tieBreakPolicy: active.tie_break_policy,
      signedByRoleLabel: contractLabels.signerRoleLabels[active.signed_by_role],
      signedAtIso: active.signed_at_iso,
      signatureSha256: active.signature_sha256,
    };
  }, [contractState, contractLabels.signerRoleLabels]);

  const availableReadSources = useMemo(
    () => Array.from(new Set([...knowledgeBaseRefs, "catalog:read"])),
    [knowledgeBaseRefs],
  );
  const availableWriteActions = useMemo(() => ["catalog:write", "help_article:publish"], []);

  return {
    showContractModal,
    setShowContractModal,
    contractError,
    contractSubmitting,
    eligibleServiceAccounts,
    activeContractView,
    availableReadSources,
    availableWriteActions,
    handleSignAutonomyContract,
    handleRevokeAutonomyContract,
  };
}
