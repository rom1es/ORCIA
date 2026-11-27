# ORCIA Architect & Reviewer Playbook (`bmad-architect-worker` — `pro`)

Load this playbook only when assigned as **Architect / Reviewer** (`pro` tier, `R-ROUTE-02`). Follow `R-CORE-01..12` and `R-READ-01..04`.

- **[R-ARCH-01]** **`pro`-Tier Docs-Only Boundary**: Focus on system boundaries, ADRs, interface contracts, complex decomposition, and `VALIDATE` / diff reviews. Edit only `_bmad/` or `docs/` — never application source or test code.
- **[R-ARCH-02]** **`T-D3` Epic Review Cadence**: Conduct the epic-level architecture review at the **start of the final story** of an epic (covering stories `1..N-1`) plus a **short diff-only review of the final story**. Retain per-story reviews for security-heavy or high-risk stories (including `32.4` pyramid pruning).
- **[R-ARCH-03]** **Graph & Diff-First Inspection**: Run GitNexus `impact` / `detect_changes` scoped to the active ORCIA worktree path; inspect `git diff` and target symbols using bounded `StartLine`/`EndLine` reads (`R-READ-01..04`). Consult `docs/product/capabilities-index.md` first for capability lookups (bounded read on `capabilities.yaml` only when editing), and never read `docs/implementation-artifacts/archive/sprint-status-epics-01-32-archive.yaml`.
- **[R-ARCH-04]** **Adversarial Review Checklist**: Verify `AD-19`/`AD-20` hexagonal boundaries (`lint-imports`), `AD-17` 5-layer test coverage, vertical wiring (`UI -> SDK -> API -> SQL`), bilingual `fr`/`en` parity, RFC 9457 error envelopes, SSRF / RBAC / `READ_ONLY_OBSERVER` guards, and zero silent `except Exception:` blocks.
- **[R-ARCH-05]** **Disk-Based Review Output**: Write ADR, spec, or review reports to dedicated files under `docs/` and return only the file path + compact triaged findings (`blocker | major | minor`).
