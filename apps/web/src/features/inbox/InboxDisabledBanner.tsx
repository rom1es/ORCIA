import React from "react";
import type { TranslationDictionary } from "../../i18n/types";
import { AssistantNoEmbeddingBanner } from "./AssistantNoEmbeddingBanner";
import { AssistantReindexingBanner } from "./AssistantReindexingBanner";

export interface InboxDisabledBannerProps {
  readonly hasActiveChatModel: boolean;
  readonly hasActiveEmbeddingModel: boolean;
  readonly isReindexing: boolean;
  readonly isReindexFailed: boolean;
  readonly progressPercentage: number;
  readonly errorMessage: string | null;
  readonly noChatLabels: TranslationDictionary["assistantNoChatModel"];
  readonly ragNoticeLabels: TranslationDictionary["assistantRagNotice"];
  readonly onRelaunchReindex: () => void;
  readonly onNavigateAiModels: () => void;
}

export function InboxDisabledBanner({
  hasActiveChatModel,
  hasActiveEmbeddingModel,
  isReindexing,
  isReindexFailed,
  progressPercentage,
  errorMessage,
  noChatLabels,
  ragNoticeLabels,
  onRelaunchReindex,
  onNavigateAiModels,
}: InboxDisabledBannerProps): React.JSX.Element | null {
  if (!hasActiveChatModel) {
    return (
      <div
        role="alert"
        data-testid="assistant-no-chat-model-banner"
        className="mb-2 flex flex-col gap-1.5 rounded-lg border border-status-warning/40 bg-status-warning/10 p-3 text-xs text-text-primary"
      >
        <div className="flex items-center gap-2 font-semibold text-status-warning">
          <span>⚠️ {noChatLabels.bannerTitle}</span>
        </div>
        <p className="text-text-secondary">{noChatLabels.bannerDescription}</p>
        <div>
          <a
            href="/settings/ai-models"
            data-testid="assistant-configure-chat-model-link"
            onClick={(e) => {
              e.preventDefault();
              onNavigateAiModels();
            }}
            className="inline-flex items-center gap-1 font-medium text-action-primary underline hover:opacity-80"
          >
            {noChatLabels.configureCta}
          </a>
        </div>
      </div>
    );
  }
  if (!hasActiveEmbeddingModel) {
    return (
      <AssistantNoEmbeddingBanner
        title={ragNoticeLabels.noEmbeddingTitle}
        description={ragNoticeLabels.noEmbeddingDescription}
        configureCta={ragNoticeLabels.configureEmbeddingCta}
        onConfigure={onNavigateAiModels}
      />
    );
  }
  if (isReindexing) {
    return (
      <AssistantReindexingBanner
        status="IN_PROGRESS"
        progressPercentage={progressPercentage}
        labels={ragNoticeLabels}
        onConfigure={onNavigateAiModels}
      />
    );
  }
  if (isReindexFailed) {
    return (
      <AssistantReindexingBanner
        status="FAILED"
        progressPercentage={progressPercentage}
        errorMessage={errorMessage}
        labels={ragNoticeLabels}
        onRelaunch={onRelaunchReindex}
        onConfigure={onNavigateAiModels}
      />
    );
  }
  return null;
}
