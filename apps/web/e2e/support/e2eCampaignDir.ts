import path from "node:path";

export const DEFAULT_E2E_CAMPAIGN_REL_DIR = "apps/web/test-results/e2e-captures";

export function resolveE2eCampaignDir(repoRoot: string, rawEnvDir?: string): string {
  const trimmed = rawEnvDir?.trim();
  if (trimmed) {
    return path.isAbsolute(trimmed) ? trimmed : path.resolve(repoRoot, trimmed);
  }
  return path.join(repoRoot, DEFAULT_E2E_CAMPAIGN_REL_DIR);
}
