import { readdirSync, readFileSync, statSync } from "node:fs";
import { join, relative } from "node:path";
import { describe, expect, it } from "vitest";
import { isJsdomRuntime } from "../lib/runtimeEnv";

const SRC_ROOT = join(__dirname, "..");
const HELPER = join("lib", "runtimeEnv.ts");

function listSources(dir: string): string[] {
  return readdirSync(dir).flatMap((name) => {
    const full = join(dir, name);
    if (name === "__tests__" || name === "generated") return [];
    return statSync(full).isDirectory()
      ? listSources(full)
      : /\.(ts|tsx)$/.test(name)
        ? [full]
        : [];
  });
}

describe("garde jsdom centralisée (TEST-03)", () => {
  it("n'est vraie que sous jsdom (Vitest)", () => {
    expect(isJsdomRuntime()).toBe(true);
  });

  it("aucune détection jsdom inline en dehors de lib/runtimeEnv.ts", () => {
    const offenders = listSources(SRC_ROOT)
      .filter((file) => relative(SRC_ROOT, file) !== HELPER)
      .filter((file) => /\/jsdom\/i\.test\(/.test(readFileSync(file, "utf8")))
      .map((file) => relative(SRC_ROOT, file));
    expect(offenders).toEqual([]);
  });
});
