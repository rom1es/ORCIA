import { createOrciaApiClient } from "@orcia/api-client";
import {
  FormattedMarkdownContent,
  StatusBadge,
} from "@orcia/ui";
import React, { useState } from "react";
import type { ConfiguredWorkflowItem } from "../../components/platformSetupStore";
import {
  formatI18nTemplate,
  resolveDictionaryForFlag,
  resolveLocaleForFlag,
} from "../../i18n";
import {
  buildGeneratedDocumentationMarkdown,
  buildOrciaDocumentationWorkflowSpec,
} from "./orciaDocProcessTemplates";

export { buildOrciaDocumentationWorkflowSpec };

export interface OrciaDocumentationProcessStepItem {
  readonly stepNumber: number;
  readonly title: string;
  readonly agentHandle: string;
  readonly summary: string;
  readonly status: "COMPLETED" | "RUNNING";
}

export interface OrciaDocumentationProcessCardProps {
  readonly isFr: boolean;
  readonly activeWorkspace?: {
    readonly workspaceId: string;
    readonly name: string;
  };
  readonly openHelpSection: (sectionId: string) => void;
  readonly upsertWorkflow: (input: ConfiguredWorkflowItem) => void;
  readonly launchRun: (input: {
    workspaceId: string;
    workspaceName: string;
    title: string;
    workflowKey: string;
  }) => void;
  readonly onLoadIntoBuilder: (draft: ConfiguredWorkflowItem) => void;
  readonly onFeedback: (message: string) => void;
}

