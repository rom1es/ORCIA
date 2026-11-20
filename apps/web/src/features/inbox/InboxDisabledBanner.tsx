import React from "react";
import type { TranslationDictionary } from "../../i18n/types";
import { AssistantNoEmbeddingBanner } from "./AssistantNoEmbeddingBanner";
import { AssistantReindexingBanner } from "./AssistantReindexingBanner";

export interface InboxDisabledBannerProps {
  readonly hasActiveEmbeddingModel: boolean;
  readonly isReindexing: boolean;
  readonly isReindexFailed: boolean;
  readonly progressPercentage: number;
  readonly errorMessage: string | null;
  readonly isFr: boolean;
  readonly labels: TranslationDictionary["assistantNoEmbeddingModel"];
  readonly onRelaunchReindex: () => void;
  readonly onNavigateAiModels: () => void;
}

export function InboxDisabledBanner({
  hasActiveEmbeddingModel,
  isReindexing,
  isReindexFailed,
  progressPercentage,
  errorMessage,
  isFr,
  labels,
  onRelaunchReindex,
  onNavigateAiModels,
}: InboxDisabledBannerProps): React.JSX.Element | null {
  if (!hasActiveEmbeddingModel) {
    return (
      <AssistantNoEmbeddingBanner
        title={labels.bannerTitle}
        description={labels.bannerDescription}
        configureCta={labels.configureCta}
        onConfigure={onNavigateAiModels}
      />
    );
  }
  if (isReindexing) {
    return (
      <AssistantReindexingBanner
        status="IN_PROGRESS"
        progressPercentage={progressPercentage}
        isFr={isFr}
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
        isFr={isFr}
        onRelaunch={onRelaunchReindex}
        onConfigure={onNavigateAiModels}
      />
    );
  }
  return null;
}
