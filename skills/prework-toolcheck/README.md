# prework-toolcheck

开工前自动扫描并列出本次任务可用的现成工具清单，只提醒、只推荐，未经点头绝不安装。

Automatically scan for and list existing tools relevant to the current task before you start working — reminder and recommendation only, never installs without explicit approval.

## 功能 / Features

- **开工提醒**：任务开始时自动扫一遍生态里有没有现成的技能、工具或 MCP，小白不用懂 skill 概念，看完清单点个头就行。**Prework reminder**: scan the ecosystem for existing skills, tools, or MCPs at task start; beginners need no skill knowledge — just review the list and approve.
- **三档清单**：按「已装可用 / 建议安装 / 可选」分类，每档最多 3 项，每项一句大白话说明能干嘛。**Three-tier list**: "already installed / recommended / optional", up to 3 items each, with a plain-language description per item.
- **默认离线**：开工默认只读本机已存数据，不联网、不回传；只有用户明确要求「重新扫」才联网。**Offline by default**: prework reads only local stored data — no network, no upload; network access only when the user explicitly asks to rescan.
- **无相关就闭嘴**：扫描结果没有和任务相关的工具时，不列清单、不提示安装，直接开工。**Silent when irrelevant**: if no tools match the task, no list, no install prompt — just start working.
- **装由别的技能做**：用户点头后交给 `github-skill-installer` 可靠安装，本技能自己不装。**Installation delegated**: after approval, `github-skill-installer` handles reliable installation; this skill never installs itself.

## 安装 / Installation

把本 skill 的 `SKILL.md`、`scripts/`、`references/`、`config/` 放到你所用 Agent 的技能目录，例如 `<你的技能根目录>/prework-toolcheck/`。不同 Agent 默认目录不同，以你自己的安装位置为准。

Place `SKILL.md`, `scripts/`, `references/`, and `config/` into your Agent's skills directory, e.g. `<your skills root>/prework-toolcheck/`. Default directories vary by Agent; use your actual installation path.

可选：注册 `scripts/hook_user_prompt_submit.py` 为 UserPromptSubmit hook，可在新会话第一次实质任务时自动提醒开工扫描。

Optional: register `scripts/hook_user_prompt_submit.py` as a UserPromptSubmit hook to auto-remind prework scanning on the first substantive task of each new session.

## 用法 / Usage

在对话里说「开工前看看有什么工具能用」「这个任务该用什么」「新手必装什么」，或被 hook 自动触发时，本技能执行扫描。

Say "what tools can I use before starting", "what should I use for this task", "what must a beginner install", or let the hook trigger it — this skill performs the scan.

命令行直接调用 / Invoke directly:

```bash
# 开工默认：只读本机已存数据（离线）/ default: local data only (offline)
bash <你的技能目录>/scripts/scan.sh "<任务原话>"

# 用户明确要求联网时 / when the user explicitly requests network access
bash <你的技能目录>/scripts/scan.sh "<任务原话>" --online

# 强制重扫 / 只看本机 / 不回传 / force rescan / local only / no upload
python3 <你的技能目录>/scripts/scan_cached.py "<任务>" --force
python3 <你的技能目录>/scripts/scan_cached.py "<任务>" --no-shared
python3 <你的技能目录>/scripts/scan_cached.py "<任务>" --no-upload
```

清单末尾会明确问你装不装、用不用，得到回答后才继续。详见 `SKILL.md`。

The list ends by explicitly asking whether to install or use anything; work continues only after your answer. See `SKILL.md` for details.

## 许可 / License

**允许个人自用，禁止商业使用。 / Personal use only; commercial use is prohibited.**

详见 [LICENSE](LICENSE)：可免费自用、修改与传播，但未取得书面许可不得用于任何商业目的（含在商业产品/服务中集成、调用或有偿提供）。

See [LICENSE](LICENSE): free for personal use, modification, and distribution, but no commercial use (including integration, invocation, or paid provision in commercial products/services) without written permission.
