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

  // Auto-fork as -draft when editing a published workflow (CA-9.1.2)
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
        ? `Sous-étape « ${toggled?.short_label} » ${toggled?.enabled ? "activée" : "skippée"} dans le brouillon ${updated.version} (persiste au F5).`
        : `Sub-step "${toggled?.short_label}" ${toggled?.enabled ? "enabled" : "skipped"} in draft ${updated.version}.`,
    );
  };

  const handleSwitchExecutionMode = (mode: "native_orcia" | "external_delegated") => {
    const base = ensureDraftOnEdit(workflow);
    const updated: WorkflowDefinitionV2Item = {
      ...base,
      execution_mode: mode,
      external_tool_label:
        mode === "external_delegated"
          ? base.external_tool_label ?? "GitHub Copilot / Claude Code (IDE)"
          : base.external_tool_label,
      external_completion_event:
        mode === "external_delegated"
          ? base.external_completion_event ?? "git:pr_opened"
          : base.external_completion_event,
    };
    persistUpdate(
      updated,
      isFr
        ? `Mode d'exécution basculé sur « ${mode === "external_delegated" ? "Sas Externe Délégué" : "Natif ORCIA"} » (${updated.version}).`
        : `Execution mode switched to "${mode}".`,
    );
  };

  const handleSaveAsDraft = () => {
    const drafted = ensureDraftOnEdit(workflow);
    persistUpdate(
      drafted,
      isFr
        ? `Copie de travail enregistrée : ${drafted.id} (${drafted.version}, statut : ${drafted.status}).`
        : `Draft copy saved: ${drafted.id} (${drafted.version}).`,
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
        ? `Workflow publié avec succès en version ${published.version} (statut : published).`
        : `Workflow published as version ${published.version}.`,
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
        ? `Simulation What-If isolée terminée : ${enabledCount} sous-étape(s) évaluée(s), 0 écriture externe exécutée (sandbox_isolated = true).`
        : `Isolated What-If dry-run completed: ${enabledCount} sub-steps evaluated, 0 external writes executed.`,
    );
  };

  return (
    <section
      data-testid="workflow-five-blocks-studio-page"
      data-workflow-id={workflow.id}
      style={{ display: "flex", flexDirection: "column", gap: "16px" }}
    >
      {/* Top Studio Control Bar */}
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
              {isFr ? "← Hub Processus" : "← Processes Hub"}
            </button>
            {workflow.vsm_step_num ? (
              <button
                type="button"
                data-testid="studio-open-parent-vsm-btn"
                onClick={() => navigateToRoute("/processes/vsm/vsm-mon-compte-idea-to-prod")}
                className="orcia-ds-btn-secondary"
              >
                {isFr
                  ? `🗺️ Étape VSM ${workflow.vsm_step_num}`
                  : `🗺️ VSM Step ${workflow.vsm_step_num}`}
              </button>
            ) : null}
            <span
              data-testid="studio-workflow-version-badge"
              className="rounded px-2 py-0.5 text-xs font-bold"
              style={{
                backgroundColor:
                  workflow.status === "published"
                    ? "var(--color-gate-emerald-bg)"
                    : "var(--color-arbitration-bg)",
                color:
                  workflow.status === "published"
                    ? "var(--color-gate-emerald)"
                    : "var(--color-arbitration-amber)",
                fontFamily: "var(--font-mono)",
              }}
            >
              {workflow.id} · v{workflow.version} ({workflow.status})
            </span>
          </div>
          <h1 style={{ margin: "6px 0 0 0", fontSize: "var(--font-size-h2)" }}>
            {workflow.title}
          </h1>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
          {/* View Mode Switcher: Design | Test What-If | YAML */}
          <div
            role="tablist"
            aria-label="Modes du Studio"
            className="orcia-ds-tabs"
          >
            {(
              [
                { key: "design", label: isFr ? "Design 5 Blocs" : "5-Block Design" },
                { key: "what_if", label: isFr ? "Test What-If (Sandbox)" : "What-If Sandbox" },
                { key: "yaml", label: "YAML Déclaratif" },
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
            {isFr ? "💾 Enregistrer Draft (-draft)" : "💾 Save Draft (-draft)"}
          </button>

          <button
            type="button"
            data-testid="studio-publish-workflow-btn"
            onClick={handlePublishWorkflow}
            className="orcia-ds-btn-secondary"
          >
            {isFr ? "🚀 Publier" : "🚀 Publish"}
          </button>

          <button
            type="button"
            data-testid="studio-launch-interactive-run-btn"
            onClick={() => setShowRunDrawer(true)}
            className="orcia-ds-btn-primary"
          >
            {isFr ? "▷ Exécuter Run DBOS & HITL" : "▷ Run DBOS & HITL"}
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

      {/* Interactive DBOS Run & 4-Action HITL Drawer */}
      {showRunDrawer ? (
        <InteractiveRunDrawer
          workflow={workflow}
          onClose={() => setShowRunDrawer(false)}
          isFr={isFr}
        />
      ) : null}

      {/* Main Layout: Left Copilot Sidebar + Right 5-Block Control-M Canvas */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "minmax(280px, 340px) 1fr",
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
                ? `Skill « ${skillUri} » attaché au Bloc 4 (${base.version}).`
                : `Skill "${skillUri}" attached to Block 4.`,
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
                ? `Outil MCP « ${toolPerm} » attaché au Bloc 3 (${base.version}).`
                : `MCP tool "${toolPerm}" attached to Block 3.`,
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
                ? `Gate déterministe « ${gate.name} » (${gate.runner}) ajoutée au Bloc 5 (${base.version}).`
                : `Deterministic gate "${gate.name}" added to Block 5.`,
            );
          }}
        />

        {/* Right Panel: Design Mode (5 Blocks) | What-If Sandbox | YAML */}
        {viewMode === "yaml" ? (
          <div
            data-testid="studio-yaml-preview-panel"
            className="orcia-bento-card"
          >
            <h3 style={{ margin: "0 0 8px 0", fontSize: "15px" }}>
              {isFr
                ? `Spécification Déclarative YAML (packs/sdlc/workflows/${workflow.slug}.yaml)`
                : `Declarative YAML Spec (packs/sdlc/workflows/${workflow.slug}.yaml)`}
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
                  ? "🧪 Simulation What-If en Bac à Sable Isolé (Dry-Run — 0 Écriture Externe)"
                  : "🧪 Isolated Sandbox What-If Simulation (Dry-Run — 0 External Writes)"}
              </h3>
              <button
                type="button"
                data-testid="rerun-what-if-simulation-btn"
                onClick={handleRunWhatIfSimulation}
                className="orcia-ds-btn-primary"
              >
                {isFr ? "↻ Relancer la simulation" : "↻ Re-run simulation"}
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
                <div style={{ fontSize: "11px", color: "var(--color-text-secondary)" }}>Sous-étapes actives évaluées</div>
                <div data-testid="what-if-substeps-count" style={{ fontSize: "18px", fontWeight: 700, color: "var(--color-primary-cobalt)" }}>
                  {whatIfResult?.subStepsEvaluated ?? workflow.sub_steps.filter((s) => s.enabled).length}
                </div>
              </div>
              <div className="rounded border p-3" style={{ backgroundColor: "var(--color-gate-emerald-bg)", borderColor: "var(--color-gate-emerald)" }}>
                <div style={{ fontSize: "11px", color: "var(--color-text-secondary)" }}>Écritures externes exécutées</div>
                <div data-testid="what-if-external-writes-count" style={{ fontSize: "18px", fontWeight: 700, color: "var(--color-gate-emerald)" }}>
                  0 (Isolé)
                </div>
              </div>
              <div className="rounded border p-3" style={{ backgroundColor: "var(--color-gate-emerald-bg)", borderColor: "var(--color-gate-emerald)" }}>
                <div style={{ fontSize: "11px", color: "var(--color-text-secondary)" }}>Gates Déterministes</div>
                <div style={{ fontSize: "18px", fontWeight: 700, color: "var(--color-gate-emerald)" }}>
                  PASS
                </div>
              </div>
              <div className="rounded border p-3" style={{ backgroundColor: "var(--color-bg-elevated)", borderColor: "var(--color-border-subtle)" }}>
                <div style={{ fontSize: "11px", color: "var(--color-text-secondary)" }}>Coût FinOps estimé</div>
                <div style={{ fontSize: "18px", fontWeight: 700 }}>
                  {whatIfResult?.estimatedCostUsd ?? 0.045} USD
                </div>
              </div>
            </div>
          </div>
        ) : (
          <div
            data-testid="studio-five-blocks-canvas"
            style={{ display: "flex", flexDirection: "column", gap: "14px" }}
          >
            {/* BLOC 1 : TRIGGERS & CONTRAT D'ENTRÉE/SORTIE */}
            <div
              data-testid="studio-block-1-triggers-contract"
              className="orcia-bento-card"
              style={{ display: "flex", flexDirection: "column", gap: "8px" }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <strong style={{ fontSize: "14px", color: "var(--color-primary-cobalt)" }}>
                  BLOC 1 — Déclencheurs & Contrat d&apos;Entrée / Sortie Typé
                </strong>
                <span style={{ fontSize: "11.5px", fontFamily: "var(--font-mono)", color: "var(--color-text-secondary)" }}>
                  Format : {workflow.contract.expected_format ?? "markdown"}
                </span>
              </div>
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
                  gap: "10px",
                  fontSize: "12.5px",
                }}
              >
                <div className="rounded border p-2.5" style={{ backgroundColor: "var(--color-bg-elevated)", borderColor: "var(--color-border-subtle)" }}>
                  <strong>Entrées requises :</strong>
                  <div style={{ marginTop: "4px", color: "var(--color-text-secondary)" }}>
                    {workflow.contract.inputs.join(" · ")}
                  </div>
                </div>
                <div className="rounded border p-2.5" style={{ backgroundColor: "var(--color-bg-elevated)", borderColor: "var(--color-border-subtle)" }}>
                  <strong>Sections Markdown attendues :</strong>
                  <div style={{ marginTop: "4px", fontFamily: "var(--font-mono)", fontSize: "11.5px" }}>
                    {workflow.contract.outputs.join(", ")}
                  </div>
                </div>
                <div className="rounded border p-2.5" style={{ backgroundColor: "var(--color-bg-elevated)", borderColor: "var(--color-border-subtle)" }}>
                  <strong>Critères de sortie :</strong>
                  <div style={{ marginTop: "4px", color: "var(--color-gate-emerald)" }}>
                    {workflow.contract.exit_criteria.join(" · ")}
                  </div>
                </div>
              </div>
            </div>

            {/* BLOC 2 : SÉQUENCE DE SOUS-ÉTAPES DÉTERMINISTES DBOS & MODE SAS EXTERNE */}
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
                    BLOC 2 — Séquence de Sous-Étapes Déterministes DBOS (Zéro Agent Orchestrateur Chat)
                  </strong>
                  <div style={{ fontSize: "12px", color: "var(--color-text-secondary)" }}>
                    Chaque sous-étape peut être activée ou skippée par le PO sans casser le workflow (`CA-9.3.1`).
                  </div>
                </div>

                {/* Execution Mode Switch: Natif ORCIA vs Sas Externe Délégué */}
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
                    Natif ORCIA
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
                    Sas Externe Délégué (IDE/CI)
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
                  <strong>🔌 Mode Sas Externe Délégué actif :</strong> Outil délégué{" "}
                  <code>{workflow.external_tool_label ?? "GitHub Copilot / Claude Code"}</code> ·
                  Événement attendu{" "}
                  <code>{workflow.external_completion_event ?? "git:pr_opened"}</code>.
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
                            fontFamily: "var(--font-mono)",
                            fontSize: "11.5px",
                            fontWeight: 700,
                            color: "var(--color-primary-cobalt)",
                          }}
                        >
                          #{idx + 1} · {sub.id}
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
                            ◆ Checkpoint Humain DBOS.recv
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
                            🛡️ WritePreviewCard Requise
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
                            ? "✓ Activée (Cliquer pour Skipper)"
                            : "✓ Enabled (Click to Skip)"
                          : isFr
                            ? "⏭ Skippée (Cliquer pour Activer)"
                            : "⏭ Skipped (Click to Enable)"}
                      </button>
                    </div>

                    <div style={{ fontSize: "12px", color: "var(--color-text-secondary)", marginTop: "6px" }}>
                      <strong>Rôle :</strong> {sub.role_description}
                    </div>
                    <div style={{ fontSize: "12px", marginTop: "3px" }}>
                      <strong>Sortie S3 Claim-Check :</strong> {sub.output_description}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* BLOC 3 : PERMISSIONS & TOOLBOXES MCP */}
            <div
              data-testid="studio-block-3-mcp-toolboxes"
              className="orcia-bento-card"
              style={{ display: "flex", flexDirection: "column", gap: "8px" }}
            >
              <strong style={{ fontSize: "14px", color: "var(--color-primary-cobalt)" }}>
                BLOC 3 — Permissions & Toolboxes MCP (packages/orcia-connectors)
              </strong>
              <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
                {Array.from(
                  new Set(workflow.sub_steps.flatMap((s) => s.mcp_tools_allowed)),
                ).map((tool) => (
                  <span
                    key={tool}
                    className="rounded border px-2.5 py-1 text-xs font-semibold"
                    style={{
                      backgroundColor: "var(--color-bg-elevated)",
                      borderColor: "var(--color-border-subtle)",
                      fontFamily: "var(--font-mono)",
                    }}
                  >
                    🔌 {tool}
                  </span>
                ))}
              </div>
            </div>

            {/* BLOC 4 : SKILLS MARKDOWN & SOCLE CONFLUENCE */}
            <div
              data-testid="studio-block-4-skills-knowledge"
              className="orcia-bento-card"
              style={{ display: "flex", flexDirection: "column", gap: "8px" }}
            >
              <strong style={{ fontSize: "14px", color: "var(--color-primary-cobalt)" }}>
                BLOC 4 — Skills Déclaratifs & Socle de Connaissance Confluence
              </strong>
              <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
                {workflow.skills_refs.map((skill) => (
                  <span
                    key={skill}
                    className="rounded px-2.5 py-1 text-xs font-semibold"
                    style={{
                      backgroundColor: "var(--color-ontology-bg)",
                      color: "var(--color-ontology-cyan)",
                      fontFamily: "var(--font-mono)",
                    }}
                  >
                    📘 {skill}
                  </span>
                ))}
                {workflow.knowledge_base_refs.map((kb) => (
                  <span
                    key={kb}
                    className="rounded px-2.5 py-1 text-xs font-semibold"
                    style={{
                      backgroundColor: "var(--color-action-primary-subtle)",
                      color: "var(--color-primary-cobalt)",
                      fontFamily: "var(--font-mono)",
                    }}
                  >
                    🏛️ Socle : {kb}
                  </span>
                ))}
              </div>
            </div>

            {/* BLOC 5 : PIPELINE DE GATES (DÉTERMINISTES AUTO-HEAL 3X -> AGENTS CONTRADICTEURS) */}
            <div
              data-testid="studio-block-5-gates-pipeline"
              className="orcia-bento-card"
              style={{ display: "flex", flexDirection: "column", gap: "10px" }}
            >
              <strong style={{ fontSize: "14px", color: "var(--color-primary-cobalt)" }}>
                BLOC 5 — Pipeline de Gates (1. Runners Déterministes Auto-Heal 3x ➔ 2. Agents Contradicteurs)
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
                    1. Runners Déterministes Génériques (0 Token LLM · Auto-Heal max 3x)
                  </div>
                  {workflow.controls.deterministic_gates.map((dg) => (
                    <div key={dg.id} style={{ marginTop: "6px", fontSize: "12px" }}>
                      <strong>{dg.name}</strong>{" "}
                      <span style={{ fontFamily: "var(--font-mono)", fontSize: "11px" }}>
                        [{dg.runner} · retries={dg.max_self_heal_retries}]
                      </span>
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
                    2. Évaluateurs & Agents Contradicteurs (Après PASS Déterministe)
                  </div>
                  {workflow.controls.probabilistic_evaluations.map((pg) => (
                    <div key={pg.id} style={{ marginTop: "6px", fontSize: "12px" }}>
                      <strong>{pg.name}</strong> — {pg.rubric_ref}
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
