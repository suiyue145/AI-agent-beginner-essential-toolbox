# prework-toolcheck

开工前自动扫描并列出本次任务可用的现成工具清单，只提醒、只推荐，未经点头绝不安装。

## 功能

- **开工提醒**：任务开始时自动扫一遍生态里有没有现成的技能、工具或 MCP，小白不用懂 skill 概念，看完清单点个头就行。
- **三档清单**：按「已装可用 / 建议安装 / 可选」分类，每档最多 3 项，每项一句大白话说明能干嘛。
- **默认离线**：开工默认只读本机已存数据，不联网、不回传；只有用户明确要求「重新扫」才联网。
- **无相关就闭嘴**：扫描结果没有和任务相关的工具时，不列清单、不提示安装，直接开工。
- **装由别的技能做**：用户点头后交给 `github-skill-installer` 可靠安装，本技能自己不装。

## 安装

把本 skill 的 `SKILL.md`、`scripts/`、`references/`、`config/` 放到你所用 Agent 的技能目录，例如 `<你的技能根目录>/prework-toolcheck/`。不同 Agent 默认目录不同，以你自己的安装位置为准。

可选：注册 `scripts/hook_user_prompt_submit.py` 为 UserPromptSubmit hook，可在新会话第一次实质任务时自动提醒开工扫描。

## 用法

在对话里说「开工前看看有什么工具能用」「这个任务该用什么」「新手必装什么」，或被 hook 自动触发时，本技能执行扫描。

命令行直接调用：

```bash
# 开工默认：只读本机已存数据（离线）
bash <你的技能目录>/scripts/scan.sh "<任务原话>"

# 用户明确要求联网时
bash <你的技能目录>/scripts/scan.sh "<任务原话>" --online

# 强制重扫 / 只看本机 / 不回传
python3 <你的技能目录>/scripts/scan_cached.py "<任务>" --force
python3 <你的技能目录>/scripts/scan_cached.py "<任务>" --no-shared
python3 <你的技能目录>/scripts/scan_cached.py "<任务>" --no-upload
```

清单末尾会明确问你装不装、用不用，得到回答后才继续。详见 `SKILL.md`。

## 许可

**允许个人自用，禁止商业使用。**

详见 [LICENSE](LICENSE)：可免费自用、修改与传播，但未取得书面许可不得用于任何商业目的（含在商业产品/服务中集成、调用或有偿提供）。
