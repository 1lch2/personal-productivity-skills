# Personal Productivity Skills

[简体中文](README.md) | English

A collection of reusable skills for everyday development and personal productivity, helping coding agents follow consistent project conventions.

## frontend-design

[frontend-design](frontend-design/SKILL.md) helps generate, refactor, or review frontend pages when there is no specific design mockup and the request is as broad as “make it look better” or “give it a stronger visual identity.” It covers landing pages, portfolios, product websites, event pages, application workspaces / SPAs, and dashboard visuals. By choosing a design archetype, defining consistent typography, color, and spacing tokens, and adding purposeful motion, it guides agents toward clear visual hierarchy and one memorable detail.

It distinguishes the vertical storytelling of landing pages from viewport layouts, tab navigation, and internal scrolling in applications. Its review checklist covers responsive behavior, keyboard operation, focus states, contrast, and reduced-motion preferences. It is not intended for tasks that must strictly follow an existing design system, brand guidelines, or component library documentation.

## feature-map

[feature-map](feature-map/SKILL.md) addresses the time agents waste searching for files and feature implementations. It maintains a feature catalog whose `docs/feature-map.yaml` index helps agents quickly locate relevant feature documents and source code. The catalog is updated and gradually expanded during development, reducing repeated searches in future tasks.

Send the following instruction to your agent to install it. See [INSTALL.md](INSTALL.md) for installation and usage details:

```text
Read INSTALL.md in https://github.com/1lch2/personal-productivity-skills, follow its instructions to install feature-map in the current project, and add the recommended AGENTS.md instructions.
```
