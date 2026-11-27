# WorkBuddy 小白工具包

[![skills.sh](https://img.shields.io/badge/skills.sh-install-black)](https://skills.sh)

给 AI 智能体新手的三件小工具：**开工前自动扫一遍有什么现成工具能用，你点头后稳稳装上，不用懂 skill 概念。**

三件skill解决一个完整闭环：发现工具 → 可靠安装 → 自动提醒。

## 包含什么

| 技能 | 作用 | 状态 |
|---|---|---|
| `prework-toolcheck` | 开工前按任务扫描工具，列「已装可用 / 建议安装 / 可选」三档清单，只推荐不安装 | 核心 |
| `github-skill-installer` | 从 GitHub 可靠安装 skill，绕开 git clone 卡住、API 限流；CDN 并发下载 + 完整性校验 | 核心 |
| `skill-radar-cn` | 中文入口，用大白话触发扫描（"开工前看看有什么工具能用"） | 入口 |

## 一键安装

```bash
npx skills add suiyue145/AI-agent-beginner-essential-toolbox
```

安装后可分别指定：

```bash
npx skills add suiyue145/AI-agent-beginner-essential-toolbox --skill github-skill-installer
```

支持 Claude Code、Cursor、Codex、GitHub Copilot、Windsurf 等约 20 种 Agent。

## 怎么用（小白视角）

1. 开工时说一句："开工前帮我看看这个任务有什么现成工具"
2. 它列出三档清单，每项一句大白话说明能干嘛
3. 你说"装 XX"或直接开始——**没点头绝不安装**
4. 点头后由 `github-skill-installer` 走 CDN 通道装，装完校验文件完整性

## 共享扫描结果：先看云端，没有再自己扫

每次开工扫描按这个顺序走：

1. **先查 GitHub**：有没有这个任务 **3 天内** 的共享结果？有就下载直接用，标 `[云端命中]`。
2. **再看本机**：GitHub 没有/过期，就看本机 3 天内自己扫过的缓存。
3. **自己扫**：都没有才现场扫描，结果存本机 3 天。

共享结果由维护者定期生成，放在公开仓库 `suiyue145/AI-agent-beginner-essential-toolbox`。你**不用配置 token、不用做任何维护**，匿名即可下载；没联网或没收录时会自动降级到本机扫描，不卡住。云端清单 6 小时最多检查一次。

想临时只看本机、不查云端：给扫描命令加 `--no-shared` / `--no-upload`。

## 可选依赖

`prework-toolcheck` 和 `skill-radar-cn` 的**本机实时扫描**功能依赖 `skill-radar`（MIT 开源，DeezGit21/skill-radar）。不装也能用——共享结果正常显示，只是没收录的任务无法现场扫。

本仓库 `vendor/` 提供**多平台增强版**扫描逻辑（原版的覆盖补丁），扫描范围覆盖：

- **skills.sh 热门榜**（跨平台 8000+ skill 的统一目录，按真实安装量排序）
- **官方目录**：Anthropic skills、OpenAI Codex skills、Vercel agent-skills、DeepSeek Harness（dsh）、Hermes Agent
- **各平台 topic**：WorkBuddy、codex-skills、claude-skills、agent-skills
- MCP 注册表、GitHub 通用搜索

安装步骤（先装原版，再用本包覆盖增强）：

```bash
# 1) 安装原版 skill-radar（网络能通 git clone 时）
#    <你选的目录> 换成你的安装位置，例如 ~/.claude/skill-radar、
#    ~/.codex/skill-radar 或你自己的工具目录，本包不强制具体路径
git clone --depth 1 https://github.com/DeezGit21/skill-radar.git <你选的目录>/skill-radar
cd <你选的目录>/skill-radar && python3 -m pip install -e .
# 若 git clone 不通，可用本包的 github-skill-installer 走 CDN 通道装

# 2) 覆盖为多平台增强版（本仓库根目录执行）
#    若 skill-radar 装在非默认位置，先指定再运行：
#    export WB_SKILL_RADAR_DIR="<你选的目录>/skill-radar"
bash vendor/install.sh
```

增强版会自动读取环境变量 `GITHUB_TOKEN`（可选）把 API 配额从 60 次/小时提到 5000 次/小时；不配 token 也能匿名扫描，只是较慢。`vendor/install.sh` 会先备份原文件为 `*.bak-multipublish`，可随时还原。

## 自动触发（可选，WorkBuddy 用户）

`prework-toolcheck/scripts/hook_user_prompt_submit.py` 是 UserPromptSubmit hook：每个新会话的第一次实质任务会自动提醒先做开工扫描，后续追问不打扰。

把它注册到 Agent 的 hook 配置文件（即你所用 Agent 的 `settings.json` 路径，例如 Claude Code 用 `~/.claude/settings.json`；路径以你实际安装位置为准）：

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python3 <本skill路径>/scripts/hook_user_prompt_submit.py",
            "timeout": 10
          }
        ]
      }
    ]
  }
}
```

不想用了：`touch <本skill路径>/scripts/.disabled`。

## 安全边界

- **只推荐，绝不自动安装**——安装必须用户明确点头。
- 星标/安装量只代表热度，不等于质量。有实测显示安装量 Top10 里只有 3 个能跑通首条命令。
- 第三方 skill 有安全风险（历史上出现过恶意技能与伪造下载量）。来源不明的先审查再装。
- 安装脚本只做下载与校验，不修改你的系统配置，不执行被装 skill 的代码。

## 许可

MIT — 详见 [LICENSE](LICENSE)。
