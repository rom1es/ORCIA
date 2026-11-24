import type React from "react";

export interface DiscoveredModelOption {
  readonly id: string;
  readonly displayName?: string | null;
  readonly description?: string | null;
  readonly usageHint?: "chat" | "embedding" | "unknown";
  readonly ownedBy?: string | null;
}

export interface OrciaModelComboboxLabels {
  readonly noModelsFound: string;
  readonly refreshLabel: string;
  readonly loadingLabel: string;
  readonly toggleListAriaLabel: string;
  readonly freeformHint?: string;
  readonly chatBadge?: string;
  readonly embeddingBadge?: string;
}

export interface OrciaModelComboboxProps {
  readonly id?: string;
  readonly testId: string;
  readonly value: string;
  readonly onChange: (value: string) => void;
  readonly models: readonly DiscoveredModelOption[];
  readonly targetUsage?: "chat" | "embedding";
  readonly isLoading?: boolean;
  readonly errorMessage?: string | null;
  readonly onRefresh?: () => void;
  readonly placeholder?: string;
  readonly disabled?: boolean;
  readonly labels: OrciaModelComboboxLabels;
  readonly className?: string;
  readonly style?: React.CSSProperties;
  readonly maxDisplayedItems?: number;
}
