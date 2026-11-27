#!/bin/zsh
# github-skill-installer 通用安装脚本
# 从 GitHub 仓库可靠安装 skill，绕开本机被拦的 git clone/zip/raw 和限流的 API。
# 用法: bash install.sh <owner/repo> [仓库内skill子目录] [本地目标名]
# 例:   bash install.sh mvanhorn/last30days-skill skills/last30days last30days
#       bash install.sh DeezGit21/skill-radar . skill-radar-from-gh
#
# 安装根目录：可用 WB_SKILLS_DIR 指定（如 ~/.claude/skills、~/.codex/skills），
# 未设时默认 $HOME/skills。本脚本不假设任何特定 Agent 的安装路径。

set -e
REPO="$1"
SUBDIR="${2:-.}"
NAME="${3:-$(basename "$REPO")}"
BRANCH="${GH_BRANCH:-main}"
SKILLS_ROOT="${WB_SKILLS_DIR:-$HOME/skills}"
DEST="$SKILLS_ROOT/$NAME"
TMP="/tmp/ghsi-$$"
LOG="$TMP/log"
mkdir -p "$TMP"
>"$LOG"

log() { echo "$@" | tee -a "$LOG"; }

if [ -z "$REPO" ]; then
  echo "用法: bash install.sh <owner/repo> [子目录] [本地名]"; exit 1
fi

log "=== 安装 $REPO (子目录: $SUBDIR, 分支: $BRANCH) → $DEST ==="

# 1) 取文件树（GitHub API 一次调用，不逐文件；带重试防网络抖动）
log "[1/4] 获取仓库文件树..."
TREE_URL="https://api.github.com/repos/$REPO/git/trees/$BRANCH?recursive=1"
TREE_OK=0
for attempt in 1 2 3; do
  if curl -sL --max-time 20 "$TREE_URL" -o "$TMP/tree.json" && python3 -c "import json,sys; d=json.load(open('$TMP/tree.json')); sys.exit(0 if 'tree' in d else 1)" 2>/dev/null; then
    TREE_OK=1; break
  fi
  [ "$attempt" -lt 3 ] && sleep 2
done
if [ "$TREE_OK" -ne 1 ]; then
  log "[错误] 无法访问 GitHub API（已重试3次），检查网络或分支名"; exit 2;
fi
python3 - "$TMP/tree.json" "$SUBDIR" "$DEST" > "$TMP/files.tsv" 2> "$TMP/meta" <<'PY'
import json, sys, os
tree_path, subdir, dest = sys.argv[1], sys.argv[2].strip('./'), sys.argv[3]
d = json.load(open(tree_path, encoding='utf-8'))
if 'tree' not in d:
    sys.stderr.write("ERROR: " + str(d.get('message', d))[:200]); sys.exit(2)
prefix = (subdir + '/') if subdir else ''
blobs = [x for x in d['tree'] if x['type']=='blob' and x['path'].startswith(prefix)]
if not blobs:
    sys.stderr.write("ERROR: 子目录下无文件，检查子目录路径"); sys.exit(3)
for x in blobs:
    rel = x['path'][len(prefix):]
    print(f"{rel}\t{x.get('size',-1)}")
sys.stderr.write(f"COUNT={len(blobs)}\n")
PY
COUNT=$(grep '^COUNT=' "$TMP/meta" | cut -d= -f2)
if [ -z "$COUNT" ]; then log "[错误] $(cat "$TMP/meta")"; exit 3; fi
log "    共 $COUNT 个文件"

# 2) CDN 并发下载（不消耗 API 配额）
log "[2/4] 通过 jsDelivr CDN 并发下载..."
python3 - "$TMP/files.tsv" "$REPO" "$BRANCH" "$SUBDIR" "$DEST" "$TMP/dl.log" <<'PY'
import sys, os, urllib.request, time
from concurrent.futures import ThreadPoolExecutor, as_completed
tsv, repo, branch, subdir, dest, logf = sys.argv[1:7]
prefix = (subdir.strip('./') + '/') if subdir.strip('./') else ''
BASE = f"https://cdn.jsdelivr.net/gh/{repo}@{branch}/"
items = []
for line in open(tsv, encoding='utf-8'):
    rel, size = line.rstrip('\n').split('\t')
    items.append((rel, int(size)))

def lg(m):
    with open(logf, 'a') as f: f.write(m+'\n')

def dl(it):
    rel, size = it
    out = os.path.join(dest, rel)
    if os.path.exists(out) and (size < 0 or os.path.getsize(out) == size):
        return 'skip'
    url = BASE + prefix + rel
    for a in range(4):
        try:
            req = urllib.request.Request(url, headers={'User-Agent':'workbuddy-installer'})
            with urllib.request.urlopen(req, timeout=45) as r:
                data = r.read()
            os.makedirs(os.path.dirname(out), exist_ok=True)
            with open(out, 'wb') as f: f.write(data)
            return 'ok'
        except Exception:
            if a == 3: return 'fail:' + rel
            time.sleep(1 + a)

ok = skip = 0; fail = []
with ThreadPoolExecutor(max_workers=12) as ex:
    for fut in as_completed([ex.submit(dl, it) for it in items]):
        r = fut.result()
        if r == 'ok': ok += 1
        elif r == 'skip': skip += 1
        else: fail.append(r)
lg(f"RESULT ok={ok} skip={skip} fail={len(fail)}")
for f in fail[:20]: lg("FAIL " + f)
PY
RES=$(tail -1 "$TMP/dl.log")
log "    $RES"
if echo "$RES" | grep -q "fail=[1-9]"; then
  log "[警告] 部分文件下载失败，见 $TMP/dl.log"
fi

# 3) 完整性校验（对比文件数与大小）
log "[3/4] 校验完整性..."
python3 - "$TMP/files.tsv" "$DEST" <<'PY'
import sys, os
tsv, dest = sys.argv[1], sys.argv[2]
missing = []; bad = []
for line in open(tsv, encoding='utf-8'):
    rel, size = line.rstrip('\n').split('\t'); size = int(size)
    p = os.path.join(dest, rel)
    if not os.path.exists(p): missing.append(rel)
    elif size >= 0 and os.path.getsize(p) != size: bad.append(rel)
print(f"FILECHECK missing={len(missing)} sizebad={len(bad)}")
PY

# 4) 运行自检（SKILL.md 存在 + 主脚本可 --help）
log "[4/4] 运行自检..."
if [ -f "$DEST/SKILL.md" ]; then
  log "    SKILL.md 存在 ✓ ($(wc -c < "$DEST/SKILL.md") 字节)"
else
  log "    [警告] 未找到 SKILL.md，可能子目录指定不对"
fi
MAIN=$(find "$DEST" -maxdepth 2 -name "*.py" -type f | head -1)
if [ -n "$MAIN" ]; then
  python3 "$MAIN" --help >/dev/null 2>&1 && log "    主脚本 $MAIN 可运行 ✓" || log "    主脚本 $MAIN 需特定参数（非致命）"
fi

log ""
log "=== 完成：$DEST ==="
log "文件数: $(find "$DEST" -type f 2>/dev/null | wc -l) | 大小: $(du -sh "$DEST" 2>/dev/null | cut -f1)"
echo "$DEST"
