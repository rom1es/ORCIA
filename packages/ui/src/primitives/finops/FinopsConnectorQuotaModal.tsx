import React, { useEffect, useState } from "react";
import { OrciaDialog } from "../RadixDesignSystemPrimitives";
import type {
  RemoteServiceRowData,
  RemoteServicesTabLabels,
  UiValuationMode,
  UpdateConnectorQuotaInput,
} from "./FinopsDashboardTypes";

export interface FinopsConnectorQuotaModalProps {
  readonly open: boolean;
  readonly onOpenChange: (open: boolean) => void;
  readonly service: RemoteServiceRowData | null;
  readonly labels: RemoteServicesTabLabels;
  readonly onSaveQuota?: (input: UpdateConnectorQuotaInput) => void;
}

export function FinopsConnectorQuotaModal({
  open,
  onOpenChange,
  service,
  labels,
  onSaveQuota,
}: FinopsConnectorQuotaModalProps): React.ReactElement {
  const [valuationMode, setValuationMode] = useState<UiValuationMode>(
    service?.valuationMode ?? "NATIVE_TELEMETRY",
  );
  const [maxPerCallEur, setMaxPerCallEur] = useState<string>(
    String(service?.maxReportedCostPerCallEur ?? 5),
  );
  const [fixedCallCostEur, setFixedCallCostEur] = useState<string>(
    String(service?.fixedCostPerCallEur ?? 0),
  );
  const [unitTariffEur, setUnitTariffEur] = useState<string>(
    String(service?.unitTariffEur ?? 0),
  );
  const [unitName, setUnitName] = useState<string>(service?.defaultUnitName ?? "");
  const [maxDailyCalls, setMaxDailyCalls] = useState<string>(
    service?.maxDailyCalls != null ? String(service.maxDailyCalls) : "",
  );
  const [maxMonthlyCostEur, setMaxMonthlyCostEur] = useState<string>(
    service?.maxMonthlyCostEur != null ? String(service.maxMonthlyCostEur) : "",
  );

  useEffect(() => {
    if (!service) return;
    setValuationMode(service.valuationMode);
    setMaxPerCallEur(String(service.maxReportedCostPerCallEur));
    setFixedCallCostEur(String(service.fixedCostPerCallEur));
    setUnitTariffEur(String(service.unitTariffEur));
    setUnitName(service.defaultUnitName ?? "");
    setMaxDailyCalls(service.maxDailyCalls != null ? String(service.maxDailyCalls) : "");
    setMaxMonthlyCostEur(
      service.maxMonthlyCostEur != null ? String(service.maxMonthlyCostEur) : "",
    );
  }, [service]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!service) return;
    onSaveQuota?.({
      connectorKey: service.connectorKey,
      valuationMode,
      maxReportedCostPerCallEur: Math.max(0, Number(maxPerCallEur) || 0),
      fixedCostPerCallEur: Math.max(0, Number(fixedCallCostEur) || 0),
      unitTariffEur: Math.max(0, Number(unitTariffEur) || 0),
      defaultUnitName: unitName.trim() ? unitName.trim() : null,
      maxDailyCalls: maxDailyCalls.trim() ? Math.max(0, Math.trunc(Number(maxDailyCalls))) : null,
      maxMonthlyCostEur: maxMonthlyCostEur.trim()
        ? Math.max(0, Number(maxMonthlyCostEur))
        : null,
    });
    onOpenChange(false);
  };

  const modalLabels = labels.quotaModal;

  return (
    <OrciaDialog
      open={open}
      onOpenChange={onOpenChange}
      title={`${modalLabels.title}${service ? ` · ${service.displayName}` : ""}`}
      description={modalLabels.description}
      testId="finops-connector-quota-modal"
      closeLabel={modalLabels.cancelButton}
    >
      <form
        onSubmit={handleSubmit}
        data-testid="finops-connector-quota-form"
        autoComplete="off"
        data-lpignore="true"
        data-form-type="other"
        style={{ display: "flex", flexDirection: "column", gap: "14px", marginTop: "12px" }}
      >
        <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
          <label htmlFor="finops-connector-valuation-select" style={{ fontSize: "12px", fontWeight: 600 }}>
            {modalLabels.valuationModeLabel}
          </label>
          <select
            id="finops-connector-valuation-select"
            data-testid="finops-connector-valuation-select"
            value={valuationMode}
            onChange={(e) => setValuationMode(e.target.value as UiValuationMode)}
            className="orcia-ds-input"
            autoComplete="off"
            data-lpignore="true"
            data-1p-ignore="true"
            data-bwignore="true"
            data-form-type="other"
          >
            <option value="NATIVE_TELEMETRY">{labels.valuationModes.nativeTelemetry}</option>
            <option value="FIXED_SCALE">{labels.valuationModes.fixedScale}</option>
            <option value="VOLUMETRIC_ONLY">{labels.valuationModes.volumetricOnly}</option>
          </select>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
          <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
            <label htmlFor="finops-connector-max-call-eur" style={{ fontSize: "12px", fontWeight: 600 }}>
              {modalLabels.maxPerCallLabel}
            </label>
            <input
              id="finops-connector-max-call-eur"
              data-testid="finops-connector-max-call-eur"
              type="number"
              min="0"
              step="0.5"
              value={maxPerCallEur}
              onChange={(e) => setMaxPerCallEur(e.target.value)}
              className="orcia-ds-input"
              autoComplete="off"
              data-lpignore="true"
              data-1p-ignore="true"
              data-bwignore="true"
              data-form-type="other"
            />
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
            <label htmlFor="finops-connector-fixed-call-eur" style={{ fontSize: "12px", fontWeight: 600 }}>
              {modalLabels.fixedCallCostLabel}
            </label>
            <input
              id="finops-connector-fixed-call-eur"
              data-testid="finops-connector-fixed-call-eur"
              type="number"
              min="0"
              step="0.01"
              value={fixedCallCostEur}
              onChange={(e) => setFixedCallCostEur(e.target.value)}
              className="orcia-ds-input"
              autoComplete="off"
              data-lpignore="true"
              data-1p-ignore="true"
              data-bwignore="true"
              data-form-type="other"
            />
          </div>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
          <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
            <label htmlFor="finops-connector-unit-tariff-eur" style={{ fontSize: "12px", fontWeight: 600 }}>
              {modalLabels.unitTariffLabel}
            </label>
            <input
              id="finops-connector-unit-tariff-eur"
              data-testid="finops-connector-unit-tariff-eur"
              type="number"
              min="0"
              step="0.01"
              value={unitTariffEur}
              onChange={(e) => setUnitTariffEur(e.target.value)}
              className="orcia-ds-input"
              autoComplete="off"
              data-lpignore="true"
              data-1p-ignore="true"
              data-bwignore="true"
              data-form-type="other"
            />
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
            <label htmlFor="finops-connector-unit-name" style={{ fontSize: "12px", fontWeight: 600 }}>
              {modalLabels.unitNameLabel}
            </label>
            <input
              id="finops-connector-unit-name"
              data-testid="finops-connector-unit-name"
              type="search"
              value={unitName}
              onChange={(e) => setUnitName(e.target.value)}
              className="orcia-ds-input"
              autoComplete="off"
              data-lpignore="true"
              data-1p-ignore="true"
              data-bwignore="true"
              data-form-type="other"
            />
          </div>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
          <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
            <label htmlFor="finops-connector-max-daily-calls" style={{ fontSize: "12px", fontWeight: 600 }}>
              {modalLabels.maxDailyCallsLabel}
            </label>
            <input
              id="finops-connector-max-daily-calls"
              data-testid="finops-connector-max-daily-calls"
              type="number"
              min="0"
              step="1"
              value={maxDailyCalls}
              onChange={(e) => setMaxDailyCalls(e.target.value)}
              className="orcia-ds-input"
              autoComplete="off"
              data-lpignore="true"
              data-1p-ignore="true"
              data-bwignore="true"
              data-form-type="other"
            />
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
            <label htmlFor="finops-connector-max-monthly-eur" style={{ fontSize: "12px", fontWeight: 600 }}>
              {modalLabels.maxMonthlyCostLabel}
            </label>
            <input
              id="finops-connector-max-monthly-eur"
              data-testid="finops-connector-max-monthly-eur"
              type="number"
              min="0"
              step="1"
              value={maxMonthlyCostEur}
              onChange={(e) => setMaxMonthlyCostEur(e.target.value)}
              className="orcia-ds-input"
              autoComplete="off"
              data-lpignore="true"
              data-1p-ignore="true"
              data-bwignore="true"
              data-form-type="other"
            />
          </div>
        </div>

        <div style={{ display: "flex", justifyContent: "flex-end", gap: "8px", marginTop: "8px" }}>
          <button
            type="button"
            data-testid="finops-connector-quota-cancel-btn"
            className="orcia-ds-btn orcia-ds-btn-secondary"
            onClick={() => onOpenChange(false)}
          >
            {modalLabels.cancelButton}
          </button>
          <button
            type="submit"
            data-testid="finops-connector-quota-save-btn"
            className="orcia-ds-btn orcia-ds-btn-primary"
          >
            {modalLabels.saveButton}
          </button>
        </div>
      </form>
    </OrciaDialog>
  );
}
