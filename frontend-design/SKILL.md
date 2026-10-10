---
name: frontend-design
description: 当需要生成、重构或评审前端页面（落地页、作品集、产品官网、活动页、应用工作台 / SPA、Dashboard 视觉层）时使用。适用于"做个好看的页面""优化视觉""这个太丑了"等模糊需求。产出自带设计系统、微排印、生成式资产、动效、响应式与可访问性的高质量 HTML/CSS/JS。参考 Awwwards / Webby / FWA 获奖品质。
---

# 前端设计 Skill — frontend-design

> 让 Agent 在有限提示词下产出 Awwwards / Webby / FWA 获奖级别的界面。
> 核心主张：**品味 = 纸张感浅色基底 + 微排印精密控制 + 异构版式 + 1 个签名手法 + 拒绝空架子。**

---

## 0. 触发条件

**使用本 skill 当：**

- 用户说"做个页面 / 落地页 / 官网"，但没给设计稿
- 用户说"好看点 / 高级点 / 有设计感 / 像 Awwwards 那样"
- 用户给了模糊的参考（"参考 Linear / Stripe / Apple"）
- 需要评审或重构一段"AI 味很重 / 模板感强"的前端代码

**不适用：** 需要严格遵守已有 Design System / 品牌规范 / 业务组件库文档的任务。

---

## 1. 设计哲学（6 条铁律）

1. **内容优先，拒绝资产空洞。** 没有真实图片时，严禁使用空白灰色占位框；必须用精密代码生成视觉主体。
2. **对比即设计。** 极重字号与极轻字号对比、致密信息与阔绰留白对比。缺少对比 = 平庸。
3. **一个记忆点胜过十个亮点。** 每页只允许一个"签名手法"（signature move）。
4. **动效是物理连续性，不是装饰。** 每个动效都要建立空间层级与物理反馈，禁止无目的的通用动画。
5. **留白是主动决策。** 该空的地方必须空到"心疼"；该密集的区域必须精密如仪器。
6. **克制，坚持浅色高级感。** 默认浅色底，高级感来自底色微差、色相偏移阴影与发丝边缘，而不是依赖暗色背景。

---

## 2. Step 0 — 意图解析 & 模式划分

用户只给一句话时，按顺序推断以下 5 项。**不要反问用户，直接推断并在代码顶部注释里写明。**

| 维度              | 提取方式                                | 影响                         |
| ----------------- | --------------------------------------- | ---------------------------- |
| **领域 Domain**   | 关键词 → 行业原型                       | 决定色板、字体气质与阴影色相 |
| **受众 Audience** | 谁看？开发者 / 投资人 / 消费者 / 招聘方 | 决定信息密度与微排印倾向     |
| **情绪 Tone**     | 冷静 / 温暖 / 锋利 / 诗意 / 精密        | 决定动效曲线、圆角硬度       |
| **密度 Density**  | 内容量多少？                            | 决定留白节奏与网格划分       |
| **记忆点 Hook**   | 最核心的词 / 数据 / 概念                | 决定签名手法的承载位置       |

### 2.1 页面模式：严格切分落地页与应用 (SPA)

- **落地页模式（Landing）：** 品牌、营销与叙事页面。采用纵向章节呼吸节奏、超大展示级排版、非对称分栏。
- **应用 / SPA 模式（Workbench / Tool）：** 工作台、管理工具或多主题操作界面。
  - 外壳必须撑满视口（`100dvh`），顶栏保持可见，主体**禁止整页滚动**；
  - 长列表、日志、数据看板必须置于内部有边界的独立滚动容器内（配合 `min-height: 0; min-width: 0` 防止 flex/grid 容器溢出）；
  - 欢迎视图保留高冲击力 Hero 与唯一签名手法，切换到工作视图后保持同套字体、圆角与色彩规则，但收缩间距、提高密度；
  - 局部调整任务：冻结其余视觉，仅改动指定部分，不推翻原型。

---

