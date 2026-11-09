# Personal Productivity Skills

简体中文 | [English](README.en.md)

用于日常开发和个人生产力的可复用 skill 集合，帮助编码 agent 按一致的项目约定完成工作。

## frontend-design

[frontend-design](frontend-design/SKILL.md) 用于在没有明确设计稿、只有“好看点”“有设计感”等模糊需求时，生成、重构或评审前端页面。覆盖落地页、作品集、产品官网、活动页、应用工作台 / SPA 和 Dashboard 视觉层，通过选定设计原型、建立统一的字体、色彩与间距 token，以及有目的的动效，让页面形成清晰的视觉层级和一个记忆点。

它区分落地页的纵向叙事与应用的视口布局、tab 切换和内部滚动，并包含响应式、键盘操作、焦点态、对比度与减少动态效果偏好的自检要求。不适用于必须严格遵循已有设计系统、品牌规范或组件库文档的任务。

## feature-map

[feature-map](feature-map/SKILL.md) 为解决 agent 在查找文件和功能实现上耗费大量时间的问题而生。它通过维护一份功能清单，让 agent 从 `docs/feature-map.yaml` 索引快速定位到相关专题文档和源码，并在开发过程中同步更新、逐步补全清单，减少后续任务中的重复搜索。

## test-value-review

[test-value-review](test-value-review/SKILL.md) 用于审查 JS/TS 与 Python 项目的单元测试和 UI 组件测试是否真有价值，而不是数覆盖率。它用四个反事实判断每条测试：改坏行为会不会红、删掉会漏什么、只改结构会不会红、换掉固定输入还能不能通过；据此标出假信心、低价值、脆弱和有效测试，并按“无效 × 重要”排序。

它自带扫描器、单测运行器和受限的变异探测器：扫描器整理测试清单与可疑信号，运行器确认基线，变异探测器在用户明确同意后临时改一处源码，验证测试是否真的能失败。审查结束后直接回复要删、要改、要加的内容和理由，不生成报告文件，也不留下代码改动。

将下面这条指令发给 agent 即可安装，具体步骤和用法见 [INSTALL.md](INSTALL.md)：

```text
请读取 https://github.com/1lch2/personal-productivity-skills 仓库中的 INSTALL.md，按其中说明把需要的 skill（feature-map / test-value-review）安装到当前项目。
```
