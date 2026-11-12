# Data Model

**SkillLimitsPolicy** (`config/skill-limits.json`)
- `version`: 1
- `limits`: `maxSkillsLoadedPerSource`, `maxCandidatesPerRoot`, `maxSkillsInPrompt`, `maxSkillsPromptChars` (positive ints)
- `measurement`: `perSkillOverheadChars` (120), `missingDescriptionChars` (200)
- `warnAtFraction`: 0.8
Validation: all four keys present, positive ints; load <= candidates; promptCount >= load.

**ShippedSkillSet**: directories in `workspace/skills/` containing `SKILL.md`; derives `count` and `promptCharsNeeded`.

**Result of evaluate()**: list of findings `{limit, configured, needed, level: fail|warn}`; exit 1 when any fail.

**Runtime config effect**: `skills.limits.<key>` = max(existing valid int, policy).
