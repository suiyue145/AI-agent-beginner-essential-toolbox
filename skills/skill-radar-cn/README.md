# skill-radar-cn

开工前扫描必用工具并列出候选清单供你挑选，只推荐、不安装。

## 功能

- **多源扫描**：覆盖 skills.sh 热门榜、Anthropic / OpenAI Codex / Vercel / DeepSeek Harness / Hermes Agent 官方目录、各平台 topic、MCP 注册表与 GitHub 通用搜索。
- **云端优先**：先查 GitHub 上 3 天内的共享扫描结果（匿名可读），命中即停；没有再用本机缓存，都没有才现场扫描。
- **结果回传**：本机扫描成功后自动合并上传到公开仓库，别的机器下次可直接下载；网络不通或未配 token 时自动降级，不卡住。
- **中文友好**：内置中英关键词映射（如「调研市场」→ research market），同类任务用词略有不同也能命中。
- **只推荐不装**：按类别分组展示名称、星标、一句话说明与推荐理由，你看中哪个再决定装不装。

## 安装

把本 skill 的 `SKILL.md` 放到你所用 Agent 的技能目录，例如 `<你的技能根目录>/skill-radar-cn/`。

本技能依赖 `prework-toolcheck` 技能内的 `scripts/scan_cached.py` 与底层 `skill-radar`（CLI）。两者装在同一技能目录下时路径可直接使用；否则按 `SKILL.md` 里的「路径约定」替换占位符。GitHub API 限流时可配置环境变量 `GITHUB_TOKEN` 提到 5000 次/小时，不配也能匿名扫描，只是较慢。

## 用法

在对话里说「开工前帮我看看有哪些工具能用」「这个任务有没有现成的 skill / MCP」「先找找有没有能用的工具」，本技能自动触发。

命令行按任务扫描：

```bash
python3 <你的技能目录>/../prework-toolcheck/scripts/scan_cached.py "<任务描述>"
```

用户说「重新扫 / 要最新的」时：

```bash
python3 <你的技能目录>/../prework-toolcheck/scripts/scan_cached.py "<任务>" --force
python3 <你的技能目录>/../prework-toolcheck/scripts/scan_cached.py "<任务>" --refresh-shared
python3 <你的技能目录>/../prework-toolcheck/scripts/scan_cached.py "<任务>" --no-shared
```

缓存文件在 `~/.skill-radar/scan-cache.json`，删除即全量重扫。扫描范围可用 `skill-radar list-sources` 查看。详见 `SKILL.md`。

## 许可

**允许个人自用，禁止商业使用。**

详见 [LICENSE](LICENSE)：可免费自用、修改与传播，但未取得书面许可不得用于任何商业目的（含在商业产品/服务中集成、调用或有偿提供）。
