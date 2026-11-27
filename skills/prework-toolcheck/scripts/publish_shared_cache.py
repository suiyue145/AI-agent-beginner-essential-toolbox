#!/usr/bin/env python3
"""把共享扫描缓存发布到 GitHub（Contents API，不需要 git clone/push）。

支持两种写法：
  publish_shared_cache.py --file data/shared-scan-cache.json   # 整份覆盖
  publish_shared_cache.py --merge-entry /tmp/one.json          # 只合并一条结果

token 与仓库配置在本机 ~/.workbuddy/github-publish.json（绝不放进仓库）：
  {"owner": "你的用户名", "repo": "AI-agent-beginner-essential-toolbox",
   "branch": "main", "path": "data/shared-scan-cache.json",
   "token": "ghp_xxx(需要 repo 写权限)"}

也可用环境变量 GITHUB_TOKEN / GITHUB_OWNER / GITHUB_REPO / GITHUB_BRANCH 覆盖。
--create-private 是可选能力：仓库不存在时创建私有仓库；
已有仓库的可见性不会被本脚本改动（当前使用的仓库是公开的）。
"""
import argparse
import base64
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from shared_cache_common import SCHEMA_VERSION

CONFIG = Path.home() / ".workbuddy" / "github-publish.json"
REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_FILE = REPO_ROOT / "data" / "shared-scan-cache.json"
if not DEFAULT_FILE.exists():
    DEFAULT_FILE = Path.home() / ".skill-radar" / "shared-scan-cache-local.json"
API = "https://api.github.com"


def load_config():
    cfg = {}
    if CONFIG.exists():
        try:
            cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"[错误] 凭据文件格式不对：{e}", file=sys.stderr)
            return None
    for key, env in [("owner", "GITHUB_OWNER"), ("repo", "GITHUB_REPO"),
                     ("branch", "GITHUB_BRANCH"), ("token", "GITHUB_TOKEN")]:
        if os.environ.get(env):
            cfg[key] = os.environ[env]
    cfg.setdefault("branch", "main")
    cfg.setdefault("path", "data/shared-scan-cache.json")
    missing = [k for k in ("owner", "repo", "token") if not cfg.get(k) or str(cfg[k]).startswith("PLACEHOLDER")]
    if missing:
        print("[未上传] 缺少 GitHub 配置：" + "、".join(missing))
        print(f"请在 {CONFIG} 写入 owner/repo/branch/token，或用 GITHUB_TOKEN 等环境变量。")
        return None
    return cfg


