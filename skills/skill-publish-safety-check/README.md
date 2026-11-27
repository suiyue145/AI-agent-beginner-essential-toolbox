# skill-publish-safety-check

在把 skill 提交到网上或发布到技能市场前做安全检查，清除生成环境痕迹。

Run a safety check before publishing a skill online or to a skill marketplace, removing traces of the authoring environment.

## 功能 / Features

- **隐私泄漏扫描**：API key、token、真实邮箱、家目录绝对路径、内网主机名、公网 IP。**Privacy leak scan**: API keys, tokens, real email addresses, absolute home-directory paths, internal hostnames, public IPs.
- **生成环境痕迹清理**：把 `.workbuddy` / `.claude` 路径、工作区绝对路径改写成读者需自行填写的占位符（如 `<你的技能目录>`）。**Authoring-environment cleanup**: rewrite `.workbuddy` / `.claude` paths and absolute workspace paths into placeholders for readers to fill in (e.g. `<your skills directory>`).
- **README 维护者脱敏**：删除维护者章节、字段行、本机配置行，以及 `<!-- publish:remove -->` 标注区块。**README maintainer redaction**: remove maintainer sections, field lines, local configuration lines, and blocks marked `<!-- publish:remove -->`.
- **非破坏性**：只改暂存副本，绝不改动源 skill 目录。**Non-destructive**: only staging copies are modified; the source skill directory is never touched.

## 安装 / Installation

把本 skill 的 `SKILL.md`、`scripts/`、`references/` 放到你所用 Agent 的技能目录，例如 `<你的技能根目录>/skill-publish-safety-check/`。不同 Agent 默认目录不同，以你自己的安装位置为准。

Place `SKILL.md`, `scripts/`, and `references/` into your Agent's skills directory, e.g. `<your skills root>/skill-publish-safety-check/`. Default directories vary by Agent; use your actual installation path.

## 用法 / Usage

在其他 agent 准备发布 skill 版本、提交技能市场或做发布前脱敏审查时，依次执行三步：

When another agent is about to publish a skill version, submit to a marketplace, or perform a pre-release redaction review, run these three steps in order:

```bash
python3 scripts/skill_publish_check.py scan <skill目录>
python3 scripts/skill_publish_check.py sanitize <skill目录> --out <暂存目录>
python3 scripts/skill_publish_check.py verify <暂存目录>
```

`scan` 报硬问题（真实密钥等）须人工处理；`verify` 退出码为 0 才表示可发布。详细规则、配置格式与边界见 `SKILL.md` 与 `references/rewrite-rules.md`。

Hard issues reported by `scan` (e.g. real secrets) require manual handling; only an exit code of 0 from `verify` means the skill is ready to publish. See `SKILL.md` and `references/rewrite-rules.md` for full rules, configuration format, and limitations.

## 许可 / License

**允许个人自用，禁止商业使用。 / Personal use only; commercial use is prohibited.**

详见 [LICENSE](LICENSE)：可免费自用、修改与传播，但未取得书面许可不得用于任何商业目的（含在商业产品/服务中集成、调用或有偿提供）。

See [LICENSE](LICENSE): free for personal use, modification, and distribution, but no commercial use (including integration, invocation, or paid provision in commercial products/services) without written permission.
