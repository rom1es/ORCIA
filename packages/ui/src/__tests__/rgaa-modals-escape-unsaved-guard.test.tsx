import React from "react";
import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import {
  AssistantGovernanceModalAndStudio,
  CommandPaletteModal,
  DEFAULT_RGAA_MODAL_LABELS_FR,
  GuidanceDrawer,
  RgaaModalDialog,
  TopHeaderSearchCommand,
  UpstreamChallengeRewindModal,
  UserAccountDropdownAndSettingsModal,
  type AssistantGovernanceModalAndStudioLabels,
  type CommandPaletteItemSpec,
  type CommandPaletteModalLabels,
  type GuidanceDrawerLabels,
  type TopHeaderSearchCommandLabels,
  type TopSearchHitItem,
  type UpstreamChallengeModalLabels,
  type UpstreamChallengeWhatIfPreview,
  type UserAccountDropdownAndSettingsLabels,
} from "../index.js";

const SAMPLE_USER_SETTINGS_LABELS: UserAccountDropdownAndSettingsLabels = {
  triggerAriaLabel: "Menu compte utilisateur",
  dropdownWidthNote: "",
  hatSelectorLabel: "Rôle",
  themeQuickToggleLabel: "Thème",
  localeQuickToggleLabel: "Langue",
  openAccountSettingsLabel: "⚙ Mes Préférences",
  openPassthroughSourcesLabel: "Connexions personnelles",
  logoutButtonLabel: "Déconnexion",
  modalTitle: "Mes Préférences & Compte",
  tab1PreferencesTitle: "Préférences",
  tab2SecurityTitle: "Sécurité",
  tab3PassthroughTitle: "Sources Passthrough",
  tab4McpKeysTitle: "Clés MCP IDE",
  customizeAssistantRedirectCta: "Personnaliser Mon Assistant",
  testPassthroughTokenCta: "Tester la connexion",
  generateMcpTokenCta: "Générer un jeton MCP",
  revokeMcpTokenCta: "Révoquer",
  targetWholeSpaceLabel: "Espace complet",
  targetSingleAgentLabel: "Agent unique",
  ideJsonReadyTitle: "Configuration IDE prête",
};

const SAMPLE_ASSISTANT_GOV_LABELS: AssistantGovernanceModalAndStudioLabels = {
  modalTitle: "⚙ Réglages de l'assistant",
  tab1UserTitle: "Mes préférences",
  tab2WorkspaceTitle: "Réglages de l'Espace",
  tab3AssemblyTitle: "Assemblage complet",
  toneLabel: "Ton de réponse",
  formatLabel: "Format préféré",
  defaultHatLabel: "Rôle par défaut",
  personalInstructionsLabel: "Instructions personnelles",
  saveUserPrefsCta: "Enregistrer mes préférences",
  workspaceInstructionsLabel: "Instructions de l'Espace",
  workspaceReadOnlyBadge: "Lecture seule",
  mcpExposeToggleLabel: "Exposer via MCP",
  mcpFrozenByUpperBadge: "Verrouillé par niveau supérieur",
  copyMcpConfigCta: "Copier config MCP",
  saveWorkspaceSettingsCta: "Enregistrer l'Espace",
  openStudioModeBCta: "🛠 Ouvrir dans le Studio (Mode B)",
  studioHeaderTitle: "Studio DAG — Mode B",
  studioPrePromptLabel: "Pré-prompt IA",
  studioHarnessImmutableBadge: "Bornes AssistantHarness immuables",
  studioTestDryRunCta: "Tester (Dry-Run)",
  studioSaveOverrideCta: "Publier la surcharge",
  studioResetDefaultCta: "Réinitialiser",
};

const SAMPLE_UPSTREAM_PREVIEW: UpstreamChallengeWhatIfPreview = {
  runId: "run-001",
  challengerStepKey: "step-arch-review",
  targetUpstreamStepKey: "step-prd-spec",
  challengedSectionKey: "sec-fx-guarantee",
  targetProfileArchetype: "PRODUCT_LEADER",
  translatedSummary: "Impact sur la fenêtre de garantie FX.",
  invalidatedDownstreamStepKeys: ["step-api-contract"],
  invalidatedArtifactSections: ["sec-fx-guarantee"],
  invalidatedOntologyAxiomKeys: ["axiom.fx_window"],
  preservedUpstreamStepKeys: ["step-vision"],
  upstreamTokensSaved: 1420,
};

