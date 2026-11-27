# 小白必装工具基线清单

> 来源：2026-11 对 42 个智能体对象的六轮公开资料调研（工具清单与风险提示，非广告）。
> 用法：开工扫描命中某工具后，来这里对照它的定位、风险、是否免费。
> 原则：清单宁短不长。星标/安装量只代表热度，不代表质量。

## 一、通用底座（几乎任何任务都值得有）

| 工具 | 一句话能帮你干嘛 | 费用 | 风险提示 |
|---|---|---|---|
| find-skills（vercel-labs） | 你用大白话说需求，它帮你找到合适的技能，不用记暗号 | 免费 | 社区实测建议话里带"skill"更保险；安装量 4.5M 是热度非质量 |
| skill-radar | 开工前扫 GitHub/MCP/技能市场，评分后列清单，只推荐不安装 | 免费 MIT | 可选依赖；需手动触发；评分门槛是星标，不等于好用 |
| 深度研究 deep-research | 专业调研、多源交叉验证、生成报告 | 免费 | 需点名"用 deep-research"或说"深度调研" |

## 二、宿主环境常见内置技能（很多 Agent 自带，先看看有没有）

| 工具 | 触发说法 | 能帮你干嘛 |
|---|---|---|
| multi-search-engine | "搜一下/多找几个来源/核实消息" | 跨 16 个引擎检索、去重、交叉验证 |
| deep-research | "用 deep-research 调研 X" | 结构化深度调研并出报告 |
| pii-redact | "把这段信息脱敏" | 敏感信息脱敏（注意：若无 description 则触发不了，需先补 frontmatter） |
| agent-local-memory-keeper | "帮我一键配好记忆" | 跨会话记住你的偏好 |
| skill-radar-cn | "开工前扫一下有什么工具" | 本仓库的中文入口技能 |

提示：不同 Agent 内置技能不同。开工扫描脚本会先列出你本机实际已装的，以那个为准。

## 三、按任务类型选

| 任务类型 | 首选工具 | 小白友好度 | 备注 |
|---|---|---|---|
| 深度调研 / 市场分析 | deep-research + multi-search-engine | 高 | 已装 |
| 做 PPT / Word / Excel / 脑图 | WorkBuddy 内置 Office 技能 | 高 | 说"做个PPT"即可，无需外装 |
| 敏感资料处理 | LobsterAI（有道龙虾）+ pii-redact | 中 | LobsterAI MIT 开源、可接 Ollama 断网跑；GUI 一键装 |
| 无人值守跑任务 | Kimi Work / 阶跃 AI 桌面版 | 中 | 本地桌面、每敏感步骤确认；Kimi 需会员 |
| 找并试新技能 | DeepSkill（美团） / SkillsMP | 中 | DeepSkill 按真实运行记录排序，不看下载量；SkillsMP 400K+ 但质量参差 |
| 搜最近30天社交平台找人/找话题 | last30days | 高 | 免密钥源（Reddit/HN/Digg/arXiv 等）可直接用。仓库大（204 文件/19MB），若 git clone 被网络拦，用本仓库的 github-skill-installer 走 CDN 通道装。用 `--research-only --quick` 试跑，主题走位置参数，`--search` 只收源名不收自由文本 |
| 装前安全审查 | SkillVetter | 中 | 手动触发、需 OpenClaw；ClawHavoc 事件 11.9% 恶意样本 |

## 四、红线工具（默认行为与"开工前确认"相悖，提醒后才建议）

| 工具 | 风险 |
|---|---|
| Goose | 默认"完全自主"，改删文件不询问，小白必须先改档 |
| Claude Code（新版） | 默认 auto 分类器替代人工弹窗，且需联网+付费 |
| Microsoft Scout | 能力最全但需企业 Frontier 资格+管理员，小白拿不到 |
| 各类" installer 一键装"脚本 | 装前先验来源；不要盲目复制陌生仓库的安装命令 |

## 五、别被数字骗了（调研已证伪）

- find-skills 4.5M 安装、SkillsMP 434 万文件数、DeepSkill 35.9 万条目 —— 全是热度/条目数，不是质量。
- 有实测把安装 Top10 逐个跑：只有 3 个能跑通首条命令，第 2 名 skill 的 SKILL.md 只有 157 字节。
- "危险命令拦截率 89% vs 人工 13.6%" 是 Claude Code Auto Mode 的数据，不是 Goose 的——别记混。
- 厂商宣传的"零配置""启动即扫描"多是话术，落地往往要敲一条命令或配一次 cron。
