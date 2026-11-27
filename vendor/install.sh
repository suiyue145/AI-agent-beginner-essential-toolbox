#!/usr/bin/env bash
# 一键把"多平台增强版" skill-radar 装到本机，覆盖原版窄扫描逻辑。
# 用法：bash vendor/install.sh
# 覆盖内容：<你安装的 skill-radar 目录>/skill_radar.py  和  ~/.skill-radar/sources.json
# 安装目录用环境变量 WB_SKILL_RADAR_DIR 指定，未设时默认 $HOME/skill-radar。
# 不碰任何 token，不改系统其他位置。

set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
TARGET_DIR="${WB_SKILL_RADAR_DIR:-${HOME}/skill-radar}"
RADAR_PY="${TARGET_DIR}/skill_radar.py"
SOURCES="${HOME}/.skill-radar/sources.json"

echo "== 安装多平台增强版 skill-radar =="

# 1) 目标目录不存在时提示先装原版（增强版是覆盖补丁，不是独立程序）
if [ ! -d "$TARGET_DIR" ]; then
  echo "[提示] 没找到 ${TARGET_DIR}。先安装原版 skill-radar 再运行本脚本："
  echo "  git clone --depth 1 https://github.com/DeezGit21/skill-radar.git ${TARGET_DIR}"
  echo "  cd ${TARGET_DIR} && python3 -m pip install -e ."
  exit 1
fi

# 2) 备份原文件（带时间戳，只备份一次）
TS="$(date +%Y%m%d-%H%M%S)"
if [ -f "$RADAR_PY" ] && [ ! -f "${RADAR_PY}.bak-multipublish" ]; then
  cp "$RADAR_PY" "${RADAR_PY}.bak-multipublish"
  echo "[备份] ${RADAR_PY}.bak-multipublish"
fi

# 3) 覆盖增强版扫描逻辑
mkdir -p "$TARGET_DIR"
cp "$HERE/skill_radar.py" "$RADAR_PY"
echo "[覆盖] $RADAR_PY"

# 4) 写入多平台扫描源（保留用户已有的自定义源）
mkdir -p "$(dirname "$SOURCES")"
if [ ! -f "$SOURCES" ]; then
  cp "$HERE/sources.json.template" "$SOURCES"
  echo "[新建] $SOURCES"
else
  python3 - "$SOURCES" "$HERE/sources.json.template" <<'PY'
import json, sys
cur_path, tpl_path = sys.argv[1], sys.argv[2]
cur = json.load(open(cur_path))
tpl = json.load(open(tpl_path))
added = []
for k, v in tpl.items():
    if k not in cur:
        cur[k] = v
        added.append(k)
json.dump(cur, open(cur_path, 'w'), indent=2, ensure_ascii=False)
print('[增补] 扫描源:', ', '.join(added) if added else '已是最新，无需增补')
PY
fi

# 5) 自检
echo ""
echo "== 自检 =="
python3 -c "import ast; ast.parse(open('$RADAR_PY').read()); print('  语法 OK')"
skill-radar list-sources 2>/dev/null | grep -E 'skillsh-hot|official-catalogs|workbuddy' || echo "  [提示] 运行 skill-radar list-sources 确认新源已生效"

echo ""
echo "完成。现在扫描会覆盖：skills.sh 热门（跨平台）、Anthropic / Codex / Vercel / DeepSeek Harness / Hermes 官方目录、WorkBuddy topic、MCP 注册表。"
echo "如需让 GitHub API 配额从 60次/小时 提升到 5000次/小时，设置环境变量 GITHUB_TOKEN 即可（可选，不设也能匿名扫描）。"
