# UI 组件测试审查

UI 测试最常见的两种失败：**只证明页面上有某个固定字符串**，以及**只证明 React 把事件接上了**。两种都能绿，但都抓不住真实回归。

---

## 1. 固定内容：先分“契约文案”和“附带文案”

| 类型 | 例子 | 能不能锁字面量 |
|---|---|---|
| 契约文案 | 法律条款、错误提示、i18n key、按钮的 accessible name、产品明确要求的标题 | 可以；这是需求的一部分 |
| 附带文案 | 占位符、辅助说明、示例数据、布局里的装饰文字 | 不要锁；用 role/name 或结构断言 |

**反证**：把这段文案改一个字，需求是否真的被违反？不是 → 不要锁字面量；是 → 锁住并说明来源。

---

## 2. 变量绑定：单值测试等于没测绑定

```tsx
// 弱：只证明页面上有 Alice
render(<UserCard user={{ name: "Alice" }} />);
expect(screen.getByText("Alice")).toBeInTheDocument();
```

```tsx
// 强：证明 name 真的被使用
const { rerender } = render(<UserCard user={{ name: "Alice" }} />);
expect(screen.getByRole("heading", { name: "Alice" })).toBeInTheDocument();

rerender(<UserCard user={{ name: "Bob" }} />);
expect(screen.getByRole("heading", { name: "Bob" })).toBeInTheDocument();
```

**硬编码变异**：把组件里的 `{user.name}` 改成 `"Alice"`。如果测试仍绿，它从来没有验证绑定。这是 UI 审查里最值得做的一次“破坏实验”。

**至少两个值**，且这两个值要不同到足以区分：

- 两段不同的标题/姓名/金额。
- 空字符串 vs 非空。
- 长文本 vs 短文本。
- 特殊字符（`<`, `&`, emoji）vs 普通文本。
- 有条件渲染时：`null` vs 对象、`loading` vs 成功、`error` vs 成功。

不需要每个维度都测；挑这个组件**最可能写错**的那个维度。

---

## 3. 条件状态：有分支就要变条件

组件里有 `if` / 三元 / `&&` 渲染时，至少让一个测试走到另一条分支：

- loading / success / error / empty
- disabled / enabled
- 有权限 / 无权限
- 已选中 / 未选中
- 可选字段存在 / 缺失

**反证**：把条件写反（`isLoading ? content : spinner`），测试会红吗？不会 → 这个分支没被验证。

不要为了“覆盖所有状态”而写 12 条测试；只挑后果最严重的 1–2 个分支。

---

## 4. 交互：断言可见结果，不断言 spy

```tsx
// 弱：只证明 onClick 被调用
await user.click(screen.getByRole("button", { name: "Select" }));
expect(onSelect).toHaveBeenCalled();
```

```tsx
// 强：断言点击后的用户可见结果
await user.click(screen.getByRole("button", { name: "Select" }));
expect(screen.getByRole("status")).toHaveTextContent("Selected");
```

**例外**：组件的职责就是转发事件（设计系统包装、HOC、受控组件）。这时可以断言 spy，但要断言参数、调用次数、禁用/加载条件，而不是只断言“被调用过”。

**优先用 `userEvent`**，它更接近真实交互（焦点、键盘、指针事件）。`fireEvent` 不是禁忌；简单事件或需要精确控制时可以用，但不要用它绕开 `userEvent` 的异步行为。

**异步**：

```tsx
await user.click(screen.getByRole("button", { name: "Load" }));
expect(await screen.findByText("Loaded")).toBeInTheDocument();
```

- `await` 用户事件。
- 用 `findBy*` / `waitFor` 等结果，不要 `sleep`。
- 不要在 `waitFor` 里放空断言；`waitFor(() => {})` 永远通过。
- 同步 `getBy*` 紧跟未等待的异步操作，可能读到旧状态——这种“假绿”要标出来。

---

## 5. 查询方式：从用户视角出发

优先级大致是：

1. `getByRole(..., { name })` —— 最接近用户和辅助技术。
2. `getByLabelText` / `getByPlaceholderText` —— 表单。
3. `getByText` —— 契约文案。
4. `getByTestId` —— 没有语义时的退路；它本身不是错误。
5. `container.querySelector` / class / DOM 结构 —— 脆弱，除非结构就是契约。

**反证**：换一个 CSS class、包一层 div、改组件内部结构，测试会红吗？会 → 它锁的是实现，不是行为。

`toHaveClass("btn-primary")` 只有在 class 是公开契约（设计系统 API）时才合理；否则断言可见状态/aria 属性。

---

## 6. 快照：只能当补充

快照能抓“输出变了”，但不能判断“变对了”。`--updateSnapshot` 会把错误输出 bless 成新基准。

**可以保留**：快照小、稳定、经过 review，且同一测试里还有行为断言。

**要报**：

- 快照是唯一断言（`snapshot_only`）。
- 快照包含时间、随机数、递增 id、环境相关字段。
- 快照巨大到没人 review。
- CI 自动 `--updateSnapshot`。

**修法**：断言关键角色/文本/字段；快照保留为补充，或删除。

---

## 7. mock：mock 边界，不要 mock 掉被测组件

**可以 mock**：网络（MSW/fetch）、时钟、随机数、文件系统、支付/第三方 SDK。

**不要 mock**：被测组件本身、它的子组件（除非子组件是慢/外部边界）、纯展示子组件。把子组件 mock 掉后，测试只证明“父组件调用了子组件”，不证明用户看到了什么。

**不要**：`vi.mock("./UserCard")` 之后断言 `UserCard` 被调用——这等于测试被 mock 掉的实现。

**网络 mock 的首选**：MSW 或项目已有的 fetch mock；断言最终渲染，而不是“fetch 被调用”。

---

## 8. 可访问性断言是行为断言

```tsx
expect(screen.getByRole("dialog", { name: "Confirm deletion" })).toBeInTheDocument();
expect(screen.getByRole("button", { name: "Delete" })).toBeDisabled();
```

role、accessible name、`aria-*` 状态是用户可观察的契约，比 class/DOM 结构稳定。用它们做断言，通常比 `getByText` 更强。

`axe` 扫描是补充，不替代行为断言；不要因为“axe 通过”就认为交互正确。

---

## 9. 不要测的东西

- 纯样式：颜色、间距、动画曲线（除非是设计系统契约）。
- 响应式断点：jsdom 里通常测不准；交给视觉/E2E。
- 第三方组件库的内部行为：测你自己的组合和输出。
- React 自身行为：条件渲染、props 传递、事件绑定本身。
- 整页布局/路由：超出组件测试范围。

---

## 10. 一张对照表

| 场景 | 弱 | 强 |
|---|---|---|
| 渲染姓名 | `getByText("Alice")`，单值 | 两个不同 name，各断言一次 |
| 点击按钮 | `expect(onClick).toHaveBeenCalled()` | 断言选中态/详情/请求结果 |
| 打开 modal | 断言 dialog 出现 | 断言焦点进入、背景滚动锁、关闭后焦点恢复 |
| 表单校验 | 断言 error 文案存在 | 断言提交被阻止 + 错误关联到输入框 |
| 列表空态 | 断言 “No items” 存在 | 空数组渲染空态，非空数组渲染条目 |
| 加载态 | 断言 spinner 存在 | 切换 loading→success，断言最终内容 |
| 快照 | 唯一断言 | 关键字段断言 + 小快照补充 |
