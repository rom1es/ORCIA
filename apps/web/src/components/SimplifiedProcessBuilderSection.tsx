import {
  ContextualInfoTriggerButton,
  StatusBadge,
  type SubWorkflowLayerViewItem,
} from "@orcia/ui";
import React, { useState } from "react";
import type { ConfiguredWorkflowItem } from "./platformSetupStore";

export interface SimplifiedProcessBuilderSectionProps {
  readonly isFr: boolean;
  readonly workflows: readonly ConfiguredWorkflowItem[];
  readonly openHelpSection: (sectionId: string) => void;
  readonly upsertWorkflow: (input: ConfiguredWorkflowItem) => void;
  readonly onOpenProcessesMenu?: () => void;
}

const inputStyle: React.CSSProperties = {
  padding: "7px 10px",
  borderRadius: "var(--radius-sm)",
  border: "1px solid var(--color-border)",
  backgroundColor: "var(--color-surface-card)",
  color: "var(--color-foreground)",
  width: "100%",
  boxSizing: "border-box",
};

const primaryBtnStyle: React.CSSProperties = {
  padding: "7px 14px",
  borderRadius: "var(--radius-sm)",
  border: "none",
  backgroundColor: "var(--color-primary-cobalt)",
  color: "var(--color-primary-foreground)",
  fontWeight: 600,
  cursor: "pointer",
};

const secondaryBtnStyle: React.CSSProperties = {
  padding: "6px 12px",
  borderRadius: "var(--radius-sm)",
  border: "1px solid var(--color-border)",
  backgroundColor: "var(--color-surface-card)",
  color: "var(--color-foreground)",
  fontWeight: 600,
  fontSize: "12px",
  cursor: "pointer",
};

