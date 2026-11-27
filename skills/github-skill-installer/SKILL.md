---
name: github-skill-installer
description: "从 GitHub 可靠安装 skill/技能/工具，绕开本机 git clone 卡住、zip/raw 下载不通、GitHub API 限流的问题。当用户说『帮我安装这个skill/把这个技能装上/装一下XX工具/从GitHub装个技能/这个工具怎么装/装刚才说的那个/点头了，装吧』，或开工工具扫描后用户明确同意安装某个工具时，使用本技能。自动探测仓库结构、走 CDN 并发下载、校验完整性、做运行自检，全程不消耗 GitHub API 逐文件配额。"
display_name: 技能可靠安装助手
version: 1.0.0
agent_created: true
tags: ["安装技能", "GitHub", "可靠下载", "小白友好"]
risk: safe
---

# 技能可靠安装助手（GitHub Skill Installer）

帮用户把一个 GitHub 上的 skill 稳稳装到本机。本机网络有个已知毛病：`git clone` 会卡在 HTTP2、zip 和 raw 下载域名不通、GitHub API 未认证每小时只有 60 次配额——普通安装方式十有八九失败。这个技能用验证过的办法绕开这些坑。

## 路径约定（先看这里）

下文命令里的 `<你的技能目录>` 指**你把本包装到本机后的实际位置**，不是固定路径。不同 Agent 的默认技能目录不一样（例如 Claude Code 常在 `~/.claude/skills`、Codex 常在 `~/.codex/skills`），以你自己的安装位置为准。安装目标目录可用环境变量 `WB_SKILLS_DIR` 覆盖。

## 什么时候用

- 用户明确点头要装某个工具/skill（如开工扫描后说"装吧"）
- 用户说"帮我装这个技能""从 GitHub 装个 XX""这个工具怎么装"
- 用户没同意、只是在问 → 只介绍不安装

## 核心原则

1. **用户点头才装**。没有明确同意绝不安装。
2. **先查再装**。装之前确认仓库是真的、有 SKILL.md、来源可靠。
3. **装完必验**。校验文件完整性 + 运行自检，不装半成品。
4. **失败要说实话**。装不上就如实说原因和替代方案，不留残broken目录。

## 工作流程

### 第 1 步：确认要装什么

从用户的话或上下文拿到 GitHub 仓库地址（`owner/repo`）。若用户只说了工具名，先查 `references/known-repos.md` 找有没有验证过的地址；没有就用 WebFetch/WebSearch 搜官方仓库。

**安装前安全检查**（问一句或自己判断）：
- 仓库是不是官方/知名作者？star 数、最近更新时间
- 是不是从搜索结果里冒出来的仿冒仓库（历史上出现过假冒热门 skill 骗安装量的）
- 用户若在意安全，提醒可先跑 SkillVetter 扫一遍

### 第 2 步：确定仓库内 skill 子目录

很多仓库的 skill 不在根目录，而在 `skills/xxx/` 下。探测办法：

```bash
curl -sL --max-time 30 "https://api.github.com/repos/<owner/repo>/git/trees/main?recursive=1" \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print('\n'.join(sorted(set(x['path'].rsplit('/',1)[0] for x in d.get('tree',[]) if x['path'].endswith('SKILL.md')))))"
```

列出所有含 SKILL.md 的目录，选主 skill 那个（通常是 `skills/<名字>` 或根目录 `.`）。

### 第 3 步：执行安装

```bash
bash <你的技能目录>/scripts/install.sh <owner/repo> <子目录> <本地名>
```

例：
```bash
bash <你的技能目录>/scripts/install.sh mvanhorn/last30days-skill skills/last30days last30days
bash <你的技能目录>/scripts/install.sh DeezGit21/skill-radar . skill-radar-from-gh
```

脚本自动完成：取文件树（1 次 API）→ jsDelivr CDN 12 路并发下载（不耗配额）→ 完整性校验 → 运行自检。默认装到环境变量 `WB_SKILLS_DIR` 指定的目录（未设时是你的主目录下 `skills/`），例如：

```bash
WB_SKILLS_DIR=<你的技能根目录> bash <你的技能目录>/scripts/install.sh mvanhorn/last30days-skill skills/last30days last30days
```

分支不是 main 时先设 `GH_BRANCH=master` 再跑。

### 第 4 步：核实结果并告诉用户

- 看脚本输出的 `FILECHECK missing=0 sizebad=0` 和 SKILL.md/主脚本自检结果
- 有失败文件 → 重跑一次（脚本会跳过已下好的，只补缺的）
- 装好后用一句大白话告诉用户：装好了没、能干嘛、怎么触发
- 提醒：新装的 skill 要**下次开会话**才进入自动触发列表

## 通道经验（本机实测，别再踩坑）

| 通道 | 结果 | 结论 |
|---|---|---|
| jsDelivr CDN `cdn.jsdelivr.net/gh/<repo>@<branch>/<path>` | ✅ 可用、无配额、大文件完整 | **首选** |
| GitHub API contents / git-trees | ✅ 可用但限流 60 次/时 | 只用来取文件树（1 次），不逐文件下 |
| `git clone` / zip / raw.githubusercontent.com | ❌ HTTP2 报错 / 域名不通 / 空响应 | 别用 |
| codeload tarball | ⚠️ HTTP 200 但大文件传不完整 | 别用 |
| `npx skills add` | ❌ 底层 git clone，同样卡住 | 别用 |

## 边界

- 只负责"把 skill 文件装到本机"，不做启动后的调用编排（那是各 skill 自己的事）。
- 星标/安装量只代表热度不等于质量；装第三方 skill 有安全风险，来源不明时先扫再装。
- 若 CDN 也拿不到某个文件，如实报告失败文件清单，不假装成功。
