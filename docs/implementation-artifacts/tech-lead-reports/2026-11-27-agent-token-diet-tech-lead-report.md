---
date: 2026-11-27
story: 2026-11-27-agent-token-diet
domain: Agent Harness / Token Economy / Documentation Governance (hygiene)
summary: Cut per-turn and per-activation agent context (BMAD facts, AGENTS.md, skills, spine, epics, TLR index) by condensing, splitting and auto-generating the files agents load.
status: done
route: dispatch
baseline_commit: bf44884
review_loop_iteration: 0
---

# 2026-11-27 — Agent Token Diet (Rules, Architecture Spine, Epics, TLR Index, BMAD Overrides)

- **Date**: 2026-11-27
- **Story / Sprint Key**: `2026-11-27-agent-token-diet` (`Epic 13` / `Cross-Cutting Adjustment`)
- **Capability(ies)**: `none (hygiene)` — classification: `hygiene`
- **Author / Context**: Follow-up of Epic 32 (token economy). Reduce the context agents load per turn and per BMAD workflow activation without losing any decision text, keeping `lint_spine.py`, `/showcase`, `check_implementation_docs.py` and traceability tests green. Covers `AD-17` (tests for new tooling), `AD-19` boundaries (scripts only, no domain change).
- **Associated Commits**: `06da7ca` (Phase 0), `51f99e0` (Phase 1), `80da0dd` (Phase 2), `db3afb5` (Phase 3), `4e28bbf` (Phase 4), `992b087` (Phase 5), `53f7038` (Phase 6), `0358e36` (Phase 7), `bdc5380` (Phase 8), Phase 9 (this commit)

---

## 1. Needs Analysis & Tech Lead Impact Study (Pre-Implementation)

### 1.1 Context & Problem Statement
- Agent cost is dominated by files injected or read wholesale, not by code:

| Source | Size | ≈ Tokens | When paid |
| :--- | ---: | ---: | :--- |
| `_bmad/custom/config.toml` persistent facts (spine + `capabilities.yaml` + `AGENTS.md` + routing + template) | ~270 KB | **~75k** | Every BMAD workflow activation |
| `docs/planning-artifacts/epics.md` | 710 KB | ~190k | On read (R-ROUTE-01 points orchestrator to it) |
| `ARCHITECTURE-SPINE.md` | 149 KB | ~40k | On read + BMAD facts |
| `architecture.md` (+ FAQ dup §8, testing dup §7) | 102 KB | ~27k | `*architecture*` glob scans |
| `visual-architecture-blueprint.html` | 39 KB | ~10k | `*architecture*` glob scans |
| `tech-lead-reports/README.md` | 290 KB | ~78k | Read to append a row (R-CORE-11) |
| `tech-lead-reports/_i18n-audit-inventory-raw.md` | 1.6 MB | — | Folder scans; counted as a report by help workflow |
| `AGENTS.md` + `bmad-model-routing.md` | 8.5 KB | ~2.3k | Every turn, every agent |
| Skill catalog (≈ 45 descriptions) | — | ~4.5k | Every turn |
| `CLAUDE.md` (Claude Code only) | 9.7 KB | ~2.6k | Every Claude Code turn |
| Stale copies `docs/architecture.md`, `docs/epics.md` | 167 KB | ~45k | If ever read |

- Expected: always-on context ≤ ~4k tokens; BMAD activation facts ≤ ~1k; spine ≤ 25 KB with per-AD detail on demand; TLR index generated and never read by agents; one committed story artifact (Tech Lead Report).
- Spine constraints: `lint_spine.py` (each AD block contains `binds`/`prevents`/`rule`, ascending unique ids, pinned Stack versions) and `parse_architecture_spine` (`### AD-N — Title [ADOPTED]`, `## Stack` Name|Version) must keep passing.

### 1.2 Exploration, GitNexus Impact Analysis, Refactoring & Technical Debt
- **GitNexus Impact Analysis**: this worktree is not indexed; the main checkout index (same `bf44884`, clean tree) is stale (541 symbols) and resolves none of `parse_tech_lead_reports`, `parse_architecture_spine`, `check_docs`, `execute_orcia_documentation_workflow`. Impact established by exhaustive `grep` instead:

| Symbol / File | Consumers | Risk |
| :--- | :--- | :--- |
| `parse_architecture_spine` (`infra/scripts/_site_repo_parsers.py`) | `sync_site_catalog.py` → `apps/web/src/generated/orciaSiteManifest.ts`, `docs/site-catalog/index.html`; `test_site_catalog_sync.py` | MEDIUM — AD titles shown in `/showcase` change (regenerated, format kept) |
| `parse_tech_lead_reports` | `sync_site_catalog.py`; `orcia-showcase-site.test.tsx` (one report id) | MEDIUM — row format contract kept |
| `check_docs` (`scripts/check_implementation_docs.py`) | pre-commit hook; `agent_check_lib/bounce.py` closure checks | MEDIUM — index check becomes 0-diff vs generator |
| `tech-lead-reports/README.md` | 3 traceability tests (`filename in index_text`) | LOW — every filename stays in the generated table |
| `execute_orcia_documentation_workflow` (`_help_orcia_docs_workflow.py`) | `tech_lead_reports_count` in help article model | LOW — fix off-by-one (counts `_*.md` annex) |
| `_i18n-audit-inventory-raw.md` | `.pre-commit-config.yaml` exclude, 2 lines in `sprint-status.yaml`; no code reader | LOW |
| `bmad-build` spec path | `{implementation_artifacts}/spec-{slug}.md` from global config | LOW — rerouted via override prepend |

- **Exploration & Key Metrics**: 261 TLRs (6.7 MB) vs 40 specs (epics 1–8, last 2026-11-16); README rows: 253 with 5 cells, 7 irregular (8–12 cells); longest README line 2,773 chars; `docs/architecture.md` / `docs/epics.md` are 97–98 % identical prefixes of the planning-artifacts versions; FAQ ↔ `architecture.md §8` similarity 0.84; only `epic-13` open.
- **Refactoring & Debt**: new `scripts/generate_tlr_index.py` mirrors `generate_test_fixture_index.py` (≤ 300 lines). Follow-up debt (not in scope): `docs/product/capabilities.yaml` (111 KB) deserves a generated compact index; GitNexus re-index of active worktrees.

### 1.3 Acceptance Criteria
| # | Criterion |
| :--- | :--- |
| AC1 | `lint_spine.py` → `0` findings; `parse_architecture_spine` returns the same 25 AD codes and same stack items; spine ≤ 25 KB; every AD body preserved verbatim in `adr/AD-NN-*.md` |
| AC2 | `tech-lead-reports/README.md` is generated (`pnpm site:sync`), `--check` fails on drift, all 3 traceability tests and `orcia-showcase-site.test.tsx` pass |
| AC3 | `AGENTS.md` ≤ 3.5 KB with layer rules reachable via pointer; R-CORE-11 forbids reading/editing the TLR index |
| AC4 | `epics.md` index ≤ 30 KB + `epics/epic-NN.md` verbatim; every consumer still resolves its epic |
| AC5 | BMAD activation facts contain no `file:` entry > 5 KB; `_bmad/custom/` tracked in Git (zero secrets, zero absolute paths, `*.user.toml` ignored); `bmad-build` / `bmad-build-auto` write the story spec directly as `tech-lead-reports/<story-key>-tech-lead-report.md` (§1–§2 frozen pre-implementation, §3 completed post-implementation); no new `spec-*.md` |
| AC6 | `agent_check.py static` and `impact` PASS; `pnpm site:check` PASS; `check_implementation_docs.py` PASS |

### 1.4 I/O & Edge Cases
| Input | Expected |
| :--- | :--- |
| TLR with YAML frontmatter | Index row from frontmatter |
| Legacy TLR without frontmatter | Row from `_index-legacy.json`, else `**Date**` line / filename date + H1 |
| Irregular legacy row (pipes inside cells) | Extracted once into JSON; generator escapes `|` in cells |
| Summary > 200 chars | Truncated with `…` |
| `_*.md` annex or `README.md` | Excluded from index and help count |
| Two reports same date | Stable order by filename |
| TLR with leading `---` frontmatter + HTML-comment frozen markers | Passes `check_implementation_docs.py`, parsed by `sync_site_catalog.py`, counted once by help workflow |

