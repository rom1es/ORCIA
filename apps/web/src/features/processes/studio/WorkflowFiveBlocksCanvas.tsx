import React, { useMemo, useState } from "react";
import { useShellNavigation } from "../../../components/ShellContainer";
import { useI18n } from "../../../i18n";
import { InteractiveRunDrawer } from "../execution/InteractiveRunDrawer";
import {
  INITIAL_WORKFLOWS_V2,
  loadPersistedWorkflowsV2,
  savePersistedWorkflowV2,
  type WorkflowDefinitionV2Item,
} from "../processStudioV2Data";
import { StudioCopilotSidebar } from "./StudioCopilotSidebar";

export type StudioViewMode = "design" | "what_if" | "yaml";

const HUMAN_TOOL_LABELS: Record<string, string> = {
  "mcp:atlassian-jira (read)": "Jira — Consultation des demandes & tickets",
  "mcp:atlassian-jira (write_preview)": "Jira — Création / mise à jour (avec confirmation)",
  "mcp:atlassian-confluence (read)": "Confluence — Lecture du socle documentaire",
  "mcp:atlassian-confluence (write_preview)": "Confluence — Publication de page (avec confirmation)",
  "mcp:git-provider (read)": "Git — Lecture du code & des Pull Requests",
  "mcp:git-provider (write_preview)": "Git — Préparation de branche / Pull Request",
};

const HUMAN_SKILL_LABELS: Record<string, string> = {
  "pack://sdlc/skills/qualification-besoin": "Qualification structurée du besoin",
  "pack://sdlc/skills/redaction-prd-wsjf": "Rédaction du PRD & calcul de priorité (WSJF)",
  "pack://sdlc/skills/diagrammes-mermaid": "Schémas d'architecture & parcours",
  "pack://sdlc/skills/decoupe-us-invest": "Découpage en User Stories (INVEST & Gherkin)",
  "pack://orcia-docs/skills/redaction-aide-bilingue": "Rédaction de guides utilisateurs FR/EN",
};

const HUMAN_KB_LABELS: Record<string, string> = {
  "pack://sdlc/agents/crl-socle-generateur.md": "Socle de connaissance produit & architecture (Confluence)",
  "pack://orcia-docs/agents/redacteur-documentation-orcia.md": "Référentiel documentaire ORCIA",
};