## 3. Step 1 — 选定设计原型（Archetype）

从下表中**只选一个**，不得混合。**所有原型一律默认为浅色模式。**

> **CDN 字体硬性要求：** 只要使用了非系统默认字体，**HTML `<head>` 必须引入对应的 Google Fonts `<link>` 与 preconnect**，并配置稳妥的系统降级字体族。禁止只在 CSS 声明 `font-family` 却不引入字体文件。

### A. Editorial（编辑画报风）

- **气质：** 杂志排版、衬线优雅、阔绰留白、文学与学术感
- **字体：** 标题 `Instrument Serif` / `Fraunces` / `Bodoni Moda`；正文 `Inter` / `Geist` / 系统西文
- **CDN 导入：** `https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=Inter:wght@400;500;600&display=swap`
- **色板：** 画报米白纸底 `#F6F4EE` + 墨黑 `#121110` + 次级铅字灰 `#6B6860` + 一抹朱红强调 `#D9381E`（阴影色相偏暖：`--shadow-hue: 35`）
- **适合：** 品牌官网、作品集、文化消费、精品独立产品

### B. Technical（精密工业风）

- **气质：** 仪表盘般的精密、高对比等宽字、微网格线、刻度感（不依赖暗底即可体现技术感）
- **字体：** 标题 `Space Grotesk` / `Geist`；数据与标签 `JetBrains Mono` / `Geist Mono`
- **CDN 导入：** `https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;700&family=JetBrains+Mono:wght@400;500;600&family=Inter:wght@400;500&display=swap`
- **色板：** 工业冷白灰 `#F4F6F8` + 深冷墨 `#0B0F17` + 次级灰 `#5A6578` + 深松石绿/冷紫强调 `#0E7490`（阴影色相偏冷：`--shadow-hue: 215`）
- **适合：** SaaS、开发者工具、AI 应用、数据平台、金融科技

### C. Neo-Brutalist（新粗野主义）

- **气质：** 结构裸露、硬朗实黑边框、几何色块、物理撞击感、绝不圆滑
- **字体：** 标题 `Syne` / `Archivo Black`；正文 `Space Grotesk` / 系统无衬线
- **CDN 导入：** `https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=Space+Grotesk:wght@400;600&display=swap`
- **色板：** 纯白 `#FFFFFF` + 纯黑硬边 `#000000` + 骨白底 `#F0F0EE` + 1 个硬强调色（如亮柠檬黄 `#FFE600` 或电气青 `#00F0FF`）
- **适合：** 创意机构、独立黑客、前卫活动页、潮流品牌

### D. Soft / Organic（柔和呼吸感）

- **气质：** 亲和、柔和圆角、光影温润、生活美学
- **字体：** 标题 `Fraunces` / `Newsreader`；正文 `Plus Jakarta Sans` / `Manrope`
- **CDN 导入：** `https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,600;9..144,700&family=Plus+Jakarta+Sans:wght@400;500;600&display=swap`
- **色板：** 燕麦奶底 `#FBF8F3` + 暖深棕 `#1E1A17` + 陶土橙强调 `#C85A32` + 橄榄灰 `#6E695E`（阴影色相偏暖：`--shadow-hue: 25`）
- **适合：** 健康生活、消费品牌、教育、身心健康产品

### E. Kinetic Editorial（动态排版海报风）

- **气质：** 巨大文字作为图形、滚动视差联动、文字穿插破界
- **字体：** 单一高素质无衬线或可变字体（如 `Syne` / `Geist`），发挥 weight/optical-size 的极致反差
- **CDN 导入：** `https://fonts.googleapis.com/css2?family=Syne:wght@400;700;800&family=Inter:wght@400;500&display=swap`
- **色板：** 纯净纸白 `#FAFAFA` + 极深炭黑 `#0A0A0A` + 发丝灰色线 `#E5E5E5` + 仅 1 处微小高光点
- **适合：** 设计师宣言、音乐/艺术展、极简产品发布会

