// @vitest-environment jsdom
import {
  OrciaAlertBanner,
  OrciaButton,
  OrciaInput,
  OrciaSectionCard,
  OrciaSelect,
  OrciaTabBar,
  OrciaTextarea,
} from "../../../../packages/ui/src/primitives/DesignSystemControls";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import fs from "node:fs";
import path from "node:path";
import React from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

const REPO_ROOT = path.resolve(__dirname, "../../../..");
const UI_SRC_DIR = path.join(REPO_ROOT, "packages/ui/src");
const WEB_SRC_DIR = path.join(REPO_ROOT, "apps/web/src");
const TOKENS_CSS_PATH = path.join(UI_SRC_DIR, "styles/tokens.css");

function walkCodeFiles(dir: string): string[] {
  const entries = fs.readdirSync(dir, { withFileTypes: true });
  const files: string[] = [];
  for (const entry of entries) {
    const fullPath = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      if (entry.name !== "__tests__" && entry.name !== "node_modules") {
        files.push(...walkCodeFiles(fullPath));
      }
    } else if (entry.isFile() && /\.(ts|tsx|css)$/.test(entry.name)) {
      files.push(fullPath);
    }
  }
  return files;
}

describe("Sally & Winston Audit — 4 Golden Invariants of Look & Feel Separation (@orcia/ui vs apps/web)", () => {
  afterEach(() => {
    cleanup();
  });

  const uiFiles = walkCodeFiles(UI_SRC_DIR);
  const uiTsFiles = uiFiles.filter((f) => /\.(ts|tsx)$/.test(f));
  const webFiles = walkCodeFiles(WEB_SRC_DIR);
  const webTsFiles = webFiles.filter((f) => /\.(ts|tsx)$/.test(f));
  const tokensCssContent = fs.readFileSync(TOKENS_CSS_PATH, "utf-8");

  it("Invariant 1 (Purity of @orcia/ui): packages/ui/src/** never imports routers, API clients, fetch, or apps/web stores", () => {
    for (const filePath of uiTsFiles) {
      const content = fs.readFileSync(filePath, "utf-8");
      const rel = path.relative(REPO_ROOT, filePath);
      expect(
        content,
        `Forbidden @tanstack/* import in ${rel}`,
      ).not.toMatch(/from\s+["']@tanstack\//);
      expect(
        content,
        `Forbidden @orcia/api-client import in ${rel}`,
      ).not.toMatch(/from\s+["']@orcia\/api-client/);
      expect(
        content,
        `Forbidden apps/web import in ${rel}`,
      ).not.toMatch(/apps\/web/);
      expect(
        content,
        `Forbidden network fetch() in ${rel}`,
      ).not.toMatch(/\bfetch\s*\(/);
      expect(
        content,
        `Forbidden platformSetupStore import in ${rel}`,
      ).not.toContain("platformSetupStore");
    }
  });

  it("Invariant 2 (Zero Raw Hex Colors Outside tokens.css): no .ts/.tsx file in packages/ui or apps/web hardcodes hex colors, and --color-human-led-violet is exclusive to HumanLedAnchorCard", () => {
    const hexColorRegex = /#[0-9a-fA-F]{3,8}\b/;
    for (const filePath of [...uiTsFiles, ...webTsFiles]) {
      const content = fs.readFileSync(filePath, "utf-8");
      const rel = path.relative(REPO_ROOT, filePath);
      expect(
        hexColorRegex.test(content),
        `Found forbidden raw hex color in ${rel}`,
      ).toBe(false);

      if (path.basename(filePath) === "HumanLedAnchorCard.tsx") {
        expect(content).toContain("--color-human-led-violet");
      } else {
        expect(
          content,
          `--color-human-led-violet is reserved exclusively for HumanLedAnchorCard.tsx, found in ${rel}`,
        ).not.toContain("--color-human-led-violet");
      }
    }
  });

  it("Invariant 3 (100% Centralized Look & Feel in tokens.css): every var(--*) CSS variable referenced in packages/ui or apps/web is defined in tokens.css, along with all .orcia-ds-* classes", () => {
    const definedVariables = new Set<string>();
    const defRegex = /(--[a-zA-Z0-9_-]+)\s*:/g;
    let defMatch: RegExpExecArray | null;
    while ((defMatch = defRegex.exec(tokensCssContent)) !== null) {
      if (defMatch[1]) {
        definedVariables.add(defMatch[1]);
      }
    }

    const usedVariables = new Set<string>();
    const useRegex = /var\(\s*(--[a-zA-Z0-9_-]+)\s*\)/g;
    for (const filePath of [...uiTsFiles, ...webTsFiles]) {
      const content = fs.readFileSync(filePath, "utf-8");
      let useMatch: RegExpExecArray | null;
      while ((useMatch = useRegex.exec(content)) !== null) {
        if (useMatch[1]) {
          usedVariables.add(useMatch[1]);
        }
      }
    }

    const undefinedVariables = [...usedVariables].filter(
      (v) => !definedVariables.has(v),
    );
    expect(
      undefinedVariables,
      `Found CSS variables used in components but missing from tokens.css: ${undefinedVariables.join(", ")}`,
    ).toEqual([]);

    const requiredDesignSystemClasses = [
      ".orcia-ds-page",
      ".orcia-ds-card",
      ".orcia-ds-header",
      ".orcia-ds-tabs",
      ".orcia-ds-tab",
      ".orcia-ds-label",
      ".orcia-ds-input",
      ".orcia-ds-select",
      ".orcia-ds-textarea",
      ".orcia-ds-btn",
      ".orcia-ds-btn-primary",
      ".orcia-ds-btn-secondary",
      ".orcia-ds-btn-danger",
      ".orcia-ds-btn-ghost",
      ".orcia-ds-row",
      ".orcia-ds-alert",
      ".orcia-ds-alert-success",
      ".orcia-ds-alert-warning",
      ".orcia-ds-alert-error",
      ".orcia-ds-alert-info",
    ];
    for (const cls of requiredDesignSystemClasses) {
      expect(
        tokensCssContent.includes(cls),
        `Missing Design System class ${cls} in packages/ui/src/styles/tokens.css`,
      ).toBe(true);
    }
  });

  it("Invariant 4 (Pure DesignSystemControls Primitives): renders OrciaSectionCard, OrciaTabBar, OrciaButton, OrciaInput, OrciaSelect, OrciaTextarea, and OrciaAlertBanner with .orcia-ds-* classes and anti-LastPass protection", () => {
    const onOpenHelp = vi.fn();
    const onSelectTab = vi.fn();

    render(
      <OrciaSectionCard
        testId="ds-card-demo"
        title="Configuration du Modèle"
        subtitle="Sous-titre piloté par les props"
        helpSectionId="ai-models-overview"
        helpLabel="Aide sur les modèles"
        onOpenHelpSection={onOpenHelp}
        actions={
          <OrciaButton testId="ds-btn-secondary" variant="secondary">
            Action secondaire
          </OrciaButton>
        }
      >
        <OrciaTabBar
          ariaLabel="Navigation de section"
          activeTab="general"
          onSelectTab={onSelectTab}
          tabs={[
            { key: "general", label: "Général", testId: "ds-tab-general" },
            { key: "advanced", label: "Avancé", testId: "ds-tab-advanced" },
          ]}
        />

        <OrciaInput
          testId="ds-input-demo"
          placeholder="Nom du modèle..."
          defaultValue="claude-3-7-sonnet"
        />

        <OrciaSelect testId="ds-select-demo" defaultValue="api_key">
          <option value="api_key">Clé d'API</option>
          <option value="none_local">Serveur local</option>
        </OrciaSelect>

        <OrciaTextarea
          testId="ds-textarea-demo"
          rows={2}
          defaultValue="Instructions"
        />

        <OrciaAlertBanner testId="ds-alert-demo" tone="emerald">
          Connexion vérifiée avec succès.
        </OrciaAlertBanner>

        <OrciaButton testId="ds-btn-primary" variant="primary" type="submit">
          Enregistrer
        </OrciaButton>
      </OrciaSectionCard>,
    );

    const card = screen.getByTestId("ds-card-demo");
    expect(card.className).toContain("orcia-bento-card");
    expect(card.className).toContain("orcia-ds-card");

    const infoBtn = screen.getByTestId(
      "contextual-info-trigger-ai-models-overview",
    );
    fireEvent.click(infoBtn);
    expect(onOpenHelp).toHaveBeenCalledWith("ai-models-overview");

    const advTab = screen.getByTestId("ds-tab-advanced");
    expect(advTab.className).toContain("orcia-ds-tab");
    expect(advTab.getAttribute("aria-selected")).toBe("false");
    fireEvent.click(advTab);
    expect(onSelectTab).toHaveBeenCalledWith("advanced");

    const input = screen.getByTestId("ds-input-demo");
    expect(input.className).toContain("orcia-ds-input");
    expect(input.getAttribute("data-lpignore")).toBe("true");
    expect(input.getAttribute("data-1p-ignore")).toBe("true");
    expect(input.getAttribute("autoComplete")).toBe("off");

    const select = screen.getByTestId("ds-select-demo");
    expect(select.className).toContain("orcia-ds-select");
    expect(select.getAttribute("data-lpignore")).toBe("true");

    const textarea = screen.getByTestId("ds-textarea-demo");
    expect(textarea.className).toContain("orcia-ds-textarea");
    expect(textarea.getAttribute("data-lpignore")).toBe("true");

    const alert = screen.getByTestId("ds-alert-demo");
    expect(alert.className).toContain("orcia-ds-alert-success");
    expect(alert.getAttribute("role")).toBe("status");

    const primaryBtn = screen.getByTestId("ds-btn-primary");
    expect(primaryBtn.className).toContain("orcia-ds-btn-primary");

    const uiBarrelIndex = fs.readFileSync(
      path.join(UI_SRC_DIR, "index.ts"),
      "utf-8",
    );
    for (const exportedSymbol of [
      "OrciaButton",
      "OrciaInput",
      "OrciaSelect",
      "OrciaTextarea",
      "OrciaSectionCard",
      "OrciaTabBar",
      "OrciaAlertBanner",
    ]) {
      expect(uiBarrelIndex).toContain(exportedSymbol);
    }
  });
});
