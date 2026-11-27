---
date: 2026-11-27
story: 2026-11-27-e2e-campaign-debris-cleanup
domain: Repository Hygiene / E2E Campaign Artifacts / Test Governance (hygiene)
summary: Purge 346 superseded E2E campaign screenshots/manifests/JSON dumps (~54 MB), fix e2eCaptureFixture default capture leak via pure helper, retire 4 closed-epic 21-24 traceability test files, and add binary-purge hygiene guard.
status: done
route: direct
baseline_commit: b554586
review_loop_iteration: 0
---

# 2026-11-27 — E2E Campaign Binary/JSON Purge, `e2eCaptureFixture.ts` Leak Fix & Closed Epics 21–24 Handoff Retirement

- **Date**: 2026-11-27
- **Story / Sprint Key**: `2026-11-27-e2e-campaign-debris-cleanup` (`Epic 13` / `Lot B / Option 2 Hygiene`)
- **Capability(ies)**: `none (hygiene)` — classification: `hygiene`
- **Author / Context**: Repository hygiene task following Epics 21–24 closure. Purges superseded E2E campaign PNGs, `manifest.jsonl` logs, and obsolete `playwright-results.json` dumps while preserving all audit/synthesis Markdown reports and the sole live `e2e-campaign-epic-24/playwright-results.json` read by `uj_e2e_coverage.py`; eliminates the default `e2eCaptureFixture.ts` write leak into `docs/implementation-artifacts/`; and retires the 4 obsolete closed-epic 21–24 traceability test files in favor of live governance gates and a compact binary-purge hygiene test.

---

## 1. Needs Analysis & Tech Lead Impact Study (Pre-Implementation)

### 1.1 Context & Problem Statement
- Four closed E2E campaign folders under `docs/implementation-artifacts/e2e-campaign-epic-2{1,2,3,4}` accumulate **~54.7 MB** of tracked binary PNG screenshots (`339` files), `manifest.jsonl` files (`4`), and superseded `playwright-results.json` dumps (`3` in epics 21–23):
  - `e2e-campaign-epic-21`: `23M` (`110` PNGs, `manifest.jsonl`, `playwright-results.json`, `4` `.md` reports)
  - `e2e-campaign-epic-22`: `7.7M` (`110` PNGs, `manifest.jsonl`, `playwright-results.json`, `4` `.md` reports)
  - `e2e-campaign-epic-23`: `11M` (`58` PNGs, `manifest.jsonl`, `playwright-results.json`, `4` `.md` reports)
  - `e2e-campaign-epic-24`: `13M` (`61` PNGs, `manifest.jsonl`, `playwright-results.json` [live], `4` `.md` reports)
- `apps/web/e2e/support/e2eCaptureFixture.ts` defaults `ORCIA_E2E_CAMPAIGN_DIR` to `docs/implementation-artifacts/e2e-campaign-epic-22`, causing any local/CI Playwright run without `ORCIA_E2E_CAMPAIGN_DIR` to pollute tracked documentation artifacts.
- Four closed-epic handoff test files (`test_epic21_to_epic22_traceability.py`, `test_epic22_to_epic23_traceability.py`, `test_epic23_to_epic24_traceability.py`, `_epic23_to_epic24_constants.py`) test zero production code and duplicate live governance already enforced by `test_capabilities_registry.py`, `infra/scripts/uj_e2e_coverage.py`, `scripts/generate_tlr_index.py --check`, and `scripts/check_implementation_docs.py`.

### 1.2 Consumer Audit & Impact Analysis
- **`e2e-campaign-epic-2[1-4]` references**:
  - `infra/scripts/uj_e2e_coverage.py`: reads only `docs/implementation-artifacts/e2e-campaign-epic-24/playwright-results.json` (preserved).
  - `apps/web/e2e/support/e2eCaptureFixture.ts`: hardcoded fallback `docs/implementation-artifacts/e2e-campaign-epic-22` (remediated).
  - `tests/unit/{_epic23_to_epic24_constants,test_epic21_to_epic22_traceability,test_epic22_to_epic23_traceability,test_epic23_to_epic24_traceability}.py`: retired in this lot.
  - `scripts/tlr_index_legacy.json`: historical summary strings only (no runtime/I/O dependency).
- **Traceability test references**: `0` references in `docs/product/capabilities.yaml`, `scripts/`, `.github/`, or `tests/README.md`; `scripts/lint_tests_ratchet.json` already has `redundancy_audit_exempt_files: []`.
- **`apps/web/dist`**: confirmed untracked (`git ls-files apps/web/dist` empty).
- **`.gitignore`**: root `.gitignore:25` already ignores `test-results/`, covering the new default `apps/web/test-results/e2e-captures`.

