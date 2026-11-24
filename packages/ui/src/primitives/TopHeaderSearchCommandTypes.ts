import type { RgaaModalGuardLabels } from "../components/RgaaModalDialog.js";

export type TopSearchScopeMode = "SCREEN" | "WORKSPACE" | "ALL_WORKSPACES";

export type TopSearchFamilyKey =
  | "FOLDERS_DISCUSSIONS"
  | "PROCESSES_EXECUTIONS"
  | "AGENTS_TOOLS"
  | "DELIVERABLES_ARTIFACTS"
  | "SOURCES_SNIPPETS"
  | "ONTOLOGY_GLOSSARY"
  | "HELP_ACTIONS";

export interface TopSearchHitItem {
  readonly itemId: string;
  readonly family: TopSearchFamilyKey;
  readonly title: string;
  readonly snippet: string;
  readonly workspaceId: string;
  readonly screenRoute: string;
  readonly deepLinkUri: string;
  readonly speedTier: 1 | 2;
  readonly lockedTop: boolean;
  readonly score: number;
  readonly badge: string | null;
  readonly highlightDurationMs: number;
  readonly opensContextualHelpColumn: boolean;
}

export interface TopHeaderSearchCommandLabels {
  readonly modalTitle: string;
  readonly inputPlaceholder: string;
  readonly scopeScreenLabel: string;
  readonly scopeWorkspaceLabel: string;
  readonly scopeAllWorkspacesLabel: string;
  readonly speed1SectionTitle: string;
  readonly speed2SectionTitle: string;
  readonly semanticCloseMatchBadge: string;
  readonly emptyResultsLabel: string;
  readonly previewPaneTitle: string;
  readonly deepLinkActionLabel: string;
  readonly openHelpColumnActionLabel: string;
  readonly askAssistantFooterPrefix: string;
  readonly askAssistantFooterSuffix: string;
  readonly deepSearchCtaLabel?: string;
  readonly searchScopesAriaLabel?: string;
  readonly helpColumnDeepLinkPrefix?: string;
  readonly autoFocusDeepLinkPrefix?: string;
  readonly durationMsUnit?: string;
  readonly keyboardShortcutsHint?: string;
  readonly disabledOpenHint?: string;
  readonly closeCta?: string;
  readonly familyLabels: Readonly<Record<TopSearchFamilyKey, string>>;
}

export interface DeepLinkResolutionPayload {
  readonly itemId: string;
  readonly deepLinkUri: string;
  readonly highlightDurationMs: number;
  readonly opensContextualHelpColumn: boolean;
}

export interface TopHeaderSearchCommandProps {
  readonly labels: TopHeaderSearchCommandLabels;
  readonly initialQuery?: string;
  readonly initialScope?: TopSearchScopeMode;
  readonly speed1Hits: readonly TopSearchHitItem[];
  readonly speed2Hits?: readonly TopSearchHitItem[];
  readonly speed2Loading?: boolean;
  readonly speed2Executed?: boolean;
  readonly speed2Error?: string | null;
  readonly isDirty?: boolean;
  readonly rgaaLabels?: RgaaModalGuardLabels;
  readonly onQueryChange?: (query: string, scope: TopSearchScopeMode) => void;
  readonly onScopeChange?: (scope: TopSearchScopeMode) => void;
  readonly onTriggerSpeed2Now?: (query: string, scope: TopSearchScopeMode) => void;
  readonly onSelectDeepLink?: (payload: DeepLinkResolutionPayload) => void;
  readonly onAskAssistant?: (query: string, scope: TopSearchScopeMode) => void;
  readonly onClose?: () => void;
}
