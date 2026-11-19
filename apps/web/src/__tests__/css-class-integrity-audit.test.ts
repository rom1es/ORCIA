import fs from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";
import { orciaTailwindV4Plugin } from "../../viteTailwindV4Plugin";

const REPO_ROOT = path.resolve(__dirname, "../../../..");
const WEB_DIR = path.join(REPO_ROOT, "apps/web");
const WEB_SRC_DIR = path.join(WEB_DIR, "src");
const UI_SRC_DIR = path.join(REPO_ROOT, "packages/ui/src");
const TOKENS_CSS_PATH = path.join(UI_SRC_DIR, "styles/tokens.css");

function collectTsFiles(dir: string): string[] {
  if (!fs.existsSync(dir)) return [];
  const results: string[] = [];
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    if (
      entry.name === "node_modules" ||
      entry.name === "dist" ||
      entry.name === "__tests__" ||
      entry.name === "generated"
    ) {
      continue;
    }
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      results.push(...collectTsFiles(full));
    } else if (
      entry.isFile() &&
      !entry.name.includes(".test.") &&
      (entry.name.endsWith(".ts") || entry.name.endsWith(".tsx"))
    ) {
      results.push(full);
    }
  }
  return results;
}

describe("CI Guardrail — Tailwind v4 Plugin Compilation, Direction C Tokens & Hex Isolation", () => {
  it("activates orciaTailwindV4Plugin in vite.config.ts and compiles active utility classes", async () => {
    const viteConfig = fs.readFileSync(path.join(WEB_DIR, "vite.config.ts"), "utf8");
    expect(viteConfig).toContain("orciaTailwindV4Plugin");
    expect(viteConfig).toContain("orciaTailwindV4Plugin()");

    const plugin = orciaTailwindV4Plugin();
    const loadHook = plugin.load as (id: string) => Promise<string | null>;
    const compiledCss = await loadHook("\0virtual:orcia-tailwind.css");

    expect(compiledCss).not.toBeNull();
    expect(compiledCss).toContain(".z-50");
    expect(compiledCss).toContain(".pl-5");
    expect(compiledCss).toContain(".grid-cols-1");
    expect(compiledCss).toContain(".w-\\[680px\\]");
    expect(compiledCss).toContain(".max-h-\\[480px\\]");
  });

  it("compiles critical arbitrary Tailwind v4 sizing & layout classes (.z-50, .h-[580px], .max-w-[820px], .pl-5, .grid-cols-1)", async () => {
    const tailwindRoot = path.join(WEB_DIR, "node_modules/tailwindcss");
    const { compile } = (await import(path.join(tailwindRoot, "dist/lib.mjs"))) as {
      compile: (
        css: string,
        opts: {
          loadStylesheet: (
            id: string,
            base: string,
          ) => Promise<{ path: string; base: string; content: string }>;
        },
      ) => Promise<{ build: (candidates: string[]) => string }>;
    };

    const compiler = await compile('@import "tailwindcss/theme";\n@import "tailwindcss/utilities";', {
      loadStylesheet: async (id: string, base: string) => {
        const resolved =
          id === "tailwindcss/theme"
            ? path.join(tailwindRoot, "theme.css")
            : id === "tailwindcss/utilities"
              ? path.join(tailwindRoot, "utilities.css")
              : path.resolve(base, id);
        return {
          path: resolved,
          base: path.dirname(resolved),
          content: fs.readFileSync(resolved, "utf8"),
        };
      },
    });

    const css = compiler.build(["z-50", "h-[580px]", "max-w-[820px]", "pl-5", "grid-cols-1"]);
    expect(css).toContain(".z-50");
    expect(css).toContain(".h-\\[580px\\]");
    expect(css).toContain(".max-w-\\[820px\\]");
    expect(css).toContain(".pl-5");
    expect(css).toContain(".grid-cols-1");
  });

  it("defines Direction C stacking tokens (--z-overlay, --z-dialog) in tokens.css and keeps #hex colors + #6D28D9 strictly isolated", () => {
    const tokensCss = fs.readFileSync(TOKENS_CSS_PATH, "utf8");
    expect(tokensCss).toContain("--z-overlay:");
    expect(tokensCss).toContain("--z-dialog:");
    expect(tokensCss).toContain("--z-popover:");
    expect(tokensCss).toContain("--z-tooltip:");
    expect(tokensCss).toContain("--color-human-led-violet: #6D28D9;");

    const hexRegex = /#[0-9a-fA-F]{3,8}\b/;
    const hexViolations: string[] = [];
    const violetViolations: string[] = [];

    for (const filePath of [...collectTsFiles(WEB_SRC_DIR), ...collectTsFiles(UI_SRC_DIR)]) {
      const content = fs.readFileSync(filePath, "utf8");
      const rel = path.relative(REPO_ROOT, filePath);
      if (hexRegex.test(content)) {
        hexViolations.push(rel);
      }
      if (
        content.includes("--color-human-led-violet") &&
        path.basename(filePath) !== "HumanLedAnchorCard.tsx"
      ) {
        violetViolations.push(rel);
      }
    }

    expect(hexViolations).toEqual([]);
    expect(violetViolations).toEqual([]);
  });
});
