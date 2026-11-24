import type {
  ControlCenterWorkspaceGovItem,
  ProductLifecyclePhaseType,
  WorkspaceVisibilityMode,
} from "@orcia/ui";
import React, { useState } from "react";
import { resolveDictionaryForFlag } from "../../i18n";
import { WorkspaceCompactHeader } from "./WorkspaceCompactHeader";

export interface WorkspaceStudioCardsAndDetailViewProps {
  readonly isFr: boolean;
  readonly initialWorkspaceId?: string;
  readonly workspaces: readonly ControlCenterWorkspaceGovItem[];
  readonly isCreateFormExpanded: boolean;
  readonly onSelectWorkspace?: (workspaceId: string) => void;
  readonly onToggleCreateForm: () => void;
  readonly onNavigateToRoute: (route: string) => void;
  readonly onUpdateWorkspacePhase: (
    workspaceId: string,
    phase: ProductLifecyclePhaseType,
  ) => void | Promise<void>;
  readonly onUpdateWorkspaceVisibility: (
    workspaceId: string,
    visibilityMode: WorkspaceVisibilityMode,
  ) => void | Promise<void>;
  readonly onFeedback: (message: string) => void;
}

export function WorkspaceStudioCardsAndDetailView({
  isFr,
  initialWorkspaceId,
  workspaces,
  isCreateFormExpanded,
  onSelectWorkspace,
  onToggleCreateForm,
  onNavigateToRoute,
  onUpdateWorkspacePhase,
  onUpdateWorkspaceVisibility,
  onFeedback,
}: WorkspaceStudioCardsAndDetailViewProps): React.ReactElement {
  const studioCopy = resolveDictionaryForFlag(isFr).featureWorkspaces.studioCards;
  const [localSelectedWsId, setLocalSelectedWsId] = useState<string>(initialWorkspaceId ?? "");
  const [autosavedWsIds, setAutosavedWsIds] = useState<readonly string[]>([]);

  const resolvedWsId = initialWorkspaceId || localSelectedWsId;
  const activeWorkspace =
    workspaces.find((w) => w.workspaceId === resolvedWsId) ?? workspaces[0] ?? null;

  const handleSelectWorkspace = (workspaceId: string) => {
    setLocalSelectedWsId(workspaceId);
    onSelectWorkspace?.(workspaceId);
  };

  const markAutosaved = (workspaceId: string) => {
    setAutosavedWsIds((prev) => (prev.includes(workspaceId) ? prev : [...prev, workspaceId]));
  };

  return (
    <div
      data-testid="workspaces-redesigned-studio-view"
      style={{ display: "flex", flexDirection: "column", gap: "16px" }}
    >
      <WorkspaceCompactHeader
        isFr={isFr}
        workspaces={workspaces}
        activeWorkspace={activeWorkspace}
        isAutosaved={Boolean(
          activeWorkspace && autosavedWsIds.includes(activeWorkspace.workspaceId),
        )}
        isCreateFormExpanded={isCreateFormExpanded}
        onSelectWorkspace={handleSelectWorkspace}
        onToggleCreateForm={onToggleCreateForm}
        onNavigateToGlossary={() => onNavigateToRoute("/ontology")}
        onUpdateWorkspacePhase={onUpdateWorkspacePhase}
        onUpdateWorkspaceVisibility={onUpdateWorkspaceVisibility}
        onMarkAutosaved={markAutosaved}
        onFeedback={onFeedback}
      />

      {!activeWorkspace ? (
        <section
          data-testid="workspaces-cards-empty-state"
          className="orcia-bento-card"
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: "10px",
            fontSize: "13px",
            color: "var(--color-muted-foreground)",
          }}
        >
          <span>{studioCopy.emptyFilterText}</span>
        </section>
      ) : null}
    </div>
  );
}
