#!/usr/bin/env python3
"""共享结果优先的开工扫描包装器。

取结果顺序：
  1) 先查 GitHub 上有没有 3 天内的共享扫描结果 → 有就下载直接用
  2) GitHub 没有 → 看本机 3 天内缓存（之前自己扫过的）
  3) 都没有 → 本机真实调用 skill-radar 扫描
  4) 本机扫描成功后，把这一条上传到 GitHub（公开仓库）

用法：
  scan_cached.py "<任务>"                 # 按上面顺序
  scan_cached.py "<任务>" --force         # 跳过远端和本机缓存，强制本机重扫
  scan_cached.py "<任务>" --refresh-shared# 强制重新下载云端清单
  scan_cached.py "<任务>" --no-shared      # 本次完全不用云端结果
  scan_cached.py "<任务>" --no-upload      # 本次扫描后不上传
  scan_cached.py "<任务>" --no-cache       # 本次绕过缓存且不写入
  scan_cached.py "<任务>" --show-key       # 只看缓存 key 和关键词
"""
import argparse
import base64
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from shared_cache_common import (
    DOWNLOAD_TTL_SECONDS, SCHEMA_VERSION, TTL_SECONDS,
    cache_key, is_fresh,
)

CACHE_FILE = Path(os.environ.get("SKILL_RADAR_CACHE", str(Path.home() / ".skill-radar" / "scan-cache.json")))
SHARED_DOWNLOAD = Path(os.environ.get("SKILL_RADAR_SHARED_DOWNLOAD", str(Path.home() / ".skill-radar" / "shared-cache-download.json")))
LOCAL_SOURCE = Path(os.environ.get("SKILL_RADAR_SHARED_SOURCE", str(Path.home() / ".skill-radar" / "shared-source.json")))
SKILL_SOURCE = HERE.parent / "config" / "shared-source.json"
# 可选的本机凭据路径：仅回传结果时才需要，读者只读云端不用配。
# 读者若在本机放了凭据，用 GITHUB_PUBLISH_CONFIG 指定其实际位置即可。
GITHUB_CONFIG = Path(os.environ.get(
    "GITHUB_PUBLISH_CONFIG",
    str(Path.home() / ".config" / "skill-radar" / "github-publish.json"),
))
API = "https://api.github.com"
MIN_STARS = 100


def load_cache():
    if not CACHE_FILE.exists():
        return {}
    try:
        data = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_cache(cache):
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    CACHE_FILE.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")