const SAMPLE_UPSTREAM_LABELS: UpstreamChallengeModalLabels = {
  modalTitle: "Contester une décision amont",
  modalSubtitle: "Simulation d'impact avant rembobinage ciblé",
  targetStepLabel: "Étape amont visée",
  sectionKeyLabel: "Section contestée",
  reasonLabel: "Motif de contestation",
  reasonPlaceholder: "Expliquez la contradiction...",
  whatIfTitle: "Aperçu d'impact What-If",
  invalidatedStepsLabel: "Étapes invalidées",
  invalidatedSectionsLabel: "Sections invalidées",
  invalidatedAxiomsLabel: "Axiomes impactés",
  preservedStepsLabel: "Étapes préservées",
  translatedSummaryLabel: "Traduction métier",
  submitChallengeCta: "Valider la contestation",
  replayStepCta: "Relancer l'étape",
  closeCta: "Annuler",
  challengeSubmittedFeedback: "Contestation soumise",
  replayTriggeredFeedback: "Étape relancée",
};

const SAMPLE_COMMAND_PALETTE_ITEMS: readonly CommandPaletteItemSpec[] = [
  {
    entryId: "nav-cockpit",
    category: "NAVIGATION",
    label: "Aller au Cockpit",
    subtitle: "Vue principale des décisions",
    shortcut: "G C",
    targetRoute: "/cockpit",
  },
];

const SAMPLE_COMMAND_PALETTE_LABELS: CommandPaletteModalLabels = {
  modalTitle: "Palette de commandes",
  searchPlaceholder: "Rechercher une action...",
  closeButton: "Annuler",
  emptyResults: "Aucun résultat",
  contributorBadge: "Contributeur",
  observerBadge: "Observateur",
};

const SAMPLE_TOP_SEARCH_HITS: readonly TopSearchHitItem[] = [
  {
    itemId: "hit-1",
    family: "HELP_ACTIONS",
    title: "Cockpit & Décisions",
    snippet: "Arbitrages prioritaires",
    workspaceId: "ws-1",
    screenRoute: "/cockpit",
    deepLinkUri: "/cockpit",
    speedTier: 1,
    lockedTop: true,
    score: 0.99,
    badge: null,
    highlightDurationMs: 2000,
    opensContextualHelpColumn: false,
  },
];

const SAMPLE_TOP_SEARCH_LABELS: TopHeaderSearchCommandLabels = {
  modalTitle: "Recherche fédérée",
  inputPlaceholder: "Rechercher...",
  scopeScreenLabel: "Cet écran",
  scopeWorkspaceLabel: "Cet espace",
  scopeAllWorkspacesLabel: "Tous les espaces",
  speed1SectionTitle: "Résultats immédiats",
  speed2SectionTitle: "Passages proches",
  semanticCloseMatchBadge: "Passage proche",
  emptyResultsLabel: "Aucun résultat",
  previewPaneTitle: "Aperçu",
  deepLinkActionLabel: "Valider et ouvrir",
  openHelpColumnActionLabel: "Ouvrir l'aide",
  askAssistantFooterPrefix: "Demander à l'assistant :",
  askAssistantFooterSuffix: "dans cet espace",
  familyLabels: {
    FOLDERS_DISCUSSIONS: "Dossiers",
    PROCESSES_EXECUTIONS: "Processus",
    AGENTS_TOOLS: "Agents",
    DELIVERABLES_ARTIFACTS: "Livrables",
    SOURCES_SNIPPETS: "Sources",
    ONTOLOGY_GLOSSARY: "Glossaire",
    HELP_ACTIONS: "Aide",
  },
};

const SAMPLE_GUIDANCE_LABELS: GuidanceDrawerLabels = {
  drawerTitle: "Guide de démarrage",
  toggleExpand: "Déplier",
  toggleCollapse: "Replier",
  commandPrefix: "Commande",
};