function slugifyProcessTitle(value: string): string {
  return value
    .normalize("NFD")
    .replace(/\p{M}/gu, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

export function SimplifiedProcessBuilderSection({
  isFr,
  workflows,
  openHelpSection,
  upsertWorkflow,
  onOpenProcessesMenu,
}: SimplifiedProcessBuilderSectionProps) {
  const [wfTitle, setWfTitle] = useState("");
  const [wfKey, setWfKey] = useState("");
  const [wfVersion, setWfVersion] = useState("1.0.0");
  const [wfStatus, setWfStatus] = useState<"DRAFT" | "PUBLISHED">("DRAFT");
  const [wfPrePrompt, setWfPrePrompt] = useState("");
  const [wfParamsCsv, setWfParamsCsv] = useState("");
  const [wfSectionsCsv, setWfSectionsCsv] = useState("");
  const [layers, setLayers] = useState<readonly SubWorkflowLayerViewItem[]>([
    {
      layerId: "layer-ctx",
      label: isFr
        ? "1. Collecte des documents et du contexte"
        : "1. Gather documents and context",
      zone: "inputs",
      orderIndex: 1,
      enabled: true,
    },
    {
      layerId: "layer-agent",
      label: isFr
        ? "2. Analyse par les agents et vérification croisée"
        : "2. Agent analysis and cross-checking",
      zone: "capabilities",
      orderIndex: 1,
      enabled: true,
    },
    {
      layerId: "layer-out",
      label: isFr
        ? "3. Validation humaine finale du livrable"
        : "3. Final human approval of deliverable",
      zone: "deliverables",
      orderIndex: 1,
      enabled: true,
    },
  ]);

  const publishedCount = workflows.filter((w) => w.status === "PUBLISHED").length;
  const draftCount = workflows.filter((w) => w.status === "DRAFT").length;

  return (
    <section
      data-testid="settings-workflows-section"
      style={{ display: "flex", flexDirection: "column", gap: "14px" }}
    >
      {/* En-tête explicite avec compteurs en français et bouton d'aide contextuelle ⓘ */}
      <div
        className="orcia-bento-card"
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "12px",
        }}
      >
        <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
            <h2 style={{ margin: 0, fontSize: "16px" }}>
              {isFr
                ? "Créer et Gérer mes Processus Métiers"
                : "Create and Manage Business Processes"}
            </h2>
            <ContextualInfoTriggerButton
              sectionId="workflows-overview"
              label={
                isFr
                  ? "Comprendre à quoi sert un processus métier et comment le construire"
                  : "Understand what a business process is for and how to build it"
              }
              onOpenHelpSection={openHelpSection}
            />
          </div>
          <p style={{ margin: 0, fontSize: "13px", color: "var(--color-muted-foreground)" }}>
            {isFr
              ? "Définissez en 3 étapes simples un processus réutilisable qui combine vos agents IA et vos validations humaines."
              : "Define in 3 simple steps a reusable process combining your AI agents and human reviews."}
          </p>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
          <StatusBadge
            label={isFr ? `Publiés : ${publishedCount}` : `Published: ${publishedCount}`}
            tone="emerald"
          />
          <StatusBadge
            label={isFr ? `Brouillons : ${draftCount}` : `Drafts: ${draftCount}`}
            tone="cobalt"
          />
          {onOpenProcessesMenu ? (
            <button
              type="button"
              data-testid="settings-workflows-open-processes-menu-btn"
              onClick={onOpenProcessesMenu}
              style={secondaryBtnStyle}
            >
              {isFr ? "Ouvrir dans ☍ Mes Processus →" : "Open in ☍ My Processes →"}
            </button>
          ) : null}
        </div>
      </div>

      {/* Formulaire guidé en 3 étapes claires */}
      <form
        data-testid="create-workflow-form"
        autoComplete="off"
        data-lpignore="true"
        data-form-type="other"
        className="orcia-bento-card"
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
              "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
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
        }}
        style={{ display: "flex", flexDirection: "column", gap: "14px" }}
      >
        {/* Étape 1 : Identité du processus */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
            gap: "10px",
          }}
        >
          <label style={{ display: "flex", flexDirection: "column", gap: "4px", fontSize: "12px", fontWeight: 600 }}>
            <span>{isFr ? "1. Nom du processus *" : "1. Process name *"}</span>
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

        {/* Étape 2 : Objectif et instructions données aux agents */}
        <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
            <label htmlFor="workflow-preprompt-textarea" style={{ fontSize: "12px", fontWeight: 600 }}>
              {isFr
                ? "2. Objectif et instructions données aux agents"
                : "2. Goal and instructions for agents"}
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
                ? "Décrivez simplement ce que ce processus doit accomplir (ex : analyser les clauses critiques, vérifier la conformité et préparer une synthèse pour validation)..."
                : "Describe in plain language what this process should accomplish..."
            }
            style={inputStyle}
          />
        </div>

        {/* Étape 3 : Informations au lancement et rubriques du livrable (optionnel) */}
        <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
            <strong style={{ fontSize: "12px" }}>
              {isFr
                ? "3. Informations demandées au lancement et structure du livrable (optionnel)"
                : "3. Launch inputs and deliverable structure (optional)"}
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
              gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
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

        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: "8px" }}>
          <span style={{ fontSize: "12px", color: "var(--color-muted-foreground)" }}>
            {isFr ? `Version : ${wfVersion}` : `Version: ${wfVersion}`}
          </span>
          <button type="submit" data-testid="save-workflow-btn" style={primaryBtnStyle}>
            {isFr ? "+ Enregistrer le Processus" : "+ Save Process"}
          </button>
        </div>
      </form>

      {/* Les 3 grandes étapes d'exécution du processus */}
      <div className="orcia-bento-card" style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <strong style={{ fontSize: "14px" }}>
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
        <div style={{ display: "grid", gap: "8px" }}>
          {layers.map((layer) => (
            <div
              key={layer.layerId}
              data-testid={`process-layer-row-${layer.layerId}`}
              style={{
                padding: "8px 12px",
                borderRadius: "var(--radius-sm)",
                border: "1px solid var(--color-border)",
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                gap: "10px",
              }}
            >
              <span style={{ fontSize: "13px", fontWeight: 500 }}>{layer.label}</span>
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
                  ? isFr
                    ? "✓ Étape active"
                    : "✓ Step enabled"
                  : isFr
                    ? "Étape ignorée"
                    : "Step skipped"}
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* Liste des processus enregistrés */}
      <div className="orcia-bento-card" style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
        <strong style={{ fontSize: "14px" }}>
          {isFr
            ? `Processus enregistrés (${workflows.length})`
            : `Saved processes (${workflows.length})`}
        </strong>
        {workflows.length === 0 ? (
          <p data-testid="workflows-empty-state" style={{ margin: 0, fontSize: "13px", color: "var(--color-muted-foreground)" }}>
            {isFr
              ? "Aucun processus enregistré pour le moment. Utilisez le formulaire ci-dessus pour créer votre premier processus."
              : "No process saved yet. Use the form above to create your first process."}
          </p>
        ) : (
          <div data-testid="workflow-saved-list" style={{ display: "grid", gap: "8px" }}>
            {workflows.map((wf) => (
              <div
                key={wf.workflowKey}
                data-testid={`workflow-row-${wf.workflowKey}`}
                style={{
                  padding: "8px 12px",
                  borderRadius: "var(--radius-sm)",
                  border: "1px solid var(--color-border)",
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  flexWrap: "wrap",
                  gap: "8px",
                }}
              >
                <div>
                  <strong>{wf.title}</strong>{" "}
                  <span style={{ fontSize: "12px", color: "var(--color-muted-foreground)" }}>
                    ({wf.workflowKey} · v{wf.version})
                  </span>
                </div>
                <StatusBadge
                  label={
                    wf.status === "PUBLISHED"
                      ? isFr
                        ? "Publié"
                        : "Published"
                      : isFr
                        ? "Brouillon"
                        : "Draft"
                  }
                  tone={wf.status === "PUBLISHED" ? "emerald" : "cobalt"}
                />
              </div>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}
