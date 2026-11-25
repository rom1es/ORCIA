import {
  OrciaDataCard,
  type ControlCenterWorkspaceGovItem,
} from "@orcia/ui";
import React from "react";
import { resolveDictionaryForFlag } from "../../i18n";
import { WorkspaceCompactHeader } from "./WorkspaceCompactHeader";

export interface WorkspaceStudioCardsAndDetailViewProps {
  readonly isFr: boolean;
  readonly initialWorkspaceId?: string;
  readonly workspaces: readonly ControlCenterWorkspaceGovItem[];
  readonly isAutosaved?: boolean;
  readonly isCreateFormExpanded: boolean;
  readonly alertSlot?: React.ReactNode;
  readonly onToggleCreateForm: () => void;
  readonly onNavigateToRoute: (route: string) => void;
}

export function WorkspaceStudioCardsAndDetailView({
  isFr,
  initialWorkspaceId,
  workspaces,
  isAutosaved = false,
  isCreateFormExpanded,
  alertSlot,
  onToggleCreateForm,
  onNavigateToRoute,
}: WorkspaceStudioCardsAndDetailViewProps): React.ReactElement {
  const studioCopy = resolveDictionaryForFlag(isFr).featureWorkspaces.studioCards;
  const activeWorkspace =
    workspaces.find((w) => w.workspaceId === initialWorkspaceId) ?? workspaces[0] ?? null;

  return (
    <div
      data-testid="workspaces-redesigned-studio-view"
      style={{ display: "flex", flexDirection: "column", gap: "16px" }}
    >
      <WorkspaceCompactHeader
        isFr={isFr}
        activeWorkspace={activeWorkspace}
        isAutosaved={isAutosaved}
        isCreateFormExpanded={isCreateFormExpanded}
        alertSlot={alertSlot}
        onToggleCreateForm={onToggleCreateForm}
        onNavigateToGlossary={() => onNavigateToRoute("/ontology")}
      />

      {!activeWorkspace ? (
        <OrciaDataCard testId="workspaces-cards-empty-state">
          <div
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
          </div>
        </OrciaDataCard>
      ) : null}
    </div>
  );
}
