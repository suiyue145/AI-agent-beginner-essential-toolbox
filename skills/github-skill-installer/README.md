# github-skill-installer

从 GitHub 可靠安装 skill / 技能 / 工具，绕开 `git clone` 卡住、raw/zip 下载不通、GitHub API 限流的问题。

## 功能

- **确认再装**：仓库真实性、来源可靠性先查一遍，用户没点头绝不安装。
- **可靠下载**：自动探测仓库结构（根目录还是 `skills/xxx/`），走 jsDelivr CDN 并发下载，只花 1 次 API 取文件树，不消耗逐文件配额。
- **装完必验**：完整性校验 + 运行自检，失败只补缺的文件，不留半成品目录。
- **小白友好**：装完用大白话说明装好了没、能干嘛、怎么触发。

## 安装

把本 skill 的 `SKILL.md`、`scripts/`、`references/` 放到你所用 Agent 的技能目录，例如 `<你的技能根目录>/github-skill-installer/`。不同 Agent 的默认技能目录不同，以你自己的安装位置为准。

安装目标目录可用环境变量 `WB_SKILLS_DIR` 覆盖。

## 用法

在对话里说「帮我装这个 skill」「从 GitHub 装个 XX」「点头了，装吧」，或开工扫描后明确同意安装某个工具时，本技能自动接管。

命令行直接调用安装脚本：

```bash
bash <你的技能目录>/scripts/install.sh <owner/repo> <子目录> <本地名>
```

例：

```bash
bash <你的技能目录>/scripts/install.sh mvanhorn/last30days-skill skills/last30days last30days
bash <你的技能目录>/scripts/install.sh DeezGit21/skill-radar . skill-radar-from-gh
```

分支不是 `main` 时先设 `GH_BRANCH=master`。装好后核对输出里的 `FILECHECK missing=0 sizebad=0`；新装的 skill 要**下次开会话**才进入自动触发列表。详见 `SKILL.md`。

## 许可

**允许个人自用，禁止商业使用。**

详见 [LICENSE](LICENSE)：可免费自用、修改与传播，但未取得书面许可不得用于任何商业目的（含在商业产品/服务中集成、调用或有偿提供）。