### 1.3 Acceptance Criteria
1. `apps/web/e2e/support/e2eCampaignDir.ts` exports pure `resolveE2eCampaignDir(repoRoot, rawEnvDir?)` with zero `@playwright/test` imports, defaulting to `apps/web/test-results/e2e-captures` and honoring relative/absolute `ORCIA_E2E_CAMPAIGN_DIR` overrides; wired into `e2eCaptureFixture.ts` and covered by a Vitest unit test in `apps/web/src/__tests__/`.
2. `screenshots/` and `manifest.jsonl` are purged across `e2e-campaign-epic-21..24`, and `playwright-results.json` is purged across `e2e-campaign-epic-21..23`, while preserving all `16` audit/synthesis `.md` reports and `e2e-campaign-epic-24/playwright-results.json`.
3. The 4 closed-epic handoff test files are deleted without modifying `scripts/lint_tests.py` or `scripts/lint_tests_ratchet.json`, and `tests/unit/tooling/test_e2e_campaign_artifacts_hygiene.py` (`<= 80` L) guards against re-introduction.
4. `site:sync && site:check`, `check_implementation_docs.py`, targeted `pytest`, `@orcia/web` Vitest + `tsc`, `agent_check.py impact`, and post-commit `lint_tests.py` + `agent_check.py static` all pass cleanly.

---

## 2. Implementation Plan

1. Extract `apps/web/e2e/support/e2eCampaignDir.ts` (`resolveE2eCampaignDir`), wire `apps/web/e2e/support/e2eCaptureFixture.ts`, and add `apps/web/src/__tests__/e2e-campaign-dir.test.ts` (Vitest).
2. Remove `screenshots/`, `manifest.jsonl` across `e2e-campaign-epic-21..24` and `playwright-results.json` across `e2e-campaign-epic-21..23`.
3. Delete the 4 retired closed-epic traceability files in `tests/unit/` and add `tests/unit/tooling/test_e2e_campaign_artifacts_hygiene.py`.
4. Sync generated docs (`pnpm site:sync`, `generate_test_fixture_index.py` if needed), record before/after metrics in §3 (`status: done`), run pre-commit checks, commit in a single commit, and verify post-commit strict `lint_tests.py` and `agent_check.py static` on `HEAD`.

---

## 3. Summary of Changes, Footprint Metrics & Verification

### 3.1 Disk Footprint & Deleted File Counts

| Folder | Before (`du -sh`) | After (`du -sh`) | Deleted Files | Preserved Files |
| :--- | ---: | ---: | :--- | :--- |
| `docs/implementation-artifacts/e2e-campaign-epic-21` | `23M` | `236K` | `110` PNGs (`screenshots/`), `1` `manifest.jsonl`, `1` `playwright-results.json` (`112` total) | `4` audit/synthesis `.md` |
| `docs/implementation-artifacts/e2e-campaign-epic-22` | `7.7M` | `196K` | `110` PNGs (`screenshots/`), `1` `manifest.jsonl`, `1` `playwright-results.json` (`112` total) | `4` audit/synthesis `.md` |
| `docs/implementation-artifacts/e2e-campaign-epic-23` | `11M` | `156K` | `58` PNGs (`screenshots/`), `1` `manifest.jsonl`, `1` `playwright-results.json` (`60` total) | `4` audit/synthesis `.md` |
| `docs/implementation-artifacts/e2e-campaign-epic-24` | `13M` | `200K` | `61` PNGs (`screenshots/`), `1` `manifest.jsonl` (`62` total) | `4` `.md` + `playwright-results.json` (live `uj_e2e_coverage.py` input) |
| **Total Campaign Artifacts** | **~54.7M** | **788K** | **346 files** (`339` PNGs + `4` `manifest.jsonl` + `3` `playwright-results.json`) | **17 files** (`16` `.md` + `1` `playwright-results.json`) |

- **Retired Closed-Epic Traceability Test Files Deleted (`4` files)**:
  - `tests/unit/test_epic21_to_epic22_traceability.py`
  - `tests/unit/test_epic22_to_epic23_traceability.py`
  - `tests/unit/test_epic23_to_epic24_traceability.py`
  - `tests/unit/_epic23_to_epic24_constants.py`
- **Created / Updated Code & Guard Files**:
  - `apps/web/e2e/support/e2eCampaignDir.ts` (`11` L, pure helper, zero `@playwright/test` imports)
  - `apps/web/e2e/support/e2eCaptureFixture.ts` (wired to `resolveE2eCampaignDir(...)`)
  - `apps/web/src/__tests__/e2e-campaign-dir.test.ts` (`30` L, Vitest coverage for default + relative/absolute overrides)
  - `tests/unit/tooling/test_e2e_campaign_artifacts_hygiene.py` (`38` L, binary-purge & live JSON guard)
  - `scripts/lint_tests.py` and `scripts/lint_tests_ratchet.json` untouched (`redundancy_audit_exempt_files: []`).

### 3.2 Verification Evidence
- `.venv/bin/python scripts/generate_test_fixture_index.py` → `tests/README.md` unchanged (`0` diff).
- `.venv/bin/pytest -q --no-cov tests/unit/test_uj_e2e_coverage_gate.py tests/unit/tooling/test_e2e_campaign_artifacts_hygiene.py tests/unit/test_capabilities_registry.py` → `24 passed`.
- `pnpm --filter @orcia/web test` → `103` test files passed, `375` tests passed (including `e2e-campaign-dir.test.ts`).
- `pnpm --filter @orcia/web exec tsc --noEmit --target ES2022 --module ESNext --moduleResolution Bundler --skipLibCheck e2e/support/e2eCaptureFixture.ts e2e/support/e2eCampaignDir.ts` & `pnpm --filter @orcia/web typecheck` → `PASS`.
- Pre-commit & post-commit `site:sync && site:check`, `check_implementation_docs.py`, `agent_check.py impact`, `lint_tests.py`, and `agent_check.py static` executed cleanly on closure.
