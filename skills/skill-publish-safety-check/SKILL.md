---
name: skill-publish-safety-check
description: 在把 skill 提交到网上或发布到技能市场前做安全检查，清除生成环境痕迹。检测 API key、token、真实邮箱、家目录路径等敏感信息与 .workbuddy/.claude 环境路径，把环境路径改成读者需自行填写的占位符，并从 README 移除维护者配置。当其他 agent 准备发布 skill 版本、提交技能市场、或需要给 skill 做发布前脱敏审查时，应使用本 skill。
agent_created: true
---

# Skill 提交前安全检查

## 用途

在 skill 对外发布前拦两件事：

1. **隐私泄漏**：密钥、token、真实邮箱、本机家目录绝对路径、内网主机名、公网 IP。
2. **生成环境痕迹**：本机 `.workbuddy` / `.claude` 路径、工作区绝对路径、README 里的维护者配置。

核心原则：**只改暂存副本，绝不改动源 skill 目录**。发布者从暂存目录发布，源文件保持原样。

## 何时使用

- 其他 agent 要把一个 skill 发布到网上 / 技能市场 / GitHub 仓库。
- 用户说「发布前检查一下」「提交给市场前脱敏」「去掉本机路径」。
- 需要判断一个 skill 目录是否含有不该公开的生成环境信息。

不使用：只想检查单个文件的一两处文本（直接用编辑工具）；管理真实密钥（用密钥管理工具，本 skill 只处理文档与示例数据）。

## 标准流程

### 第 1 步：只读扫描

```bash
python3 scripts/skill_publish_check.py scan <skill目录>
```

输出四类：`hard`（硬问题，必须处理才能发布）、`warn`（需人工确认）、`env_hits`（环境路径痕迹）、`readme_maintainer`（README 维护者项）。退出码 1 表示有硬问题。

### 第 2 步：生成干净暂存副本

```bash
python3 scripts/skill_publish_check.py sanitize <skill目录> --out <暂存目录>
```

脚本会：

- 复制发布器实际会收集的文件（跳过运行态产物、平台元数据、软连接）；
- 把家目录 / `.workbuddy/skills/<技能名>` / 工作区绝对路径替换为读者占位符，如 `<你的技能目录>`、`~`、`%USERPROFILE%`；
- 从 README 删除维护者章节、维护者字段行、维护者本机配置行，以及 `<!-- publish:remove -->` 标注的区块。

`<暂存目录>` 必须位于源目录之外且尚不存在。需要自定义规则时加 `--config <配置.json>`，格式见 `references/rewrite-rules.md`。

### 第 3 步：校验暂存副本

```bash
python3 scripts/skill_publish_check.py verify <暂存目录>
```

退出码 0 才算通过。若仍报残留，回到源文件用编辑工具处理后再重新 sanitize。

### 第 4 步：人工复核

脚本只做确定性改写，无法判断语义层面的业务指纹。发布前仍需人工确认：业务名称、客户名、内部项目代号、示例数据是否可公开。

## 判定口径

- `hard` 命中一律阻断发布：API key、私钥块、GitHub/Slack/Google/AWS token、明文口令。
- `warn` 与 `env_hits` 需人工确认：真实邮箱、家目录路径、`.workbuddy` / `.claude` 字样、内网主机名、公网 IP。文档里的占位示例写法（`<xxx>`、`example`、`your_*` 等）自动豁免，不计入。
- README 维护者项一律视为应清除，因为读者不需要维护者本机的路径与配置。

详细规则、配置格式与边界见 `references/rewrite-rules.md`。

## 资源

- `scripts/skill_publish_check.py`：扫描 / 改写 / 校验三合一脚本，无第三方依赖，Python 3.10+。
- `references/rewrite-rules.md`：完整规则表、配置示例、误报处理与已知边界。
