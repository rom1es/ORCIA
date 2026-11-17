import type {
  CreateWorkflowTriggerRequest,
  DeleteWorkflowTriggerResponse,
  FireManualTriggerRequest,
  TriggerDispatchResponse,
  UpdateWorkflowTriggerRequest,
  WorkflowTriggerListResponse,
  WorkflowTriggerResponse,
} from "../generated/workflow_triggers";
import type { createRequestJson } from "../helpers";

type RequestJsonFn = ReturnType<typeof createRequestJson>;

export type {
  CreateWorkflowTriggerRequest,
  DeleteWorkflowTriggerResponse,
  FireManualTriggerRequest,
  TriggerDispatchResponse,
  UpdateWorkflowTriggerRequest,
  WorkflowTriggerListResponse,
  WorkflowTriggerResponse,
};

export function createWorkflowTriggersDomainClient(requestJson: RequestJsonFn) {
  return {
    listWorkflowTriggers(
      workspaceId: string,
      workflowId: string,
    ): Promise<WorkflowTriggerListResponse> {
      const ws = encodeURIComponent(workspaceId);
      const wf = encodeURIComponent(workflowId);
      return requestJson<WorkflowTriggerListResponse>(
        `/api/v1/workspaces/${ws}/workflows/${wf}/triggers`,
      );
    },

    createWorkflowTrigger(
      workspaceId: string,
      workflowId: string,
      payload: CreateWorkflowTriggerRequest,
    ): Promise<WorkflowTriggerResponse> {
      const ws = encodeURIComponent(workspaceId);
      const wf = encodeURIComponent(workflowId);
      return requestJson<WorkflowTriggerResponse>(
        `/api/v1/workspaces/${ws}/workflows/${wf}/triggers`,
        "POST",
        payload,
      );
    },

    updateWorkflowTrigger(
      workspaceId: string,
      workflowId: string,
      triggerId: string,
      payload: UpdateWorkflowTriggerRequest,
    ): Promise<WorkflowTriggerResponse> {
      const ws = encodeURIComponent(workspaceId);
      const wf = encodeURIComponent(workflowId);
      const tid = encodeURIComponent(triggerId);
      return requestJson<WorkflowTriggerResponse>(
        `/api/v1/workspaces/${ws}/workflows/${wf}/triggers/${tid}`,
        "PATCH",
        payload,
      );
    },

    deleteWorkflowTrigger(
      workspaceId: string,
      workflowId: string,
      triggerId: string,
    ): Promise<DeleteWorkflowTriggerResponse> {
      const ws = encodeURIComponent(workspaceId);
      const wf = encodeURIComponent(workflowId);
      const tid = encodeURIComponent(triggerId);
      return requestJson<DeleteWorkflowTriggerResponse>(
        `/api/v1/workspaces/${ws}/workflows/${wf}/triggers/${tid}`,
        "DELETE",
      );
    },

    fireManualWorkflowTrigger(
      workspaceId: string,
      workflowId: string,
      triggerId: string,
      payload?: FireManualTriggerRequest,
    ): Promise<TriggerDispatchResponse> {
      const ws = encodeURIComponent(workspaceId);
      const wf = encodeURIComponent(workflowId);
      const tid = encodeURIComponent(triggerId);
      return requestJson<TriggerDispatchResponse>(
        `/api/v1/workspaces/${ws}/workflows/${wf}/triggers/${tid}/fire`,
        "POST",
        payload ?? {},
      );
    },

    resetWorkflowTriggerCircuit(
      workspaceId: string,
      workflowId: string,
      triggerId: string,
    ): Promise<WorkflowTriggerResponse> {
      const ws = encodeURIComponent(workspaceId);
      const wf = encodeURIComponent(workflowId);
      const tid = encodeURIComponent(triggerId);
      return requestJson<WorkflowTriggerResponse>(
        `/api/v1/workspaces/${ws}/workflows/${wf}/triggers/${tid}/reset-circuit`,
        "POST",
        {},
      );
    },
  };
}
