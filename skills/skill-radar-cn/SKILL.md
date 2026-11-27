---
name: skill-radar-cn
description: "开工前扫描必用工具并列出候选清单供用户选用。当用户说『开工前帮我看看有哪些工具能用/有什么工具适合这个任务/扫一下有没有现成的工具或技能/这个活儿有没有现成的skill/先找找有没有能用的工具/有哪些MCP或技能可以帮我做X/看看本机能用什么工具/调研一下有什么现成方案可以用』时触发。从 GitHub、MCP 注册表、技能市场扫描相关技能/工具，按相关度+星标+新鲜度评分，只推荐绝不自动安装，列出清单让用户挑选。注意：本技能只做发现与推荐，不负责拆解任务与自动调用工具。"
version: 1.5.0-cn
tags: ["工具发现", "开工扫描", "技能推荐", "MCP", "小白友好"]
risk: safe
---

# Skill Radar 中文版（开工前工具扫描）

帮你在动手之前，先看看生态里有没有现成的技能、MCP 服务器或工具可以用——只推荐、不安装，你挑中哪个再装。

## 什么时候用

- 你说"开工前扫一下有什么工具能用" → 用本技能
- 你说"这个任务有没有现成的 skill / MCP" → 用本技能
- 你说"先找找有没有能用的工具" → 用本技能
- 你说"调研一下有什么现成方案" → 用本技能

## 怎么执行（GitHub 共享结果 → 本机缓存 → 真扫 → 回传）

### 方式一：按任务扫描（用户给了具体任务）★ 首选

```bash
python3 ~/.workbuddy/skills/prework-toolcheck/scripts/scan_cached.py "<用户的任务描述>"
```

取结果顺序（命中即停）：

- **GitHub 共享结果（优先）**：先查 GitHub 上有没有这个任务 3 天内的扫描结果，有就下载直接用，标 `[云端命中]`；公开仓库，匿名即可读取。
- **本机缓存**：GitHub 没有/过期时，复用本机 3 天内自己扫过的结果。
- **真实扫描**：都没有才现场扫描，结果存本机缓存，3 天有效。
- **回传 GitHub**：本机扫描成功后，这一条会自动合并上传到 GitHub（公开仓库），别的机器下次就能直接下载。
- 云端清单 6 小时最多检查一次，条目自身 3 天过期；网络不通/没配 token 自动降级，不卡住。
- 中文任务已内置中英关键词映射（"调研市场"→ research market），同类任务用词略有不同也能命中。

用户明确说"重新扫/刷新/要最新的"时：

```bash
# 强制本机重扫
python3 ~/.workbuddy/skills/prework-toolcheck/scripts/scan_cached.py "<任务>" --force
# 只强制刷新公共清单
python3 ~/.workbuddy/skills/prework-toolcheck/scripts/scan_cached.py "<任务>" --refresh-shared
# 本次不用云端结果
python3 ~/.workbuddy/skills/prework-toolcheck/scripts/scan_cached.py "<任务>" --no-shared
# 本次扫描后不回传 GitHub
python3 ~/.workbuddy/skills/prework-toolcheck/scripts/scan_cached.py "<任务>" --no-upload
```

### 方式二：全量扫描新工具（用户只说"扫一下"）

```bash
skill-radar cron-scan --min-stars 100
```

这会找出之前没见过的新工具（此命令不走任务缓存）。

### 方式三：用封装脚本（结果自动存档）

```bash
bash <本skill同级目录>/prework-toolcheck/scripts/scan.sh "<任务描述>"
```

内部走同一份缓存，结果自动存档（可用 `WB_SCAN_OUT` 指定存档目录）。

### 缓存管理

缓存文件：`~/.skill-radar/scan-cache.json`。想清空全部缓存让它下次全量重扫，删除该文件即可（安全，只影响扫描结果）。

## 输出要求

扫描结果出来后：
1. 按类别分组展示（MCP 服务器 / Agent 技能 / 工具 / 插件）
2. 每项显示：名称、星标、一句话说明、为什么推荐
3. 明确告诉用户：**这里只推荐、不安装**
4. 问用户看中哪个，得到明确同意后才执行安装

## 重要边界

- 本技能**只做发现与推荐**，不做任务拆解、不做工具自动调用
- **绝不自动安装任何东西**——这是设计原则
- ★100+ 星门槛过滤低信誉仓库，但星标不等于质量
- 用户是小白，解释时用大白话，不要堆术语

## 故障排查

如果报 `gh: command not found` 或 GitHub 搜索失败：说明底层补丁失效，检查 `~/.workbuddy/skill-radar/skill_radar.py` 的 `github_search` 函数是否还在用 curl（原文件备份为 `skill_radar.py.orig`）。

安装位置：`~/.workbuddy/skill-radar`（cli 命令 `skill-radar`）。
