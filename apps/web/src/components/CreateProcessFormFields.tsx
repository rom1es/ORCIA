import {
  ContextualInfoTriggerButton,
  type SubWorkflowLayerViewItem,
} from "@orcia/ui";
import React from "react";
import type { ShellChromeDictionary } from "../i18n/locales/shell_chrome_labels";
import {
  processDialogInputStyle,
  processDialogSecondaryBtnStyle,
  slugifyProcessTitle,
} from "./CreateProcessFormDialogHelpers";

type CreateProcessCopy = ShellChromeDictionary["createProcessDialog"];

export interface CreateProcessFormFieldsProps {
  readonly copy: CreateProcessCopy;
  readonly wfTitle: string;
  readonly setWfTitle: (v: string) => void;
  readonly wfKey: string;
  readonly setWfKey: (v: string) => void;
  readonly wfStatus: "DRAFT" | "PUBLISHED";
  readonly setWfStatus: (v: "DRAFT" | "PUBLISHED") => void;
  readonly wfPrePrompt: string;
  readonly setWfPrePrompt: (v: string) => void;
  readonly wfParamsCsv: string;
  readonly setWfParamsCsv: (v: string) => void;
  readonly wfSectionsCsv: string;
  readonly setWfSectionsCsv: (v: string) => void;
  readonly layers: readonly SubWorkflowLayerViewItem[];
  readonly onToggleLayer: (layerId: string) => void;
  readonly openHelpSection: (sectionId: string) => void;
}

export function CreateProcessFormFields({
  copy,
  wfTitle,
  setWfTitle,
  wfKey,
  setWfKey,
  wfStatus,
  setWfStatus,
  wfPrePrompt,
  setWfPrePrompt,
  wfParamsCsv,
  setWfParamsCsv,
  wfSectionsCsv,
  setWfSectionsCsv,
  layers,
  onToggleLayer,
  openHelpSection,
}: CreateProcessFormFieldsProps): React.ReactElement {
  return (
    <>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
          gap: "10px",
        }}
      >
        <label style={{ display: "flex", flexDirection: "column", gap: "4px", fontSize: "12px", fontWeight: 600 }}>
          <span>{copy.nameLabel}</span>
          <input
            type="text"
            autoComplete="off"
            data-lpignore="true"
            data-1p-ignore="true"
            data-bwignore="true"
            data-form-type="other"
            data-testid="workflow-title-input"
            value={wfTitle}
            onChange={(e) => setWfTitle(e.target.value)}
            placeholder={copy.namePlaceholder}
            style={processDialogInputStyle}
          />
        </label>

        <label style={{ display: "flex", flexDirection: "column", gap: "4px", fontSize: "12px", fontWeight: 600 }}>
          <span>{copy.keyLabel}</span>
          <input
            type="text"
            autoComplete="off"
            data-lpignore="true"
            data-1p-ignore="true"
            data-bwignore="true"
            data-form-type="other"
            data-testid="workflow-key-input"
            value={wfKey}
            onChange={(e) => setWfKey(e.target.value)}
            placeholder={slugifyProcessTitle(wfTitle) || copy.keyPlaceholder}
            style={processDialogInputStyle}
          />
        </label>

        <label style={{ display: "flex", flexDirection: "column", gap: "4px", fontSize: "12px", fontWeight: 600 }}>
          <span>{copy.statusLabel}</span>
          <select
            data-testid="workflow-status-select"
            value={wfStatus}
            onChange={(e) => setWfStatus(e.target.value as "DRAFT" | "PUBLISHED")}
            style={processDialogInputStyle}
          >
            <option value="DRAFT">{copy.statusDraft}</option>
            <option value="PUBLISHED">{copy.statusPublished}</option>
          </select>
        </label>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
          <label htmlFor="workflow-preprompt-textarea" style={{ fontSize: "12px", fontWeight: 600 }}>
            {copy.prePromptLabel}
          </label>
          <ContextualInfoTriggerButton
            sectionId="workflows-instructions"
            label={copy.prePromptHelpLabel}
            onOpenHelpSection={openHelpSection}
          />
        </div>
        <textarea
          id="workflow-preprompt-textarea"
          autoComplete="off"
          data-lpignore="true"
          data-1p-ignore="true"
          data-bwignore="true"
          data-form-type="other"
          data-testid="workflow-preprompt-textarea"
          value={wfPrePrompt}
          onChange={(e) => setWfPrePrompt(e.target.value)}
          rows={3}
          placeholder={copy.prePromptPlaceholder}
          style={processDialogInputStyle}
        />
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
          <strong style={{ fontSize: "12px" }}>{copy.contractHeading}</strong>
          <ContextualInfoTriggerButton
            sectionId="workflows-deliverable-contract"
            label={copy.contractHelpLabel}
            onOpenHelpSection={openHelpSection}
          />
        </div>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
            gap: "10px",
          }}
        >
          <input
            type="text"
            autoComplete="off"
            data-lpignore="true"
            data-1p-ignore="true"
            data-bwignore="true"
            data-form-type="other"
            data-testid="workflow-params-input"
            value={wfParamsCsv}
            onChange={(e) => setWfParamsCsv(e.target.value)}
            placeholder={copy.paramsPlaceholder}
            style={processDialogInputStyle}
          />
          <input
            type="text"
            autoComplete="off"
            data-lpignore="true"
            data-1p-ignore="true"
            data-bwignore="true"
            data-form-type="other"
            data-testid="workflow-sections-input"
            value={wfSectionsCsv}
            onChange={(e) => setWfSectionsCsv(e.target.value)}
            placeholder={copy.sectionsPlaceholder}
            style={processDialogInputStyle}
          />
        </div>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <strong style={{ fontSize: "12px" }}>{copy.layersHeading}</strong>
          <ContextualInfoTriggerButton
            sectionId="workflows-steps-layers"
            label={copy.layersHelpLabel}
            onOpenHelpSection={openHelpSection}
          />
        </div>
        <div style={{ display: "grid", gap: "6px" }}>
          {layers.map((layer) => (
            <div
              key={layer.layerId}
              data-testid={`process-layer-row-${layer.layerId}`}
              style={{
                padding: "6px 10px",
                borderRadius: "var(--radius-sm)",
                border: "1px solid var(--color-border)",
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                gap: "10px",
              }}
            >
              <span style={{ fontSize: "12.5px", fontWeight: 500 }}>{layer.label}</span>
              <button
                type="button"
                data-testid={`toggle-process-layer-btn-${layer.layerId}`}
                onClick={() => onToggleLayer(layer.layerId)}
                style={processDialogSecondaryBtnStyle}
              >
                {layer.enabled ? copy.stepEnabled : copy.stepSkipped}
              </button>
            </div>
          ))}
        </div>
      </div>
    </>
  );
}
