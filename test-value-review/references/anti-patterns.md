# 反模式目录

每条都给出：形态、为什么没有保护、扫描信号、报之前的反证、典型判定。**扫描信号只是待查清单，不是判决。**

判定标签：FAKE / WEAK / BRITTLE / STRONG。重要性 H / M / L 由被测行为决定，不由模式决定。

---

## 1. 无断言：只执行，不验证

```python
def test_create_user():
    service.create("a@example.com")
```

**为什么没有保护**：函数不抛错就绿；返回错值、写错字段、没写库，都发现不了。

**信号**：`no_assertion`，`assertions=0` 且 `helper_assertions=0`。

**报之前**：确认没有调用自定义断言 helper（`expectNoErrors()`、`assertValid()`）。有 helper 就看 helper 是否真的会失败。

**例外**：冒烟测试只验证“能启动/不崩溃”，可以保留；但它保护的是崩溃，不是业务结果，不要把它算进业务覆盖。

**判定**：FAKE（业务测试）或 WEAK（冒烟）。修法：断言返回值、持久化结果或用户可见状态。

---

## 2. 同义反复：两边是同一个表达式

```ts
expect(formatPrice(1234)).toBe(formatPrice(1234))
```

```python
assert calculate(100, "silver") == calculate(100, "silver")
```

**为什么没有保护**：两边一起错、一起对，实现怎么改都绿。

**信号**：`tautological`。

**报之前**：确认不是“用另一个独立实现算期望”（例如用 Decimal 手算对比 float 实现）。独立 oracle 不算同义反复。

**判定**：FAKE。修法：手算期望值，或从需求/规格取固定样本。

---

## 3. mock 自证 / mock echo

```ts
const repo = { save: vi.fn().mockReturnValue(42) };
expect(repo.save()).toBe(42);
```

**为什么没有保护**：断言的是 mock 自己返回的值，被测逻辑没有参与。

**信号**：`mock_echo`；或断言值等于 `mockReturnValue` 的字面量。

**报之前**：确认被测函数不是“把边界值原样透传”的适配器。即使透传，也应该断言透传后的结构/调用参数，而不是只断言 mock 的返回值。

**判定**：FAKE 或 WEAK。修法：让真实被测逻辑执行，断言它产出的结果。

---

## 4. 只断言 mock 被调用

```ts
await service.create(user);
expect(repo.save).toHaveBeenCalled();
```

**为什么没有保护**：调用发生了，但参数、落库结果、错误处理都可能是错的。

**信号**：`mock_interaction_only`；`toHaveBeenCalled*` 是唯一断言。

**报之前**：确认交互本身是不是契约：

- 事件总线/analytics/消息队列：发出事件就是结果，可以断言调用，但要断言 payload 和条件。
- 回调 prop/HOC 转发：调用就是组件的职责，可以保留；仍应断言参数。
- 普通 repository/service：结果在数据库/返回值里，断言调用是弱保护。

**判定**：WEAK（交互是契约时可能 STRONG）。修法：断言参数 + 结果，或换成 fake 依赖断言最终状态。

---

## 5. 内部状态 / 私有方法

```ts
expect(wrapper.state("openIndex")).toBe(1);
wrapper.instance().setOpenIndex(2);
```

**为什么没有保护**：状态名、结构、方法名都可能变；行为没变测试也会红（BRITTLE），行为变了测试可能还绿（FAKE）。

**信号**：扫描器不直接识别；看到 `state(`、`instance()`、`__private`、反射、`@VisibleForTesting` 时人工确认。

**报之前**：确认这个内部状态是不是唯一的可观察契约（例如没有公开 API 的库内部不变量）。是的话，说明理由并降级为 P3。

**判定**：BRITTLE 或 FAKE。修法：通过公开输入/输出断言。

---

## 6. 复述实现：测试里重算一遍

```python
expected = amount * (1 - 0.15)
assert calculate_discount(amount, "silver") == expected
```

**为什么没有保护**：测试复制了实现的公式；公式错，两边一起错。

**信号**：扫描器不直接识别；读测试体时看期望值是否由同一算法生成。

**报之前**：确认不是“独立的 oracle”（不同算法/不同数据源/规格表）。独立实现可以接受。

**判定**：FAKE。修法：手算固定样本，或从规格表取期望值。

---

## 7. 快照橡皮图章

```ts
expect(container).toMatchSnapshot();
```

**为什么没有保护**：`--updateSnapshot` 会把任何输出（包括坏的）写成新基准；快照只证明“和上次一样”，不证明“对”。

**信号**：`snapshot_only`；只有 `toMatchSnapshot` 断言。

**报之前**：确认快照是不是小而稳定、经过人工 review、并且只是补充断言。大快照、含时间/随机值、自动更新流程中的快照，问题更大。

**判定**：BRITTLE（通常）或 WEAK。修法：断言关键字段/角色/可见文本；快照保留为补充。

---

## 8. 吞错 / 不可达断言

```python
try:
    parse("nope")
    assert False, "should not reach"
except Exception:   # 捕获了 AssertionError
    pass
```

```ts
try {
  doThing();
  expect(result).toBe("ok");
} catch (e) {
  // ignore
}
```

**为什么没有保护**：`except Exception` / 裸 `except` / JS 的 `catch` 会连 `AssertionError` 一起吞掉；断言失败被当成“预期错误”忽略。或者断言在 `return` 之后永远不执行。

**信号**：`assert_in_try`。Python 扫描器只把它判为可疑，当且仅当 except 能捕获 `AssertionError`（裸 except、`Exception`、`BaseException`、`AssertionError`）。

