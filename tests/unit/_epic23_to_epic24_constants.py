"""Constants and path mappings for `test_epic23_to_epic24_traceability.py`."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
CAMPAIGN_23_DIR = REPO_ROOT / "docs" / "implementation-artifacts" / "e2e-campaign-epic-23"
MASTER_PLAN_PATH = (
    REPO_ROOT
    / "docs"
    / "planning-artifacts"
    / "sprint-change-proposal-2026-11-20-epic-24-remediation-plan.md"
)
REPORTS_DIR = REPO_ROOT / "docs" / "implementation-artifacts" / "tech-lead-reports"
REPORTS_INDEX_PATH = REPORTS_DIR / "README.md"
CAPABILITIES_PATH = REPO_ROOT / "docs" / "product" / "capabilities.yaml"
SPRINT_STATUS_PATH = REPO_ROOT / "docs" / "implementation-artifacts" / "sprint-status.yaml"
EPICS_PATH = REPO_ROOT / "docs" / "planning-artifacts" / "epics.md"

MAX_PNG_BYTES = 450 * 1024
STORY_23_8_KEY = "23-8-rapports-tech-lead-plan-correction-global-et-initialisation-epic-24"
ACTION_ITEM_23_6_ID = "ACTION_ITEM-23.6"

EPIC_24_KEYS = (
    "24-1-persistance-pg18-actions-jira-staged-mcp-et-vsm-v2",
    "24-2-triggers-uuidv7-sans-collision-waivers-await-adn-pg18-et-fin-default-ws",
    "24-3-banc-mcp-audit-ledger-fin-pass-optimiste-et-assainissement-composition-root",
    "24-4-refonte-css-tailwind-tokens-modales-rgaa-contraste-onglets-et-shell",
    "24-5-identite-accostage-cockpit-sync-navigation-zone4-et-coherence-jour0",
    "24-6-recherche-cmdk-filtre-langue-purge-jargon-packs-et-microcopy",
    "24-7-reconciliation-e2e-captures-jalons-campagne-52-sur-52-et-cloture-epic-24",
)

EXPECTED_FAILING_SCENARIOS: dict[str, tuple[str, ...]] = {
    "#15": ("06-gates-review-and-anti-rubber-stamping.spec.ts", "06"),
    "#16": ("07-spaces-org-and-workspace-persistence.spec.ts", "07"),
    "#40": ("17-workspace-sources-codegraph-dna-and-ontology.spec.ts", "17#3"),
    "#41": ("18-catalog-packs-wizards-and-mcp-bench.spec.ts", "18#1"),
    "#45": ("18-catalog-packs-wizards-and-mcp-bench.spec.ts", "18#5"),
    "#47": ("19-orchestration-whatif-replay-and-gates.spec.ts", "19#2"),
    "#48": ("20-process-studio-v2-finops-and-log-sink.spec.ts", "20#1"),
    "#49": ("20-process-studio-v2-finops-and-log-sink.spec.ts", "20#2"),
}

USER_BUG_TARGETS: dict[str, tuple[str, str]] = {
    "USER24-BUG-1": ("24-4", EPIC_24_KEYS[3]),
    "USER24-BUG-2": ("24-5", EPIC_24_KEYS[4]),
    "USER24-BUG-3": ("24-6", EPIC_24_KEYS[5]),
    "USER24-BUG-4A": ("24-4", EPIC_24_KEYS[3]),
    "USER24-BUG-4B": ("24-4", EPIC_24_KEYS[3]),
    "USER24-BUG-5": ("24-4", EPIC_24_KEYS[3]),
    "USER24-BUG-6": ("24-2", EPIC_24_KEYS[1]),
}

ALLOWED_EPIC_24_STATUSES = frozenset({"backlog", "in-progress", "done"})
ALLOWED_STORY_24_STATUSES = frozenset({"backlog", "ready-for-dev", "in-progress", "review", "done"})
