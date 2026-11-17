export type UiTraceEventKind =
  | "GROUP_HEADER"
  | "THOUGHT_DELTA"
  | "THOUGHT_COMPLETED"
  | "CHECK_EXECUTED"
  | "FILE_ANALYZED"
  | "AGENT_DELEGATED"
  | "WRITE_PREVIEW_REQUESTED"
  | "SYNTHESIS_READY"
  | "EXECUTION_FINISHED";

export type UiReflexiveSessionStatus =
  | "RUNNING"
  | "WAITING_WRITE_PREVIEW"
  | "SYNTHESIZING"
  | "COMPLETED"
  | "CANCELLED"
  | "FAILED";

export type UiFileBadgeCode = "M↓" | "Y" | "TS" | "PY" | "JSON" | "SQL" | "DOC" | string;

export interface UiAgentTraceEventItem {
  readonly eventId: string;
  readonly sequence: number;
  readonly kind: UiTraceEventKind;
  readonly label: string;
  readonly actorSlug: string;
  readonly groupKey?: string | null;
  readonly durationSeconds?: number | null;
  readonly thoughtContent?: string | null;
  readonly resourceUri?: string | null;
  readonly displayFilename?: string | null;
  readonly fileBadgeCode?: UiFileBadgeCode | null;
  readonly startLine?: number | null;
  readonly endLine?: number | null;
  readonly redacted?: boolean;
  readonly delegatedAgentSlug?: string | null;
  readonly writePreviewSummary?: string | null;
  readonly createdAtIso?: string;
}

export interface UiReflexivePendingWritePreview {
  readonly previewId: string;
  readonly targetConnector: string;
  readonly actionSummary: string;
  readonly payloadPreview?: Readonly<Record<string, unknown>>;
}

export interface UiSourceLineInspectTarget {
  readonly uri: string;
  readonly startLine: number;
  readonly endLine: number;
  readonly filename?: string;
  readonly badgeCode?: UiFileBadgeCode;
}

export interface AgentExecutionTraceLabels {
  readonly heading: string;
  readonly defaultGroupTitle: string;
  readonly runningStatus: string;
  readonly synthesizingStatus: string;
  readonly completedStatus: string;
  readonly pausedWriteStatus: string;
  readonly cancelledStatus: string;
  readonly failedStatus: string;
  readonly stepsCountLabel: (count: number) => string;
  readonly thoughtSummaryLabel: (seconds: number) => string;
  readonly thoughtInProgressLabel: string;
  readonly analyzedPrefix: string;
  readonly linesRangeShort: (start: number, end: number) => string;
  readonly redactedPillSuffix: string;
  readonly delegatedPrefix: (agentHandle: string) => string;
  readonly synthesizeNowButtonLabel: string;
  readonly synthesizeNowButtonHint: string;
  readonly writePreviewHeading: string;
  readonly writePreviewTargetPrefix: string;
  readonly approveWriteButtonLabel: string;
  readonly rejectWriteButtonLabel: string;
  readonly expandGroupAriaLabel: string;
  readonly collapseGroupAriaLabel: string;
}

export interface SourceLineInspectorLineItem {
  readonly lineNumber: number;
  readonly content: string;
}

export interface SourceLineInspectorLabels {
  readonly dialogAriaLabel: string;
  readonly linesSliceSummary: (startLine: number, endLine: number, totalLines: number) => string;
  readonly copySliceButtonLabel: (startLine: number, endLine: number) => string;
  readonly copiedSliceFeedbackLabel: string;
  readonly closeButtonLabel: string;
  readonly loadingLabel: string;
  readonly redactedTitle: string;
  readonly redactedBody: string;
  readonly redactedHintPrefix: string;
  readonly emptySliceLabel: string;
}
