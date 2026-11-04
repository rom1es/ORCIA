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
              ? "Aucune étape de validation en attente actuellement"
              : "No review checkpoint currently awaiting approval"}
          </strong>
          <p
            style={{
              margin: "4px 0 0 0",
              fontSize: "13px",
              color: "var(--color-muted-foreground)",
            }}
          >
            {isFr
              ? "Les contrôles automatiques, revues croisées et étapes de validation humaine s'affichent lors de l'exécution d'un processus. Vous pouvez adapter vos processus dans la Configuration."
              : "Automated checks, cross-checked reviews, and human approval steps are displayed while a process runs. You can tailor your processes in Configuration."}
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
          {isFr ? "Configurer les Processus" : "Configure Processes"}
        </button>
      </div>

      {/* Création et Évolution de Packs Métiers (démarre 100 % vide) */}
      <PackBuilderProcessesStudioView
        agents={[]}
        initialHumanAnchorIntent=""
        whatIfImpacts={[]}
        certifications={[]}
        labels={dictionary.packBuilderStudio}
      />

      {/* Rédaction et Mise à Jour des Fiches d'Aide Contextuelle (démarre 100 % vide) */}
      <HelpArticleGeneratorAndValidatorView
        articleId=""
        version="1.0.0"
        packId=""
        triggerRegime="STAGED_HUMAN_REVIEW"
        boundRoutes={[]}
        validationFr={{
          articleId: "",
          lang: "fr",
          passed: false,
          boundRoutesValid: false,
          uiComponentsAndSectionsValid: false,
          glossaryAndZeroSecretValid: false,
          elapsedMs: 0,
          violations: [],
        }}
        validationEn={{
          articleId: "",
          lang: "en",
          passed: false,
          boundRoutesValid: false,
          uiComponentsAndSectionsValid: false,
          glossaryAndZeroSecretValid: false,
          elapsedMs: 0,
          violations: [],
        }}
        invalidatedRedisKeys={[]}
        exportedGitPaths={[]}
        hotAttachElapsedMs={0}
        labels={dictionary.helpArticleGenerator}
      />
    </div>
  );
}
