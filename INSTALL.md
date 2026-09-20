# Installation and Usage

## feature-map

1. Copy the `feature-map/` directory into your project's `.agents/skills/feature-map/` directory.
2. Ask your agent to use the skill, for example: “Use feature-map to locate and explain the login flow.” If your project has no feature map yet, ask the agent to create the index and feature documents for a specific feature, following the conventions in `SKILL.md`.
3. We recommend adding the following instructions to your project's `AGENTS.md` so agents use and maintain the feature map as part of their normal workflow:

```markdown
## Feature Navigation

- Before locating, explaining, or modifying a project feature's implementation, use the project-level [feature-map skill](.agents/skills/feature-map/SKILL.md). Start by matching the feature in [docs/feature-map.yaml](docs/feature-map.yaml), read the linked topic documents in `docs/features/` as needed, and then verify against the current source code.
- When adding, changing, or removing features, or when refactoring affects the navigation map, follow the skill to update the affected entries within the same task. Do not modify files during read-only analysis. The navigation map is not yet comprehensive; do not expand the current task's scope just to fill gaps in it.
```

The read-only instruction above takes precedence over the skill's default behavior of documenting newly confirmed features after analysis.

When installing, preserve existing project instructions and any local skill customizations. Create `AGENTS.md` if needed, or update its existing Feature Navigation section without duplicating it.
