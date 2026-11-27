---
date: 2026-11-27
story: 2026-11-27-agent-token-diet
domain: Agent Harness / Token Economy / Documentation Governance (hygiene)
summary: Cut per-turn and per-activation agent context (BMAD facts, AGENTS.md, skills, spine, epics, TLR index) by condensing, splitting and auto-generating the files agents load.
---

# 2026-11-27 — Agent Token Diet (Rules, Architecture Spine, Epics, TLR Index, BMAD Overrides)

- **Date**: 2026-11-27
- **Story / Sprint Key**: `2026-11-27-agent-token-diet` (`Epic 13` / `Cross-Cutting Adjustment`)
- **Capability(ies)**: `none (hygiene)` — classification: `hygiene`
- **Author / Context**: Follow-up of Epic 32 (token economy). Reduce the context agents load per turn and per BMAD workflow activation without losing any decision text, keeping `lint_spine.py`, `/showcase`, `check_implementation_docs.py` and traceability tests green. Covers `AD-17` (tests for new tooling), `AD-19` boundaries (scripts only, no domain change).
- **Associated Commits**: _to be filled at closure_

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

_To be completed after verification gates._
