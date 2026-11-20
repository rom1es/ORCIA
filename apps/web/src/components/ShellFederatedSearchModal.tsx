import { createOrciaApiClient } from "@orcia/api-client";
import {
  TopHeaderSearchCommand,
  type ControlCenterWorkspaceGovItem,
  type TopHeaderSearchCommandLabels,
  type TopSearchFamilyKey,
  type TopSearchHitItem,
  type TopSearchScopeMode,
  type UiCatalogExplorerItemView,
  type UiOntologyConceptView,
} from "@orcia/ui";
import React, { useState } from "react";

export interface ShellFederatedSearchModalProps {
  readonly isOpen: boolean;
  readonly isFr: boolean;
  readonly pathname: string | undefined;
  readonly activeScopeId: string;
  readonly workspaces: readonly ControlCenterWorkspaceGovItem[];
  readonly catalogItems: readonly UiCatalogExplorerItemView[];
  readonly ontologyConcepts: readonly UiOntologyConceptView[];
  readonly labels: TopHeaderSearchCommandLabels;
  readonly onSelectDeepLink: (deepLinkUri: string) => void;
  readonly onAskAssistant: (query: string) => void;
  readonly onClose: () => void;
}

function mapBackendSearchFamily(rawFamily: string): TopSearchFamilyKey {
  if (rawFamily === "AGENTS_SKILLS") return "AGENTS_TOOLS";
  if (rawFamily === "GLOSSARY_RULES") return "ONTOLOGY_GLOSSARY";
  if (
    rawFamily === "FOLDERS_DISCUSSIONS" ||
    rawFamily === "PROCESSES_EXECUTIONS" ||
    rawFamily === "AGENTS_TOOLS" ||
    rawFamily === "DELIVERABLES_ARTIFACTS" ||
    rawFamily === "SOURCES_SNIPPETS" ||
    rawFamily === "ONTOLOGY_GLOSSARY" ||
    rawFamily === "HELP_ACTIONS"
  ) {
    return rawFamily;
  }
  return "SOURCES_SNIPPETS";
}

export function ShellFederatedSearchModal({
  isOpen,
  isFr,
  pathname,
  activeScopeId,
  workspaces,
  catalogItems,
  ontologyConcepts,
  labels,
  onSelectDeepLink,
  onAskAssistant,
  onClose,
}: ShellFederatedSearchModalProps): React.ReactElement | null {
  const [speed2Hits, setSpeed2Hits] = useState<readonly TopSearchHitItem[]>([]);
  const [speed2Loading, setSpeed2Loading] = useState<boolean>(false);
  const [speed2Executed, setSpeed2Executed] = useState<boolean>(false);
  const [speed2Error, setSpeed2Error] = useState<string | null>(null);

  if (!isOpen) {
    return null;
  }

  const runFederatedSpeed2Search = (
    query: string,
    requestedScope: TopSearchScopeMode = "ALL_WORKSPACES",
  ): void => {
    const trimmed = query.trim();
    if (!trimmed) {
      setSpeed2Hits([]);
      setSpeed2Loading(false);
      setSpeed2Executed(false);
      setSpeed2Error(null);
      return;
    }
    setSpeed2Loading(true);
    setSpeed2Executed(false);
    setSpeed2Error(null);
    const activeWsId = workspaces[0]?.workspaceId ?? null;
    const effectiveScope: TopSearchScopeMode =
      activeWsId === null && requestedScope === "WORKSPACE" ? "ALL_WORKSPACES" : requestedScope;
    const client = createOrciaApiClient({ baseUrl: "" });
    void client
      .searchFederated(trimmed, effectiveScope, activeWsId, pathname ?? "/cockpit", true)
      .then((res) => {
        setSpeed2Loading(false);
        setSpeed2Executed(Boolean(res.speed2_executed ?? true));
        const mapped = (res.hits ?? []).map(
          (hit): TopSearchHitItem => ({
            itemId: hit.item_id,
            family: mapBackendSearchFamily(String(hit.family ?? "")),
            title: hit.title,
            snippet: hit.snippet,
            workspaceId: hit.workspace_id,
            screenRoute: hit.screen_route,
            deepLinkUri: hit.deep_link_uri,
            speedTier: 2,
            lockedTop: false,
            score: Number(hit.score ?? 0.85),
            badge: hit.badge ?? (isFr ? "Passage proche" : "Close match"),
            highlightDurationMs: Number(hit.highlight_duration_ms ?? 2000),
            opensContextualHelpColumn: Boolean(hit.opens_contextual_help_column),
          }),
        );
        setSpeed2Hits(mapped);
      })
      .catch((err: unknown) => {
        setSpeed2Loading(false);
        setSpeed2Executed(false);
        setSpeed2Hits([]);
        const detail = err instanceof Error ? err.message : String(err);
        setSpeed2Error(
          isFr
            ? `Erreur lors de la recherche fédérée (recherche approfondie) : ${detail}`
            : `Federated search error (deep search): ${detail}`,
        );
      });
  };

  return (
    <div
      data-testid="cmdk-modal-backdrop"
      className="fixed inset-0 z-40 flex items-center justify-center p-4"
      style={{ backgroundColor: "rgba(15, 23, 42, 0.35)" }}
    >
      <TopHeaderSearchCommand
        labels={labels}
        speed1Hits={[
          ...workspaces.map(
            (ws): TopSearchHitItem => ({
              itemId: ws.workspaceId,
              family: "FOLDERS_DISCUSSIONS",
              title: ws.name,
              snippet: ws.lifecyclePhase,
              workspaceId: ws.workspaceId,
              screenRoute: "/workspaces",
              deepLinkUri: "/workspaces",
              speedTier: 1,
              lockedTop: true,
              score: 0.99,
              badge: null,
              highlightDurationMs: 2000,
              opensContextualHelpColumn: false,
            }),
          ),
          ...catalogItems.map(
            (cat): TopSearchHitItem => ({
              itemId: cat.resourceId,
              family: "PROCESSES_EXECUTIONS",
              title: cat.title,
              snippet: cat.uri,
              workspaceId: activeScopeId,
              screenRoute: "/catalog",
              deepLinkUri: "/catalog",
              speedTier: 1,
              lockedTop: true,
              score: 0.95,
              badge: null,
              highlightDurationMs: 2000,
              opensContextualHelpColumn: false,
            }),
          ),
          ...ontologyConcepts.map(
            (c): TopSearchHitItem => ({
              itemId: c.conceptKey,
              family: "ONTOLOGY_GLOSSARY",
              title: c.canonicalTerm,
              snippet: c.definitionText,
              workspaceId: activeScopeId,
              screenRoute: "/workspaces",
              deepLinkUri: "/workspaces",
              speedTier: 1,
              lockedTop: true,
              score: 0.92,
              badge: null,
              highlightDurationMs: 2000,
              opensContextualHelpColumn: false,
            }),
          ),
        ]}
        speed2Hits={speed2Hits}
        speed2Loading={speed2Loading}
        speed2Executed={speed2Executed}
        speed2Error={speed2Error}
        onQueryChange={(query) => {
          if (!query.trim()) {
            setSpeed2Hits([]);
            setSpeed2Loading(false);
            setSpeed2Executed(false);
            setSpeed2Error(null);
          }
        }}
        onTriggerSpeed2Now={(query, scope) => runFederatedSpeed2Search(query, scope)}
        onSelectDeepLink={(payload) => onSelectDeepLink(payload.deepLinkUri)}
        onAskAssistant={(query) => onAskAssistant(query)}
        onClose={onClose}
      />
    </div>
  );
}