def request(url, method="GET", headers=None, data=None, timeout=40):
    req = urllib.request.Request(url, method=method, data=data, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except Exception as e:
        return 0, str(e)


def api_headers(cfg):
    return {
        "Authorization": f"Bearer {cfg['token']}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "workbuddy-beginner-tools",
        "Content-Type": "application/json",
    }


def create_private_repo(cfg, headers):
    """仓库不存在时创建一个私有仓库。只创建，不改已有仓库可见性。"""
    body = json.dumps({
        "name": cfg["repo"],
        "private": True,
        "description": "WorkBuddy beginner tools - shared scan cache (private, not announced)",
    }).encode("utf-8")
    status, resp = request(f"{API}/user/repos", method="POST", headers=headers, data=body)
    if status in (200, 201):
        owner = json.loads(resp).get("owner", {}).get("login")
        print(f"[已创建私有仓库] {owner}/{cfg['repo']}（未对外公布）")
        if owner and owner.lower() != str(cfg["owner"]).lower():
            print(f"[注意] 实际创建在 {owner} 名下，与配置 owner={cfg['owner']} 不一致，请把配置改成实际用户名。")
        return True
    print(f"[创建仓库失败] HTTP {status}：{resp[:300]}")
    return False


def fetch_remote(cfg, headers, target):
    """返回 (数据 dict 或 None, sha 或 None, HTTP 状态码)。"""
    status, body = request(f"{target}?ref={cfg['branch']}", headers=headers)
    if status == 200:
        try:
            meta = json.loads(body)
            data = json.loads(base64.b64decode(meta["content"]).decode("utf-8"))
            return data, meta.get("sha"), status
        except Exception as e:
            print(f"[错误] 远端缓存解析失败：{e}")
            return None, None, status
    return None, None, status


def merge_entry(cfg, headers, target, merge_file):
    raw = json.loads(Path(merge_file).read_text(encoding="utf-8"))
    key = raw["key"]
    entry = raw["entry"]
    data, sha, status = fetch_remote(cfg, headers, target)
    if status == 404:
        data = {
            "schema": SCHEMA_VERSION,
            "generated_at": time.strftime("%Y-%m-%d %H:%M:%S %z", time.localtime()),
            "generated_ts": time.time(),
            "ttl_days": 3,
            "task_count": 0,
            "ok_count": 0,
            "entries": {},
        }
        sha = None
    elif status != 200 or not isinstance(data, dict):
        print(f"[错误] 读取远端缓存失败（HTTP {status}），不合并。")
        return None, None
    entries = data.setdefault("entries", {})
    entries[key] = entry
    data["ok_count"] = len(entries)
    data["task_count"] = max(int(data.get("task_count", 0)), data["ok_count"])
    data["generated_at"] = time.strftime("%Y-%m-%d %H:%M:%S %z", time.localtime())
    data["generated_ts"] = time.time()
    print(f"[合并条目] key={key}，当前共 {data['ok_count']} 条")
    return data, sha


def main():
    ap = argparse.ArgumentParser(description="发布/合并共享扫描缓存到 GitHub")
    ap.add_argument("--file", default=str(DEFAULT_FILE), help="整份覆盖用的 JSON")
    ap.add_argument("--merge-entry", help="只合并一条结果的 JSON（含 key 和 entry）")
    ap.add_argument("--check", action="store_true", help="只检查配置，不写仓库")
    ap.add_argument("--create-private", action="store_true", help="仓库不存在时创建私有仓库")
    args = ap.parse_args()

    cfg = load_config()
    if cfg is None:
        return 3  # 让定时任务能区分"扫描成功但未上传"

    target = f"{API}/repos/{cfg['owner']}/{cfg['repo']}/contents/{cfg['path']}"
    if args.check:
        print(f"[检查通过] 目标：https://github.com/{cfg['owner']}/{cfg['repo']}/blob/{cfg['branch']}/{cfg['path']}")
        print("[隐私] 脚本不会修改已有仓库可见性；加 --create-private 时新建的仓库为私有。")
        return 0

    headers = api_headers(cfg)

    # 先探测仓库/文件是否存在；不存在且要求私有则创建
    status, body = request(f"{API}/repos/{cfg['owner']}/{cfg['repo']}", headers=headers)
    if status == 404:
        if args.create_private:
            if not create_private_repo(cfg, headers):
                return 1
        else:
            print(f"[错误] 仓库 {cfg['owner']}/{cfg['repo']} 不存在；如需新建私有仓库请加 --create-private。")
            return 1
    elif status != 200:
        print(f"[错误] 读取仓库信息失败（HTTP {status}）：{body[:300]}")
        return 1

    if args.merge_entry:
        data, sha = merge_entry(cfg, headers, target, args.merge_entry)
        if data is None:
            return 1
        content = json.dumps(data, ensure_ascii=False, indent=2)
        msg = f"chore: add shared scan result {time.strftime('%Y-%m-%d %H:%M')}"
    else:
        path = Path(args.file)
        if not path.exists():
            print(f"[错误] 找不到扫描结果：{path}", file=sys.stderr)
            return 2
        content = path.read_text(encoding="utf-8")
        _, sha, cstatus = fetch_remote(cfg, headers, target)
        if cstatus not in (200, 404):
            print(f"[错误] 读取已有文件失败（HTTP {cstatus}）")
            return 1
        msg = f"chore: refresh shared scan cache {time.strftime('%Y-%m-%d %H:%M')}"

    payload = {
        "message": msg,
        "content": base64.b64encode(content.encode("utf-8")).decode("ascii"),
        "branch": cfg["branch"],
    }
    if sha:
        payload["sha"] = sha

    status, body = request(target, method="PUT", headers=headers,
                           data=json.dumps(payload).encode("utf-8"))
    if status in (200, 201):
        print(f"[已上传] https://github.com/{cfg['owner']}/{cfg['repo']}/blob/{cfg['branch']}/{cfg['path']}")
        print("[公开] 共享结果已上传到公开仓库，使用者可匿名读取。")
        return 0
    if status == 401:
        print("[错误] token 无效或过期。")
    elif status == 403:
        print("[错误] 无写权限或触发限流，稍后重试。")
    elif status == 404:
        print("[错误] 仓库/分支/路径不存在。")
    print(f"[上传失败] HTTP {status}：{body[:500]}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
