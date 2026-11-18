import { createOrciaApiClient } from "@orcia/api-client";
import {
  ContextualHelpColumnAndCenter,
  OrciaAlertBanner,
  type AutonomousExecutionBadgeLabels,
  type UiContextualHelpArticleView,
  type UiHelpArticleLayer,
} from "@orcia/ui";
import React, { useCallback, useEffect, useMemo, useState } from "react";
import type { TranslationDictionary } from "../i18n/types";
import { useAuthSessionStore } from "../stores/authSessionStore";

export interface ShellContextualHelpColumnProps {
  readonly pathname?: string;
  readonly locale: "fr" | "en";
  readonly contextualHelpArticle: UiContextualHelpArticleView;
  readonly activeHelpSectionId: string | null;
  readonly labels: TranslationDictionary["contextualHelpHybrid"];
  readonly autonomousBadgeLabels?: AutonomousExecutionBadgeLabels;
  readonly onAskAssistant: () => void;
}

export function ShellContextualHelpColumn({
  pathname,
  locale,
  contextualHelpArticle,
  activeHelpSectionId,
  labels,
  autonomousBadgeLabels,
  onAskAssistant,
}: ShellContextualHelpColumnProps): React.ReactElement {
  const effectiveRoute = pathname ?? "/cockpit";
  const roles = useAuthSessionStore((s) => s.roles);
  const readOnlyObserver = useAuthSessionStore((s) => s.readOnlyObserver);
  const isAdmin =
    !readOnlyObserver &&
    roles.some((r) => r === "PLATFORM_ADMIN" || r === "ARCHITECT" || r === "TEAM_LEAD");

  const [resolvedArticle, setResolvedArticle] = useState<UiContextualHelpArticleView | null>(null);
  const [resolvedLayers, setResolvedLayers] = useState<readonly UiHelpArticleLayer[]>([
    "BASE",
    "PACK",
    "WORKSPACE",
  ]);
  const [resolvedCacheKey, setResolvedCacheKey] = useState<string>(
    `help:route:${effectiveRoute}:core:${locale}`,
  );
  const [rollbackAvailable, setRollbackAvailable] = useState<boolean>(true);
  const [actionError, setActionError] = useState<string | null>(null);

  const apiClient = useMemo(() => createOrciaApiClient({ baseUrl: "" }), []);

  const refreshResolvedHelp = useCallback(async () => {
    try {
      const res = await apiClient.resolveContextualHelp(effectiveRoute, locale, "core");
      if (res && res.active_article) {
        const art = res.active_article;
        setResolvedArticle({
          resourceId: art.resource_id,
          uri: art.uri,
          title: art.title,
          version: art.version,
          lang: art.lang,
          layer: art.layer,
          packName: art.pack_name ?? null,
          boundRoutes: art.bound_routes,
          summaryWhatFor: art.summary_what_for,
          stepByStepItems: art.step_by_step_items,
          keyTermsItems: art.key_terms_items,
          faqItems: art.faq_items,
          sections: contextualHelpArticle.sections,
          casKey: art.cas_key,
          sha256: art.sha256,
          previousVersion: art.previous_version ?? null,
          isAutonomousGenerated: Boolean(res.is_autonomous_generated),
          autonomousRunId: res.run_id ?? null,
          contractLabel: res.contract_label ?? null,
          triggerLabel: res.trigger_label ?? null,
        });
        setResolvedLayers(res.merged_layers);
        setResolvedCacheKey(res.redis_cache_key);
        setRollbackAvailable(
          Boolean(res.previous_version_available ?? res.rollback_available),
        );
      }
    } catch {
      // Keep local fallback article when unauthenticated or offline
    }
  }, [apiClient, contextualHelpArticle.sections, effectiveRoute, locale]);

  useEffect(() => {
    setResolvedArticle(null);
    void refreshResolvedHelp();
  }, [refreshResolvedHelp]);

  const handleInvalidateAndRestoreAutonomousHelp = useCallback(
    async (runId: string, resourceId: string) => {
      try {
        setActionError(null);
        await apiClient.invalidateAndRestoreAutonomousRun(runId, {
          help_resource_id: resourceId,
          comment: "",
        });
        await refreshResolvedHelp();
      } catch (err: unknown) {
        setActionError(err instanceof Error ? err.message : String(err));
      }
    },
    [apiClient, refreshResolvedHelp],
  );

  const handleRollbackVersion = useCallback(
    async (resourceId: string) => {
      try {
        setActionError(null);
        await apiClient.rollbackContextualHelp({ resource_id: resourceId });
        await refreshResolvedHelp();
      } catch (err: unknown) {
        setActionError(err instanceof Error ? err.message : String(err));
      }
    },
    [apiClient, refreshResolvedHelp],
  );

  const displayedArticle = resolvedArticle ?? contextualHelpArticle;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
      {actionError && (
        <OrciaAlertBanner tone="crimson" role="alert" testId="contextual-help-restore-error">
          {actionError}
        </OrciaAlertBanner>
      )}
      <ContextualHelpColumnAndCenter
        mode="COLUMN_340PX"
        route={effectiveRoute}
        pack="core"
        redisCacheKey={resolvedCacheKey}
        mergedLayers={resolvedLayers}
        article={displayedArticle}
        activeSectionId={activeHelpSectionId}
        rollbackAvailable={rollbackAvailable}
        isAdmin={isAdmin}
        labels={labels}
        autonomousBadgeLabels={autonomousBadgeLabels}
        onRollbackVersion={(resId) => void handleRollbackVersion(resId)}
        onInvalidateAndRestoreAutonomousHelp={(rid, resId) =>
          void handleInvalidateAndRestoreAutonomousHelp(rid, resId)
        }
        onAskAssistantOnScreen={onAskAssistant}
      />
    </div>
  );
}
