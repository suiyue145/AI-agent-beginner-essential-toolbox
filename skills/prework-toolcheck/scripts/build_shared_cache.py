#!/usr/bin/env python3
"""生产者：维护者本机定时跑一遍常用任务，生成可发布到 GitHub 的共享扫描缓存。

用法：
  python3 build_shared_cache.py [--output <路径>] [--tasks <路径>] [--min-stars 100]

默认读取同技能 config/shared-tasks.json，写到发布仓库 data/shared-scan-cache.json
（若不在发布仓库结构里，则写 ~/.skill-radar/shared-scan-cache-local.json）。
"""
import argparse
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from shared_cache_common import SCHEMA_VERSION, TTL_SECONDS, cache_key

HERE = Path(__file__).resolve().parent
SKILL_DIR = HERE.parent
DEFAULT_TASKS = SKILL_DIR / "config" / "shared-tasks.json"
REPO_DATA = HERE.parents[2] / "data" / "shared-scan-cache.json"
LOCAL_FALLBACK = Path.home() / ".skill-radar" / "shared-scan-cache-local.json"


def default_output():
    # 只在真正的发布仓库结构里写 data/，否则写到本机缓存目录，不污染用户配置
    root = HERE.parents[2]
    return REPO_DATA if (root / "README.md").exists() else LOCAL_FALLBACK


def scan(task, min_stars):
    cmd = ["skill-radar", "discover", task, "--min-stars", str(min_stars)]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=240)
        out = (r.stdout or "") + (("\n[STDERR] " + r.stderr) if r.stderr else "")
        return out, r.returncode == 0
    except Exception as e:
        return f"[扫描失败] {e}", False


def main():
    ap = argparse.ArgumentParser(description="生成共享扫描缓存")
    ap.add_argument("--tasks", default=str(DEFAULT_TASKS), help="任务清单 JSON")
    ap.add_argument("--output", default=str(default_output()), help="输出 JSON 路径")
    ap.add_argument("--min-stars", type=int, default=100)
    args = ap.parse_args()

    if not shutil.which("skill-radar"):
        print("[错误] 找不到 skill-radar 命令，无法生成本机扫描结果。", file=sys.stderr)
        return 2

    cfg = json.loads(Path(args.tasks).read_text(encoding="utf-8"))
    tasks = cfg.get("tasks", cfg if isinstance(cfg, list) else [])
    if not tasks:
        print("[错误] 任务清单为空。", file=sys.stderr)
        return 2

    now = time.time()
    entries = {}
    failed = []
    for i, task in enumerate(tasks, 1):
        key, kws = cache_key(task)
        print(f"[{i}/{len(tasks)}] 扫描: {task}  (关键词: {', '.join(kws) or '无'})")
        out, ok = scan(task, args.min_stars)
        if not ok:
            failed.append(task)
            print(f"    失败，跳过：{out.splitlines()[-1][:120] if out.strip() else '无输出'}")
            continue
        entries[key] = {
            "task": task,
            "keywords": kws,
            "ts": now,
            "time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now)),
            "output": out,
        }

    payload = {
        "schema": SCHEMA_VERSION,
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S %z", time.localtime(now)),
        "generated_ts": now,
        "ttl_days": TTL_SECONDS // 86400,
        "task_count": len(tasks),
        "ok_count": len(entries),
        "entries": entries,
    }

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n[完成] 成功 {len(entries)}/{len(tasks)} 项，写入 {out_path}")
    if failed:
        print("[注意] 以下任务扫描失败，未包含进共享缓存：" + "、".join(failed))
    return 0 if entries else 1


if __name__ == "__main__":
    sys.exit(main())