---

## 4. Step 2 — Token 系统（显式 `:root` 规范）

禁止组件中硬编码颜色、阴影与字阶。在 CSS 顶部显式声明以下基准：

```css
:root {
  /* ========================================================
     1. 字体比例 (Type Scale) + 微排印控制
     ======================================================== */
  --font-display: 'Instrument Serif', Georgia, serif;
  --font-sans: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
  --font-mono: 'JetBrains Mono', ui-monospace, monospace;

  --fs-display: clamp(3.25rem, 10vw, 9.5rem);
  --fs-h1: clamp(2.25rem, 5.5vw, 4.25rem);
  --fs-h2: clamp(1.75rem, 3.2vw, 2.75rem);
  --fs-h3: clamp(1.25rem, 2vw, 1.65rem);
  --fs-body: clamp(0.9375rem, 1.05vw, 1.0625rem);
  --fs-small: 0.8125rem;
  --fs-label: 0.6875rem;

  --lh-display: 0.92;
  --lh-heading: 1.12;
  --lh-body: 1.65;

  /* 微排印字距：大字必须负字距，小标签必须正字距并大写 */
  --ls-display: -0.04em;
  --ls-heading: -0.02em;
  --ls-body: -0.005em;
  --ls-label: 0.1em;

  /* ========================================================
     2. 间距尺度 (非线性系统)
     ======================================================== */
  --sp-1: 0.25rem;
  --sp-2: 0.5rem;
  --sp-3: 0.75rem;
  --sp-4: 1rem;
  --sp-6: 1.5rem;
  --sp-8: 2rem;
  --sp-12: 3rem;
  --sp-16: 4rem;
  --sp-24: 6rem;
  --sp-32: 8rem;
  --sp-48: 12rem;

  /* 页面内边距与垂直呼吸空间 */
  --page-gutter: clamp(1rem, 2vw, 1.75rem); /* 应用/SPA 默认 */
  --section-y: clamp(4.5rem, 10vw, 10rem); /* 落地页纵向节奏 */

  /* ========================================================
     3. 角色化色板 (全员默认浅色模式)
     ======================================================== */
  --c-canvas: #f6f4ee; /* 主纸张背景底色 */
  --c-surface: #ffffff; /* 卡片/操作面 */
  --c-subtle: #eeebe2; /* 次级微弱衬底 */
  --c-ink: #121110; /* 主标题与正文 */
  --c-muted: #636058; /* 次要文字与说明 (对比度 ≥ 4.5:1) */
  --c-line: rgba(18, 17, 16, 0.08); /* 发丝分割线 */
  --c-line-strong: rgba(18, 17, 16, 0.16);
  --c-accent: #d9381e; /* 强调色 —— 严控全页占比 ≤ 5% */
  --c-accent-soft: rgba(217, 56, 30, 0.08);

  /* ========================================================
     4. 色相偏移物理阴影系统 (禁止纯黑脏阴影)
     ======================================================== */
  --shadow-hue: 35; /* 配合纸张底偏暖；若选 Technical 则改用 215 */
  --sh-key: 0 1px 2px hsl(var(--shadow-hue) 20% 12% / 0.04);
  --sh-ambient: 0 12px 32px -4px hsl(var(--shadow-hue) 25% 12% / 0.06);
  --sh-card: var(--sh-key), var(--sh-ambient);
  --sh-floating: 0 20px 48px -8px hsl(var(--shadow-hue) 30% 10% / 0.1);

  /* 容器发丝微光边框 */
  --border-hairline: 1px solid var(--c-line);
  --border-glow: 1px solid rgba(255, 255, 255, 0.6);

  /* ========================================================
     5. 动效时间与贝塞尔曲线
     ======================================================== */
  --ease-out: cubic-bezier(0.16, 1, 0.3, 1); /* 物理出场，利落干脆 */
  --ease-spring: cubic-bezier(0.34, 1.4, 0.64, 1); /* 弹性反馈，仅用于按钮小组件 */
  --dur-fast: 180ms;
  --dur-base: 320ms;
  --dur-reveal: 800ms;
}
```

