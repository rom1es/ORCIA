import React from "react";
import { ContextualHelpColumnView } from "./ContextualHelpColumnView";
import type { ContextualHelpColumnAndCenterProps } from "./ContextualHelpTypes";
import { HelpCenterCatalogView } from "./HelpCenterCatalogView";

export type {
  ContextualHelpColumnAndCenterLabels,
  ContextualHelpColumnAndCenterProps,
  UiContextualHelpArticleView,
  UiContextualHelpSectionItem,
  UiHelpArticleLayer,
} from "./ContextualHelpTypes";
export { ContextualHelpColumnView } from "./ContextualHelpColumnView";
export { HelpCenterCatalogView } from "./HelpCenterCatalogView";

/**
 * Dispatcher preserving backwards-compatible `ContextualHelpColumnAndCenter` export
 * across Zone 4 (`COLUMN_340PX` -> `ContextualHelpColumnView`) and `/help` (`HELP_MENU_CENTER` -> `HelpCenterCatalogView`).
 */
export function ContextualHelpColumnAndCenter(
  props: ContextualHelpColumnAndCenterProps,
): React.ReactElement {
  if (props.mode === "HELP_MENU_CENTER") {
    return <HelpCenterCatalogView {...props} />;
  }
  return <ContextualHelpColumnView {...props} />;
}
