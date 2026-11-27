import path from "node:path";
import { describe, expect, it } from "vitest";
import {
  DEFAULT_E2E_CAMPAIGN_REL_DIR,
  resolveE2eCampaignDir,
} from "../../e2e/support/e2eCampaignDir";

describe("resolveE2eCampaignDir", () => {
  const repoRoot = path.resolve("/workspace/orcia");

  it("defaults outside docs/implementation-artifacts when env var is unset or blank", () => {
    const expected = path.join(repoRoot, DEFAULT_E2E_CAMPAIGN_REL_DIR);
    expect(resolveE2eCampaignDir(repoRoot)).toBe(expected);
    expect(resolveE2eCampaignDir(repoRoot, "")).toBe(expected);
    expect(resolveE2eCampaignDir(repoRoot, "   ")).toBe(expected);
    expect(expected.replace(/\\/g, "/")).not.toContain("docs/implementation-artifacts");
    expect(expected.replace(/\\/g, "/")).toContain("apps/web/test-results/e2e-captures");
  });

  it("resolves relative ORCIA_E2E_CAMPAIGN_DIR overrides against repoRoot", () => {
    expect(resolveE2eCampaignDir(repoRoot, "  custom/e2e-out  ")).toBe(
      path.resolve(repoRoot, "custom/e2e-out"),
    );
  });

  it("preserves absolute ORCIA_E2E_CAMPAIGN_DIR overrides", () => {
    const absDir = path.resolve("/tmp/orcia-e2e-run-42");
    expect(resolveE2eCampaignDir(repoRoot, ` ${absDir} `)).toBe(absDir);
  });
});
