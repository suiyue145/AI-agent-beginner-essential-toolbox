# 已验证的 GitHub skill 仓库配方

装之前先在这里查有没有现成地址；装成功后把新验证的仓库追加进来。

| 工具名 | 仓库 (owner/repo) | skill 子目录 | 本地名 | 状态 |
|---|---|---|---|---|
| last30days | mvanhorn/last30days-skill | skills/last30days | last30days | ✅ 2026-11-26 实测装成功，204 文件/19MB，v4.6.0，`--welcome` 自检通过。免密钥源 Reddit/HN/Digg/arXiv 可直接用 |
| skill-radar | DeezGit21/skill-radar | . | skill-radar | ⚠️ 本机已通过 git clone 装过（小仓库 clone 能通）；大仓库才需走 CDN。原版依赖 gh + 只认英文关键词，已打补丁（curl + 中文映射） |
| find-skills | vercel-labs/skills | 需探测 | — | 未在本机验证安装；skills.sh 榜首，装前先探测子目录 |

## 使用注意

- `--search` 参数只收搜索源名，不收自由文本；主题用位置参数或 `--discover`，试跑用 `--research-only --quick`。
- 装的 skill 要走 CDN 通道（见主 SKILL.md 通道经验表）。
- 新装 skill 下次开会话才进入自动触发列表。
