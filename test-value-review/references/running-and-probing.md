# 运行测试与变异探测

运行测试只为一件事服务：**确认这条测试到底能不能失败**。不要为了“更严谨”而把整个套件跑一遍。

---

## 1. 先决定要不要跑

| 情况 | 要不要跑 |
|---|---|
| 结构性问题：无断言、同义反复、mock 自证、空 catch | 不用跑，静态就能判 |
| 断言看起来对，但不确定是否真的执行到 | 跑基线 |
| 异步/条件分支/mock 调用，静态说不清 | 跑基线，必要时变异 |
| 测试已经被跳过/todo | 不用跑；它不提供保护 |
| 测试本身红了 | 先报“测试已红”，不要用它证明假信心 |

静态结论和运行结论要分开标注：`static` / `run` / `mutation`。没跑又依赖运行时行为，标 `UNVERIFIED`。

---

## 2. 基线：这条测试现在能过吗

```bash
python "<skill-base>/scripts/run_test.py" --root . \
  --file src/components/UserCard.test.tsx \
  --name "renders two different names"
```

- 脚本自动识别 vitest / jest / playwright / cypress / mocha / pytest / unittest。
- Cypress 组件测试通常需要 `cypress run --component --spec ...`；自动检测可能只发 E2E 模式，这时用 `--command` 传项目自己的命令。
- 只跑一个文件或一个测试名；不跑 watch；默认 120 秒超时。
- `--dry-run` 只打印识别到的命令，不执行。
- 识别不到时用 `--command` 传项目已有的单测命令：

```bash
python "<skill-base>/scripts/run_test.py" --root . \
  --file src/foo.test.ts \
  --command "pnpm vitest run src/foo.test.ts -t 'renders the title'"
```

**结果**：

- `PASS`：测试当前能过。可以继续判断它是否**有意义**。
- `FAIL`：测试当前是红的。这本身是一个发现（测试坏了），不是“假测试”的证据。
- `SETUP ERROR`（JSON `setup_error: true`）：runner 没启动/依赖缺失；这不是测试缺陷，报告“执行不可用”。
- `NO TESTS`（JSON `zero_tests: true`）：没有发现测试；不要当成通过。
- `TIMEOUT`：不确定。不要当成 killed，也不要当成 survived。

**跑不起来**：缺依赖、缺配置、环境错误——报告“执行不可用”，继续静态审查；不要安装依赖，不要改配置来让它跑。

---

## 3. 变异探测：改坏行为，它会不会红

这是回答“测试有没有保护”的最强证据，但会临时改源码。**必须先得到用户明确同意**（例如用户说“可以临时改代码验证”）。用户没同意，就只做静态推断。

```bash
python "<skill-base>/scripts/probe_mutation.py" --root . \
  --file src/lib/discount.ts \
  --find "0.15" --replace "0.05" \
  --test-file src/lib/discount.test.ts \
  --name "applies the silver discount"
```

### 选什么改动

优先选**会改变行为、但不会让代码无法编译/运行**的一行：

- 常量：`0.15` → `0.05`
- 比较符：`>` → `>=`，`===` → `!==`
- 返回值：`return true` → `return false`
- 分支：删掉一个 `if`，或把条件取反
- 字符串：错误码/文案 → 另一个值
- 输入使用：`{user.name}` → `"Alice"`（UI 绑定检查）
- 边界：`limit` → `limit - 1`

不要选：改变量名、格式、注释、日志、纯类型标注。这些不改变行为，survived 不能说明测试弱。

### 结果怎么读

| 基线 | 变异后 | 结论 |
|---|---|---|
| PASS | FAIL | `killed`：测试抓住了这个行为变化 |
| PASS | PASS | `survived`：测试没有保护这个行为 |
| FAIL | 任意 | `baseline_failed`：测试本来就是红的，先修测试 |
| 跳过 | PASS | `survived_unverified_baseline`：不可靠，别当强证据 |
| 跳过 | FAIL | `inconclusive`：可能是别的原因导致失败 |
| 任意 | 启动失败/0 tests | `inconclusive`：改动把 runner/编译弄坏了，不算 killed |
| 任意 | TIMEOUT | `timeout`：不确定；除非改动明显会导致挂起，否则不要算 killed |

**一次只改一处、只跑一条测试。** 多个变异一起上，无法归因。

### 安全边界

脚本会：

1. 要求 `--find` 在文件里只出现一次；
2. 要求源码文件在 git 里是干净的，或显式 `--allow-dirty`；
3. 备份到系统临时目录；
4. 在 `finally` 里恢复原文件并校验 sha256；
5. 恢复失败时退出码 3，并打印备份路径。

即使如此，它仍然在改源码。遵守：

- 不要在用户没同意时运行。
- 不要在未提交的重要改动上运行；先 commit/stash，或至少确认备份可用。
- 不要在 CI/共享工作区运行。
- 恢复失败立即停止，报告备份路径；不要继续改别的文件。
- 不要并行跑多个变异。

---

## 4. 运行前后的检查

跑之前：

- [ ] 用户允许运行测试；变异探测另外需要允许改源码。
- [ ] 只选了一个文件/一个测试名。
- [ ] 没有 watch、没有 coverage、没有 `--updateSnapshot`。
- [ ] 知道基线的预期：这条测试本来是绿的还是红的。

跑之后：

- [ ] 记录命令、退出码、关键输出。
- [ ] 基线红 → 单独报“测试已红”。
- [ ] 变异 survived → 写清楚“改了什么、测试为什么没红”。
- [ ] 恢复校验通过；失败则停止。
- [ ] 结论标注证据级别。

---

## 5. 常见误用

- **把“跑通了”当成“测试有效”**：跑通只证明当前能过，不证明能抓住回归。
- **把“跑挂了”当成“测试无效”**：可能是环境/依赖/测试本身坏了。
- **用覆盖率代替变异**：覆盖到某行不等于断言了那行的结果。
- **一次跑全量套件**：慢、噪音大，而且不能回答“这条测试有没有用”。
- **为了让测试跑起来改配置/装依赖**：越界；报告执行不可用即可。
- **变异后不恢复**：脚本会恢复；如果手工做，必须用 `try/finally` 或先 commit。
- **把 flaky 当成 killed/survived**：先复跑一次确认；仍不稳定就标 `UNVERIFIED`。
