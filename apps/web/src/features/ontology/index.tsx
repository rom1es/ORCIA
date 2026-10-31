import {
  ContextualHelpColumnAndCenter,
  OntologyAndKbExplorerPanel,
  type UiOntologyLevel,
} from "@orcia/ui";
import React, { useState } from "react";
import { usePlatformSetup } from "../../components/platformSetupStore";
import { useI18n } from "../../i18n";

export function OntologyFeaturePanel() {
  const { dictionary, locale } = useI18n();
  const { ontologyConcepts, addOntologyConcept } = usePlatformSetup();
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
        <strong>
          {isFr
            ? "Initialiser un Concept ou Axiome dans l'Ontologie"
            : "Initialize an Ontology Concept or Axiom"}
        </strong>
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
            <option value="1_ENTERPRISE">1_ENTERPRISE (Axiome Global)</option>
            <option value="2_DOMAIN">2_DOMAIN (Domaine BU)</option>
            <option value="3_TEAM">3_TEAM (Équipe)</option>
            <option value="3_WORKSPACE">3_WORKSPACE (Espace de Travail)</option>
            <option value="4_RUN_EPHEMERAL">4_RUN_EPHEMERAL (Branche L4)</option>
          </select>
          <input
            type="text"
            data-testid="ontology-concept-name-input"
            value={conceptName}
            onChange={(e) => setConceptName(e.target.value)}
            placeholder={isFr ? "Nom canonique du concept..." : "Canonical concept name..."}
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
            placeholder={isFr ? "Définition métier..." : "Business definition..."}
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
            {isFr ? "+ Ajouter le concept" : "+ Add concept"}
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

      {/* Story 9.5 & 12.3 — Centre d'Aide Hybride (mode=HELP_MENU_CENTER) sur /help */}
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
            ? "Centre d'Aide Contextuelle Hybride & Glossaire Actif"
            : "Hybrid Contextual Help Center & Active Glossary",
          version: "1.0.0",
          lang: locale,
          layer: "BASE",
          packName: "orcia-pack-sdlc",
          boundRoutes: ["/cockpit", "/assistant", "/spaces", "/processes", "/agents", "/help"],
          summaryWhatFor: isFr
            ? "Ce centre rassemble les fiches HelpArticle (catalog_items + cas/<sha256>) rattachées à vos écrans et Packs métiers."
            : "This center aggregates HelpArticle entries (catalog_items + cas/<sha256>) bound to your screens and Business Packs.",
          stepByStepItems: isFr
            ? [
                "Ouvrez la colonne ❓ (340px) sur n'importe quel écran pour obtenir la fiche ciblée (< 10 ms Redis).",
                "Utilisez le Processus 5 (generate-and-attach-help) dans Processus & Studio pour générer et rattacher à chaud (< 100 ms) de nouvelles fiches.",
              ]
            : [
                "Open the ❓ (340px) column on any screen to get the targeted article (< 10 ms Redis).",
                "Use Process 5 (generate-and-attach-help) in Processes & Studio to generate and hot-attach (< 100 ms) new articles.",
              ],
          keyTermsItems: [
            "HelpArticle (REFERENCE)",
            "Fusion 4 couches (BASE -> PACK -> WORKSPACE -> USER)",
            "Validation déterministe Palier 1 (< 5 s)",
          ],
          faqItems: [
            isFr
              ? "Comment revenir à la version précédente ? Cliquez sur ⏪ Rollback @v(N-1)."
              : "How to revert to the previous version? Click ⏪ Rollback @v(N-1).",
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
