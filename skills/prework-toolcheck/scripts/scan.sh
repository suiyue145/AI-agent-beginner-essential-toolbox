#!/bin/zsh
# prework-toolcheck 开工扫描底层脚本
# 用法: bash scan.sh "<任务原话>"              # 只读本机已存数据，不联网（默认）
#       bash scan.sh "<任务原话>" --online     # 显式允许联网下载/现场扫描/回传
# 依赖: skill-radar 可选；不装也能直接用 GitHub 上的共享扫描结果，不报错

TASK="$1"
# 存档目录和"本机已装技能"目录都可通过环境变量覆盖，读者按自己 Agent 的实际位置设置
OUT_DIR="${WB_SCAN_OUT:-${XDG_CACHE_HOME:-$HOME/.cache}/skill-radar/scan-results}"
SKILLS_DIR="${WB_SKILLS_DIR:-$HOME/skills}"
mkdir -p "$OUT_DIR"
TS=$(date "+%Y-%m-%d_%H%M")

if [ -z "$TASK" ]; then
  echo "ERROR: 缺少任务描述"; exit 1
fi

echo "=== 开工扫描：$TASK ==="
echo ""

# 1) 本机已装技能（直接从目录名读，最可靠；未按任务筛相关性）
echo "[ALREADY] 本机已装的技能（未按本次任务筛相关性，不能当作扫描命中）："
echo "---"
ls "$SKILLS_DIR" 2>/dev/null | grep -v '^__' | head -40 || echo "[提示] 设置 WB_SKILLS_DIR 指向你的技能目录可列出已装技能"
echo "---"
echo ""

# 2) 取工具清单：默认只读本机已存数据，不联网（--online 时才下载/现场扫描/回传）
SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
CACHED="$SKILL_DIR/scripts/scan_cached.py"
MODE="--offline"
[ "$2" = "--online" ] && MODE=""
FOUND=0
if [ -f "$CACHED" ]; then
  LOG="$OUT_DIR/开工扫描_${TS}.txt"
  [ "$MODE" = "--offline" ] && echo "[离线模式] 只读本机已存数据，不联网、不现场扫描、不回传"
  ( python3 "$CACHED" "$TASK" $MODE 2>&1 || echo "[WARN] 扫描部分失败，已装技能清单仍可用" ) | tee "$LOG"
  grep -q '\[结果:有相关工具\]' "$LOG" && FOUND=1
  echo ""
  echo "完整扫描结果已存档：$LOG"
elif [ "$MODE" = "--online" ] && command -v skill-radar >/dev/null 2>&1; then
  echo "[WARN] 缓存包装器缺失，退回直接扫描"
  OUT=$( skill-radar discover "$TASK" --min-stars 100 2>&1 ) || echo "[WARN] 扫描失败"
  printf '%s\n' "$OUT"
  printf '%s\n' "$OUT" | grep -Eq '^[[:space:]]*[0-9]+[.)][[:space:]]' && FOUND=1
else
  echo "[WARN] 缓存包装器不可用（离线模式不现场扫描），仅返回已装技能清单。"
fi

echo ""
if [ "$FOUND" -eq 1 ]; then
  echo "=== 扫到与本次任务相关的工具：请按 references/beginner-musthave.md 对照，列三档清单并提醒用户选用。只推荐不安装。==="
else
  echo "=== 没扫到与本次任务相关的工具：不用列清单、不用提示安装，直接开工。==="
fi
