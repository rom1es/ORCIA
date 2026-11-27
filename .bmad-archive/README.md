# Archived BMAD Planning Skills

These 11 planning-phase skills were moved out of `.agent/skills/` to save ~1.5–2k skill-catalog tokens per turn during implementation sprints.

Archived skills:
- `bmad-agent-analyst`
- `bmad-agent-pm`
- `bmad-agent-ux-designer`
- `bmad-brainstorming`
- `bmad-deep-recon`
- `bmad-forge-idea`
- `bmad-party-mode`
- `bmad-prd`
- `bmad-prfaq`
- `bmad-product-brief`
- `bmad-ux`

To restore any skill for planning work:
```bash
git mv .bmad-archive/skills/<skill-name> .agent/skills/
```