export function OrciaDocumentationProcessCard({
  isFr,
  activeWorkspace,
  upsertWorkflow,
  launchRun,
  onLoadIntoBuilder,
  onFeedback,
}: OrciaDocumentationProcessCardProps) {
  const resolvedLocale = resolveLocaleForFlag(isFr);
  const docCopy = resolveDictionaryForFlag(isFr, resolvedLocale).featureCockpitGates.gates.docProcess;
  const [executedSteps, setExecutedSteps] = useState<
    readonly OrciaDocumentationProcessStepItem[]
  >([]);
  const [generatedMarkdown, setGeneratedMarkdown] = useState<string>("");

  const handleRunDocumentationProcess = () => {
    const publishedSpec = buildOrciaDocumentationWorkflowSpec(isFr, "PUBLISHED");
    upsertWorkflow(publishedSpec);

    if (activeWorkspace) {
      launchRun({
        workspaceId: activeWorkspace.workspaceId,
        workspaceName: activeWorkspace.name,
        title: publishedSpec.title,
        workflowKey: publishedSpec.workflowKey,
      });
    }

    const steps: readonly OrciaDocumentationProcessStepItem[] = docCopy.steps.map((s) => ({
      ...s,
      status: "COMPLETED" as const,
    }));

    const markdownPreview = buildGeneratedDocumentationMarkdown(isFr);
    setExecutedSteps(steps);
    setGeneratedMarkdown(markdownPreview);
    onFeedback(docCopy.publishSuccessBanner);

    const client = createOrciaApiClient({ baseUrl: "" });
    void client
      .validateHelpArticle({
        markdown_text:
          "---\nid: help.orcia.complete-documentation\nversion: 1.0.0\npack_id: orcia://packs/orcia-pack-builder\nbound_routes:\n  - /cockpit\n  - /processes\n  - /help\nroles_allowed:\n  - CONTRIBUTOR\nglossary_terms: []\nrelated_workflows:\n  - orcia://pack-builder/workflows/generate-orcia-documentation\n---\n# Documentation Complète d'ORCIA {#top}\n## 1. À quoi sert cet écran ? {#overview}\nGuide complet d'ORCIA.\n## 2. Comment faire (Pas-à-pas) {#steps}\n- Lancer la génération de documentation ORCIA\n## 3. Questions fréquentes & Dépannage {#faq}\n- Comment mettre à jour la documentation ?",
        lang: resolvedLocale,
        extra_allowed_routes: ["/cockpit", "/processes", "/help"],
        known_glossary_terms: [],
      })
      .catch((err: unknown) => {
        const detail =
          err instanceof Error ? err.message : docCopy.localValidationFallback;
        onFeedback(
          formatI18nTemplate(docCopy.publishWithDetailTemplate, { detail }),
        );
      });
  };

  const handleLoadIntoBuilder = () => {
    const draftSpec = buildOrciaDocumentationWorkflowSpec(isFr, "PUBLISHED");
    upsertWorkflow(draftSpec);
    onLoadIntoBuilder(draftSpec);
    onFeedback(docCopy.loadedInBuilderBanner);
  };

  return (
    <section
      data-testid="orcia-doc-generation-process-card"
      className="orcia-bento-card"
      style={{ display: "flex", flexDirection: "column", gap: "12px" }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
          flexWrap: "wrap",
          gap: "10px",
        }}
      >
        <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
            <h3 style={{ margin: 0, fontSize: "15px" }}>
              {docCopy.cardTitle}
            </h3>
          </div>
          <p style={{ margin: 0, fontSize: "13px", color: "var(--color-muted-foreground)" }}>
            {docCopy.cardDescription}
          </p>
        </div>
        <StatusBadge label={docCopy.badgeLabel} tone="cobalt" />
      </div>

      <div style={{ display: "flex", flexWrap: "wrap", gap: "8px" }}>
        <button
          type="button"
          data-testid="run-orcia-doc-generation-process-btn"
          onClick={handleRunDocumentationProcess}
          style={{
            padding: "7px 14px",
            borderRadius: "var(--radius-sm)",
            border: "none",
            backgroundColor: "var(--color-primary-cobalt)",
            color: "var(--color-primary-foreground)",
            fontWeight: 600,
            cursor: "pointer",
          }}
        >
          {docCopy.runBtn}
        </button>

        <button
          type="button"
          data-testid="load-orcia-doc-process-in-builder-btn"
          onClick={handleLoadIntoBuilder}
          style={{
            padding: "7px 14px",
            borderRadius: "var(--radius-sm)",
            border: "1px solid var(--color-border)",
            backgroundColor: "var(--color-surface-card)",
            color: "var(--color-foreground)",
            fontWeight: 600,
            cursor: "pointer",
          }}
        >
          {docCopy.loadInBuilderBtn}
        </button>
      </div>

      {executedSteps.length > 0 ? (
        <div
          data-testid="orcia-doc-generation-steps-summary"
          style={{
            display: "grid",
            gap: "8px",
            padding: "10px 12px",
            borderRadius: "var(--radius-sm)",
            border: "1px solid var(--color-border)",
            backgroundColor: "var(--color-bg-elevated)",
          }}
        >
          <strong style={{ fontSize: "13px" }}>
            {docCopy.stepsSummaryTitle}
          </strong>
          {executedSteps.map((step) => (
            <div
              key={step.stepNumber}
              data-testid={`orcia-doc-generation-step-${step.stepNumber}`}
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "flex-start",
                gap: "8px",
                fontSize: "12px",
              }}
            >
              <div>
                <strong>{step.title}</strong>{" "}
                <span style={{ color: "var(--color-muted-foreground)" }}>
                  ({step.agentHandle})
                </span>
                <div style={{ color: "var(--color-text-secondary)", marginTop: "2px" }}>
                  {step.summary}
                </div>
              </div>
              <StatusBadge label={docCopy.stepCompletedBadge} tone="emerald" />
            </div>
          ))}
        </div>
      ) : null}

      {generatedMarkdown ? (
        <div
          data-testid="orcia-doc-generation-output-preview"
          style={{
            padding: "12px",
            borderRadius: "var(--radius-sm)",
            border: "1px solid var(--color-border)",
            backgroundColor: "var(--color-surface-card)",
          }}
        >
          <FormattedMarkdownContent content={generatedMarkdown} />
        </div>
      ) : null}
    </section>
  );
}