---

## 5. Step 3 — 版面结构与“生成式视觉资产”

### 5.1 生成式视觉资产（硬性禁令与解决方案）

> **铁律：** 严禁出现无内容的灰底方块（如灰卡片上写着"Image Placeholder"）。
> **当没有可用图片时，必须用纯内联 SVG 或 CSS 几何系统构建工艺级视觉锚点：**

1. **技术坐标与标尺系统（适用于 Technical / Editorial）：**
   使用细弱十字光标（`+`）、虚线基准线、毫米刻度条、等宽经纬度数据标签点缀版面四周。
2. **算法几何 / 拓扑等高线图（Topographic SVG）：**
   用内联 `<svg>` 绘制交叠的莫比乌斯曲面、薄层拓扑等高线、正弦示波曲线，配合 `stroke-width="1"` 和 `stroke="currentColor"`，形成高精密度视觉重心。
3. **微型应用拟真（Interactive Mockup Asset）：**
   用代码手写一个微缩代码编辑器、精致迷你数据仪表盘或滑块控件，作为 Hero 区的插画替代物。

### 5.2 Bento Grid（异构便当盒布局规则）

当展示特性、数据或工作流时，**坚决杜绝“三张一模一样的三列卡片”**。改用异构 Bento Grid：

```
+------------------------------------------+--------------------+
| A. 核心数据 / 巨大数字指标 (Col 1-8)        | B. 状态/胶囊指示器  |
| 带有微型等高线 SVG 背景与交互数值           | (Col 9-12)         |
+--------------------+---------------------+--------------------+
| C. 精密微缩交互    | D. 编辑风格大字观点 / 签名图示            |
| (Col 1-5)          | (Col 6-12)                               |
+--------------------+------------------------------------------+

```

- **异构性要求：** 每个 Bento 格子的内容类型必须完全不同（数字格、交互格、排版格、图解格），圆角统一，边框统一使用 `var(--border-hairline)`。

### 5.3 破网格与版面张力手法（至少使用 1 个）

- **非对称比例：** Hero 区域采用 7:5 或 8:4 分栏，坚决不搞居中 6:6 对称平分。
- **大字溢出剪裁：** 标题允许设置超大字号 `font-size: 11vw`，突破内边距自然溢出，外层容器配合 `overflow-x: clip`。
- **出血对比：** 背景色块、刻度标尺或复杂图形向外全宽出血，文字严格锁在网格中。
- **基线错位：** 左右并列的两栏，顶部对齐故意垂直偏移 `48px ~ 80px`，打破水平僵死感。

---

## 6. Step 4 — 动效与交互微体验

### 6.1 鼠标局部感应光（Spotlight Hover — 浅色专用）

在 Bento 卡片或关键功能容器上加入浅色微光感应，赋予物理界面的通透触感：

```js
document.querySelectorAll('[data-spotlight]').forEach((el) => {
  el.addEventListener('pointermove', (e) => {
    const r = el.getBoundingClientRect();
    el.style.setProperty('--x', `${e.clientX - r.left}px`);
    el.style.setProperty('--y', `${e.clientY - r.top}px`);
  });
});
```

```css
[data-spotlight] {
  position: relative;
  overflow: hidden;
}
[data-spotlight]::before {
  content: '';
  position: absolute;
  inset: 0;
  pointer-events: none;
  background: radial-gradient(
    380px circle at var(--x, -999px) var(--y, -999px),
    rgba(18, 17, 16, 0.035),
    transparent 80%
  );
  opacity: 0;
  transition: opacity var(--dur-fast) var(--ease-out);
}
[data-spotlight]:hover::before {
  opacity: 1;
}
```

### 6.2 优雅入场揭示（落地页关键节点）

