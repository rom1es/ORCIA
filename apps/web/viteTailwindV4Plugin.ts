import fs from "node:fs";
import path from "node:path";
import type { Plugin, ViteDevServer } from "vite";

const VIRTUAL_MODULE_ID = "virtual:orcia-tailwind.css";
const RESOLVED_VIRTUAL_MODULE_ID = `\0${VIRTUAL_MODULE_ID}`;

const TAILWIND_INPUT_CSS = `
@import "tailwindcss/theme" reference;
@theme inline reference {
  --color-surface: var(--color-surface);
  --color-surface-card: var(--color-surface-card);
  --color-surface-elevated: var(--color-surface-elevated);
  --color-surface-hover: var(--color-surface-hover);
  --color-surface-primary: var(--color-surface-primary);
  --color-surface-secondary: var(--color-surface-secondary);
  --color-surface-border: var(--color-surface-border);
  --color-text-primary: var(--color-text-primary);
  --color-text-secondary: var(--color-text-secondary);
  --color-action-primary: var(--color-action-primary);
  --color-brand-primary: var(--color-brand-primary);
  --color-primary: var(--color-primary-cobalt);
  --color-status-success: var(--color-status-success);
  --color-status-warning: var(--color-status-warning);
  --color-status-danger: var(--color-status-danger);
  --color-status-error: var(--color-status-error);
}
@import "tailwindcss/utilities";
`;

function collectSourceFiles(dir: string, acc: string[]): void {
  if (!fs.existsSync(dir)) return;
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    if (
      entry.name === "node_modules" ||
      entry.name === "__tests__" ||
      entry.name === "dist" ||
      entry.name === "e2e"
    ) {
      continue;
    }
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      collectSourceFiles(full, acc);
    } else if (entry.isFile() && /\.(ts|tsx)$/.test(entry.name)) {
      acc.push(full);
    }
  }
}

function extractCandidateTokens(content: string): string[] {
  const tokens: string[] = [];
  const regex = /[A-Za-z0-9_:\-./\[\]()!%]+/g;
  let match: RegExpExecArray | null = regex.exec(content);
  while (match !== null) {
    tokens.push(match[0]);
    match = regex.exec(content);
  }
  return tokens;
}

export function orciaTailwindV4Plugin(): Plugin {
  const webRoot = __dirname;
  const repoRoot = path.resolve(webRoot, "../..");
  const scanDirs = [
    path.join(webRoot, "src"),
    path.join(repoRoot, "packages/ui/src"),
  ];
  const tailwindRoot = path.join(webRoot, "node_modules/tailwindcss");

  let devServer: ViteDevServer | null = null;

  async function compileTailwindUtilities(): Promise<string> {
    const libPath = path.join(tailwindRoot, "dist/lib.mjs");
    const { compile } = (await import(libPath)) as {
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

    const compiler = await compile(TAILWIND_INPUT_CSS, {
      loadStylesheet: async (id: string, base: string) => {
        let resolvedPath: string;
        if (id === "tailwindcss/theme") {
          resolvedPath = path.join(tailwindRoot, "theme.css");
        } else if (id === "tailwindcss/utilities") {
          resolvedPath = path.join(tailwindRoot, "utilities.css");
        } else if (id === "tailwindcss/preflight") {
          resolvedPath = path.join(tailwindRoot, "preflight.css");
        } else if (id === "tailwindcss") {
          resolvedPath = path.join(tailwindRoot, "index.css");
        } else {
          resolvedPath = path.resolve(base, id);
        }
        return {
          path: resolvedPath,
          base: path.dirname(resolvedPath),
          content: fs.readFileSync(resolvedPath, "utf8"),
        };
      },
    });

    const files: string[] = [];
    for (const dir of scanDirs) {
      collectSourceFiles(dir, files);
    }

    const candidateSet = new Set<string>();
    for (const file of files) {
      const content = fs.readFileSync(file, "utf8");
      for (const token of extractCandidateTokens(content)) {
        candidateSet.add(token);
      }
    }

    return compiler.build(Array.from(candidateSet));
  }

  return {
    name: "orcia-tailwind-v4-plugin",
    enforce: "pre",
    configureServer(server) {
      devServer = server;
    },
    resolveId(id) {
      if (id === VIRTUAL_MODULE_ID) {
        return RESOLVED_VIRTUAL_MODULE_ID;
      }
      return null;
    },
    async load(id) {
      if (id === RESOLVED_VIRTUAL_MODULE_ID) {
        return compileTailwindUtilities();
      }
      return null;
    },
    handleHotUpdate(ctx) {
      if (
        devServer &&
        /\.(ts|tsx)$/.test(ctx.file) &&
        scanDirs.some((dir) => ctx.file.startsWith(dir))
      ) {
        const mod = devServer.moduleGraph.getModuleById(RESOLVED_VIRTUAL_MODULE_ID);
        if (mod) {
          devServer.moduleGraph.invalidateModule(mod);
        }
      }
    },
  };
}
