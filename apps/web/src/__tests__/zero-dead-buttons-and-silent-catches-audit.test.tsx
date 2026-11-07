import fs from "node:fs";
import path from "node:path";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import React from "react";
import { afterEach, describe, expect, it } from "vitest";
import { ShellContainer } from "../components/ShellContainer";
import { CatalogFeaturePanel } from "../features/catalog";
import { GatesFeaturePanel } from "../features/gates";
import { InboxFeaturePanel } from "../features/inbox";
import { WorkspacesFeaturePanel } from "../features/workspaces";
import { I18nProvider } from "../i18n";

afterEach(() => {
  cleanup();
});

const WEB_SRC_DIR = path.resolve(__dirname, "..");

function collectTsxFiles(dir: string): string[] {
  const entries = fs.readdirSync(dir, { withFileTypes: true });
  const results: string[] = [];
  for (const entry of entries) {
    const fullPath = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      if (entry.name === "__tests__" || entry.name === "generated") {
        continue;
      }
      results.push(...collectTsxFiles(fullPath));
    } else if (entry.isFile() && /\.(ts|tsx)$/.test(entry.name)) {
      results.push(fullPath);
    }
  }
  return results;
}

describe("Permanent CI Guardrail — Zero Dead Buttons, Zero Omitted Callbacks & Zero Silent Catches", () => {
  it("forbids silent .catch(() => undefined) inside apps/web/src/features/ and apps/web/src/routes/", () => {
    const targetDirs = [
      path.join(WEB_SRC_DIR, "features"),
      path.join(WEB_SRC_DIR, "routes"),
    ];
    const violations: string[] = [];

    for (const dir of targetDirs) {
      for (const filePath of collectTsxFiles(dir)) {
        const content = fs.readFileSync(filePath, "utf-8");
        const lines = content.split("\n");
        lines.forEach((line, idx) => {
          if (/\.catch\(\s*\(\s*\)\s*=>\s*(undefined|null|\{\s*\})\s*\)/.test(line)) {
            const rel = path.relative(WEB_SRC_DIR, filePath);
            violations.push(`${rel}:${idx + 1} -> ${line.trim()}`);
          }
        });
      }
    }

    expect(violations).toEqual([]);
  });

  it("verifies that every interactive @orcia/ui primitive mounted in apps/web receives its action callbacks", () => {
    const requiredPropsByComponent: Record<string, readonly string[]> = {
      AssistantSpeedSelectorAndStreamView: ["onSendTurn", "onStopGeneration"],
      AssistantGovernanceModalAndStudio: [
        "onSaveUserPreferences",
        "onSaveWorkspaceSettings",
        "onSaveStudioOverride",
        "onResetStudioOverride",
      ],
      AssistantFoldersAndCollaborativeThreadView: [
        "onSelectFolder",
        "onCreateFolder",
        "onUpdatePinnedNotes",
        "onChangeVisibility",
        "onSendCollaborativeMessage",
        "onLaunchProcessFromFolder",
      ],
      AssistantCitationPillsAndArtifactCard: ["onSaveDraft", "onContinueInProcess"],
      RemoteServiceTestBenchAndMcpExposureView: [
        "onRunTestBench",
        "onActivateService",
        "onToggleMcpExposure",
      ],
      PackBuilderProcessesStudioView: ["onCreateBusinessPack", "onPromoteAssetToPack"],
      HelpArticleGeneratorAndValidatorView: ["onGenerateAndAttach"],
      CommandPaletteModal: ["onSelectItem", "onClose"],
      WorkspaceFiveTabsAndExternalRebaseView: ["onSelectTab", "onRegisterWaiver"],
      DnaStarlarkCompilerAndGlossaryLifecycleView: [
        "onCompileFromNorm",
        "onSignAndActivate",
        "onPromoteInFlow",
        "onRejectCandidate",
      ],
      TopHeaderSearchCommand: [
        "onQueryChange",
        "onTriggerSpeed2Now",
        "onSelectDeepLink",
        "onAskAssistant",
        "onClose",
      ],
    };

    const allFiles = collectTsxFiles(WEB_SRC_DIR);
    const missingWiring: string[] = [];

    for (const [componentName, requiredProps] of Object.entries(requiredPropsByComponent)) {
      const tagRegex = new RegExp(`<${componentName}\\b([\\s\\S]*?)\\/>`, "g");
      let foundMount = false;

      for (const filePath of allFiles) {
        const content = fs.readFileSync(filePath, "utf-8");
        let match = tagRegex.exec(content);
        while (match !== null) {
          foundMount = true;
          const propsBlock = match[1] ?? "";
          const rel = path.relative(WEB_SRC_DIR, filePath);
          for (const reqProp of requiredProps) {
            const propRegex = new RegExp(`\\b${reqProp}\\s*=`);
            if (!propRegex.test(propsBlock)) {
              missingWiring.push(`${rel}: <${componentName}> is missing prop "${reqProp}"`);
            }
          }
          match = tagRegex.exec(content);
        }
      }

      if (!foundMount) {
        missingWiring.push(`Component <${componentName}> was not found mounted anywhere in apps/web`);
      }
    }

    expect(missingWiring).toEqual([]);
  });

  it("dynamically verifies that clicking 'Envoyer à Mon Assistant', selecting Model & Thinking Level, saving/resuming conversations across F5 reloads, and '+ Nouveau dossier' in InboxFeaturePanel updates the DOM", async () => {
    const firstRender = render(
      <I18nProvider initialLocale="fr">
        <ShellContainer>
          <InboxFeaturePanel />
        </ShellContainer>
      </I18nProvider>,
    );

    // 0. Minimalist Welcome Hero ("Par quoi voulez-vous commencer ?") is shown initially without Cockpit clutter or Redis keys
    expect(screen.getByTestId("assistant-welcome-hero-title").textContent).toContain(
      "Par quoi voulez-vous commencer ?",
    );
    expect(screen.queryByTestId("inbox-empty-state")).toBeNull();
    expect(screen.queryByTestId("inbox-amber-counter")).toBeNull();
    expect(screen.queryByTestId("assistant-prompt-cache-badge")).toBeNull();

    // 1. Open Model & Thinking Level dropdown popover and select 'complex' + 'deep'
    fireEvent.click(screen.getByTestId("assistant-model-and-effort-picker-trigger"));
    expect(screen.getByTestId("assistant-model-picker-popover")).toBeDefined();
    fireEvent.click(screen.getByTestId("assistant-model-option-complex"));
    fireEvent.click(screen.getByTestId("assistant-effort-option-deep"));

    // Verify bottom folders panel is collapsed by default (sr-only) until user clicks '📁 Dossiers'
    expect(
      screen.getByTestId("assistant-folders-panel-wrapper").className,
    ).toContain("sr-only");

    // 2. Send a first question -> auto-creates a saved conversation and clears the input
    const promptInput = screen.getByTestId(
      "assistant-three-speed-input",
    ) as HTMLInputElement;
    fireEvent.change(promptInput, {
      target: { value: "Quels sont les points critiques de l'architecture ?" },
    });
    const sendBtn = screen.getByTestId("assistant-three-speed-send-btn");
    fireEvent.click(sendBtn);
    expect(promptInput.value).toBe("");

    await waitFor(() => {
      const output = screen.getByTestId("assistant-streamed-response-box");
      expect(output.textContent).toContain("[SPEED_3_DEEP_AUDIT]");
      expect(screen.getByTestId("assistant-conversation-messages-list").textContent).toContain(
        "Quels sont les points critiques de l'architecture ?",
      );
      // Once turn is completed and displayed in ActiveConversationMessagesView, the duplicate stream box & citations card are visually hidden (display: none + sr-only) so the reply appears only once on screen
      expect(output.className).toContain("sr-only");
      expect(output.style.display).toBe("none");
      expect(
        screen.getByTestId("assistant-citations-card-wrapper").className,
      ).toContain("sr-only");
      expect(
        screen.getByTestId("assistant-citations-card-wrapper").style.display,
      ).toBe("none");
      expect(
        screen.getByTestId("assistant-folders-panel-wrapper").style.display,
      ).toBe("none");
      const userBubble = screen.getByTestId("assistant-user-question-bubble");
      expect(userBubble.style.backgroundColor).toBe("var(--color-action-primary)");
      expect(userBubble.style.marginLeft).toBe("auto");
    });

    // Verify Saved Conversations button counter incremented to (1)
    expect(
      screen.getByTestId("assistant-saved-conversations-toggle-btn").textContent,
    ).toContain("(1)");

    // 3. Click '+ Nouvelle conversation' -> returns to the clean welcome screen ("Par quoi voulez-vous commencer ?")
    fireEvent.click(screen.getByTestId("assistant-new-conversation-btn"));
    expect(screen.getByTestId("assistant-welcome-hero-title")).toBeDefined();

    // 4. Simulate F5 browser reload (unmount -> render) and resume the saved conversation in 1 click
    firstRender.unmount();

    render(
      <I18nProvider initialLocale="fr">
        <ShellContainer>
          <InboxFeaturePanel />
        </ShellContainer>
      </I18nProvider>,
    );

    // Open '🕒 Conversations sauvegardées (1)' and click the saved conversation to resume it
    fireEvent.click(screen.getByTestId("assistant-saved-conversations-toggle-btn"));
    const savedList = screen.getByTestId("assistant-saved-conversations-list");
    expect(savedList.textContent).toContain(
      "Quels sont les points critiques de l'architecture ?",
    );
    const resumeBtn = savedList.querySelector(
      '[data-testid^="assistant-resume-conversation-"]',
    ) as HTMLButtonElement;
    expect(resumeBtn).not.toBeNull();
    fireEvent.click(resumeBtn);

    // Full conversation thread is restored and can be continued!
    expect(screen.getByTestId("assistant-conversation-messages-list").textContent).toContain(
      "Quels sont les points critiques de l'architecture ?",
    );

    // 5. Open '📁 Dossiers' and click '+ Nouveau dossier' -> creates and selects a folder without raw PRIVATE or ': :'
    fireEvent.click(screen.getByTestId("assistant-folders-toggle-btn"));
    expect(screen.getByTestId("assistant-folders-and-notes-explainer")).toBeDefined();
    expect(screen.getByTestId("assistant-main-tab-ACTIVE_DISCUSSION").parentElement?.style.display).toBe("none");

    const folderInput = screen.getByTestId("assistant-new-folder-title-input");
    fireEvent.change(folderInput, { target: { value: "Audit DORA 2026" } });
    fireEvent.click(screen.getByTestId("assistant-create-folder-btn"));

    await waitFor(() => {
      expect(screen.getByTestId("assistant-governance-feedback-banner").textContent).toContain(
        "Audit DORA 2026",
      );
      const pillText = screen.getByTestId("assistant-active-folder-pill").textContent ?? "";
      expect(pillText).toContain("📁 Dossier actif : Audit DORA 2026");
      expect(pillText).not.toContain(": :");
      expect(screen.getByTestId("assistant-prompt-active-folder-badge").textContent).toContain(
        "Audit DORA 2026",
      );
    });

    // Save pinned notes on the active folder and verify visibility label has zero raw PRIVATE enum
    const notesTextarea = screen.getByTestId("assistant-folder-pinned-notes-textarea");
    fireEvent.change(notesTextarea, {
      target: { value: "Toujours vérifier l'article 28 DORA sur les prestataires TIC critiques." },
    });
    fireEvent.click(screen.getByTestId("assistant-save-pinned-notes-btn"));
    expect(screen.getByTestId("assistant-prompt-active-folder-note-indicator").textContent).toContain(
      "Note active prise en compte",
    );

    const foldersSectionText = screen.getByTestId("assistant-tab-panel-folders").textContent ?? "";
    expect(foldersSectionText).toContain("🔒 Privé (Moi uniquement)");
    expect(foldersSectionText).not.toContain("PRIVATE");

    // 6. Open '⚙️ Réglages de Mon Assistant' and customize tone + personal instructions
    fireEvent.click(screen.getByTestId("assistant-open-governance-btn"));
    expect(screen.getByTestId("assistant-gov-explainer-banner")).toBeDefined();
    fireEvent.change(screen.getByTestId("assistant-gov-tone-select"), {
      target: { value: "SYNTHETIC" },
    });
    const personalInput = screen.getByTestId("assistant-user-instructions-input");
    fireEvent.change(personalInput, {
      target: { value: "Toujours structurer avec des exemples concrets." },
    });

    // 7. Unmount and re-render (F5 reload) -> verify folder, pinned notes, and governance settings survive F5!
    cleanup();
    render(
      <I18nProvider initialLocale="fr">
        <ShellContainer>
          <InboxFeaturePanel />
        </ShellContainer>
      </I18nProvider>,
    );
    expect(screen.getByTestId("assistant-prompt-active-folder-badge").textContent).toContain(
      "Audit DORA 2026",
    );
    expect(screen.getByTestId("assistant-prompt-active-folder-note-indicator").textContent).toContain(
      "Note active prise en compte",
    );
    fireEvent.click(screen.getByTestId("assistant-open-governance-btn"));
    expect(
      (screen.getByTestId("assistant-user-instructions-input") as HTMLTextAreaElement).value,
    ).toContain("Toujours structurer avec des exemples concrets.");
  });

  it("dynamically verifies that clicking 'Lancer le test & Découvrir' and 'Activer le service' in CatalogFeaturePanel updates the DOM", async () => {
    render(
      <I18nProvider initialLocale="fr">
        <ShellContainer>
          <CatalogFeaturePanel />
        </ShellContainer>
      </I18nProvider>,
    );

    const testBenchBtn = screen.getByTestId("run-test-bench-btn");
    fireEvent.click(testBenchBtn);

    await waitFor(() => {
      expect(screen.getByTestId("catalog-action-feedback-banner").textContent).toContain(
        "Banc de test exécuté avec succès",
      );
    });

    const activateBtn = screen.getByTestId("activate-remote-service-btn");
    expect((activateBtn as HTMLButtonElement).disabled).toBe(false);
    fireEvent.click(activateBtn);

    await waitFor(() => {
      expect(screen.getByTestId("catalog-action-feedback-banner").textContent).toContain(
        "Connecteur externe activé",
      );
    });
  });

  it("dynamically verifies that clicking 'Promouvoir vers le Pack' and 'Générer et rattacher la fiche d'aide' in GatesFeaturePanel updates the DOM", async () => {
    render(
      <I18nProvider initialLocale="fr">
        <ShellContainer>
          <GatesFeaturePanel />
        </ShellContainer>
      </I18nProvider>,
    );

    const promoteBtn = screen.getByTestId("process4-promote-btn");
    fireEvent.click(promoteBtn);

    await waitFor(() => {
      expect(screen.getByTestId("gates-action-feedback-banner").textContent).toContain(
        "Composant promu",
      );
    });

    const generateHelpBtn = screen.getByTestId("generate-and-attach-help-btn");
    expect((generateHelpBtn as HTMLButtonElement).disabled).toBe(false);
    fireEvent.click(generateHelpBtn);

    await waitFor(() => {
      expect(screen.getByTestId("gates-action-feedback-banner").textContent).toContain(
        "Fiche d'aide",
      );
    });
  });

  it("dynamically verifies that clicking 'Générer le contrôle automatique' in WorkspacesFeaturePanel compiles a rule and updates the DOM", async () => {
    render(
      <I18nProvider initialLocale="fr">
        <ShellContainer>
          <WorkspacesFeaturePanel />
        </ShellContainer>
      </I18nProvider>,
    );

    const compileBtn = screen.getByTestId("compile-starlark-btn");
    fireEvent.click(compileBtn);

    await waitFor(() => {
      expect(screen.getByTestId("workspaces-action-feedback-banner").textContent).toContain(
        "Contrôle automatique généré",
      );
      expect(screen.getByTestId("starlark-compiler-panel")).toBeDefined();
    });
  });
});