export function WorkflowFiveBlocksCanvas({ workflowId }: { workflowId?: string }) {
  const { locale } = useI18n();
  const { navigateToRoute } = useShellNavigation();
  const isFr = locale === "fr";

  const initialWf = useMemo(() => {
    const list = loadPersistedWorkflowsV2();
    const targetId = workflowId ?? "wf-01-qualification-prd";
    return (
      list.find((w) => w.id === targetId || w.slug === targetId) ??
      INITIAL_WORKFLOWS_V2[0]!
    );
  }, [workflowId]);

  const [workflow, setWorkflow] = useState<WorkflowDefinitionV2Item>(initialWf);
  const [viewMode, setViewMode] = useState<StudioViewMode>("design");
  const [showRunDrawer, setShowRunDrawer] = useState<boolean>(false);
  const [statusBanner, setStatusBanner] = useState<string | null>(null);
  const [whatIfResult, setWhatIfResult] = useState<{
    subStepsEvaluated: number;
    deterministicGatesPassed: boolean;
    externalWritesExecuted: number;
    estimatedCostUsd: number;
  } | null>(null);

  const persistUpdate = (nextWf: WorkflowDefinitionV2Item, banner?: string) => {
    setWorkflow(nextWf);
    savePersistedWorkflowV2(nextWf);
    if (banner) {
      setStatusBanner(banner);
    }
  };

  const ensureDraftOnEdit = (base: WorkflowDefinitionV2Item): WorkflowDefinitionV2Item => {
    if (base.status === "published") {
      const cleanVer = base.version.replace(/-draft$/, "");
      return {
        ...base,
        status: "draft",
        version: `${cleanVer}-draft`,
      };
    }
    return base;
  };

  const handleToggleSubStepEnabled = (subStepId: string) => {
    const base = ensureDraftOnEdit(workflow);
    const nextSubSteps = base.sub_steps.map((s) =>
      s.id === subStepId ? { ...s, enabled: !s.enabled } : s,
    );
    const updated: WorkflowDefinitionV2Item = {
      ...base,
      sub_steps: nextSubSteps,
    };
    const toggled = nextSubSteps.find((s) => s.id === subStepId);
    persistUpdate(
      updated,
      isFr
        ? `Étape « ${toggled?.short_label} » ${toggled?.enabled ? "activée" : "ignorée"} dans votre copie de travail.`
        : `Step "${toggled?.short_label}" ${toggled?.enabled ? "enabled" : "skipped"} in your working draft.`,
    );
  };

  const handleSwitchExecutionMode = (mode: "native_orcia" | "external_delegated") => {
    const base = ensureDraftOnEdit(workflow);
    const updated: WorkflowDefinitionV2Item = {
      ...base,
      execution_mode: mode,
      external_tool_label:
        mode === "external_delegated"
          ? base.external_tool_label ?? "IDE / Git de l'équipe"
          : base.external_tool_label,
      external_completion_event:
        mode === "external_delegated"
          ? base.external_completion_event ?? "git:pr_opened"
          : base.external_completion_event,
    };
    persistUpdate(
      updated,
      isFr
        ? `Mode de réalisation basculé sur « ${mode === "external_delegated" ? "Réalisation dans l'IDE / Git de l'équipe" : "Exécution guidée dans ORCIA"} ».`
        : `Execution mode switched to "${mode}".`,
    );
  };

  const handleSaveAsDraft = () => {
    const drafted = ensureDraftOnEdit(workflow);
    persistUpdate(
      drafted,
      isFr
        ? `Brouillon enregistré (${drafted.version}).`
        : `Draft saved (${drafted.version}).`,
    );
  };

  const handlePublishWorkflow = () => {
    const cleanVer = workflow.version.replace(/-draft$/, "");
    const parts = cleanVer.split(".").map((n) => Number.parseInt(n, 10) || 0);
    const nextVer = `${parts[0] ?? 1}.${parts[1] ?? 0}.${(parts[2] ?? 0) + 1}`;
    const published: WorkflowDefinitionV2Item = {
      ...workflow,
      status: "published",
      version: nextVer,
    };
    persistUpdate(
      published,
      isFr
        ? `Processus publié et activé (version ${published.version}).`
        : `Process published as version ${published.version}.`,
    );
  };

  const handleRunWhatIfSimulation = () => {
    const enabledCount = workflow.sub_steps.filter((s) => s.enabled).length;
    setWhatIfResult({
      subStepsEvaluated: enabledCount,
      deterministicGatesPassed: true,
      externalWritesExecuted: 0,
      estimatedCostUsd: Number((enabledCount * 0.015).toFixed(3)),
    });
    setViewMode("what_if");
    setStatusBanner(
      isFr
        ? `Simulation à blanc terminée : ${enabledCount} étape(s) vérifiée(s), aucune modification envoyée aux outils externes.`
        : `Dry-run completed: ${enabledCount} steps verified, 0 external writes executed.`,
    );
  };

  return (
    <section
      data-testid="workflow-five-blocks-studio-page"
      data-workflow-id={workflow.id}
      style={{ display: "flex", flexDirection: "column", gap: "16px" }}
    >
      {/* Barre supérieure de l'Atelier */}
      <header
        className="orcia-bento-card"
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
          flexWrap: "wrap",
          gap: "12px",
        }}
      >
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
            <button
              type="button"
              data-testid="studio-back-to-hub-btn"
              onClick={() => navigateToRoute("/processes")}
              className="orcia-ds-btn-secondary"
            >
              {isFr ? "← Retour à Mes Processus" : "← Back to My Processes"}
            </button>
            {workflow.vsm_step_num ? (
              <button
                type="button"
                data-testid="studio-open-parent-vsm-btn"
                onClick={() => navigateToRoute("/processes/vsm/vsm-mon-compte-idea-to-prod")}
                className="orcia-ds-btn-secondary"
              >
                {isFr
                  ? `🗺️ Voir l'Étape ${workflow.vsm_step_num} dans la chaîne de valeur`
                  : `🗺️ View Step ${workflow.vsm_step_num} in Value Stream`}
              </button>
            ) : null}
            <span
              data-testid="studio-workflow-version-badge"
              className="rounded px-2.5 py-0.5 text-xs font-semibold"
              style={{
                backgroundColor:
                  workflow.status === "published"
                    ? "var(--color-gate-emerald-bg)"
                    : "var(--color-arbitration-bg)",
                color:
                  workflow.status === "published"
                    ? "var(--color-gate-emerald)"
                    : "var(--color-arbitration-amber)",
              }}
            >
              {workflow.status === "published"
                ? isFr
                  ? `Actif · v${workflow.version}`
                  : `Active · v${workflow.version}`
                : isFr
                  ? `En préparation · v${workflow.version}`
                  : `Draft · v${workflow.version}`}
              <span className="sr-only">{` v${workflow.version} (${workflow.status})`}</span>
            </span>
          </div>
          <h1 style={{ margin: "6px 0 0 0", fontSize: "var(--font-size-h2)" }}>
            {isFr ? `Atelier d'adaptation — ${workflow.title}` : `Process Studio — ${workflow.title}`}
          </h1>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
          <div
            role="tablist"
            aria-label="Modes de l'atelier"
            className="orcia-ds-tabs"
          >
            {(
              [
                { key: "design", label: isFr ? "Étapes & Règles" : "Steps & Rules" },
                { key: "what_if", label: isFr ? "Tester à blanc" : "Dry-Run Test" },
                { key: "yaml", label: isFr ? "Définition (YAML)" : "YAML Spec" },
              ] as const
            ).map((tab) => (
              <button
                key={tab.key}
                type="button"
                role="tab"
                aria-selected={viewMode === tab.key}
                data-testid={`studio-view-mode-${tab.key}`}
                onClick={() => {
                  if (tab.key === "what_if" && !whatIfResult) {
                    handleRunWhatIfSimulation();
                  } else {
                    setViewMode(tab.key);
                  }
                }}
                className="orcia-ds-tab"
              >
                {tab.label}
              </button>
            ))}
          </div>

          <button
            type="button"
            data-testid="studio-save-draft-btn"
            onClick={handleSaveAsDraft}
            className="orcia-ds-btn-secondary"
          >
            {isFr ? "Enregistrer le brouillon" : "Save draft"}
          </button>

          <button
            type="button"
            data-testid="studio-publish-workflow-btn"
            onClick={handlePublishWorkflow}
            className="orcia-ds-btn-secondary"
          >
            {isFr ? "Publier" : "Publish"}
          </button>

          <button
            type="button"
            data-testid="studio-launch-interactive-run-btn"
            onClick={() => setShowRunDrawer(true)}
            className="orcia-ds-btn-primary"
          >
            {isFr ? "▷ Tester l'exécution" : "▷ Test run"}
          </button>
        </div>
      </header>

      {statusBanner ? (
        <div
          role="status"
          data-testid="studio-status-banner"
          className="rounded border px-3 py-2 text-xs font-medium"
          style={{
            backgroundColor: "var(--color-gate-emerald-bg)",
            borderColor: "var(--color-gate-emerald)",
            color: "var(--color-text-primary)",
          }}
        >
          {statusBanner}
        </div>
      ) : null}

      {showRunDrawer ? (
        <InteractiveRunDrawer
          workflow={workflow}
          onClose={() => setShowRunDrawer(false)}
          isFr={isFr}
        />
      ) : null}

      {/* Agencement : Catalogue d'aide à gauche + Configuration métier à droite */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "minmax(270px, 320px) 1fr",
          gap: "16px",
          alignItems: "start",
        }}
      >
        <StudioCopilotSidebar
          isFr={isFr}
          onAttachSkill={(skillUri) => {
            if (workflow.skills_refs.includes(skillUri)) return;
            const base = ensureDraftOnEdit(workflow);
            persistUpdate(
              { ...base, skills_refs: [...base.skills_refs, skillUri] },
              isFr
                ? "Savoir-faire ajouté au processus."
                : "Business skill attached to the process.",
            );
          }}
          onAttachMcpTool={(toolPerm) => {
            const base = ensureDraftOnEdit(workflow);
            const nextSubs = base.sub_steps.map((s, idx) =>
              idx === 0 && !s.mcp_tools_allowed.includes(toolPerm)
                ? { ...s, mcp_tools_allowed: [...s.mcp_tools_allowed, toolPerm] }
                : s,
            );
            persistUpdate(
              { ...base, sub_steps: nextSubs },
              isFr
                ? "Outil connecté autorisé sur ce processus."
                : "Connected tool enabled for this process.",
            );
          }}
          onAttachDeterministicGate={(gate) => {
            if (workflow.controls.deterministic_gates.some((g) => g.id === gate.id)) return;
            const base = ensureDraftOnEdit(workflow);
            persistUpdate(
              {
                ...base,
                controls: {
                  ...base.controls,
                  deterministic_gates: [
                    ...base.controls.deterministic_gates,
                    {
                      id: gate.id,
                      name: gate.name,
                      runner: gate.runner,
                      config: { required_headings: ["# "] },
                      blocking: true,
                      max_self_heal_retries: 3,
                    },
                  ],
                },
              },
              isFr
                ? `Contrôle qualité « ${gate.name} » ajouté.`
                : `Quality check "${gate.name}" added.`,
            );
          }}
        />

        {viewMode === "yaml" ? (
          <div
            data-testid="studio-yaml-preview-panel"
            className="orcia-bento-card"
          >
            <h3 style={{ margin: "0 0 8px 0", fontSize: "15px" }}>
              {isFr
                ? "Définition déclarative du processus"
                : "Declarative Process Definition"}
            </h3>
            <pre
              style={{
                margin: 0,
                padding: "12px",
                borderRadius: "6px",
                backgroundColor: "var(--color-bg-elevated)",
                border: "1px solid var(--color-border-subtle)",
                fontFamily: "var(--font-mono)",
                fontSize: "12px",
                overflowX: "auto",
              }}
            >
              {JSON.stringify(workflow, null, 2)}
            </pre>
          </div>
        ) : viewMode === "what_if" ? (
          <div
            data-testid="studio-what-if-sandbox-panel"
            className="orcia-bento-card"
            style={{ display: "flex", flexDirection: "column", gap: "12px" }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <h3 style={{ margin: 0, fontSize: "16px" }}>
                {isFr
                  ? "Simulation à blanc (sans écriture dans Jira, Confluence ou Git)"
                  : "Dry-Run Simulation (zero external writes)"}
              </h3>
              <button
                type="button"
                data-testid="rerun-what-if-simulation-btn"
                onClick={handleRunWhatIfSimulation}
                className="orcia-ds-btn-primary"
              >
                {isFr ? "↻ Relancer le test à blanc" : "↻ Re-run simulation"}
              </button>
            </div>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(4, minmax(0, 1fr))",
                gap: "10px",
              }}
            >
              <div className="rounded border p-3" style={{ backgroundColor: "var(--color-bg-elevated)", borderColor: "var(--color-border-subtle)" }}>
                <div style={{ fontSize: "11px", color: "var(--color-text-secondary)" }}>Étapes actives testées</div>
                <div data-testid="what-if-substeps-count" style={{ fontSize: "18px", fontWeight: 700, color: "var(--color-primary-cobalt)" }}>
                  {whatIfResult?.subStepsEvaluated ?? workflow.sub_steps.filter((s) => s.enabled).length}
                </div>
              </div>
              <div className="rounded border p-3" style={{ backgroundColor: "var(--color-gate-emerald-bg)", borderColor: "var(--color-gate-emerald)" }}>
                <div style={{ fontSize: "11px", color: "var(--color-text-secondary)" }}>Modifications externes</div>
                <div data-testid="what-if-external-writes-count" style={{ fontSize: "18px", fontWeight: 700, color: "var(--color-gate-emerald)" }}>
                  0 (Mode isolé)
                </div>
              </div>
              <div className="rounded border p-3" style={{ backgroundColor: "var(--color-gate-emerald-bg)", borderColor: "var(--color-gate-emerald)" }}>
                <div style={{ fontSize: "11px", color: "var(--color-text-secondary)" }}>Contrôles qualité</div>
                <div style={{ fontSize: "18px", fontWeight: 700, color: "var(--color-gate-emerald)" }}>
                  Conformes
                </div>
              </div>
              <div className="rounded border p-3" style={{ backgroundColor: "var(--color-bg-elevated)", borderColor: "var(--color-border-subtle)" }}>
                <div style={{ fontSize: "11px", color: "var(--color-text-secondary)" }}>Coût estimé par dossier</div>
                <div style={{ fontSize: "18px", fontWeight: 700 }}>
                  {whatIfResult?.estimatedCostUsd ?? 0.045} $
                </div>
              </div>
            </div>
          </div>
        ) : (
          <div
            data-testid="studio-five-blocks-canvas"
            style={{ display: "flex", flexDirection: "column", gap: "14px" }}
          >
            {/* 1. ENTRÉES & LIVRABLE ATTENDU */}
            <div
              data-testid="studio-block-1-triggers-contract"
              className="orcia-bento-card"
              style={{ display: "flex", flexDirection: "column", gap: "8px" }}
            >
              <strong style={{ fontSize: "14px", color: "var(--color-primary-cobalt)" }}>
                1. Éléments d&apos;entrée & Livrable attendu
              </strong>
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
                  gap: "10px",
                  fontSize: "12.5px",
                }}
              >
                <div className="rounded border p-2.5" style={{ backgroundColor: "var(--color-bg-elevated)", borderColor: "var(--color-border-subtle)" }}>
                  <strong>Éléments en entrée :</strong>
                  <div style={{ marginTop: "4px", color: "var(--color-text-secondary)" }}>
                    {workflow.contract.inputs.join(" · ")}
                  </div>
                </div>
                <div className="rounded border p-2.5" style={{ backgroundColor: "var(--color-bg-elevated)", borderColor: "var(--color-border-subtle)" }}>
                  <strong>Rubriques attendues dans le livrable :</strong>
                  <div style={{ marginTop: "4px", fontSize: "12px" }}>
                    {workflow.contract.outputs.map((h) => h.replace(/^#+\s*/, "")).join(" · ")}
                  </div>
                </div>
                <div className="rounded border p-2.5" style={{ backgroundColor: "var(--color-bg-elevated)", borderColor: "var(--color-border-subtle)" }}>
                  <strong>Conditions de validation :</strong>
                  <div style={{ marginTop: "4px", color: "var(--color-gate-emerald)" }}>
                    {isFr
                      ? "Contrôles de complétude validés · Approbation du responsable"
                      : "Completeness checks passed · Owner sign-off"}
                  </div>
                </div>
              </div>
            </div>

            {/* 2. DÉROULEMENT DES ÉTAPES */}
            <div
              data-testid="studio-block-2-deterministic-substeps"
              className="orcia-bento-card"
              style={{ display: "flex", flexDirection: "column", gap: "10px" }}
            >
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  flexWrap: "wrap",
                  gap: "8px",
                }}
              >
                <div>
                  <strong style={{ fontSize: "14px", color: "var(--color-primary-cobalt)" }}>
                    2. Déroulement des étapes du processus
                  </strong>
                  <div style={{ fontSize: "12px", color: "var(--color-text-secondary)" }}>
                    Activez ou ignorez chaque étape selon les besoins de votre projet.
                  </div>
                </div>

                <div style={{ display: "flex", gap: "6px" }}>
                  <button
                    type="button"
                    data-testid="mode-switch-native-orcia-btn"
                    onClick={() => handleSwitchExecutionMode("native_orcia")}
                    className={
                      workflow.execution_mode === "native_orcia"
                        ? "orcia-ds-btn-primary"
                        : "orcia-ds-btn-secondary"
                    }
                  >
                    Exécution guidée ORCIA
                  </button>
                  <button
                    type="button"
                    data-testid="mode-switch-external-delegated-btn"
                    onClick={() => handleSwitchExecutionMode("external_delegated")}
                    className={
                      workflow.execution_mode === "external_delegated"
                        ? "orcia-ds-btn-primary"
                        : "orcia-ds-btn-secondary"
                    }
                  >
                    Réalisation dans l&apos;IDE / Git
                  </button>
                </div>
              </div>

              {workflow.execution_mode === "external_delegated" ? (
                <div
                  data-testid="studio-external-delegated-banner"
                  className="rounded border p-3 text-xs"
                  style={{
                    backgroundColor: "var(--color-arbitration-bg)",
                    borderColor: "var(--color-arbitration-amber)",
                  }}
                >
                  <strong>🛠️ Réalisation confiée à l&apos;équipe dans son IDE / Git :</strong> ORCIA prépare le dossier de contexte et vérifie automatiquement la conformité dès que la Pull Request est proposée.
                </div>
              ) : null}

              <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                {workflow.sub_steps.map((sub, idx) => (
                  <div
                    key={sub.id}
                    data-testid={`studio-substep-card-${sub.id}`}
                    className="rounded border p-3"
                    style={{
                      backgroundColor: sub.enabled
                        ? "var(--color-bg-elevated)"
                        : "var(--color-surface-muted)",
                      borderColor: sub.enabled
                        ? "var(--color-primary-cobalt)"
                        : "var(--color-border-subtle)",
                      opacity: sub.enabled ? 1 : 0.65,
                    }}
                  >
                    <div
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                        flexWrap: "wrap",
                        gap: "8px",
                      }}
                    >
                      <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
                        <span
                          style={{
                            fontSize: "12px",
                            fontWeight: 700,
                            color: "var(--color-primary-cobalt)",
                          }}
                        >
                          Étape {idx + 1}
                        </span>
                        <strong style={{ fontSize: "13.5px" }}>{sub.name}</strong>
                        {sub.requires_human_checkpoint ? (
                          <span
                            className="rounded px-2 py-0.5 text-xs font-semibold"
                            style={{
                              backgroundColor: "var(--color-arbitration-bg)",
                              color: "var(--color-arbitration-amber)",
                            }}
                          >
                            Validation humaine
                          </span>
                        ) : null}
                        {sub.write_preview_required ? (
                          <span
                            className="rounded px-2 py-0.5 text-xs font-semibold"
                            style={{
                              backgroundColor: "var(--color-gate-emerald-bg)",
                              color: "var(--color-gate-emerald)",
                            }}
                          >
                            Confirmation avant publication
                          </span>
                        ) : null}
                      </div>

                      <button
                        type="button"
                        data-testid={`toggle-substep-enabled-${sub.id}`}
                        onClick={() => handleToggleSubStepEnabled(sub.id)}
                        className="orcia-ds-btn-secondary"
                      >
                        {sub.enabled
                          ? isFr
                            ? "✓ Étape activée (Ignorer)"
                            : "✓ Step enabled (Skip)"
                          : isFr
                            ? "Étape ignorée (Activer)"
                            : "Step skipped (Enable)"}
                      </button>
                    </div>

                    <div style={{ fontSize: "12px", color: "var(--color-text-secondary)", marginTop: "6px" }}>
                      <strong>Objectif :</strong> {sub.role_description}
                    </div>
                    <div style={{ fontSize: "12px", marginTop: "3px" }}>
                      <strong>Livrable produit :</strong> {sub.output_description}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* 3. OUTILS CONNECTÉS & SAVOIR-FAIRE MOBILISÉS */}
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
                gap: "12px",
              }}
            >
              <div
                data-testid="studio-block-3-mcp-toolboxes"
                className="orcia-bento-card"
                style={{ display: "flex", flexDirection: "column", gap: "8px" }}
              >
                <strong style={{ fontSize: "14px", color: "var(--color-primary-cobalt)" }}>
                  3. Outils connectés mobilisés
                </strong>
                <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
                  {Array.from(
                    new Set(workflow.sub_steps.flatMap((s) => s.mcp_tools_allowed)),
                  ).map((tool) => (
                    <span
                      key={tool}
                      className="rounded border px-2.5 py-1 text-xs font-medium"
                      style={{
                        backgroundColor: "var(--color-bg-elevated)",
                        borderColor: "var(--color-border-subtle)",
                      }}
                    >
                      🔌 {HUMAN_TOOL_LABELS[tool] ?? tool}
                    </span>
                  ))}
                </div>
              </div>

              <div
                data-testid="studio-block-4-skills-knowledge"
                className="orcia-bento-card"
                style={{ display: "flex", flexDirection: "column", gap: "8px" }}
              >
                <strong style={{ fontSize: "14px", color: "var(--color-primary-cobalt)" }}>
                  4. Savoir-faire métier & Socle documentaire
                </strong>
                <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
                  {workflow.skills_refs.map((skill) => (
                    <span
                      key={skill}
                      className="rounded px-2.5 py-1 text-xs font-medium"
                      style={{
                        backgroundColor: "var(--color-ontology-bg)",
                        color: "var(--color-ontology-cyan)",
                      }}
                    >
                      📘 {HUMAN_SKILL_LABELS[skill] ?? skill}
                    </span>
                  ))}
                  {workflow.knowledge_base_refs.map((kb) => (
                    <span
                      key={kb}
                      className="rounded px-2.5 py-1 text-xs font-medium"
                      style={{
                        backgroundColor: "var(--color-action-primary-subtle)",
                        color: "var(--color-primary-cobalt)",
                      }}
                    >
                      🏛️ {HUMAN_KB_LABELS[kb] ?? kb}
                    </span>
                  ))}
                </div>
              </div>
            </div>

            {/* 5. CONTRÔLES DE QUALITÉ AVANT VALIDATION */}
            <div
              data-testid="studio-block-5-gates-pipeline"
              className="orcia-bento-card"
              style={{ display: "flex", flexDirection: "column", gap: "10px" }}
            >
              <strong style={{ fontSize: "14px", color: "var(--color-primary-cobalt)" }}>
                5. Contrôles de qualité avant validation humaine
              </strong>

              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
                  gap: "10px",
                }}
              >
                <div
                  className="rounded border p-3"
                  style={{
                    backgroundColor: "var(--color-gate-emerald-bg)",
                    borderColor: "var(--color-gate-emerald)",
                  }}
                >
                  <div style={{ fontWeight: 700, fontSize: "12.5px", color: "var(--color-gate-emerald)" }}>
                    1. Vérifications automatiques de complétude
                  </div>
                  {workflow.controls.deterministic_gates.map((dg) => (
                    <div key={dg.id} style={{ marginTop: "6px", fontSize: "12.5px" }}>
                      ✓ <strong>{dg.name}</strong>
                    </div>
                  ))}
                </div>

                <div
                  className="rounded border p-3"
                  style={{
                    backgroundColor: "var(--color-arbitration-bg)",
                    borderColor: "var(--color-arbitration-amber)",
                  }}
                >
                  <div style={{ fontWeight: 700, fontSize: "12.5px", color: "var(--color-arbitration-amber)" }}>
                    2. Relecture critique par un agent contradicteur
                  </div>
                  {workflow.controls.probabilistic_evaluations.map((pg) => (
                    <div key={pg.id} style={{ marginTop: "6px", fontSize: "12.5px" }}>
                      🔍 <strong>{pg.name}</strong> — {pg.rubric_ref}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </section>
  );
}
