import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const srcDir = path.resolve(scriptDir, "../src");
const featuresDir = path.join(srcDir, "features");

const FEATURE_DOMAINS = [
  "cockpit",
  "inbox",
  "catalog",
  "ontology",
  "gates",
  "finops",
  "admin",
  "workspaces",
];

function walkTsFiles(dir) {
  if (!fs.existsSync(dir)) return [];
  const entries = fs.readdirSync(dir, { withFileTypes: true });
  const files = [];
  for (const entry of entries) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      files.push(...walkTsFiles(full));
    } else if (entry.isFile() && /\.(ts|tsx)$/.test(entry.name)) {
      files.push(full);
    }
  }
  return files;
}

export function validateWebFeatureBoundaries(baseFeaturesDir = featuresDir) {
  const violations = [];
  for (const domain of FEATURE_DOMAINS) {
    const domainDir = path.join(baseFeaturesDir, domain);
    if (!fs.existsSync(domainDir)) {
      violations.push(`Missing required feature directory: features/${domain}`);
      continue;
    }
    const files = walkTsFiles(domainDir);
    for (const filePath of files) {
      const content = fs.readFileSync(filePath, "utf8");
      for (const otherDomain of FEATURE_DOMAINS) {
        if (otherDomain === domain) continue;
        const relPattern = new RegExp(`from\\s+["'](?:\\.\\./)+${otherDomain}(?:/|["'])`);
        const aliasPattern = new RegExp(`from\\s+["']@/features/${otherDomain}(?:/|["'])`);
        if (relPattern.test(content) || aliasPattern.test(content)) {
          violations.push(
            `Forbidden cross-feature import from features/${domain} to features/${otherDomain} in ${path.relative(srcDir, filePath)}`,
          );
        }
      }
      if (/from\s+["']next(\/|["'])/.test(content)) {
        violations.push(`Forbidden next/* import in ${path.relative(srcDir, filePath)}`);
      }
    }
  }
  return violations;
}

if (import.meta.url === `file://${process.argv[1]}`) {
  const violations = validateWebFeatureBoundaries();
  if (violations.length > 0) {
    for (const v of violations) {
      console.error(`✖ ${v}`);
    }
    process.exit(1);
  }
}
