import {
  ContextualHelpColumnAndCenter,
  type UiContextualHelpArticleView,
} from "@orcia/ui";
import React from "react";
import type { TranslationDictionary } from "../i18n/types";

export interface ShellContextualHelpColumnProps {
  readonly pathname?: string;
  readonly locale: string;
  readonly contextualHelpArticle: UiContextualHelpArticleView;
  readonly activeHelpSectionId: string | null;
  readonly labels: TranslationDictionary["contextualHelpHybrid"];
  readonly onAskAssistant: () => void;
}

export function ShellContextualHelpColumn({
  pathname,
  locale,
  contextualHelpArticle,
  activeHelpSectionId,
  labels,
  onAskAssistant,
}: ShellContextualHelpColumnProps): React.ReactElement {
  return (
    <ContextualHelpColumnAndCenter
      mode="COLUMN_340PX"
      route={pathname ?? "/cockpit"}
      pack="orcia-core"
      redisCacheKey={`help:route:${pathname ?? "/cockpit"}:core:${locale}`}
      mergedLayers={["BASE", "PACK", "WORKSPACE"]}
      article={contextualHelpArticle}
      activeSectionId={activeHelpSectionId}
      rollbackAvailable={true}
      isAdmin={true}
      labels={labels}
      onAskAssistantOnScreen={onAskAssistant}
    />
  );
}