describe("RGAA Modal & Popup Accessibility — Escape, Cancel, Unsaved Changes Guard & Enter Submit", () => {
  describe("1. RgaaModalDialog shared primitive", () => {
    it("closes immediately on Escape or Cancel click when isDirty is false", () => {
      const onClose = vi.fn();
      const onSubmit = vi.fn();
      render(
        <RgaaModalDialog
          isOpen={true}
          title="Titre de test"
          testId="shared-rgaa-modal"
          isDirty={false}
          onClose={onClose}
          onSubmit={onSubmit}
          labels={DEFAULT_RGAA_MODAL_LABELS_FR}
        >
          <p>Contenu</p>
        </RgaaModalDialog>,
      );

      fireEvent.keyDown(window, { key: "Escape" });
      expect(onClose).toHaveBeenCalledTimes(1);

      fireEvent.click(screen.getByTestId("shared-rgaa-modal-cancel-btn"));
      expect(onClose).toHaveBeenCalledTimes(2);
    });

    it("intercepts Escape and Cancel when isDirty is true, showing an alertdialog with stay/discard options", () => {
      const onClose = vi.fn();
      const onDiscard = vi.fn();
      render(
        <RgaaModalDialog
          isOpen={true}
          title="Titre de test"
          testId="shared-rgaa-modal"
          isDirty={true}
          onClose={onClose}
          onDiscardUnsavedChanges={onDiscard}
          labels={DEFAULT_RGAA_MODAL_LABELS_FR}
        >
          <p>Formulaire modifié</p>
        </RgaaModalDialog>,
      );

      // Try Escape -> should NOT close, should show alertdialog
      fireEvent.keyDown(window, { key: "Escape" });
      expect(onClose).not.toHaveBeenCalled();
      expect(
        screen.getByTestId("shared-rgaa-modal-unsaved-changes-alert"),
      ).toBeDefined();

      // Click "Continuer l'édition" (stay) -> hides alertdialog, keeps modal open
      fireEvent.click(screen.getByTestId("shared-rgaa-modal-unsaved-stay-btn"));
      expect(
        screen.queryByTestId("shared-rgaa-modal-unsaved-changes-alert"),
      ).toBeNull();
      expect(onClose).not.toHaveBeenCalled();

      // Click "Annuler" -> shows alertdialog again
      fireEvent.click(screen.getByTestId("shared-rgaa-modal-cancel-btn"));
      expect(
        screen.getByTestId("shared-rgaa-modal-unsaved-changes-alert"),
      ).toBeDefined();

      // Click "Quitter sans enregistrer" (discard) -> calls onDiscard + onClose
      fireEvent.click(screen.getByTestId("shared-rgaa-modal-unsaved-discard-btn"));
      expect(onDiscard).toHaveBeenCalledTimes(1);
      expect(onClose).toHaveBeenCalledTimes(1);
    });

    it("triggers onSubmit when focus is on the Valider button and Enter is pressed", () => {
      const onClose = vi.fn();
      const onSubmit = vi.fn();
      render(
        <RgaaModalDialog
          isOpen={true}
          title="Titre de test"
          testId="shared-rgaa-modal"
          isDirty={true}
          onClose={onClose}
          onSubmit={onSubmit}
          labels={DEFAULT_RGAA_MODAL_LABELS_FR}
        >
          <p>Contenu</p>
        </RgaaModalDialog>,
      );

      const submitBtn = screen.getByTestId("shared-rgaa-modal-submit-btn");
      submitBtn.focus();
      expect(document.activeElement).toBe(submitBtn);

      fireEvent.keyDown(submitBtn, { key: "Enter" });
      expect(onSubmit).toHaveBeenCalledTimes(1);
    });
  });

  describe("2. UserAccountDropdownAndSettingsModal", () => {
    it("closes on Escape when clean, guards unsaved changes when dirty, and validates on Enter", () => {
      const onSync = vi.fn();
      render(
        <UserAccountDropdownAndSettingsModal
          userDisplayName="Romain"
          userEmail="romain@orcia.io"
          userRole="PLATFORM_ADMIN"
          initialLocale="fr"
          initialTheme="system"
          labels={SAMPLE_USER_SETTINGS_LABELS}
          onPreferencesSync={onSync}
        />,
      );

      // Open dropdown and open modal
      fireEvent.click(screen.getByTestId("user-account-dropdown-trigger"));
      fireEvent.click(screen.getByTestId("dropdown-open-settings-modal-btn"));
      expect(screen.getByTestId("user-settings-modal")).toBeDefined();

      // 1. Clean close via Escape
      fireEvent.keyDown(window, { key: "Escape" });
      expect(screen.queryByTestId("user-settings-modal")).toBeNull();

      // Re-open modal
      fireEvent.click(screen.getByTestId("user-account-dropdown-trigger"));
      fireEvent.click(screen.getByTestId("dropdown-open-settings-modal-btn"));
      expect(screen.getByTestId("user-settings-modal")).toBeDefined();

      // 2. Switch to IDE_MCP_KEYS tab and modify slug -> dirty state
      fireEvent.click(screen.getByTestId("user-settings-tab-IDE_MCP_KEYS"));
      fireEvent.change(screen.getByTestId("mcp-target-slug-input"), {
        target: { value: "mon-espace-critique" },
      });

      // Press Escape -> unsaved alert appears, modal stays open
      fireEvent.keyDown(window, { key: "Escape" });
      expect(
        screen.getByTestId("user-settings-modal-unsaved-changes-alert"),
      ).toBeDefined();
      expect(screen.getByTestId("user-settings-modal")).toBeDefined();

      // Choose "Continuer l'édition"
      fireEvent.click(screen.getByTestId("user-settings-modal-unsaved-stay-btn"));
      expect(
        screen.queryByTestId("user-settings-modal-unsaved-changes-alert"),
      ).toBeNull();

      // 3. Focus Valider button and press Enter -> saves and closes modal
      const submitBtn = screen.getByTestId("user-settings-modal-submit-btn");
      submitBtn.focus();
      fireEvent.keyDown(submitBtn, { key: "Enter" });
      expect(screen.queryByTestId("user-settings-modal")).toBeNull();
    });
  });

  describe("3. AssistantGovernanceModalAndStudio", () => {
    it("supports Escape/Cancel when clean, guards unsaved changes when dirty, and submits on Enter", () => {
      const onClose = vi.fn();
      const onSaveUserPrefs = vi.fn();
      render(
        <AssistantGovernanceModalAndStudio
          workspaceId="ws-1"
          canEditWorkspaceLayer={true}
          canOpenStudioModeB={true}
          assembledLayers={[]}
          studioNodes={[]}
          labels={SAMPLE_ASSISTANT_GOV_LABELS}
          onSaveUserPreferences={onSaveUserPrefs}
          onClose={onClose}
        />,
      );

      // 1. Clean Escape calls onClose
      fireEvent.keyDown(window, { key: "Escape" });
      expect(onClose).toHaveBeenCalledTimes(1);

      // 2. Make dirty by editing personal instructions
      fireEvent.change(screen.getByTestId("assistant-user-instructions-input"), {
        target: { value: "Nouvelle directive métier" },
      });

      // Click Annuler -> unsaved changes alert appears
      fireEvent.click(screen.getByTestId("assistant-gov-cancel-btn"));
      expect(onClose).toHaveBeenCalledTimes(1); // not incremented
      expect(
        screen.getByTestId("assistant-gov-unsaved-changes-alert"),
      ).toBeDefined();

      // Click stay
      fireEvent.click(screen.getByTestId("assistant-gov-unsaved-stay-btn"));
      expect(
        screen.queryByTestId("assistant-gov-unsaved-changes-alert"),
      ).toBeNull();

      // 3. Focus Save button and press Enter
      const saveBtn = screen.getByTestId("assistant-save-user-prefs-btn");
      saveBtn.focus();
      fireEvent.keyDown(saveBtn, { key: "Enter" });
      expect(onSaveUserPrefs).toHaveBeenCalledWith(
        expect.objectContaining({
          personalInstructions: "Nouvelle directive métier",
        }),
      );
    });
  });

  describe("4. UpstreamChallengeRewindModal", () => {
    it("closes on Escape/Cancel when unmodified, guards unsaved reason edits, and submits on Enter", () => {
      const onClose = vi.fn();
      const onSubmitChallenge = vi.fn();
      render(
        <UpstreamChallengeRewindModal
          isOpen={true}
          preview={SAMPLE_UPSTREAM_PREVIEW}
          labels={SAMPLE_UPSTREAM_LABELS}
          onClose={onClose}
          onSubmitChallenge={onSubmitChallenge}
        />,
      );

      // 1. Clean close via Cancel button
      fireEvent.click(screen.getByTestId("upstream-challenge-cancel-btn"));
      expect(onClose).toHaveBeenCalledTimes(1);

      // 2. Edit reason -> becomes dirty
      fireEvent.change(screen.getByTestId("upstream-challenge-reason-input"), {
        target: {
          value: "Nouveau motif de contestation détaillé dépassant dix caractères.",
        },
      });

      // Press Escape -> shows unsaved changes alert
      fireEvent.keyDown(window, { key: "Escape" });
      expect(onClose).toHaveBeenCalledTimes(1);
      expect(
        screen.getByTestId("upstream-challenge-unsaved-changes-alert"),
      ).toBeDefined();

      // Stay in modal
      fireEvent.click(screen.getByTestId("upstream-challenge-unsaved-stay-btn"));

      // 3. Focus submit button and press Enter
      const submitBtn = screen.getByTestId("upstream-challenge-submit-btn");
      submitBtn.focus();
      fireEvent.keyDown(submitBtn, { key: "Enter" });
      expect(onSubmitChallenge).toHaveBeenCalledWith({
        targetUpstreamStepKey: "step-prd-spec",
        challengedSectionKey: "sec-fx-guarantee",
        challengeReason:
          "Nouveau motif de contestation détaillé dépassant dix caractères.",
      });
    });
  });

  describe("5. CommandPaletteModal & TopHeaderSearchCommand & GuidanceDrawer", () => {
    it("supports Escape, Cancel, Unsaved Guard, and Enter on Valider in CommandPaletteModal", () => {
      const onClose = vi.fn();
      const onSelectItem = vi.fn();
      const { rerender } = render(
        <CommandPaletteModal
          isOpen={true}
          items={SAMPLE_COMMAND_PALETTE_ITEMS}
          labels={SAMPLE_COMMAND_PALETTE_LABELS}
          isDirty={false}
          onClose={onClose}
          onSelectItem={onSelectItem}
        />,
      );

      fireEvent.keyDown(window, { key: "Escape" });
      expect(onClose).toHaveBeenCalledTimes(1);

      // Focus Valider button and press Enter
      const submitBtn = screen.getByTestId("command-palette-submit-btn");
      submitBtn.focus();
      fireEvent.keyDown(submitBtn, { key: "Enter" });
      expect(onSelectItem).toHaveBeenCalledWith(SAMPLE_COMMAND_PALETTE_ITEMS[0]);

      // Dirty guard check
      rerender(
        <CommandPaletteModal
          isOpen={true}
          items={SAMPLE_COMMAND_PALETTE_ITEMS}
          labels={SAMPLE_COMMAND_PALETTE_LABELS}
          isDirty={true}
          onClose={onClose}
          onSelectItem={onSelectItem}
        />,
      );
      fireEvent.click(screen.getByTestId("command-palette-cancel-btn"));
      expect(
        screen.getByTestId("command-palette-unsaved-changes-alert"),
      ).toBeDefined();
    });

    it("supports Escape, Cancel, Unsaved Guard, and Enter on Valider in TopHeaderSearchCommand", () => {
      const onClose = vi.fn();
      const onSelectDeepLink = vi.fn();
      render(
        <TopHeaderSearchCommand
          labels={SAMPLE_TOP_SEARCH_LABELS}
          speed1Hits={SAMPLE_TOP_SEARCH_HITS}
          isDirty={true}
          onClose={onClose}
          onSelectDeepLink={onSelectDeepLink}
        />,
      );

      // Dirty Escape -> shows alert
      fireEvent.keyDown(window, { key: "Escape" });
      expect(onClose).not.toHaveBeenCalled();
      expect(screen.getByTestId("cmdk-unsaved-changes-alert")).toBeDefined();

      // Stay
      fireEvent.click(screen.getByTestId("cmdk-unsaved-stay-btn"));

      // Focus submit button and press Enter
      const submitBtn = screen.getByTestId("cmdk-submit-btn");
      submitBtn.focus();
      fireEvent.keyDown(submitBtn, { key: "Enter" });
      expect(onSelectDeepLink).toHaveBeenCalledWith(
        expect.objectContaining({ itemId: "hit-1", deepLinkUri: "/cockpit" }),
      );
    });

    it("supports Escape and Cancel in GuidanceDrawer with unsaved guard", () => {
      const onClose = vi.fn();
      render(
        <GuidanceDrawer
          steps={[
            {
              stepNumber: 1,
              title: "Étape 1",
              description: "Configurer",
              actionCommand: "orcia init",
            },
          ]}
          labels={SAMPLE_GUIDANCE_LABELS}
          defaultOpen={true}
          isDirty={true}
          onClose={onClose}
        />,
      );

      fireEvent.click(screen.getByTestId("guidance-drawer-cancel-btn"));
      expect(onClose).not.toHaveBeenCalled();
      expect(
        screen.getByTestId("guidance-drawer-unsaved-changes-alert"),
      ).toBeDefined();

      fireEvent.click(screen.getByTestId("guidance-drawer-unsaved-discard-btn"));
      expect(onClose).toHaveBeenCalledTimes(1);
    });
  });
});
