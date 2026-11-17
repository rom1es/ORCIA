import { createOrciaApiClient } from "@orcia/api-client";
import type {
  SourceLineInspectorLineItem,
  UiFileBadgeCode,
  UiSourceLineInspectTarget,
} from "@orcia/ui";
import { useCallback, useState } from "react";
import {
  inferFileBadgeFromUri,
  parseUriWithLineRange,
} from "./reflexiveTraceMappers";

export interface UseSourceLineInspectorOptions {
  readonly locale?: "fr" | "en";
  readonly workspaceId?: string;
  readonly onFeedback?: (message: string) => void;
}

export interface SourceLineInspectorViewState {
  readonly open: boolean;
  readonly resourceUri: string;
  readonly displayFilename: string;
  readonly fileBadgeCode: UiFileBadgeCode;
  readonly startLine: number;
  readonly endLine: number;
  readonly totalLines: number;
  readonly lines: readonly SourceLineInspectorLineItem[];
  readonly isLoading: boolean;
  readonly redacted: boolean;
  readonly redactedReason: string | null;
  readonly permissionRequestHint: string | null;
  readonly errorMessage: string | null;
  readonly copiedFeedback: boolean;
}

const INITIAL_INSPECTOR_STATE: SourceLineInspectorViewState = {
  open: false,
  resourceUri: "",
  displayFilename: "",
  fileBadgeCode: "DOC",
  startLine: 1,
  endLine: 1,
  totalLines: 1,
  lines: [],
  isLoading: false,
  redacted: false,
  redactedReason: null,
  permissionRequestHint: null,
  errorMessage: null,
  copiedFeedback: false,
};

export function useSourceLineInspector(
  options: UseSourceLineInspectorOptions = {},
) {
  const { locale = "fr", workspaceId, onFeedback } = options;
  const [state, setState] = useState<SourceLineInspectorViewState>(
    INITIAL_INSPECTOR_STATE,
  );

  const setOpen = useCallback((nextOpen: boolean) => {
    setState((prev) => ({
      ...prev,
      open: nextOpen,
      copiedFeedback: false,
    }));
  }, []);

  const openInspectTarget = useCallback(
    (target: UiSourceLineInspectTarget) => {
      const parsed = parseUriWithLineRange(target.uri);
      const effectiveStart =
        target.startLine > 0 ? target.startLine : parsed.startLine;
      const effectiveEnd =
        target.endLine >= effectiveStart
          ? target.endLine
          : Math.max(effectiveStart, parsed.endLine);
      const fallbackFilename =
        target.filename || parsed.uri.split("/").pop() || parsed.uri;
      const fallbackBadge =
        target.badgeCode || inferFileBadgeFromUri(parsed.uri);

      setState({
        open: true,
        resourceUri: parsed.uri,
        displayFilename: fallbackFilename,
        fileBadgeCode: fallbackBadge,
        startLine: effectiveStart,
        endLine: effectiveEnd,
        totalLines: effectiveEnd,
        lines: [],
        isLoading: true,
        redacted: false,
        redactedReason: null,
        permissionRequestHint: null,
        errorMessage: null,
        copiedFeedback: false,
      });

      const client = createOrciaApiClient({ baseUrl: "", locale });
      void client
        .inspectSourceLines({
          uri: parsed.uri,
          startLine: effectiveStart,
          endLine: effectiveEnd,
          ...(workspaceId ? { workspaceId } : {}),
        })
        .then((res) => {
          setState((prev) => ({
            ...prev,
            resourceUri: res.resource_uri || parsed.uri,
            displayFilename: res.display_filename || fallbackFilename,
            fileBadgeCode:
              (res.file_badge_code as UiFileBadgeCode | undefined) ||
              fallbackBadge,
            startLine: res.start_line ?? effectiveStart,
            endLine: res.end_line ?? effectiveEnd,
            totalLines: res.total_lines ?? effectiveEnd,
            lines: (res.lines ?? []).map((ln) => ({
              lineNumber: ln.line_number,
              content: ln.content,
            })),
            isLoading: false,
            redacted: Boolean(res.redacted),
            redactedReason: res.redacted_reason ?? null,
            permissionRequestHint: res.permission_request_hint ?? null,
            errorMessage: null,
          }));
        })
        .catch((err: unknown) => {
          const detail =
            err instanceof Error
              ? err.message
              : locale === "fr"
                ? "Impossible de lire cet extrait source."
                : "Unable to load source excerpt.";
          setState((prev) => ({
            ...prev,
            isLoading: false,
            lines: [],
            errorMessage: detail,
          }));
          onFeedback?.(detail);
        });
    },
    [locale, workspaceId, onFeedback],
  );

  const openInspectCitationUri = useCallback(
    (rawUri: string, title?: string) => {
      const parsed = parseUriWithLineRange(rawUri);
      openInspectTarget({
        uri: parsed.uri,
        startLine: parsed.startLine,
        endLine: parsed.endLine,
        ...(title ? { filename: title } : {}),
      });
    },
    [openInspectTarget],
  );

  const copyCurrentSlice = useCallback(() => {
    if (state.redacted || state.lines.length === 0) return;
    const formatted = state.lines
      .filter(
        (ln) =>
          ln.lineNumber >= state.startLine && ln.lineNumber <= state.endLine,
      )
      .map((ln) => ln.content)
      .join("\n");
    const textToCopy =
      formatted.length > 0
        ? formatted
        : state.lines.map((ln) => ln.content).join("\n");

    if (
      typeof navigator !== "undefined" &&
      navigator.clipboard &&
      typeof navigator.clipboard.writeText === "function"
    ) {
      void navigator.clipboard
        .writeText(textToCopy)
        .then(() => {
          setState((prev) => ({ ...prev, copiedFeedback: true }));
        })
        .catch((err: unknown) => {
          const detail = err instanceof Error ? err.message : "Clipboard";
          onFeedback?.(detail);
        });
    } else {
      setState((prev) => ({ ...prev, copiedFeedback: true }));
    }
  }, [state.redacted, state.lines, state.startLine, state.endLine, onFeedback]);

  return {
    inspectorState: state,
    setInspectorOpen: setOpen,
    openInspectTarget,
    openInspectCitationUri,
    copyCurrentSlice,
  };
}
