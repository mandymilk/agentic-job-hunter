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

## 完整使用流程（分步）

1. **准备** —— 在 `inbox/input.md` 中：选择 `runtime`、填写 **Preferences（偏好）**，
   并在标记行下方粘贴你的**简历**。
2. **map** —— agent 会构建一份*有策略的*目标公司清单 → `data/companies.md`
   （策略见下文）。
3. **source** —— 读取每家公司的**公开 ATS**，登记符合条件的高级职位；对于无法读取的
   招聘板，则生成可直接点击的搜索链接。
4. **ingest**（可选）—— 规整你粘贴进 `inbox/jobs.md` 的职位（例如来自
   LinkedIn/Indeed —— 见下文）。
5. **rank** —— 对照*你自己的*简历给每个职位打分，并生成 **`output/ranking.html`**。
6. **查看并迭代** —— 打开该 HTML，排序/筛选，点击某行查看完整评估 + 职位描述，
   并用 **Advanced（高级）** 面板去其他招聘站搜索。粘贴更多职位或调整偏好后重新运行，
   只有发生变化的内容才会被重新打分。

### 🎯 目标公司清单是一种*策略*，而非随意抓取

**map** 这一步不会堆砌无关公司，而是在 `data/companies.md` 中构建一份精心筛选的清单：

- **信誉门槛** —— 只收录上市/知名公司，或近期获得顶级投资方（a16z、Sequoia、
  Benchmark、Accel、Lightspeed、Tiger、Index、GV 等）投资的初创公司，不收录默默无闻的公司。
- **契合*你自己*** —— 依据你的简历 + 偏好（行业、职位类型、地点）来匹配；始终包含你的
  **preferred/seed（优先/种子）公司**，绝不出现你**屏蔽**的公司。
- **每家公司都有可读来源** —— 每一行都标注了 `tier`
  （`ats` · `browser` · `walled` · `manual`）和 `source`（如 `greenhouse:stripe`），
  让 source 步骤清楚知道该如何读取。

你可以随意编辑 `data/companies.md` 来调整方向，然后重新运行 `source` → `rank`。

### 📋 在 LinkedIn / Indeed 上看到心仪职位？粘贴进来，一样会被打分

我们绝不抓取 LinkedIn/Indeed/聚合站点 —— 但你可以自己把任意职位交给匹配器。打开
**`inbox/jobs.md`**，粘贴职位内容，然后运行 **ingest**（`api` 运行方式会自动完成）。
它会像自动抓取的职位一样，用同一套诚实的评分标准对照你的简历打分并排名。

```
## Job
URL: https://www.linkedin.com/jobs/view/1234567890
Description: <把完整的职位描述粘贴到这里>
---
```

小贴士：如果是可抓取的公司招聘页，只填 URL 即可（ingest 会自动抓取 JD）；而
LinkedIn 等受限聚合站点则需要粘贴完整的 **Description**。`output/ranking.html` 中的
**Advanced** 面板提供了预填的 LinkedIn / Indeed / Google 搜索链接，方便你快速找到这些职位。

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
