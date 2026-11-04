import {
  ContextualHelpColumnAndCenter,
  ContextualInfoTriggerButton,
  OntologyAndKbExplorerPanel,
  type UiOntologyLevel,
} from "@orcia/ui";
import React, { useState } from "react";
import { usePlatformSetup } from "../../components/platformSetupStore";
import { useShellNavigation } from "../../components/ShellContainer";
import { useI18n } from "../../i18n";

export function OntologyFeaturePanel() {
  const { dictionary, locale } = useI18n();
  const { ontologyConcepts, addOntologyConcept } = usePlatformSetup();
  const { openHelpSection } = useShellNavigation();
  const isFr = locale === "fr";

  const [conceptName, setConceptName] = useState("");
  const [conceptLevel, setConceptLevel] = useState<UiOntologyLevel>("1_ENTERPRISE");
  const [conceptDef, setConceptDef] = useState("");

  const handleAddConcept = (e: React.FormEvent) => {
    e.preventDefault();
    if (!conceptName.trim()) return;
    addOntologyConcept({
      conceptKey: `concept-${ontologyConcepts.length + 1}`,
      canonicalTerm: conceptName.trim(),
      level: conceptLevel,
      scopeId: "scope-global",
      definitionText: conceptDef.trim() || conceptName.trim(),
      immutable: conceptLevel === "1_ENTERPRISE",
      synonyms: [],
      profileTranslations: {
        EXECUTIVE: conceptDef.trim() || conceptName.trim(),
        PM_PO: conceptDef.trim() || conceptName.trim(),
        ARCHITECT: conceptDef.trim() || conceptName.trim(),
        TECH_LEAD: conceptDef.trim() || conceptName.trim(),
        DEVELOPER: conceptDef.trim() || conceptName.trim(),
        SECOPS: conceptDef.trim() || conceptName.trim(),
      },
      impactedTemplates: [],
      impactedWorkflows: [],
      impactedRuns: [],
    });
    setConceptName("");
    setConceptDef("");
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
      <section
        data-testid="ontology-create-concept-card"
        className="orcia-bento-card"
        style={{ display: "flex", flexDirection: "column", gap: "10px" }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <strong>
            {isFr
              ? "Ajouter un Terme Métier ou une Règle au Glossaire"
              : "Add a Business Term or Rule to the Glossary"}
          </strong>
          <ContextualInfoTriggerButton
            sectionId="glossary-rules"
            label={
              isFr
                ? "Comprendre le glossaire métier et les règles de l'organisation"
                : "Understand the business glossary and organization rules"
            }
            onOpenHelpSection={openHelpSection}
          />
        </div>
        <form
          data-testid="ontology-create-concept-form"
          onSubmit={handleAddConcept}
          style={{ display: "flex", flexWrap: "wrap", gap: "8px" }}
        >
          <select
            data-testid="ontology-level-select"
            value={conceptLevel}
            onChange={(e) => setConceptLevel(e.target.value as UiOntologyLevel)}
            style={{
              padding: "7px 10px",
              borderRadius: "var(--radius-sm)",
              border: "1px solid var(--color-border)",
            }}
          >
            <option value="1_ENTERPRISE">
              {isFr ? "1. Organisation (Règle commune)" : "1. Organization (Shared rule)"}
            </option>
            <option value="2_DOMAIN">
              {isFr ? "2. Direction / Pôle (BU)" : "2. Division / Department (BU)"}
            </option>
            <option value="3_TEAM">
              {isFr ? "3a. Équipe" : "3a. Team"}
            </option>
            <option value="3_WORKSPACE">
              {isFr ? "3b. Espace de Travail" : "3b. Workspace"}
            </option>
            <option value="4_RUN_EPHEMERAL">
              {isFr ? "4. Exécution en cours" : "4. Current execution"}
            </option>
          </select>
          <input
            type="text"
            data-testid="ontology-concept-name-input"
            value={conceptName}
            onChange={(e) => setConceptName(e.target.value)}
            placeholder={isFr ? "Intitulé du terme métier..." : "Business term name..."}
            style={{
              flex: 1,
              minWidth: "180px",
              padding: "7px 10px",
              borderRadius: "var(--radius-sm)",
              border: "1px solid var(--color-border)",
            }}
          />
          <input
            type="text"
            data-testid="ontology-concept-def-input"
            value={conceptDef}
            onChange={(e) => setConceptDef(e.target.value)}
            placeholder={isFr ? "Définition claire et partagée..." : "Clear shared definition..."}
            style={{
              flex: 2,
              minWidth: "220px",
              padding: "7px 10px",
              borderRadius: "var(--radius-sm)",
              border: "1px solid var(--color-border)",
            }}
          />
          <button
            type="submit"
            data-testid="ontology-create-concept-btn"
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
            {isFr ? "+ Ajouter au glossaire" : "+ Add to glossary"}
          </button>
        </form>
      </section>

      <div className="orcia-bento-card">
        <OntologyAndKbExplorerPanel
          concepts={[...ontologyConcepts]}
          tripartiteEdges={[]}
          staleAlerts={[]}
          labels={dictionary.ontologyExplorer}
        />
      </div>

      {/* Story 9.5 & 12.3 — Centre d'Aide (mode=HELP_MENU_CENTER) sur /help */}
      <ContextualHelpColumnAndCenter
        mode="HELP_MENU_CENTER"
        route="/help"
        pack="orcia-pack-sdlc@1.0.0"
        redisCacheKey={`help:route:/help:orcia-pack-sdlc@1.0.0:${locale}`}
        mergedLayers={["BASE", "PACK", "WORKSPACE"]}
        article={{
          resourceId: "help-center-overview",
          uri: "orcia://system/help/help-center-overview@1.0.0",
          title: isFr
            ? "Centre d'Aide Contextuelle & Glossaire de Votre Organisation"
            : "Contextual Help Center & Organization Glossary",
          version: "1.0.0",
          lang: locale,
          layer: "BASE",
          packName: "orcia-pack-sdlc",
          boundRoutes: ["/cockpit", "/assistant", "/spaces", "/processes", "/agents", "/help"],
          summaryWhatFor: isFr
            ? "Ce centre rassemble les guides pratiques et explications rattachés à vos écrans et à vos Packs métiers."
            : "This center gathers practical guides and explanations bound to your screens and Business Packs.",
          stepByStepItems: isFr
            ? [
                "Ouvrez la colonne ❓ ou cliquez sur une icône ⓘ sur n'importe quel écran pour afficher l'explication dédiée.",
                "Utilisez l'outil de création de fiches d'aide dans Mes Processus pour rédiger et publier de nouveaux guides pour vos équipes.",
              ]
            : [
                "Open the ❓ column or click an ⓘ icon on any screen to display the dedicated explanation.",
                "Use the help guide authoring tool in My Processes to write and publish new guides for your teams.",
              ],
          keyTermsItems: isFr
            ? [
                "Fiche de référence : Guide officiel associé à un écran.",
                "Adaptation par niveau : Guides enrichis par votre métier et votre Espace.",
                "Vérification de qualité : Contrôle automatique des liens et du vocabulaire.",
              ]
            : [
                "Reference guide: Official guide linked to a screen.",
                "Level customization: Guides enriched by your domain and Workspace.",
                "Quality check: Automated verification of links and terminology.",
              ],
          faqItems: [
            isFr
              ? "Comment rétablir la version précédente d'un guide ? Cliquez sur ⏪ Version précédente."
              : "How can I restore the previous version of a guide? Click ⏪ Previous version.",
          ],
          casKey: "cas/help-center-overview-v1",
          sha256: "sha256-help-center-v1",
          previousVersion: "0.9.0",
        }}
        rollbackAvailable={true}
        isAdmin={true}
        labels={dictionary.contextualHelpHybrid}
      />
    </div>
  );
}
