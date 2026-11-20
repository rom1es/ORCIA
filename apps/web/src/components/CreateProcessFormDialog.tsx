import {
  ContextualInfoTriggerButton,
  OrciaDialog,
  type SubWorkflowLayerViewItem,
} from "@orcia/ui";
import React, { useEffect, useState } from "react";
import {
  buildDefaultProcessLayers,
  processDialogInputStyle,
  processDialogSecondaryBtnStyle,
  slugifyProcessTitle,
  type CreateProcessFormDialogProps,
} from "./CreateProcessFormDialogHelpers";

export type { CreateProcessFormDialogProps };

const inputStyle = processDialogInputStyle;
const secondaryBtnStyle = processDialogSecondaryBtnStyle;

export function CreateProcessFormDialog({
  open,
  onOpenChange,
  isFr,
  openHelpSection,
  upsertWorkflow,
  presetDraft,
}: CreateProcessFormDialogProps): React.ReactElement {
  const [wfTitle, setWfTitle] = useState("");
  const [wfKey, setWfKey] = useState("");
  const [wfVersion, setWfVersion] = useState("1.0.0");
  const [wfStatus, setWfStatus] = useState<"DRAFT" | "PUBLISHED">("DRAFT");
  const [wfPrePrompt, setWfPrePrompt] = useState("");
  const [wfParamsCsv, setWfParamsCsv] = useState("");
  const [wfSectionsCsv, setWfSectionsCsv] = useState("");
  const [layers, setLayers] = useState<readonly SubWorkflowLayerViewItem[]>(() =>
    buildDefaultProcessLayers(isFr),
  );

  useEffect(() => {
    if (!presetDraft) return;
    setWfTitle(presetDraft.title);
    setWfKey(presetDraft.workflowKey);
    setWfVersion(presetDraft.version);
    setWfStatus(presetDraft.status);
    setWfPrePrompt(presetDraft.prePrompt);
    setWfParamsCsv(presetDraft.requiredParams.join(", "));
    setWfSectionsCsv(presetDraft.requiredMarkdownSections.join(", "));
    if (presetDraft.layers.length > 0) {
      setLayers(presetDraft.layers);
    }
  }, [presetDraft]);

  return (
    <OrciaDialog
      open={open}
      onOpenChange={onOpenChange}
      title={isFr ? "Créer un Processus Métier" : "Create a Business Process"}
      testId="create-process-modal"
      closeLabel={isFr ? "Fermer" : "Close"}
      hideHeaderCloseButton
      contentClassName="orcia-ds-dialog-content-wide"
    >
      <form
        data-testid="create-workflow-form"
        autoComplete="off"
        data-lpignore="true"
        data-form-type="other"
        className="orcia-ds-dialog-body"
        onSubmit={(e) => {
          e.preventDefault();
          const effectiveTitle = wfTitle.trim() || wfKey.trim();
          const effectiveKey =
            wfKey.trim() || slugifyProcessTitle(wfTitle) || "processus-metier";
          if (!effectiveTitle) return;
          upsertWorkflow({
            workflowKey: effectiveKey,
            title: effectiveTitle,
            version: wfVersion.trim() || "1.0.0",
            status: wfStatus,
            prePrompt: wfPrePrompt.trim(),
            prePromptSha256:
              "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855", // pragma: allowlist secret
            requiredParams: wfParamsCsv
              .split(",")
              .map((s) => s.trim())
              .filter(Boolean),
            requiredMarkdownSections: wfSectionsCsv
              .split(",")
              .map((s) => s.trim())
              .filter(Boolean),
            triggers: ["manual"],
            layers,
          });
          setWfTitle("");
          setWfKey("");
          setWfPrePrompt("");
          setWfParamsCsv("");
          setWfSectionsCsv("");
          onOpenChange(false);
        }}
      >
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
            gap: "10px",
          }}
        >
          <label style={{ display: "flex", flexDirection: "column", gap: "4px", fontSize: "12px", fontWeight: 600 }}>
            <span>{isFr ? "Nom du processus *" : "Process name *"}</span>
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
              placeholder={
                isFr
                  ? "Ex : Revue de contrat fournisseur, Analyse de demande client..."
                  : "E.g., Supplier contract review..."
              }
              style={inputStyle}
            />
          </label>

          <label style={{ display: "flex", flexDirection: "column", gap: "4px", fontSize: "12px", fontWeight: 600 }}>
            <span>
              {isFr
                ? "Identifiant court (généré automatiquement si vide)"
                : "Short identifier (auto-generated if empty)"}
            </span>
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
              placeholder={
                slugifyProcessTitle(wfTitle) ||
                (isFr ? "Ex : revue-contrat-fournisseur" : "E.g., supplier-contract-review")
              }
              style={inputStyle}
            />
          </label>

          <label style={{ display: "flex", flexDirection: "column", gap: "4px", fontSize: "12px", fontWeight: 600 }}>
            <span>{isFr ? "Statut à l'enregistrement" : "Status when saved"}</span>
            <select
              data-testid="workflow-status-select"
              value={wfStatus}
              onChange={(e) => setWfStatus(e.target.value as "DRAFT" | "PUBLISHED")}
              style={inputStyle}
            >
              <option value="DRAFT">
                {isFr ? "Brouillon (en préparation)" : "Draft (in preparation)"}
              </option>
              <option value="PUBLISHED">
                {isFr ? "Publié (prêt à être lancé)" : "Published (ready to run)"}
              </option>
            </select>
          </label>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
            <label htmlFor="workflow-preprompt-textarea" style={{ fontSize: "12px", fontWeight: 600 }}>
              {isFr
                ? "Objectif et instructions données aux agents"
                : "Goal and instructions for agents"}
            </label>
            <ContextualInfoTriggerButton
              sectionId="workflows-instructions"
              label={
                isFr
                  ? "Comment rédiger l'objectif et les instructions du processus ?"
                  : "How to write the process goal and instructions?"
              }
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
            placeholder={
              isFr
                ? "Décrivez simplement ce que ce processus doit accomplir..."
                : "Describe in plain language what this process should accomplish..."
            }
            style={inputStyle}
          />
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
            <strong style={{ fontSize: "12px" }}>
              {isFr
                ? "Informations demandées au lancement et structure du livrable (optionnel)"
                : "Launch inputs and deliverable structure (optional)"}
            </strong>
            <ContextualInfoTriggerButton
              sectionId="workflows-deliverable-contract"
              label={
                isFr
                  ? "Comprendre les informations d'entrée et les rubriques du livrable final"
                  : "Understand launch inputs and final deliverable sections"
              }
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
              placeholder={
                isFr
                  ? "Informations demandées au lancement (ex : fournisseur, montant)..."
                  : "Information requested at launch (e.g., supplier, amount)..."
              }
              style={inputStyle}
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
              placeholder={
                isFr
                  ? "Rubriques du document final (ex : Résumé, Risques, Décision)..."
                  : "Final document sections (e.g., Summary, Risks, Decision)..."
              }
              style={inputStyle}
            />
          </div>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <strong style={{ fontSize: "12px" }}>
              {isFr
                ? "Étapes clés exécutées lors du lancement de ce processus"
                : "Key steps executed when running this process"}
            </strong>
            <ContextualInfoTriggerButton
              sectionId="workflows-steps-layers"
              label={
                isFr
                  ? "Comprendre les 3 grandes étapes d'exécution d'un processus"
                  : "Understand the 3 main execution steps of a process"
              }
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
                  onClick={() =>
                    setLayers((prev) =>
                      prev.map((item) =>
                        item.layerId === layer.layerId
                          ? { ...item, enabled: !item.enabled }
                          : item,
                      ),
                    )
                  }
                  style={secondaryBtnStyle}
                >
                  {layer.enabled
                    ? isFr ? "✓ Étape active" : "✓ Step enabled"
                    : isFr ? "Étape ignorée" : "Step skipped"}
                </button>
              </div>
            ))}
          </div>
        </div>

        <div className="orcia-ds-dialog-footer">
          <span style={{ fontSize: "12px", color: "var(--color-muted-foreground)", marginRight: "auto" }}>
            {isFr ? `Version : ${wfVersion}` : `Version: ${wfVersion}`}
          </span>
          <button
            type="button"
            onClick={() => onOpenChange(false)}
            className="orcia-ds-btn orcia-ds-btn-secondary"
          >
            {isFr ? "Annuler" : "Cancel"}
          </button>
          <button
            type="submit"
            data-testid="save-workflow-btn"
            className="orcia-ds-btn orcia-ds-btn-primary"
          >
            {isFr ? "+ Enregistrer le Processus" : "+ Save Process"}
          </button>
        </div>
      </form>
    </OrciaDialog>
  );
}
