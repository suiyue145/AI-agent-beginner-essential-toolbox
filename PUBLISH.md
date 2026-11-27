# 发布操作清单

本文件是给维护者的发布备忘，发布前删掉或保留均可（保留也无妨）。

## 当前状态：公开仓库，已上传共享结果

- 仓库：`suiyue145/AI-agent-beginner-essential-toolbox`（**Public**）
- 共享结果：`data/shared-scan-cache.json`，已上传并回读验证 10 条，任何人可匿名读取。
- 本机凭据：`~/.workbuddy/github-publish.json`（权限 600，**绝不提交到仓库**）。
- 定时任务：每 3 天 08:30 批量生成并上传整份结果。
- 读取无需 token：匿名走 jsDelivr CDN / raw；有 token 时优先 GitHub API。
- 回传需要 token：本机扫描出的新条目合并上传，需要写权限（public_repo 足够）。

## 渠道一：skills.sh（零审核）

本包已放在公开仓库，可直接安装：

```bash
npx -y skills add suiyue145/AI-agent-beginner-essential-toolbox --list
npx -y skills add suiyue145/AI-agent-beginner-essential-toolbox
```

装一次让它进入匿名安装遥测，索引会自动更新（无需提交审核）。有人安装后会出现在 skills.sh 榜单。

注意：`agentskills.io` 是格式标准站，**没有发布入口**，不用去那里提交。

## 渠道二：腾讯 SkillHub（中文用户，需审核）

方式 A — 官网：访问 skillhub.cn → 登录 → 发布 skill → 填写信息 → 上传 SKILL.md → 提交审核。需先实名认证。

方式 B — CLI：

```bash
npm i -g skillhub-cli
skillhub login
skillhub init --name AI-agent-beginner-essential-toolbox --category 效率工具
skillhub push
skillhub publish
```

审核：内容合规 + 科恩实验室漏洞扫描 + 云鼎实验室 AI 安全评估，约 3~7 工作日。

注意 SkillHub 一次通常发布一个 skill。若要求单 skill，可只传 `skills/github-skill-installer`（最通用、最自包含），另外两件在描述里注明同仓库可获取。

## 共享扫描结果的定时更新

维护者本机一次性配置：

```bash
# 1) 凭据（放在仓库外，绝不提交）
cat > ~/.workbuddy/github-publish.json <<'EOF'
{"owner":"suiyue145","repo":"AI-agent-beginner-essential-toolbox","branch":"main","path":"data/shared-scan-cache.json","token":"ghp_xxx"}
EOF
chmod 600 ~/.workbuddy/github-publish.json

# 2) 上传整份结果（仓库已存在，不用 --create-private）
python3 skills/prework-toolcheck/scripts/publish_shared_cache.py --check
python3 skills/prework-toolcheck/scripts/build_shared_cache.py --output data/shared-scan-cache.json
python3 skills/prework-toolcheck/scripts/publish_shared_cache.py --file data/shared-scan-cache.json

# 3) 日常：开工扫描自动「云端优先 → 本机兜底 → 回传一条」
python3 skills/prework-toolcheck/scripts/scan_cached.py "调研市场方向并生成报告"
```

WorkBuddy 自动化任务每 3 天 08:30 批量生成+上传；没配 token 时只在本机生成，不会失败报错。改扫描范围编辑 `skills/prework-toolcheck/config/shared-tasks.json`。

## 本地自检命令

```bash
# 1. 无硬编码路径（PUBLISH.md 里的示例命令除外）
grep -rnoE --exclude=PUBLISH.md "/Users/|Downloads/软件|zhangzan" . || echo "OK 无硬编码"

# 2. 无本机状态文件
find . -name ".trigger-state" -o -name "__pycache__" -o -name "*.pyc" || echo "OK 无状态文件"

# 3. frontmatter 齐全
for f in skills/*/SKILL.md; do echo "--- $f"; head -4 "$f"; done

# 4. 脚本语法
zsh -n skills/prework-toolcheck/scripts/scan.sh && echo "scan.sh OK"
python3 -m py_compile skills/prework-toolcheck/scripts/scan_cached.py skills/prework-toolcheck/scripts/shared_cache_common.py skills/prework-toolcheck/scripts/build_shared_cache.py skills/prework-toolcheck/scripts/publish_shared_cache.py && echo "python scripts OK"
bash -n skills/github-skill-installer/scripts/install.sh && echo "install.sh OK"
python3 -c "import json; d=json.load(open('data/shared-scan-cache.json')); print('shared entries:', len(d['entries']))"
```