```css
[data-reveal] {
  opacity: 0;
  transform: translateY(20px);
  transition:
    opacity var(--dur-reveal) var(--ease-out),
    transform var(--dur-reveal) var(--ease-out);
  transition-delay: calc(var(--d, 0) * 90ms);
}
[data-reveal].is-in {
  opacity: 1;
  transform: none;
}

@media (prefers-reduced-motion: reduce) {
  [data-reveal] {
    opacity: 1 !important;
    transform: none !important;
    transition: none !important;
  }
}
```

```js
const io = new IntersectionObserver(
  (entries) => {
    entries.forEach((e) => {
      if (e.isIntersecting) {
        e.target.classList.add('is-in');
        io.unobserve(e.target);
      }
    });
  },
  { threshold: 0.12, rootMargin: '0px 0px -50px 0px' },
);

document.querySelectorAll('[data-reveal]').forEach((el) => {
  if (el.dataset.delay) el.style.setProperty('--d', el.dataset.delay);
  io.observe(el);
});
```

### 6.3 交互硬原则

- **物理微回弹：** 所有交互按钮在 `:active` 时必须有轻微缩放反馈（`transform: scale(0.98)`），提供真实的触击确认感。
- **只操作高效属性：** 动画只能改变 `transform` 和 `opacity`。严禁通过改变 `height` / `width` / `margin` 引发全局重排。
- **耗时铁律：** 微反馈 180–320ms；展开折叠 ≤ 400ms；进入页面首屏揭示 ≤ 800ms。禁止一切拖沓动画。

---

## 7. Step 5 — 微排印与高阶质感细节

### 7.1 等宽对齐数字（数据/看板必选）

仪表盘、价格、统计数据与时钟等界面，强制开启等宽对齐，防止数字跳动并强化精密工业感：

```css
.tabular-data,
.metric-value {
  font-family: var(--font-mono);
  font-variant-numeric: tabular-nums lining-nums;
  letter-spacing: -0.02em;
}
```

### 7.2 现代排版断行与光学修正

```css
h1,
h2,
h3 {
  text-wrap: balance; /* 保证标题不会留下一行孤字 */
  letter-spacing: var(--ls-heading);
  line-height: var(--lh-heading);
}
p {
  text-wrap: pretty; /* 优化段落排版边缘 */
  max-width: 65ch; /* 锁定最优阅读长度，禁止文字贯穿全屏 */
}
.label-tag {
  font-size: var(--fs-label);
  letter-spacing: var(--ls-label);
  text-transform: uppercase;
  font-weight: 600;
  color: var(--c-muted);
}
```

### 7.3 纸质微噪点背景（几乎万能的去塑料感神技）

```css
.grain-overlay {
  position: fixed;
  inset: 0;
  z-index: 9999;
  pointer-events: none;
  opacity: 0.032;
  mix-blend-mode: multiply;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='[http://www.w3.org/2000/svg](http://www.w3.org/2000/svg)' width='240' height='240'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.8' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='240' height='240' filter='url(%23n)'/%3E%3C/svg%3E");
}
```

### 7.4 卡片质感与边缘发光（浅色立体感）

```css
.premium-card {
  background: var(--c-surface);
  border: var(--border-hairline);
  border-radius: 12px;
  box-shadow:
    inset 0 1px 0 0 rgba(255, 255, 255, 0.9),
    /* 顶边缘微反光高光线 */ var(--sh-card); /* 偏暖/偏冷的色相微阴影 */
  transition:
    transform var(--dur-fast) var(--ease-out),
    box-shadow var(--dur-fast) var(--ease-out);
}
.premium-card:hover {
  transform: translateY(-2px);
  box-shadow:
    inset 0 1px 0 0 rgba(255, 255, 255, 1),
    var(--sh-floating);
}
```

---

## 8. Step 6 — 自检清单（交付前逐项核对）

**资产与渲染**