---

## 2. Implementation Plan

### 2.1 Data Schema & Alembic Migrations
- None.

### 2.2 Hexagonal Core, Orchestration & Workers
- `packages/orcia-core/src/orcia_core/orchestration/_help_orcia_docs_workflow.py`: count only `*-tech-lead-report.md` (domain-neutral filesystem filter, no new imports).

### 2.3 Backend API, Security & Contracts
- None (no route, schema or SDK change).

### 2.4 User Interface & Experience
- None hand-edited; `orciaSiteManifest.ts` / `docs/site-catalog/index.html` regenerated by `pnpm site:sync` (AD titles shortened, report summaries ≤ 200 chars).

### 2.5 Docs, Tooling & Harness (phase order, one commit each)
1. **Spine** — `adr/AD-NN-*.md` verbatim (French kept); spine ADs rewritten in English (`Binds` / `Prevents` / `Rule` / `Detail`); Stack table unchanged.
2. **Architecture duplicates** — drop `architecture.md §7/§8` (links); move blueprint to `docs/planning-artifacts/visuals/`; delete stale `docs/architecture.md`, `docs/epics.md`; relative FAQ links.
3. **TLR index & single story artifact** — `scripts/generate_tlr_index.py` (+ `--check`), `scripts/tlr_index_legacy.json` one-time extract, regeneration in `sync_site_catalog.py` (`pnpm site:sync`), drift check in `check_implementation_docs.py` + `site:check` (Stage 3 `full-docs-site` and pre-commit, which regenerates first) — never in Stage 1 `static`; raw dump → `docs/implementation-artifacts/archive/`; help workflow counts only `*-tech-lead-report.md`. Template becomes the story spec: frontmatter (`date, story, domain, summary, status, route, baseline_commit, review_loop_iteration`), §1 between `<!-- frozen-after-approval:start -->` / `<!-- frozen-after-approval:end -->` HTML comments with §1.3 Acceptance Criteria / §1.4 I/O & Edge Cases, §2 checkable tasks, §3.5 Spec Change Log & Review Triage, BMAD-section → TLR-section mapping table.
4. **AGENTS.md** — layer rules → `docs/agent-playbooks/layers/{backend,frontend}.md`; R-CORE-11 amended (TLR = sole committed story artifact; never read/edit `tech-lead-reports/README.md`); R-CORE-12/R-ROUTE-05 merged; subagent prompts in English; `coder.md`/`verifier.md` complete §3 of the same TLR; `.agent_check/story_intent.md` (< 500 tokens) reserved for `bmad-fixer-worker`.
5. **BMAD overrides** — backup to `/tmp/orcia-bmad-custom.bak-2026-11-27/`; strip eager `file:` facts (spine, `capabilities.yaml`, `AGENTS.md`, routing rule, template) in `config.toml` + per-skill files; `bmad-build` / `bmad-build-auto` `activation_steps_prepend` + `implementation_handoff` set `spec_file` to the TLR and use the TLR template; `bmad-spec` (planning-level `SPEC.md` folders) not unified, facts stripped only. Option B: `_bmad/` stays git-ignored; 7 lean English overrides tracked in `.agents/bmad-custom/` (`*.user.toml` ignored); `scripts/init_worktree.sh` (≤ 80 lines, idempotent, + `tests/unit/tooling/test_init_worktree.py`) symlinks `.venv`, `.secrets.baseline`, `_bmad/*` from the main checkout and `_bmad/custom -> ../.agents/bmad-custom`; main-checkout switchover only post-merge; `.gitignore` gains `/.venv` (symlink-safe). <!-- pragma: allowlist secret -->
6. **Skills** — 11 planning skills → `.bmad-archive/skills/`.
7. **CLAUDE.md** — `@AGENTS.md` + GitNexus block.
8. **Epics** — `docs/planning-artifacts/epics/epic-NN.md` + slim index, after consumer check.

