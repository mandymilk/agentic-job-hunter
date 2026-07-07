# agentic-job-hunter

[English](README.md) · **简体中文**

把你的简历变成一份来自**优质公司**、**可排序、可点击的职位清单**——对于无法自动抓取的
渠道，还会为你生成可直接点击的搜索链接。

- **零代码：** 粘贴简历、运行 agent、打开一个 HTML 文件即可。
- **诚实匹配：** 严格对照*你自己的*简历打分（技能 > 资历 > 地点 > 薪资），
  匹配度弱的职位排名自然靠后。只对发生变化的内容重新打分。
- **合规且仅追踪（track-only）：** 只读取公司自己的招聘页和公开的 ATS 招聘板；
  对于 LinkedIn/Indeed 等只生成搜索链接，绝不抓取。**绝不自动投递。**

## 快速开始 —— 你只需做两件事

所有需要你编辑的内容都在**同一个文件**里：[`inbox/input.md`](inbox/input.md)。

1. **编辑 `inbox/input.md`：**
   - 把 `runtime:` 设为你想用的运行方式（`copilot` · `claude` · `codex` · `api`）。
   - 编辑 **Preferences（偏好）**（目标职位、地点、行业、屏蔽的公司等）。
   - 在 `--- PASTE RESUME BELOW THIS LINE ---` 这一行下方**粘贴你的简历**。

   _（想立刻试用？把 [`samples/input.sample.md`](samples/input.sample.md) 复制成
   `inbox/input.md` 即可。）_
2. **运行它** —— 按你选择的 `runtime` 对应的方式运行（见下表）。不确定？
   直接运行 `python scripts/run.py`，它会读取你的选择并告诉你下一步该怎么做。

随后打开 **`output/ranking.html`**：一个可排序、可筛选的职位表（点击任意一行可展开
完整评估 + 职位描述），并附带一个 **Advanced（高级）** 面板，内含可直接点击的
LinkedIn / Indeed / Google 搜索链接。

### 运行方式 —— 选择你的 runtime

| `runtime:` | 如何运行 | 由谁驱动 |
|------------|---------|----------|
| `copilot` | 在 VS Code 中打开 Copilot Chat，选择 **`job-hunter`** agent，输入 *"run the job hunt"* | [`.github/`](.github) 提示词 + agent |
| `claude`  | 在 **Claude Code** 中打开本仓库，输入 *"run the job hunt"* | [`CLAUDE.md`](CLAUDE.md) |
| `codex`   | 在 **Codex** 中打开本仓库，输入 *"run the job hunt"* | [`AGENTS.md`](AGENTS.md) |
| `api`     | 无界面运行：`export OPENAI_API_KEY=…` 然后 `python scripts/run.py` | [`scripts/run.py`](scripts/run.py) |

无论用哪种方式，**流程完全相同** —— 都是同样的 4 步（map → source → ingest → rank），
区别只在于驱动它的工具不同。

## 工作原理

```
                    ┌─ Preferences ─┐
inbox/input.md ─────┤               ├─▶ map ──▶ data/companies.md（每家公司的 tier + source）
   (runtime +       └─ Résumé ──────┘             │
    prefs + résumé)                      source ──┼─▶ 可读招聘板 → data/jobs/ 职位库
                                                  └─▶ 受限/聚合站点 → data/manual-search-links.md
                                        │ （你粘贴 JD）▶ inbox/jobs.md ─▶ ingest
                                        ▼
                          rank ──▶ data/results/ + output/ranking.html
```

Agent 负责编排；确定性的工作由 `scripts/` 下仅依赖标准库的 Python 脚本完成：

| 脚本 | 作用 |
|------|------|
| `run.py` | 单一入口 —— 读取 `runtime:` 并路由（`api` 模式下直接运行整个流程） |
| `ats_fetch.py` | 读取 Greenhouse / Lever / Ashby / SmartRecruiters / Workday 招聘板（`--save` 直接登记职位） |
| `make_search_links.py` | 根据偏好生成 LinkedIn / Indeed / Google 搜索链接 |
| `browser_fetch.py` | *可选* 的 Playwright 助手，用于 JS/DOM 类招聘板（`pip install playwright`） |
| `score.py` | *可选* 的无界面打分，需要 `OPENAI_API_KEY`（默认由 agent 完成打分） |
| `build_html.py` | 生成可视化的 `output/ranking.html` |

在仓库根目录运行任意脚本，例如：

```bash
python scripts/run.py                         # 根据 inbox/input.md 进行路由
python scripts/ats_fetch.py greenhouse stripe --senior --save --company Stripe
python scripts/make_search_links.py
python scripts/build_html.py
```

`--save` 会把匹配到的职位直接登记进职位库，并使用**幂等、防冲突**的 id
（重复运行不会产生重复项；同名不同城市的职位会按地点自动区分）；
加上 `--json` 可输出机器可读的结果。

## 不使用 agent 也能匹配（可选）

`api` 运行方式（设置 `OPENAI_API_KEY` 后运行 `python scripts/run.py`）会无界面地
跑完整个流程。若只想重新打分，运行 `python scripts/score.py`，再运行
`python scripts/build_html.py`。

## 合规与安全

只读取公司**自己的**招聘页和**公开的 ATS** 接口。**不会**抓取
LinkedIn/Indeed/聚合站点，也不会绕过反爬虫验证 —— 对这些渠道只生成搜索链接。
**仅追踪（track-only）：** 任何内容都不会被自动提交。可选的 `browser_fetch.py`
仅用于公司自己的招聘页；使用它即表示你自行承担服务条款与稳定性方面的风险。

你的简历始终保存在本地。采用 MIT 许可证 —— 详见 [LICENSE](LICENSE)。
