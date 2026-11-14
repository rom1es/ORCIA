import React from "react";
import type {
  ControlCenterWorkspaceGovItem,
  UiCatalogExplorerItemView,
  UiOntologyConceptView,
} from "@orcia/ui";
import { FirstBootAdminSetupModal } from "./FirstBootAdminSetupModal";
import { ShellFederatedSearchModal } from "./ShellFederatedSearchModal";
import type { TranslationDictionary } from "../i18n/types";

export interface ShellContainerModalsProps {
  readonly isFr: boolean;
  readonly isAdminModalOpen: boolean;
  readonly searchModalOpen: boolean;
  readonly pathname?: string;
  readonly activeScopeId: string;
  readonly workspaces: readonly ControlCenterWorkspaceGovItem[];
  readonly catalogItems: readonly UiCatalogExplorerItemView[];
  readonly ontologyConcepts: readonly UiOntologyConceptView[];
  readonly labels: TranslationDictionary["topHeaderSearch"];
  readonly disabledMenuKeys: { readonly assistant?: string };
  readonly onDismissAdminModal: () => void;
  readonly onCreatePlatformAdmin: (input: {
    displayName: string;
    email: string;
    password?: string;
  }) => void;
  readonly onCloseSearchModal: () => void;
  readonly onDispatchNavigation: (href: string) => void;
  readonly onOpenAssistantFromSearch: () => void;
}

export function ShellContainerModals({
  isFr,
  isAdminModalOpen,
  searchModalOpen,
  pathname,
  activeScopeId,
  workspaces,
  catalogItems,
  ontologyConcepts,
  labels,
  disabledMenuKeys,
  onDismissAdminModal,
  onCreatePlatformAdmin,
  onCloseSearchModal,
  onDispatchNavigation,
  onOpenAssistantFromSearch,
}: ShellContainerModalsProps): React.ReactElement {
  return (
    <>
      <FirstBootAdminSetupModal
        isOpen={isAdminModalOpen}
        isFr={isFr}
        onClose={onDismissAdminModal}
        onCreatePlatformAdmin={onCreatePlatformAdmin}
      />

      <ShellFederatedSearchModal
        isOpen={searchModalOpen}
        isFr={isFr}
        pathname={pathname}
        activeScopeId={activeScopeId}
        workspaces={workspaces}
        catalogItems={catalogItems}
        ontologyConcepts={ontologyConcepts}
        labels={labels}
        onSelectDeepLink={(deepLinkUri) => {
          onCloseSearchModal();
          onDispatchNavigation(deepLinkUri);
        }}
        onAskAssistant={() => {
          onCloseSearchModal();
          if (!disabledMenuKeys.assistant) {
            onOpenAssistantFromSearch();
          }
        }}
        onClose={onCloseSearchModal}
      />
    </>
  );
}