- [ ] **严禁空占位符：** 页面没有出现任何灰色占位方框；缺少真实图片时已用高质量内联 SVG 图形 / 标尺 / 拓扑线 / 模拟界面填补。
- [ ] **字体引入完备：** `<head>` 中正确包含 Google Fonts 的 preconnect 与 link 标签，且定义了兜底系统字体。

**色彩与材质**

- [ ] **全员纯粹浅色：** 界面首次打开为浅色纸张/工业浅灰质感，正文对比度满足 WCAG AA (≥ 4.5:1)。
- [ ] **阴影去塑料感：** 阴影包含 `--shadow-hue` 色相偏移，禁止使用纯黑粗暴的大半径阴影。
- [ ] **克制强调色：** 强调色面积严控在 5% 以下，杜绝廉价大面积紫蓝渐变。

**排版与微细节**

- [ ] 标题具备负字距（`-0.02em ~ -0.04em`），小标签有大写和正字距（`0.1em`）。
- [ ] 数据指标、价格、时间应用了 `font-variant-numeric: tabular-nums`。
- [ ] 段落使用了 `max-width: 65ch`，标题使用了 `text-wrap: balance`。

**版面与动效**

- [ ] 至少打破一次网格（非对称 7:5 分栏 / 大字溢出 / 出血元素）。
- [ ] 特性区采用异构 Bento Grid 或交替图文，**杜绝“三张一样的图标卡片”**。
- [ ] 动效只使用 `transform` 与 `opacity`，且包含 `prefers-reduced-motion` 降级支持。
- [ ] 包含 1 个明确的签名手法（Spotlight 局部感应光 / 磁性吸附按钮 / 滚动联动视差）。

**模式适配**

- [ ] **应用/SPA 模式：** 占满 `100dvh`，无整页双重滚动条，子视图使用内部有界滚动（`min-height: 0`）。
- [ ] **落地页模式：** 垂直呼吸留白充足（桌面端区块间距 ≥ 80px），页脚采用第二 Hero 级高强度排版。

---

## 9. 反模式黑名单

| ❌ 致命反模式                        | ✅ 替代方案                                             |
| ------------------------------------ | ------------------------------------------------------- |
| 灰色无内容框写着 "Image Placeholder" | 内联精密 SVG 拓扑线 / 坐标轴网格 / 拟真界面             |
| CSS 写了外部字体，HTML 却忘了引 CDN  | `<head>` 严格包含 Google Fonts preconnect 与 stylesheet |
| 纯黑单层脏阴影 `rgba(0,0,0,0.15)`    | 色相偏移双层复合阴影（接触阴影 + 环境漫射）             |
| 三张一模一样的白底圆角卡片排成一排   | 异构 Bento Grid（大数字格 + 交互小部件 + 排版引用）     |
| 所有内容强制居中对齐                 | 非对称 7:5 分栏、左对齐大字排版、错位基线               |
| 数据看板数字跳动不齐                 | 强制加上 `font-variant-numeric: tabular-nums`           |
| 动效时长超过 1 秒 / 拖沓无力         | 180–320ms 高阶缓动贝塞尔曲线 `cubic-bezier(.16,1,.3,1)` |
| 默认暗黑科技风或紫蓝大渐变           | 极简纸张浅色基底 + 发丝线条 + 微反光内边缘              |

---

## 10. 输出规范

1. **单文件优先：** 默认输出完整的 `index.html`（内含 CDN 字体链接、`<style>` 和 `<script>`）。
2. **头部标准：** `<head>` 必须声明 UTF-8、移动端 viewport、正确的 Google Fonts `<link>`，并包含 SVG 噪点背景。
3. **推断注释标注：** 在 `<style>` 开头用注释注明意图推断：

```css
/* Archetype: Technical (浅色) — 推断：开发者工作台，强调紧凑信息密度与 tabular 等宽数字 */
```

4. **交付说明：** 交付代码时附带简明的 3 项说明：

- **选用的设计原型 (Archetype)**
- **本次实现的签名手法 (Signature Move)**
- **无图情况下的生成式视觉方案 (Generative Visual Asset)**