### 2.6 Test Pyramid Impact Analysis (`AD-17`)
- **Layer 1a**: new `tests/unit/tooling/test_generate_tlr_index.py` (`--cov=scripts` ≥ 90 %, outside coverage `source`), `tests/unit/tooling/test_init_worktree.py`, `check_agent_rules.py` recursive-playbook test (frontmatter, legacy, fallback, truncation, escaping, ordering, `--check` drift); help workflow count test; existing `test_site_catalog_sync.py`, `test_story_4_1_sandbox_tier1_and_pattern_drift.py`, 3 traceability tests re-run.
- **Layer 1b**: `orcia-showcase-site.test.tsx` re-run after manifest regeneration.
- **Layer 2 / 3 / 4 / Security / 5**: no runtime, API, prompt or UI behavior change — not impacted; `lint-imports` covered by `agent_check.py static`.

---

## 3. Summary of Changes & Results (Post-Implementation)

### 3.1 Created & Modified Files (by Phase)
| Phase / Commit | Key Files Changed | Summary |
| :--- | :--- | :--- |
| Phase 0 (`06da7ca`) | `.agents/skills/` (6 removed), `.gitignore`, `README.md`, this report | Removed 6 duplicate GitNexus skills in `.agents/skills/`; symlink-safe `/.venv` ignore; registered TLR. |
| Phase 1 (`51f99e0`) | `ARCHITECTURE-SPINE.md`, `adr/00-spine-context.md`, `adr/AD-01..25-*.md`, `orciaSiteManifest.ts`, `docs/site-catalog/index.html` | Condensed spine (149 KB -> 25 KB); verbatim AD bodies moved to `adr/`; site synced. |
| Phase 2 (`80da0dd`) | `architecture.md`, `docs/planning-artifacts/visuals/orcia-blueprint.html`, `docs/{architecture,epics}.md` (deleted), `faq-architecture-modele-metier.md` | Deduplicated `architecture.md` §7/§8 to links; moved HTML blueprint; deleted stale copies; relative FAQ links. |
| Phase 3 (`db3afb5`) | `scripts/generate_tlr_index.py` (166 L), `scripts/tlr_index_legacy.json`, `scripts/check_implementation_docs.py`, `infra/scripts/sync_site_catalog.py`, `.pre-commit-config.yaml`, `_help_orcia_docs_workflow.py`, `TECH-LEAD-REPORT-TEMPLATE.md`, `docs/implementation-artifacts/archive/2026-11-20-i18n-audit-inventory-raw.md`, `sprint-status.yaml`, `tests/unit/tooling/test_generate_tlr_index.py`, `tests/unit/test_help_orcia_docs_workflow_count.py` | Auto-generated TLR index (`pnpm site:sync` + pre-commit); unified TLR as sole story spec template; archived 1.6 MB raw dump; fixed `_*.md` count bug in help workflow. |
| Phase 4 (`4e28bbf`) | `AGENTS.md`, `docs/agent-playbooks/layers/{backend,frontend}.md`, `docs/agent-playbooks/{coder,fixer,verifier}.md`, `.agents/rules/bmad-model-routing.md`, `.agents/agents/*.md`, `scripts/check_agent_rules.py`, `tests/unit/tooling/test_agent_rules_and_fixture_index.py` | Trimmed `AGENTS.md` to 3,568 B (`<= 3,584 B` cap); moved layer rules; recursive `rglob("*.md")` rule lint; English subagent prompts. |
| Phase 5 (`992b087`) | `.agents/bmad-custom/*.toml` (7 files), `scripts/init_worktree.sh` (65 L), `tests/unit/tooling/test_init_worktree.py`, `.gitignore` | Stripped 625,703 B eager `file:` loads in BMAD overrides (`0 B` remaining); added Spec-to-TLR overrides & idempotent worktree bootstrapper; backup kept at `/tmp/orcia-bmad-custom.bak-2026-11-27/`. |
| Phase 6 (`53f7038`) | `.bmad-archive/skills/` (11 moved), `.bmad-archive/README.md`, `pyproject.toml`, `.pre-commit-config.yaml` | Archived 11 planning-only skills (`27` active kept); added `.bmad-archive` ruff `--force-exclude`. |
| Phase 7 (`0358e36`) | `CLAUDE.md` | Collapsed to `@AGENTS.md` import + 2-line pointers + verbatim `gitnexus` block. |
| Phase 8 (`bdc5380`) | `docs/planning-artifacts/epics.md`, `docs/planning-artifacts/epics/00-requirements-inventory.md`, `docs/planning-artifacts/epics/epic-01..32.md`, `tests/unit/{_epic23_to_epic24_constants,test_epic21_to_epic22_traceability,test_epic22_to_epic23_traceability}.py`, `epic-26-decisions-grill-2026-11-21.md`, `sprint-change-proposal-2026-11-21-epic-26-harnais-assistant-remediation-plan.md`, `.agents/bmad-custom/config.toml`, `AGENTS.md` | Split 722 KB `epics.md` into 9.2 KB index + 32 verbatim epic files + inventory; updated traceability tests & live `epic-26` links (5 historical TLR `#L...` links left immutable). |

