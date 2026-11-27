import { fireEvent, screen, waitFor } from "@testing-library/react";
import fs from "node:fs";
import path from "node:path";
import { beforeEach, describe, expect, it } from "vitest";
import { resolveModuleFromPathname } from "../components/ShellContainer";
import { buildCockpitWorkflowPreviewGraph } from "../features/cockpit";
import { createOrciaQueryClient } from "../router";
import { preloadModuleQueryData, validateOrciaRouteSearch } from "../routes/searchSchema";
import { simulateUnauthenticatedBrowser } from "../stores/authSessionStore";
import {
  extractOpeningTags,
  renderOrciaRoute,
  resetShellTestState,
  walkTsFiles,
} from "./setup/shellTestHelpers";
import { seedVitestPlatformSetupState } from "./vitest.setup";

describe("@orcia/web static boundaries, route resolution, and RGAA inputs", () => {
  beforeEach(() => {
    resetShellTestState();
  });

  it("enforces feature-sliced boundary isolation across all 8 features/<domaine>/ modules (M11, AD-19)", () => {
    const featuresDir = path.resolve(__dirname, "../features");
    const domains = ["cockpit", "inbox", "catalog", "ontology", "gates", "finops", "admin", "workspaces"];
    for (const domain of domains) {
      const domainDir = path.join(featuresDir, domain);
      expect(fs.existsSync(domainDir)).toBe(true);
      const files = walkTsFiles(domainDir);
      expect(files.length).toBeGreaterThan(0);
      for (const filePath of files) {
        const content = fs.readFileSync(filePath, "utf-8");
        expect(content).not.toMatch(/from\s+["']next(\/|["'])/);
        expect(content).not.toMatch(/workspaceFixtures/);
        for (const other of domains) {
          if (other === domain) continue;
          expect(new RegExp(`from\\s+["'](?:\\.\\./)+${other}(?:/|["'])`).test(content)).toBe(false);
          expect(new RegExp(`from\\s+["']@/features/${other}(?:/|["'])`).test(content)).toBe(false);
        }
      }
    }
  });

  it("resolves all module routes including /settings and /wizards via resolveModuleFromPathname", () => {
    expect(resolveModuleFromPathname(null)).toBe("cockpit");
    expect(resolveModuleFromPathname("/")).toBe("cockpit");
    expect(resolveModuleFromPathname("/cockpit")).toBe("cockpit");
    expect(resolveModuleFromPathname("/inbox")).toBe("inbox");
    expect(resolveModuleFromPathname("/catalog")).toBe("catalog");
    expect(resolveModuleFromPathname("/ontology")).toBe("ontology");
    expect(resolveModuleFromPathname("/gates")).toBe("gates");
    expect(resolveModuleFromPathname("/finops")).toBe("finops");
    expect(resolveModuleFromPathname("/workspaces")).toBe("admin");
    expect(resolveModuleFromPathname("/admin")).toBe("admin");
    expect(resolveModuleFromPathname("/bootstrap")).toBe("bootstrap");
    expect(resolveModuleFromPathname("/settings")).toBe("bootstrap");
    expect(resolveModuleFromPathname("/wizards")).toBe("bootstrap");
    expect(resolveModuleFromPathname("/assistant")).toBe("inbox");
    expect(resolveModuleFromPathname("/spaces")).toBe("admin");
    expect(resolveModuleFromPathname("/agents")).toBe("catalog");
    expect(resolveModuleFromPathname("/processes")).toBe("gates");
    expect(resolveModuleFromPathname("/help")).toBe("ontology");
    expect(resolveModuleFromPathname("/activity")).toBe("finops");
    expect(resolveModuleFromPathname("/organization")).toBe("admin");
    expect(resolveModuleFromPathname("/unknown-route")).toBe("cockpit");
  });

  it("validates typed URL search params, QueryClient route preloading, and @xyflow/react cockpit graph", async () => {
    expect(validateOrciaRouteSearch({})).toEqual({});
    expect(validateOrciaRouteSearch({ q: "  pay-142  " })).toEqual({ q: "pay-142" });
    expect(validateOrciaRouteSearch({ q: "" })).toEqual({});
    expect(validateOrciaRouteSearch({ q: 123 })).toEqual({});

    const queryClient = createOrciaQueryClient();
    for (const mod of ["cockpit", "inbox", "catalog", "ontology", "gates", "finops", "admin", "bootstrap"] as const) {
      expect(await preloadModuleQueryData(queryClient, mod, false)).toEqual({ moduleKey: mod, fixture: false });
      expect(await preloadModuleQueryData(queryClient, mod, true)).toEqual({ moduleKey: mod, fixture: true });
    }

    const graph = buildCockpitWorkflowPreviewGraph();
    expect(graph.nodes).toHaveLength(5);
    expect(graph.edges).toHaveLength(4);
    expect(graph.nodes.every((n) => typeof n.id === "string" && n.id.length > 0)).toBe(true);
    expect(graph.edges.every((e) => typeof e.source === "string" && typeof e.target === "string")).toBe(true);
  });

  it("enforces anti-LastPass / password-manager attributes on 100% of <form>, <input>, and <textarea> elements across @orcia/ui and apps/web while explicitly preserving /login (BiModeLoginView)", async () => {
    const webSrcDir = path.resolve(__dirname, "..");
    const uiSrcDir = path.resolve(__dirname, "../../../../packages/ui/src");
    const allTsxFiles = [...walkTsFiles(webSrcDir), ...walkTsFiles(uiSrcDir)].filter((f) =>
      f.endsWith(".tsx"),
    );
    let auditedFormsCount = 0;
    let auditedInputsCount = 0;
    let auditedTextareasCount = 0;

    for (const filePath of allTsxFiles) {
      const content = fs.readFileSync(filePath, "utf-8");
      const relPath = path.relative(path.resolve(__dirname, "../../../.."), filePath);
      if (filePath.endsWith("BiModeLoginLocalForm.tsx")) {
        expect(content.includes('type="password"') || content.includes('maskMode="password"')).toBe(true);
        expect(content).toContain('autoComplete="current-password"');
        expect(content).toContain('autoComplete="username"');
        expect(content).toContain('data-allow-password-manager="true"');
        expect(content).not.toContain('data-lpignore="true"');
        continue;
      }

      expect(content.includes('type="password"'), `Forbidden type="password" in ${relPath}`).toBe(false);

      for (const formTag of extractOpeningTags(content, "form")) {
        auditedFormsCount += 1;
        expect(formTag.includes('autoComplete="off"'), `Missing autoComplete="off" on <form> in ${relPath}`).toBe(true);
        expect(formTag.includes('data-lpignore="true"'), `Missing data-lpignore on <form> in ${relPath}`).toBe(true);
        expect(formTag.includes('data-form-type="other"'), `Missing data-form-type on <form> in ${relPath}`).toBe(true);
      }

      for (const inputTag of extractOpeningTags(content, "input")) {
        if (inputTag.includes("{...loginProps}")) continue;
        auditedInputsCount += 1;
        expect(inputTag.includes('autoComplete="off"'), `Missing autoComplete="off" in ${relPath}: ${inputTag}`).toBe(true);
        expect(inputTag.includes('data-lpignore="true"'), `Missing data-lpignore in ${relPath}: ${inputTag}`).toBe(true);
        expect(inputTag.includes('data-1p-ignore="true"'), `Missing data-1p-ignore in ${relPath}: ${inputTag}`).toBe(true);
        expect(inputTag.includes('data-bwignore="true"'), `Missing data-bwignore in ${relPath}: ${inputTag}`).toBe(true);
        expect(inputTag.includes('data-form-type="other"'), `Missing data-form-type in ${relPath}: ${inputTag}`).toBe(true);
      }

      for (const taTag of extractOpeningTags(content, "textarea")) {
        if (taTag.includes("{...loginProps}")) continue;
        auditedTextareasCount += 1;
        expect(taTag.includes('autoComplete="off"'), `Missing autoComplete="off" in ${relPath}: ${taTag}`).toBe(true);
        expect(taTag.includes('data-lpignore="true"'), `Missing data-lpignore in ${relPath}: ${taTag}`).toBe(true);
        expect(taTag.includes('data-1p-ignore="true"'), `Missing data-1p-ignore in ${relPath}: ${taTag}`).toBe(true);
        expect(taTag.includes('data-bwignore="true"'), `Missing data-bwignore in ${relPath}: ${taTag}`).toBe(true);
        expect(taTag.includes('data-form-type="other"'), `Missing data-form-type in ${relPath}: ${taTag}`).toBe(true);
      }
    }
    expect(auditedFormsCount).toBeGreaterThanOrEqual(1);
    expect(auditedInputsCount).toBeGreaterThanOrEqual(1);
    expect(auditedTextareasCount).toBeGreaterThanOrEqual(1);

    const { unmount } = await renderOrciaRoute("/settings");
    fireEvent.click(screen.getByTestId("settings-tab-models"));
    const primaryModelInput = screen.getByTestId("llm-primary-model-input") as HTMLInputElement;
    const apiKeyInput = screen.getByTestId("llm-api-key-input") as HTMLInputElement;
    expect(primaryModelInput.getAttribute("data-lpignore")).toBe("true");
    expect(primaryModelInput.getAttribute("data-1p-ignore")).toBe("true");
    expect(primaryModelInput.getAttribute("data-bwignore")).toBe("true");
    expect(primaryModelInput.getAttribute("data-form-type")).toBe("other");
    expect(primaryModelInput.getAttribute("autocomplete")).toBe("off");
    expect(apiKeyInput.getAttribute("type")).toBe("text");
    expect(apiKeyInput.getAttribute("data-lpignore")).toBe("true");
    expect(apiKeyInput.getAttribute("data-1p-ignore")).toBe("true");
    expect(apiKeyInput.getAttribute("data-bwignore")).toBe("true");
    expect(apiKeyInput.getAttribute("data-form-type")).toBe("other");
    expect(apiKeyInput.getAttribute("autocomplete")).toBe("off");
    expect(apiKeyInput.className).toContain("orcia-masked-secret-input");

    fireEvent.change(screen.getByTestId("llm-family-input"), { target: { value: "family-a" } });
    fireEvent.change(primaryModelInput, { target: { value: "mistral-small-latest" } });
    fireEvent.change(apiKeyInput, { target: { value: "sk-test-12345" } });
    fireEvent.click(screen.getByTestId("save-llm-tier-btn"));
    await waitFor(() => {
      const rows = document.querySelectorAll('[data-testid^="llm-tier-row-"][data-tier="medium"]');
      expect(rows.length).toBeGreaterThan(0);
      expect(rows[0]!.textContent).toContain("Fournisseur principal");
      expect(rows[0]!.textContent).toContain("mistral-small-latest");
      expect(rows[0]!.textContent).not.toContain("family-a");
    });
    unmount();

    simulateUnauthenticatedBrowser();
    seedVitestPlatformSetupState({}, { email: "admin@orcia.fr", displayName: "Admin ORCIA" });
    await renderOrciaRoute("/login");
    expect(screen.getByTestId("login-page-container").getAttribute("data-allow-password-manager")).toBe("true");
    expect(screen.queryByTestId("login-local-accordion-toggle")).toBeNull();
    const loginEmailInput = await screen.findByTestId("login-local-email");
    const loginPasswordInput = await screen.findByTestId("login-local-password");
    expect(loginEmailInput.getAttribute("autocomplete")).toBe("username");
    expect(loginEmailInput.getAttribute("data-lpignore")).toBeNull();
    expect(loginPasswordInput.getAttribute("type")).toBe("password");
    expect(loginPasswordInput.getAttribute("autocomplete")).toBe("current-password");
    expect(loginPasswordInput.getAttribute("data-lpignore")).toBeNull();
    expect(loginPasswordInput.getAttribute("data-1p-ignore")).toBeNull();
    expect(loginPasswordInput.getAttribute("data-bwignore")).toBeNull();
    expect(screen.getByTestId("login-local-submit")).toBeDefined();
  });
});
