import type {
  AutonomousActionInput,
  AutonomousRunExecutionResponse,
  AutonomyContractResponse,
  AutonomyContractStateResponse,
  EligibleServicePrincipalItem,
  RevokeAutonomyContractRequest,
  SignAutonomyContractRequest,
  StartAutonomousRunRequest,
} from "../generated/autonomy_contracts";
import type { createRequestJson } from "../helpers";

type RequestJsonFn = ReturnType<typeof createRequestJson>;

export type {
  AutonomousActionInput,
  AutonomousRunExecutionResponse,
  AutonomyContractResponse,
  AutonomyContractStateResponse,
  EligibleServicePrincipalItem,
  RevokeAutonomyContractRequest,
  SignAutonomyContractRequest,
  StartAutonomousRunRequest,
};

export function createAutonomyContractsDomainClient(requestJson: RequestJsonFn) {
  return {
    getAutonomyContractState(
      workspaceId: string,
      workflowId: string,
    ): Promise<AutonomyContractStateResponse> {
      const ws = encodeURIComponent(workspaceId);
      const wf = encodeURIComponent(workflowId);
      return requestJson<AutonomyContractStateResponse>(
        `/api/v1/workspaces/${ws}/workflows/${wf}/autonomy-contract`,
      );
    },

    signAutonomyContract(
      workspaceId: string,
      workflowId: string,
      payload: SignAutonomyContractRequest,
    ): Promise<AutonomyContractResponse> {
      const ws = encodeURIComponent(workspaceId);
      const wf = encodeURIComponent(workflowId);
      return requestJson<AutonomyContractResponse>(
        `/api/v1/workspaces/${ws}/workflows/${wf}/autonomy-contract`,
        "POST",
        payload,
      );
    },

    revokeAutonomyContract(
      workspaceId: string,
      workflowId: string,
      payload?: RevokeAutonomyContractRequest,
    ): Promise<AutonomyContractResponse> {
      const ws = encodeURIComponent(workspaceId);
      const wf = encodeURIComponent(workflowId);
      return requestJson<AutonomyContractResponse>(
        `/api/v1/workspaces/${ws}/workflows/${wf}/autonomy-contract/revoke`,
        "POST",
        payload ?? { scope_path: "GLOBAL" },
      );
    },

    startAutonomousRun(
      workspaceId: string,
      workflowId: string,
      payload: StartAutonomousRunRequest,
    ): Promise<AutonomousRunExecutionResponse> {
      const ws = encodeURIComponent(workspaceId);
      const wf = encodeURIComponent(workflowId);
      return requestJson<AutonomousRunExecutionResponse>(
        `/api/v1/workspaces/${ws}/workflows/${wf}/runs/autonomous`,
        "POST",
        payload,
      );
    },
  };
}
