# Personal Productivity Skills

[简体中文](README.md) | English

A collection of reusable skills for everyday development and personal productivity, helping coding agents follow consistent project conventions.

## frontend-design

[frontend-design](frontend-design/SKILL.md) helps generate, refactor, or review frontend pages when there is no specific design mockup and the request is as broad as “make it look better” or “give it a stronger visual identity.” It covers landing pages, portfolios, product websites, event pages, application workspaces / SPAs, and dashboard visuals. By choosing a design archetype, defining consistent typography, color, and spacing tokens, and adding purposeful motion, it guides agents toward clear visual hierarchy and one memorable detail.

It distinguishes the vertical storytelling of landing pages from viewport layouts, tab navigation, and internal scrolling in applications. Its review checklist covers responsive behavior, keyboard operation, focus states, contrast, and reduced-motion preferences. It is not intended for tasks that must strictly follow an existing design system, brand guidelines, or component library documentation.

## feature-map

[feature-map](feature-map/SKILL.md) addresses the time agents waste searching for files and feature implementations. It maintains a feature catalog whose `docs/feature-map.yaml` index helps agents quickly locate relevant feature documents and source code. The catalog is updated and gradually expanded during development, reducing repeated searches in future tasks.

## test-value-review

[test-value-review](test-value-review/SKILL.md) reviews unit and UI component tests in JS/TS and Python projects for whether they are actually worth keeping, rather than counting coverage. It applies four counterfactuals to each test: would it fail if the behaviour broke, what would be lost if it were deleted, would a pure refactor break it, and would it still pass if the fixed input were replaced? It labels tests as false confidence, low value, brittle, or strong, and ranks findings by ineffectiveness × importance.

It ships with a scanner, a single-test runner, and a gated mutation probe: the scanner builds the worklist and heuristic signals, the runner confirms the baseline, and the probe temporarily changes one line only after explicit user consent to check whether the test can actually fail. The review is returned directly as delete/change/add recommendations with reasons; it writes no report file and leaves no code changes.

Send the following instruction to your agent to install it. See [INSTALL.md](INSTALL.md) for installation and usage details:

```text
Read INSTALL.md in https://github.com/1lch2/personal-productivity-skills, follow its instructions to install the skills you need (feature-map / test-value-review) in the current project.
```
