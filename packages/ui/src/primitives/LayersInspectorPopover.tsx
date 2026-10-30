export type SubWorkflowLayerZoneKey = "inputs" | "capabilities" | "deliverables";

export interface SubWorkflowLayerViewItem {
  readonly layerId: string;
  readonly label: string;
  readonly zone: SubWorkflowLayerZoneKey;
  readonly orderIndex: number;
  readonly enabled: boolean;
}

export interface LayersInspectorPopoverProps {
  readonly nodeId: string;
  readonly nodeTitle: string;
  readonly layers: readonly SubWorkflowLayerViewItem[];
  readonly onToggleLayer: (layerId: string, nextEnabled: boolean) => void;
  readonly onDeleteLayer?: (layerId: string) => void;
  readonly labels: {
    readonly badgePrefix: string;
    readonly inputsZoneTitle: string;
    readonly capabilitiesZoneTitle: string;
    readonly deliverablesZoneTitle: string;
    readonly enabledStatusLabel: string;
    readonly skippedStatusLabel: string;
    readonly deleteActionLabel: string;
  };
}

/**
 * Inspecteur de Couches (Story 8.5 / UX-DR18) sur les nœuds composites SUB_WORKFLOW :
 * Affiche le badge `COUCHES · N` et regroupe les couches en 3 zones :
 * 1. Entrées & Contexte (inputs)
 * 2. Capacités & Agents internes (capabilities)
 * 3. Livrables & Contrôles de sortie (deliverables)
 * Permet d'activer/désactiver (`enabled: false -> SKIPPED` au runtime DBOS) sans casser le DAG parent.
 */
export function LayersInspectorPopover({
  nodeId,
  nodeTitle,
  layers,
  onToggleLayer,
  onDeleteLayer,
  labels,
}: LayersInspectorPopoverProps) {
  const zones: readonly { key: SubWorkflowLayerZoneKey; title: string }[] = [
    { key: "inputs", title: labels.inputsZoneTitle },
    { key: "capabilities", title: labels.capabilitiesZoneTitle },
    { key: "deliverables", title: labels.deliverablesZoneTitle },
  ];

  return (
    <section
      data-testid={`layers-inspector-${nodeId}`}
      aria-label={`${labels.badgePrefix} ${nodeTitle}`}
      className="flex flex-col gap-3 rounded-lg border border-[var(--color-border-subtle)] bg-[var(--color-surface-elevated)] p-3"
    >
      <div className="flex items-center justify-between border-b border-[var(--color-border-subtle)] pb-2">
        <span className="text-xs font-semibold text-[var(--color-text-primary)]">
          {nodeTitle}
        </span>
        <span
          data-testid={`layers-count-badge-${nodeId}`}
          className="rounded bg-[var(--color-surface-canvas)] px-2 py-0.5 font-mono text-[11px] font-semibold text-[var(--color-brand-primary)]"
        >
          {labels.badgePrefix} · {layers.length}
        </span>
      </div>

      <div className="grid grid-cols-1 gap-2.5">
        {zones.map((zone) => {
          const zoneLayers = layers
            .filter((item) => item.zone === zone.key)
            .slice()
            .sort((a, b) => a.orderIndex - b.orderIndex);

          return (
            <div
              key={zone.key}
              data-testid={`layers-zone-${zone.key}`}
              className="rounded border border-[var(--color-border-subtle)] bg-[var(--color-surface-canvas)] p-2"
            >
              <h4 className="mb-1.5 text-[11px] font-semibold uppercase tracking-wide text-[var(--color-text-muted)]">
                {zone.title}
              </h4>
              <ul className="flex flex-col gap-1">
                {zoneLayers.map((layer) => (
                  <li
                    key={layer.layerId}
                    data-testid={`layer-row-${layer.layerId}`}
                    className="flex items-center justify-between gap-2 rounded bg-[var(--color-surface-elevated)] px-2 py-1 text-xs"
                  >
                    <div className="flex items-center gap-2">
                      <span
                        className={
                          layer.enabled
                            ? "font-medium text-[var(--color-text-primary)]"
                            : "line-through text-[var(--color-text-muted)]"
                        }
                      >
                        {layer.label}
                      </span>
                      <span
                        data-testid={`layer-status-${layer.layerId}`}
                        className="font-mono text-[10px] text-[var(--color-text-muted)]"
                      >
                        {layer.enabled ? labels.enabledStatusLabel : labels.skippedStatusLabel}
                      </span>
                    </div>

                    <div className="flex items-center gap-1.5">
                      <button
                        type="button"
                        data-testid={`layer-toggle-${layer.layerId}`}
                        aria-pressed={layer.enabled}
                        onClick={() => onToggleLayer(layer.layerId, !layer.enabled)}
                        className="rounded border border-[var(--color-border-subtle)] px-2 py-0.5 font-mono text-[10px] text-[var(--color-text-secondary)]"
                      >
                        {layer.enabled ? "ON" : "SKIPPED"}
                      </button>
                      {onDeleteLayer ? (
                        <button
                          type="button"
                          data-testid={`layer-delete-${layer.layerId}`}
                          onClick={() => onDeleteLayer(layer.layerId)}
                          className="rounded px-1.5 py-0.5 text-[10px] text-[var(--color-status-failed)]"
                        >
                          {labels.deleteActionLabel}
                        </button>
                      ) : null}
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          );
        })}
      </div>
    </section>
  );
}
