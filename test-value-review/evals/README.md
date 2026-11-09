# 校准集

这些 fixtures 用来校准两件事：

1. **扫描器**：该有的信号有没有发出来（`check_fixtures.py` 自动检查）。
2. **审查判断**：agent 能不能把同样的测试判成 FAKE / WEAK / BRITTLE / STRONG，并给出具体证据（人工/agent 对照 `expected.json`）。

这不是 CI oracle。判断有上下文，标签是校准目标，不是唯一答案。

---

## 跑扫描器

```bash
python scripts/scan_tests.py --root evals/fixtures
python evals/check_fixtures.py
```

`check_fixtures.py` 只检查 `scanner_signals`，不检查文字结论。

---

## 跑一次校准审查

在装好 skill 的环境里，对 fixtures 发起一次真实审查：

> 用 test-value-review 审查 `test-value-review/evals/fixtures`，按 skill 的输出格式直接回复。

对照 `expected.json` 检查：

- 该判 FAKE 的有没有判 FAKE（尤其是同义反复、吞错、无断言）。
- 该判 WEAK 的有没有被误判成 FAKE（固定内容、click→spy、mock-only）。
- 该判 BRITTLE 的有没有被误判成 FAKE（快照）。
- 有没有把 STRONG 误报（两个值、手算期望、pytest.raises）。
- 每条 P1 是否写出了一个具体的存活缺陷。
- 有没有建议“补断言/补覆盖”但没有说漏什么。

---

## 期望标签

| 测试 | 标签 | 重要性 | 关键理由 |
|---|---|---|---|
| React `renders the fixed name` | WEAK | M | 单值；硬编码 prop 仍绿 |
| React `renders two different names` | STRONG | M | 两个输入都断言 |
| React `calls onSelect when clicked` | WEAK | M | 只断言 spy 被调用 |
| React `matches the snapshot` | BRITTLE | M | 快照是唯一断言 |
| React `is self-consistent` | FAKE | M | 两边同一个函数 |
| React `formats a hand-computed value` | STRONG | M | 手算期望 |
| Python `test_silver_discount_is_hand_computed` | STRONG | H | 定价规则手算 |
| Python `test_discount_is_self_consistent` | FAKE | H | 两边同一个调用 |
| Python `test_unknown_tier_raises` | STRONG | M | 错误契约 |
| Python `test_invalid_int_raises` | STRONG | M | `pytest.raises` |
| Python `test_invalid_int_is_swallowed` | WEAK | M | `except ValueError` 不吞 `AssertionError`；与 `pytest.raises` 重复 |
| Python `test_invalid_int_hides_assertion` | FAKE | M | `except Exception` 吞掉断言失败 |
| Python `test_create_calls_repo` | WEAK | M | 只断言 mock 调用 |
| Python `test_create_persists_user` | STRONG | M | fake repo + 落库结果 |
| Python `test_create_does_not_raise` | WEAK | M | 只验证不崩溃 |

---

## 注意

- React fixtures 只用于静态解析，没有 `node_modules`；不要为了跑它们安装依赖。
- Python fixtures 在装了 pytest 的环境里可以跑；没装 pytest 时只做静态审查，不要为了跑它们安装依赖（unittest 风格的文件可以用 unittest 跑）。
- `test_invalid_int_is_swallowed` 的 `except ValueError` **不会**捕获 `AssertionError`，所以它是 WEAK/重复，不是 FAKE；同文件的 `test_invalid_int_hides_assertion`（`except Exception`）才是 FAKE。不要看到 `try/except` 就判死。
- 如果扫描器信号和期望不一致，先修脚本或 fixture，再调标签。
- 如果 agent 的标签和期望不一致，先看它的理由：理由成立就更新 `expected.json`，不要为了对齐而改判断。
