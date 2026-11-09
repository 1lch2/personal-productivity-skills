# 判定示例

用来校准“什么该报、什么不该报”。每个例子都给出测试、判定、证据和回复写法。

---

## 例 1：同义反复 → FAKE / P1

```ts
it("calculates the discounted price", () => {
  const expected = calculateDiscountedPrice(100, "Silver");
  expect(calculateDiscountedPrice(100, "Silver")).toBe(expected);
});
```

**判定**：FAKE，重要性 H（定价）。

**证据**：两边都调用被测函数；把 Silver 折扣从 15% 改成 5%，两边一起变，测试仍绿。

**回复**：

> **[P1]** `src/discount.test.ts:12` `calculates the discounted price` — FAKE / H
> 断言：`expect(calculateDiscountedPrice(100, "Silver")).toBe(expected)`，`expected` 也来自同一函数。
> 存活缺陷：把 Silver 折扣改成 5%，测试仍绿。
> 影响：定价错误可以上线，测试给的是假信心。
> 处理：改成手算期望 `expect(...).toBe(85)`；再加一条 Gold 的样本。

---

## 例 2：固定内容、没有验证绑定 → WEAK / P2

```tsx
it("renders the user name", () => {
  render(<UserCard user={{ name: "Alice", role: "Admin" }} />);
  expect(screen.getByText("Alice")).toBeInTheDocument();
});
```

**判定**：WEAK，重要性 M（用户信息展示）。

**证据**：只有单值。把 `{user.name}` 改成硬编码 `"Alice"`，测试仍绿；它没有证明 prop 被使用。

**回复**：

> **[P2]** `src/UserCard.test.tsx:8` `renders the user name` — WEAK / M
> 断言：`expect(screen.getByText("Alice")).toBeInTheDocument()`
> 存活缺陷：组件硬编码 `"Alice"` 后测试仍绿，传入的 `user.name` 没有被验证。
> 影响：组件不再渲染真实用户数据，测试无法发现。
> 处理：用 `"Alice"` 和 `"Bob"` 各渲染一次，断言 `heading` 的 accessible name 跟着变。

---

## 例 3：点击 → spy → WEAK / P2

```tsx
it("selects the card", async () => {
  const onSelect = vi.fn();
  const user = userEvent.setup();
  render(<UserCard user={userFixture} onSelect={onSelect} />);

  await user.click(screen.getByRole("button", { name: "Select" }));

  expect(onSelect).toHaveBeenCalled();
});
```

**判定**：WEAK，重要性 M。

**证据**：只证明事件接上了；`onSelect` 收到什么参数、选中态是否出现、是否重复触发，都没有验证。

**回复**：

> **[P2]** `src/UserCard.test.tsx:21` `selects the card` — WEAK / M
> 现在：只断言 `onSelect` 被调用。
> 漏掉：参数错误、重复触发、选中态没更新，测试都发现不了。
> 处理：断言 `onSelect` 收到用户 id，并断言卡片出现选中态；如果组件职责只是转发事件，改为断言参数并说明。

**例外**：如果 `UserCard` 是设计系统里的纯转发包装，且“接线”本来就是它唯一的职责，这条可以保留；但仍应断言参数，而不是只断言“被调用过”。

---

## 例 4：快照唯一断言 → BRITTLE / P2

```tsx
it("renders correctly", () => {
  const { container } = render(<UserCard user={userFixture} />);
  expect(container).toMatchSnapshot();
});
```

**判定**：BRITTLE，重要性 M。

**证据**：快照是唯一断言；`--updateSnapshot` 会把任何输出 bless 成新基准；改一个 class 也会红，但改坏数据绑定可能不会红（取决于快照是否包含数据）。

**回复**：

> **[P2]** `src/UserCard.test.tsx:31` `renders correctly` — BRITTLE / M
> 现在：只有整树快照。
> 问题：行为没变（换 class/包一层 div）会红；数据绑定坏了不一定红；快照可被自动更新。
> 处理：断言 heading 的 accessible name 和 role 文本；快照保留为补充，或删除。

---

## 例 5：STRONG → 保留，点名

```tsx
it("shows the selected item after clicking", async () => {
  const user = userEvent.setup();
  render(<ItemList items={[itemA, itemB]} />);

  await user.click(screen.getByRole("button", { name: itemB.name }));

  const status = screen.getByRole("status");
  expect(status).toHaveTextContent(itemB.name);
  expect(status).not.toHaveTextContent(itemA.name);
});
```

**判定**：STRONG，重要性 M。

**证据**：两个不同 item，点击后断言可见结果；把选中逻辑写反，测试会红。

**回复**：

> `src/ItemList.test.tsx:13` `shows the selected item after clicking` — STRONG：两个输入、用户交互、可见结果，能抓住选中逻辑写反。保留。

---

## 例 6：看起来可疑，其实合理 → 不报

```ts
it("emits an analytics event when checkout succeeds", async () => {
  await checkout(cart);
  expect(analytics.track).toHaveBeenCalledWith("checkout_succeeded", {
    orderId: "ord_123",
    total: 4200,
  });
});
```

**判定**：STRONG（或至少不是 WEAK）。

**理由**：这里的“调用”就是契约——analytics 事件的名称和 payload 是产品要求；断言了参数，不是只断言“被调用过”。

**回复**：不报；如果要在“不用动的”里点名，写“analytics 事件断言了名称和 payload，交互本身就是契约，保留”。

---

## 例 7：简单计算，但它是业务边界 → 不报

```python
def test_discount_rounds_to_two_decimals():
    assert calculate_discount(19.99, "silver") == 16.99
```

**判定**：STRONG / H。

**理由**：不是 `add(2, 3)`；它保护舍入规则和金额边界，写错会造成真实的多收/少收。

**对比**：

```python
def test_add():
    assert add(2, 3) == 5
```

**判定**：WEAK / L。没有分支、没有规则、没有可能写错的决策；删掉不会漏掉真实缺陷。

---

## 一句话校准

- 能说出一行“改坏它、测试还绿”的改动 → FAKE。
- 能说出“删掉它、会漏什么” → 有价值；说不出来 → WEAK。
- 只能说出“改结构它会红” → BRITTLE。
- 能说出“换一个输入，它仍然绿” → 没验证绑定。
- 说不出任何具体缺陷 → 不报。