**报之前**：确认 except 的类型是否真的能吞掉断言失败：

```python
# 不是吞错：ValueError 不会捕获 AssertionError；这是啰嗦但有效的错误路径测试
try:
    parse("nope")
    assert False, "should not reach"
except ValueError:
    pass
```

这种写法仍然在测“输入非法会抛 ValueError”；它可能因为和 `pytest.raises` 重复而低价值，但**不是 FAKE**。不要因为看到 `try/except` 就判死。

**判定**：能吞 `AssertionError` 的才是 FAKE；窄类型 except 最多是 WEAK/重复。修法：删掉 try/catch 让失败冒出来；或用 `pytest.raises` / `expect(...).rejects` 明确断言错误。

---

## 9. 条件断言

```ts
if (items.length > 0) {
  expect(screen.getByText("Item")).toBeInTheDocument();
}
```

**为什么没有保护**：条件不成立时断言根本没跑，测试仍然绿；条件由外部数据决定时尤其危险。

**信号**：`conditional_assert`。

**报之前**：确认不是参数化/表驱动测试的正常分支（每个 case 只走一个分支是合理的）。如果条件是场景的一部分，确保每个分支都有独立 case。

**判定**：WEAK 或 FAKE。修法：拆成明确的 case，或在 else 分支也断言。

---

## 10. 固定字面量 UI 查询

```ts
render(<UserCard user={{ name: "Alice" }} />);
expect(screen.getByText("Alice")).toBeInTheDocument();
```

**为什么没有保护**：只证明“页面上有 Alice”，不证明 Alice 来自 `user.name`。把组件改成硬编码 `"Alice"`，测试仍绿。

**信号**：`literal_ui_query`（低置信度）。

**报之前**：确认这个字面量是不是契约文案（法律文本、错误提示、i18n key、按钮标签）。是契约就可以断言；不是契约就用 role/accessible name，并至少用第二个值验证绑定。

**判定**：WEAK（单值、无绑定）或 BRITTLE（锁附带文案）。修法：两个不同输入各断言一次；或让实现忽略输入时测试必须红。

---

## 11. 点击 → 回调 spy

```ts
await user.click(screen.getByRole("button", { name: "Select" }));
expect(onSelect).toHaveBeenCalled();
```

**为什么没有保护**：证明 React 把 click 接上了，没证明点击后发生了什么；参数、状态、后续请求都可能是错的。

**信号**：`click_spy_only`。

**报之前**：确认组件的职责是不是“只转发事件”（设计系统包装、HOC）。是的话可以保留，但要断言参数和禁用/加载等条件。

**判定**：WEAK。修法：断言可见结果（选中态、详情出现、请求发出）；如果只关心接线，至少断言调用参数。

---

## 12. modal / toggle 开关本身

```ts
await user.click(screen.getByRole("button", { name: "Open" }));
expect(screen.getByRole("dialog")).toBeInTheDocument();
await user.click(screen.getByRole("button", { name: "Close" }));
expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
```

**为什么没有保护**：条件渲染是框架行为；除非开关背后有逻辑，否则测试的是 React，不是你的代码。

**信号**：没有专门信号；读测试体判断是否只有 open/close。

**报之前**：确认开关是否伴随：焦点恢复/陷阱、滚动锁、状态重置、未保存确认、动画结束回调、权限判断、埋点。有这些副作用时，测试有价值，应断言副作用而不是“关掉了”。

**判定**：WEAK。修法：断言副作用，或删掉只测开关的用例。

---

## 13. 平凡计算 / 常量 / getter

```python
def test_add():
    assert add(2, 3) == 5

def test_default_role():
    assert User().role == "user"
```

**为什么没有保护**：代码没有分支、没有转换、没有可能写错的决策；测试保护的是赋值语句。

**信号**：没有专门信号；读被测代码判断。

**报之前**：确认不是业务规则的边界（税率、舍入、权限矩阵、金额上限）。有规则的“简单计算”值得测。

**判定**：WEAK / L。修法：删除；如果这个常量/默认值是产品契约，改为契约测试并说明。

---

## 14. 类型 / 框架已保证

```ts
expect(typeof user.name).toBe("string");
expect(<Child />).toBeTruthy();
```

**为什么没有保护**：TypeScript 已经保证类型；React 已经保证能渲染子组件。

**信号**：没有专门信号；读断言判断。

**报之前**：确认是否有运行时校验（zod、io-ts、prop-types、API 反序列化）。运行时校验值得测；纯类型断言不值得。

**判定**：WEAK / L。修法：删除，或改为测运行时校验的失败路径。

---

## 15. 重复 / 更脆弱的重复

同一行为有两条测试：一条走公开 API，一条走内部状态/快照。后者更脆弱、定位更差。

**信号**：扫描器不直接识别；对比 `sources` 和断言目标。

**报之前**：确认重复测试是否提供速度/定位收益（单测快、E2E 慢）。有收益就可以保留；只是更脆弱又没有收益，才建议删。

**判定**：BRITTLE / WEAK。修法：保留更强的一条，删除或合并另一条。

---

## 快速反证清单

报之前逐条问：

1. 这个行为坏了，用户/业务会损失什么？说不出来 → 可能不重要。
2. 我能写出一行具体的破坏性改动吗？写不出 → 不要报 P1。
3. 这个 mock/快照/固定文案是不是契约的一部分？是 → 不报。
4. 已有更强的测试覆盖了吗？有 → 报重复/边际价值，不要报“缺失”。
5. 删掉它，真的会漏东西吗？不会 → WEAK，不是 P1。
