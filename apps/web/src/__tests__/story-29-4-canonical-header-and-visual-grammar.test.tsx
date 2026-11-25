// @vitest-environment jsdom
import { cleanup, render, screen } from "@testing-library/react";
import fs from "node:fs";
import path from "node:path";
import React from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import * as OrciaUi from "@orcia/ui";
import { I18nProvider } from "../i18n";

vi.mock("../features/ontology", () => ({
  OntologyFeaturePanel: () => <div data-testid="mock-ontology-panel">Ontology body</div>,
}));

vi.mock("../components/navigationAdapter", () => ({
  useOrciaNavigation: () => ({ pathname: "/ontology" }),
}));

vi.mock("../components/ShellContainer", () => ({
  useShellNavigation: () => ({ activeModuleKey: "ontology" }),
}));

import { ModuleWorkspaceView } from "../components/ModuleWorkspaceView";

const REPO_ROOT = path.resolve(__dirname, "../../../..");
const UI_SRC_DIR = path.join(REPO_ROOT, "packages/ui/src");
const STYLES_DIR = path.join(UI_SRC_DIR, "styles");

function readStylesCss(): string {
  return fs
    .readdirSync(STYLES_DIR)
    .filter((name) => name.endsWith(".css"))
    .sort()
    .map((name) => fs.readFileSync(path.join(STYLES_DIR, name), "utf-8"))
    .join("\n");
}

function collectUiTsFiles(dir: string): string[] {
  const out: string[] = [];
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      if (entry.name !== "__tests__" && entry.name !== "node_modules") {
        out.push(...collectUiTsFiles(full));
      }
    } else if (entry.isFile() && /\.(ts|tsx)$/.test(entry.name)) {
      out.push(full);
    }
  }
  return out;
}

describe("Story 29.4 — Canonical header exports, visual grammar CSS tokens & ModuleWorkspaceView h1", () => {
  afterEach(() => {
    cleanup();
  });

  it("exports OrciaPageHeader, OrciaTabStrip, and OrciaDataCard cleanly from @orcia/ui", () => {
    expect(typeof OrciaUi.OrciaPageHeader).toBe("function");
    expect(typeof OrciaUi.OrciaTabStrip).toBe("function");
    expect(typeof OrciaUi.OrciaDataCard).toBe("function");
  });

  it("enforces disabled secondary/ghost button tokens and canonical header/tab/card classes in CSS", () => {
    const componentsCss = fs.readFileSync(path.join(STYLES_DIR, "tokens-components.css"), "utf-8");
    const allCss = readStylesCss();

    expect(componentsCss).toMatch(
      /\.orcia-ds-btn-secondary:disabled,\s*\.orcia-ds-btn-ghost:disabled\s*\{[^}]*opacity:\s*0\.48;[^}]*cursor:\s*not-allowed;[^}]*pointer-events:\s*none;/s,
    );
    expect(allCss).toContain("--orcia-surface-card:");
    expect(allCss).toContain(".orcia-ds-page-header");
    expect(allCss).toContain(".orcia-ds-tab-strip");
    expect(allCss).toContain(".orcia-ds-tab-strip--underline");
    expect(allCss).toContain(".orcia-ds-tab-strip--segmented");
    expect(allCss).toContain(".orcia-ds-data-card");
    expect(allCss).toContain(".orcia-ds-filter-pill");
  });

  it("renders ModuleWorkspaceView module headers via OrciaPageHeader with semantic <h1> instead of <strong>", () => {
    render(
      <I18nProvider initialLocale="en">
        <ModuleWorkspaceView moduleKey="ontology" />
      </I18nProvider>,
    );

    const header = screen.getByTestId("module-header-ontology");
    expect(header.className).toContain("orcia-bento-card");
    expect(header.className).toContain("orcia-ds-page-header");

    const heading = screen.getByRole("heading", { level: 1 });
    expect(heading.textContent).toBe("Shared business glossary and knowledge base");
    expect(header.querySelector("strong")).toBeNull();
    expect(screen.getByTestId("module-uri-badge-ontology").textContent).toBe("Knowledge");
    expect(screen.getByTestId("mock-ontology-panel")).toBeTruthy();
  });

  it("preserves @orcia/ui purity (zero forbidden imports and zero raw hex outside tokens*.css)", () => {
    const uiFiles = collectUiTsFiles(UI_SRC_DIR);
    const hexRe = /#[0-9a-fA-F]{3,8}\b/;
    for (const filePath of uiFiles) {
      const content = fs.readFileSync(filePath, "utf-8");
      const rel = path.relative(REPO_ROOT, filePath);
      expect(content, `Forbidden router import in ${rel}`).not.toMatch(/from\s+["']@tanstack\/react-router/);
      expect(content, `Forbidden api-client import in ${rel}`).not.toMatch(/from\s+["']@orcia\/api-client/);
      expect(hexRe.test(content), `Forbidden raw hex in ${rel}`).toBe(false);
    }
  });
});