### 3.2 Before / After Sizes & Parity Gates
| Artifact | Before | After | Delta |
| :--- | ---: | ---: | :--- |
| BMAD `_bmad/custom` eager `file:` facts | `625,703 B` (5 files, multiple copies) | `0 B` | `-100%` |
| `docs/planning-artifacts/epics.md` | `722,055 B` | `9,159 B` index (+ `epics/epic-01..32.md`) | `-98.7%` index |
| `ARCHITECTURE-SPINE.md` | `149,212 B` | `24,981 B` (+ `adr/AD-01..25-*.md`) | `-83.3%` |
| `architecture.md` | `101,623 B` | `78,114 B` | `-23.1%` |
| `tech-lead-reports/README.md` | `290,637 B` (manual) | `163,611 B` (auto-generated, 0 agent reads) | `-43.7%` (0 agent cost) |
| `AGENTS.md` | `6,793 B` | `3,568 B` (`<= 3,584 B` cap, 0 truncated) | `-47.5%` |
| `CLAUDE.md` | `9,673 B` | `3,785 B` | `-60.9%` |
| `.agents/rules/bmad-model-routing.md` | `1,688 B` | `1,586 B` | `-6.0%` |
| Stale `docs/{architecture,epics}.md` | `167,198 B` | `0 B` (deleted) | `-100%` |
| Active `.agent/skills/` directories | `38` (incl. 11 planning-only) | `27` (11 archived in `.bmad-archive/skills/`) | `-11` skills |

- **G4 Spine Parity (`spine_parity.py`)**: `25` AD codes in order, `45` Stack rows byte-identical, `0` lost `FR`/`NFR`/`AD` tokens, verbatim AD bodies in `adr/`, `lint_spine.py`: `ok: true, total_findings: 0`.
- **G5 Epics Parity (`epics_parity.py`)**: `32` epic files, `189` Story headings (`1.1`..`32.5`) identical, `0` lost `CAP-*`/`FR-*` tokens, verbatim per-epic equality.
- **G6 Deep Anchors**: `2` live `epic-26` anchors updated to `epics/epic-26.md`; `5` historical TLR anchors (`11-4`, `11-5`, `12-1`, `2026-11-06` ×2) left untouched per immutability rule.
- **G10 Worktree Resolver**: `_bmad/scripts/resolve_customization.py --skill .agent/skills/bmad-build` and `resolve_config.py --project-root .` resolve to the active worktree's `.agents/bmad-custom/` with clean `git status`.
- **GitNexus**: Worktree not indexed (main checkout index stale at `bf44884`, 541 symbols); impact verified via exhaustive `grep` and parity scripts, diff reviewed via `git diff --stat bf44884..HEAD`.

