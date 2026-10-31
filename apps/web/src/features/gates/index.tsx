import {
  HelpArticleGeneratorAndValidatorView,
  PackBuilderProcessesStudioView,
} from "@orcia/ui";
import React from "react";
import { useShellNavigation } from "../../components/ShellContainer";
import { useI18n } from "../../i18n";

export function GatesFeaturePanel() {
  const { dictionary, locale } = useI18n();
  const { navigateToRoute } = useShellNavigation();
  const isFr = locale === "fr";

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
      <div
        data-testid="gates-empty-state-panel"
        className="orcia-bento-card"
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "12px",
        }}
      >
        <div>
          <strong>
            {isFr
              ? "Aucune Gate de Qualité ou d'Approbation en attente"
              : "No Quality or Approval Gate currently awaiting review"}
          </strong>
          <p
            style={{
              margin: "4px 0 0 0",
              fontSize: "13px",
              color: "var(--color-muted-foreground)",
            }}
          >
            {isFr
              ? "Les Gates déterministes, agentiques (5 lentilles) et humaines adaptatives s'affichent lors de l'exécution d'un Workflow Run. Vous pouvez configurer vos règles d'habilitation et vos workflows dans Paramètres."
              : "Deterministic, agentic (5-lens), and adaptive human Gates are displayed during Workflow Run execution. You can configure permission rules and workflows in Settings."}
          </p>
        </div>
        <button
          type="button"
          data-testid="gates-open-settings-btn"
          onClick={() => navigateToRoute("/settings")}
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
          {isFr ? "Paramétrer IAM & Workflows (/settings)" : "Configure IAM & Workflows (/settings)"}
        </button>
      </div>

      {/* Story 11.4 — Atelier Système orcia-pack-builder (Processus 1 à 4) */}
      <PackBuilderProcessesStudioView
        agents={[
          {
            slug: "pack-architect",
            handle: "@pack-architect",
            roleDescription: "Architecture du manifeste pack.yaml, casquettes et chaîne ADN N1->N2->N3.",
          },
          {
            slug: "workflow-designer",
            handle: "@workflow-designer",
            roleDescription: "Conception des DAGs durables, Ancres Humaines Violets et Gates orthogonales.",
          },
          {
            slug: "starlark-engineer",
            handle: "@starlark-engineer",
            roleDescription: "Compilation et certification déterministe des mécanismes Starlark Palier 1b (< 2 ms).",
          },
          {
            slug: "help-curator",
            handle: "@help-curator",
            roleDescription: "Génération bilingue FR/EN et validation déterministe des fiches HelpArticle.",
          },
        ]}
        initialHumanAnchorIntent="Pack Métier Conformité Paiements SEPA & PSD2 avec règles Starlark Palier 1b."
        whatIfImpacts={[
          {
            workspaceKey: "ws-checkout-core",
            impactedWorkflows: ["sdlc/ticket-to-tech-spec"],
            breakingNorms: [],
            activeRunsCount: 2,
            runLocksUntouched: true,
          },
        ]}
        certifications={[
          {
            toolSlug: "check_tra_threshold.star",
            sandboxTier: "TIER_1B_STARLARK",
            certified: true,
            elapsedMs: 1.2,
            certificateSha256: "cert-starlark-tra-v1",
          },
        ]}
        labels={dictionary.packBuilderStudio}
      />

      {/* Story 11.5 — Processus 5 generate-and-attach-help & Validateur validate_help_article (< 5 s) */}
      <HelpArticleGeneratorAndValidatorView
        articleId="help-processes-pack-builder"
        version="1.0.0"
        packId="orcia-pack-builder"
        triggerRegime="STAGED_HUMAN_REVIEW"
        boundRoutes={["/processes", "/spaces", "/help"]}
        validationFr={{
          articleId: "help-processes-pack-builder",
          lang: "fr",
          passed: true,
          boundRoutesValid: true,
          uiComponentsAndSectionsValid: true,
          glossaryAndZeroSecretValid: true,
          elapsedMs: 4.1,
          violations: [],
        }}
        validationEn={{
          articleId: "help-processes-pack-builder",
          lang: "en",
          passed: true,
          boundRoutesValid: true,
          uiComponentsAndSectionsValid: true,
          glossaryAndZeroSecretValid: true,
          elapsedMs: 3.9,
          violations: [],
        }}
        invalidatedRedisKeys={[
          "help:route:/processes:orcia-pack-builder:fr",
          "help:route:/processes:orcia-pack-builder:en",
        ]}
        exportedGitPaths={[
          "packages/orcia-pack-builder/help/fr/help-processes-pack-builder.md",
          "packages/orcia-pack-builder/help/en/help-processes-pack-builder.md",
        ]}
        hotAttachElapsedMs={14.2}
        labels={dictionary.helpArticleGenerator}
      />
    </div>
  );
}