def load_download():
    if not SHARED_DOWNLOAD.exists():
        return {}
    try:
        data = json.loads(SHARED_DOWNLOAD.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_download(data):
    SHARED_DOWNLOAD.parent.mkdir(parents=True, exist_ok=True)
    SHARED_DOWNLOAD.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def load_github_cfg():
    cfg = {}
    if GITHUB_CONFIG.exists():
        try:
            cfg = json.loads(GITHUB_CONFIG.read_text(encoding="utf-8"))
        except Exception:
            pass
    for key, env in [("owner", "GITHUB_OWNER"), ("repo", "GITHUB_REPO"),
                     ("branch", "GITHUB_BRANCH"), ("token", "GITHUB_TOKEN")]:
        if os.environ.get(env):
            cfg[key] = os.environ[env]
    cfg.setdefault("branch", "main")
    cfg.setdefault("path", "data/shared-scan-cache.json")
    if not cfg.get("token") or not cfg.get("owner") or not cfg.get("repo"):
        return None
    if str(cfg["owner"]).startswith("PLACEHOLDER"):
        return None
    return cfg


def resolve_shared_urls():
    """返回 [(url, 来源说明)]；未配置返回空列表。API 放第一位以支持私有仓库，公开仓库走匿名 CDN。"""
    override = os.environ.get("WB_SHARED_CACHE_URL", "").strip()
    if override:
        return [(override, "本机指定地址")]

    cfg = {}
    for p in (LOCAL_SOURCE, SKILL_SOURCE):
        if p.exists():
            try:
                cfg = json.loads(p.read_text(encoding="utf-8"))
                break
            except Exception:
                continue
    if cfg.get("url"):
        return [(cfg["url"], "本机共享配置")]

    owner = str(cfg.get("owner", ""))
    repo = str(cfg.get("repo", ""))
    branch = cfg.get("branch", "main")
    path = cfg.get("path", "data/shared-scan-cache.json")
    gh = load_github_cfg()
    # shared-source 还是占位符但本机已有发布配置时，直接用发布配置里的仓库
    if gh and (not owner or not repo or owner.startswith("PLACEHOLDER")):
        owner, repo = str(gh["owner"]), str(gh["repo"])
        branch, path = gh["branch"], gh["path"]
    if not owner or not repo or owner.startswith("PLACEHOLDER"):
        return []

    urls = []
    if gh:
        urls.append((f"{API}/repos/{gh['owner']}/{gh['repo']}/contents/{gh['path']}?ref={gh['branch']}",
                     "GitHub API（带 token 或私有仓库时使用）"))
    urls += [
        (f"https://cdn.jsdelivr.net/gh/{owner}/{repo}@{branch}/{path}", "公共 CDN"),
        (f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{path}", "GitHub 源文件"),
    ]
    return urls


def fetch_shared(force=False):
    """下载 GitHub 上的共享清单。返回 (数据, 是否本次新下载)。"""
    urls = resolve_shared_urls()
    if not urls:
        return None, False
    primary = urls[0][0]
    cached = load_download()
    if (not force and cached.get("url") == primary
            and time.time() - float(cached.get("fetched_ts", 0)) < DOWNLOAD_TTL_SECONDS
            and isinstance(cached.get("data"), dict)):
        return cached["data"], False

    gh = load_github_cfg()
    headers = {"User-Agent": "workbuddy-prework-toolcheck", "Cache-Control": "no-cache"}
    if gh:
        headers["Authorization"] = f"Bearer {gh['token']}"
        headers["Accept"] = "application/vnd.github+json"

    for url, label in urls:
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=25) as r:
                raw = r.read().decode("utf-8")
            if url.startswith(API + "/"):
                meta = json.loads(raw)
                raw = base64.b64decode(meta["content"]).decode("utf-8")
            data = json.loads(raw)
            if data.get("schema") != SCHEMA_VERSION or not isinstance(data.get("entries"), dict):
                raise ValueError("共享清单格式不匹配")
            save_download({"url": primary, "fetched_ts": time.time(), "data": data})
            return data, True
        except Exception as e:
            print(f"[共享缓存] {label} 不可用：{str(e)[:120]}")
    old = cached.get("data") if isinstance(cached.get("data"), dict) else None
    return old, False


def upload_entry(key, entry):
    """把一条本机扫描结果合并进 GitHub 共享缓存（公开仓库）。"""
    gh = load_github_cfg()
    if not gh:
        print("[未上传] 未配置 GitHub 凭据，本机结果保留在本地。")
        return False
    try:
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
            json.dump({"key": key, "entry": entry}, f, ensure_ascii=False)
            tmp = f.name
        cmd = [sys.executable, str(HERE / "publish_shared_cache.py"),
               "--merge-entry", tmp, "--create-private"]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        for line in ((r.stdout or "") + (("\n" + r.stderr) if r.stderr else "")).splitlines():
            print("[上传] " + line)
        return r.returncode == 0
    except Exception as e:
        print(f"[上传失败] {str(e)[:200]}")
        return False
    finally:
        try:
            os.unlink(tmp)
        except Exception:
            pass


def do_scan(task):
    """真实调用 skill-radar，返回 (输出文本, 是否成功)。"""
    cmd = ["skill-radar", "discover", task, "--min-stars", str(MIN_STARS)]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        return (r.stdout or "") + (("\n[STDERR] " + r.stderr) if r.stderr else ""), r.returncode == 0
    except Exception as e:
        return f"[扫描失败] {e}", False


def entry_output(entry):
    """兼容两种存储：完整 output 字符串，或逐行数组（便于大文件经连接器上传）。"""
    out = entry.get("output")
    if isinstance(out, str):
        return out
    lines = entry.get("output_lines")
    if isinstance(lines, list):
        return "\n".join(str(x) for x in lines)
    return ""


def fmt_duration(sec, suffix="前"):
    sec = int(sec)
    d, rem = divmod(sec, 86400)
    h, rem = divmod(rem, 3600)
    if d:
        return f"{d}天{h}小时{suffix}"
    if h:
        return f"{h}小时{rem // 60}分{suffix}"
    return f"{rem // 60}分钟{suffix}"


def main():
    ap = argparse.ArgumentParser(description="GitHub 共享结果优先的开工扫描")
    ap.add_argument("task", help="任务描述")
    ap.add_argument("--force", action="store_true", help="跳过远端和本机缓存，强制本机重扫")
    ap.add_argument("--no-cache", action="store_true", help="本次绕过缓存且不写入")
    ap.add_argument("--no-shared", action="store_true", help="本次不下载/使用云端结果")
    ap.add_argument("--refresh-shared", action="store_true", help="强制重新下载云端清单")
    ap.add_argument("--no-upload", action="store_true", help="本次扫描后不上传到 GitHub")
    ap.add_argument("--show-key", action="store_true", help="只显示缓存 key 和关键词，不扫描")
    args = ap.parse_args()

    key, kws = cache_key(args.task)
    if args.show_key:
        print(json.dumps({"key": key, "keywords": kws}, ensure_ascii=False))
        return

    cache = load_cache()
    now = time.time()

    # 1) GitHub 优先：3 天内的共享结果直接用
    shared_reason = ""
    if not args.no_shared and not args.no_cache and not args.force:
        shared, newly = fetch_shared(force=args.refresh_shared)
        if shared:
            hit = shared["entries"].get(key)
            fresh_file = is_fresh(shared.get("generated_ts", 0), now)
            if hit and fresh_file and is_fresh(hit.get("ts", 0), now):
                cache[key] = dict(hit, source="shared")
                save_cache(cache)
                where = "刚下载" if newly else "本地暂存的云端副本"
                print(f"[云端命中] 从 GitHub 找到 3 天内的扫描结果（{where}，生成于 {shared.get('generated_at', '未知')}），无需本机扫描")
                print(f"[关键词] {', '.join(hit.get('keywords', kws))}")
                print("=" * 50)
                print(entry_output(hit))
                return
            shared_reason = "GitHub 上没有这类任务或结果已过期，"

    # 2) 本机缓存（之前自己扫过的）
    entry = cache.get(key)
    if entry and not args.force and not args.no_cache:
        age = now - entry.get("ts", 0)
        if age < TTL_SECONDS:
            src = "共享清单" if entry.get("source") == "shared" else "本机扫描"
            print(f"[本机缓存命中·{src}] 结果来自 {fmt_duration(age)}，还有效 {fmt_duration(TTL_SECONDS - age, '')}")
            print(f"[关键词] {', '.join(entry.get('keywords', kws))}")
            print("=" * 50)
            print(entry_output(entry))
            return

    # 3) 本机真实扫描
    if entry:
        age = now - entry.get("ts", 0)
        reason = "用户强制刷新" if args.force else (
            f"上次结果已过期（{fmt_duration(age)}）" if not args.no_cache else "本次绕过缓存")
    else:
        reason = "首次扫描该任务"
    print(f"[执行扫描] {shared_reason}{reason}｜关键词: {', '.join(kws) if kws else '(无)'}")
    out, ok = do_scan(args.task)

    if ok and not args.no_cache:
        new_entry = {
            "task": args.task,
            "keywords": kws,
            "ts": now,
            "time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(now)),
            "output": out,
            "source": "local",
        }
        cache[key] = new_entry
        save_cache(cache)
        print(f"[已缓存] 本机已保存，3 天内复用（key={key}）")
        # 4) 上传这条结果到 GitHub（公开仓库）
        if not args.no_upload:
            upload_entry(key, new_entry)
    elif not ok:
        print("[注意] 本次扫描未成功，结果未写入缓存，下次会重试。")

    print("=" * 50)
    print(out)


if __name__ == "__main__":
    main()
