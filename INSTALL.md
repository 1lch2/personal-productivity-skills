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

## test-value-review

1. Copy the `test-value-review/` directory into your project's `.agents/skills/test-value-review/` directory.
2. The bundled scripts need Python 3.9+ and use only the standard library; no `pip` or `npm` install is required. Tests themselves still need the project's normal dependencies.
3. Ask your agent to use it, for example: “Use test-value-review to review the tests under `src/`” or “Review the tests in this PR with test-value-review.” The review is returned directly in the conversation; it does not write a report file.
4. Default behavior is read-only: the agent reports what to delete, change, or add, and leaves the edits to you. Running a single test file or test name is allowed when it helps the judgment. A mutation probe temporarily modifies production source, so it requires your explicit permission.
5. We recommend adding the following to your project's `AGENTS.md`:

```markdown
## Test Review

- When a PR adds or changes tests, review them with the project-level [test-value-review skill](.agents/skills/test-value-review/SKILL.md).
- Return delete/change/add recommendations with concrete evidence directly in the conversation. Do not create report files, install dependencies, update snapshots, run the full suite, or modify source for mutation probing without explicit permission.
```

The `evals/` directory is optional. It contains a small calibration set and `check_fixtures.py` for checking the scanner's signals; it is not part of the runtime review.