### 3.3 AD-17 Test Pyramid & Verification Results
- **Spine & Docs Gates**: `lint_spine.py` (`0` findings), `check_agent_rules.py` (`AGENTS.md=3568 B <= 3584 B`), `check_implementation_docs.py` (`260` reports in sync), `pnpm site:sync && pnpm site:check` (`66/66` live CAPs, `63/63` E2E, `20/20` UJ).
- **Script Branch Coverage (Layer 1a)**: `.venv/bin/coverage run --branch --source=scripts -m pytest -q tests/unit/tooling/test_generate_tlr_index.py` → `95%` (`103` stmts, `30` branches, `--fail-under=90` PASS).
- **Targeted Unit Suites (Layer 1a)**: `test_init_worktree.py`, `test_agent_rules_and_fixture_index.py`, `test_help_orcia_docs_workflow_count.py`, `test_site_catalog_sync.py`, `test_story_4_1_sandbox_tier1_and_pattern_drift.py`, `test_epic21_to_epic22_traceability.py`, `test_epic22_to_epic23_traceability.py`, `test_epic23_to_epic24_traceability.py`, `test_i18n_backend_catalog_and_english_dev_audit.py` — ALL PASS.
- **Frontend Vitest (Layer 1b)**: `pnpm --filter @orcia/web test` (`102` test files, `372` tests PASS, incl. `orcia-showcase-site.test.tsx`).
- **Runner (`agent_check.py`)**: `static` PASS (`9 gates in 20.12s`); `impact` PASS (`5 py + 0 vitest pkg(s) in 11.36s`); `full` PASS (`full-unit` 1 target `291.27s`, `full` evals/security/contract 3 targets `127.04s`, `full-diff-cover >=90%` `40.46s`, `full-vitest` 3 pkgs `74.39s`, `full-docs-site` 2 checks `2.14s`).
- **G11 Dry Run (`bmad-dev-worker` `flash`)**: Phase A (`6a587ed5`) created temporary TLR §1–§2 (`status: ready-for-dev`, `0` `spec-*.md`, `agent_check.py static` `PASS [static]: 10 gates in 20.19s`); Phase B+C (`ab331a8c`) cold-resumed from frontmatter & `- [ ]` task, closed §3 (`status: done`), and passed `pnpm site:sync`, `check_implementation_docs.py`, `pnpm site:check` before cleanup.

### 3.4 Token, Duration KPIs & Empirical Telemetry (`G12`)
- **Empirical Dry-Run Token Report** (`ORCIA_TRANSCRIPTS_DIR=/home/romain/.gemini/antigravity/brain .venv/bin/python scripts/agent_token_report.py --conv 6a587ed5-2c7a-45c4-9704-cbcdb7a60ad4 --conv ab331a8c-9437-4045-9db3-da4079ab2f74 --format json`):
  - `2` conversations, `13` turns, `191,881` total input tokens (`54,505` fresh, `137,376` cached), **`14,760` avg context tokens/turn**, `5,678` output tokens, `0.0%` duplicate `read_file` rate (`0/2`), `0` generated reads.
  - Pre-diet baseline dev-worker sample (`48edf26b`, `175` turns): `143,435` avg context tokens/turn, `25,101,175` total input tokens.
- **Post-Merge Main-Checkout Switchover** (run once on `main` after merging `harness_file_discovery`):
  ```bash
  git checkout main && git pull --ff-only
  bash scripts/init_worktree.sh
  ```
  *(Backs up `<main_checkout>/_bmad/custom` to `/tmp/orcia-bmad-custom.bak-<date>/`, preserves `*.user.toml` inside `.agents/bmad-custom/`, and replaces `_bmad/custom` with symlink `../.agents/bmad-custom`.)*

### 3.5 Spec Change Log & Review Triage
- **Spec changes**: Plan v2 adjusted with Option B (`.agents/bmad-custom/` + `scripts/init_worktree.sh` instead of tracking `_bmad/`), direct Spec-to-TLR unification, HTML-comment frozen markers, and pre-commit `ruff --force-exclude` for `.bmad-archive/`.
- **Review findings**: None blocking. Follow-up debt noted in §1.2 (`capabilities.yaml` 111 KB index generation; worktree GitNexus re-index).
