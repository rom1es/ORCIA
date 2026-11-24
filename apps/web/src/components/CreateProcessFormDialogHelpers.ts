import type { SubWorkflowLayerViewItem } from "@orcia/ui";
import type React from "react";
import { resolveDictionaryForFlag } from "../i18n";
import type { ConfiguredWorkflowItem } from "./platformSetupStore";

export interface CreateProcessFormDialogProps {
  readonly open: boolean;
  readonly onOpenChange: (open: boolean) => void;
  readonly isFr: boolean;
  readonly openHelpSection: (sectionId: string) => void;
  readonly upsertWorkflow: (input: ConfiguredWorkflowItem) => void;
  readonly presetDraft?: ConfiguredWorkflowItem | null;
}

export const processDialogInputStyle: React.CSSProperties = {
  padding: "7px 10px",
  borderRadius: "var(--radius-sm)",
  border: "1px solid var(--color-border)",
  backgroundColor: "var(--color-surface-card)",
  color: "var(--color-foreground)",
  width: "100%",
  boxSizing: "border-box",
};

export const processDialogSecondaryBtnStyle: React.CSSProperties = {
  padding: "6px 12px",
  borderRadius: "var(--radius-sm)",
  border: "1px solid var(--color-border)",
  backgroundColor: "var(--color-surface-card)",
  color: "var(--color-foreground)",
  fontWeight: 600,
  fontSize: "12px",
  cursor: "pointer",
};

export function slugifyProcessTitle(value: string): string {
  return value
    .normalize("NFD")
    .replace(/\p{M}/gu, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

export function buildDefaultProcessLayers(isFr: boolean): readonly SubWorkflowLayerViewItem[] {
  const defaultLayers = resolveDictionaryForFlag(isFr).shellChrome.createProcessDialog.defaultLayers;
  return [
    {
      layerId: "layer-ctx",
      label: defaultLayers.ctx,
      zone: "inputs",
      orderIndex: 1,
      enabled: true,
    },
    {
      layerId: "layer-agent",
      label: defaultLayers.agent,
      zone: "capabilities",
      orderIndex: 1,
      enabled: true,
    },
    {
      layerId: "layer-out",
      label: defaultLayers.out,
      zone: "deliverables",
      orderIndex: 1,
      enabled: true,
    },
  ];
}
