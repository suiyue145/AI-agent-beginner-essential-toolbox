#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""提交发布前安全检查 · 生成环境信息清理器。

用途：其他 agent 把一个 skill 提交到网上发布之前，先运行本工具：
  1) scan     只读扫描：发现密钥、真实身份、本机绝对路径、.workbuddy 等生成环境痕迹；
  2) sanitize 非破坏性改写：在**暂存副本**上把环境路径改成读者需自行填写的占位符，
              并从 README 中移除维护者配置；绝不改动源目录；
  3) verify   校验暂存副本是否仍残留敏感信息。

用法：
  python3 skill_publish_check.py scan     <skill目录> [--json]
  python3 skill_publish_check.py sanitize <skill目录> [--out 暂存目录] [--config 配置.json] [--json]
  python3 skill_publish_check.py verify   <暂存目录> [--json]

退出码：0 = 干净/可发布；1 = 存在硬问题；2 = 用法错误。
"""
from __future__ import annotations

import argparse
import io
import json
import os
import re
import shutil
import sys
from typing import Dict, List, Tuple

# ── 收集语义：这些目录/后缀/文件属于运行态或平台产物，不进暂存包 ──
EXCLUDE_DIRS = {
    ".git", ".idea", ".vscode", "node_modules", "__pycache__", ".pytest_cache",
    "tmp", "outputs", "models", "venv", ".venv", "__MACOSX",
}
EXCLUDE_SUFFIX = (
    ".pyc", ".DS_Store", "Thumbs.db", ".tmp", ".log", ".lock", ".pid",
    ".session", ".swp", ".swo", ".jsonl",
)
DENY_NAMES = {
    "_meta.json", "_skillhub_meta.json", "_knot_meta.json", "skillhub_meta.json",
    ".skillhubignore",
}
TEXT_EXT = {
    ".md", ".txt", ".py", ".sh", ".json", ".yaml", ".yml", ".toml", ".ini",
    ".cfg", ".js", ".ts", ".html", ".css", ".xml", ".csv", ".tsv", "",
}

# ── 环境路径改写规则（顺序敏感：先长后短）──
# 每条 = (规则名, 正则, 替换串, 说明)
ENV_REWRITES: List[Tuple[str, "re.Pattern[str]", str, str]] = [
    ("win_workbuddy",
     re.compile(r"[A-Za-z]:[\\/]+Users[\\/]+[^\\/\s\"'<>|]+[\\/]+\.workbuddy[\\/]+skills[\\/]+[^\\/\s\"'<>|]+"),
     "<你的技能目录>",
     "Windows 下的 .workbuddy/skills/<技能名> 绝对路径 → 读者占位符"),
    ("posix_workbuddy",
     re.compile(r"(?<![\w.])/(?:Users|home)/[A-Za-z0-9._-]+/\.workbuddy/skills/[A-Za-z0-9._-]+"),
     "<你的技能目录>",
     "POSIX 下的 .workbuddy/skills/<技能名> 绝对路径 → 读者占位符"),
    ("tilde_workbuddy",
     re.compile(r"(?<![\w.])~?[\\/]?\.workbuddy[\\/]+skills[\\/]+[A-Za-z0-9._-]+"),
     "<你的技能目录>",
     "~ 开头的 .workbuddy/skills/<技能名> → 读者占位符"),
    ("workspace_root",
     re.compile(r"/Users/[^/\s\"'<>|]+/(?:Downloads|Desktop|Documents)/[^\s\"'<>|]+"),
     "<你的项目目录>",
     "工作区绝对路径 → 读者占位符"),
    ("win_home",
     re.compile(r"[A-Za-z]:[\\/]+Users[\\/]+[^\\/\s\"'<>|]+"),
     "%USERPROFILE%",
     "Windows 家目录 → 环境变量占位符"),
    ("posix_home",
     re.compile(r"(?<![\w.])/(?:Users|home)/[A-Za-z0-9._-]+"),
     "~",
     "POSIX 家目录 → ~"),
]

# ── README 维护者配置清理规则 ──
# 整节删除：标题命中关键词 → 删到下一个同级或更高级标题前
README_SECTION_KW = re.compile(r"维护者|作者信息|作者配置|联系方式|maintainer|author|contact", re.I)
# 单行删除：以这些字段开头的行
README_LINE_KW = re.compile(
    r"^\s*(?:[-*]\s*)?(?:维护者|作者|邮箱|联系(?:人|方式)?|maintainer|author|contact|email)\s*[:：]",
    re.I,
)
# 配置/环境变量行：维护者本机专用
README_CONFIG_KW = re.compile(
    r"(?:KEEPER_FORBID_ROOTS|FORBID_ROOTS|PUBLISH_CONFIG|FORBIDDEN_ROOTS)\s*=", re.I,
)
REMOVE_BLOCK_RE = re.compile(
    r"<!--\s*publish:remove\b[^>]*-->.*?<!--\s*/publish:remove\s*-->", re.I | re.S,
)

# ── 安全检查：硬问题（阻断发布）──
HARD_SCAN: List[Tuple[str, "re.Pattern[str]", str]] = [
    ("openai_key", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}"), "OpenAI 风格 API key"),
    ("gh_token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}"), "GitHub token"),
    ("slack_token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}"), "Slack token"),
    ("google_key", re.compile(r"\bAIza[0-9A-Za-z_-]{30,}"), "Google API key"),
    ("aws_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b"), "AWS access key"),
    ("private_key", re.compile(r"-----BEGIN (?:RSA |OPENSSH |EC |PGP )?PRIVATE KEY-----"), "私钥块"),
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"), "JWT"),
    ("skillhub_token", re.compile(r"\bskh_[A-Za-z0-9]{40,}"), "SkillHub token"),
    ("password", re.compile(r"\b(?:password|passwd|pwd)\s*[:=]\s*['\"]?[^\s'\"<>{}]{6,}", re.I), "明文口令"),
]
# ── 安全检查：报警项（需人工确认）──
WARN_SCAN: List[Tuple[str, "re.Pattern[str]", str]] = [
    ("real_email", re.compile(r"[\w.+-]+@(?:qq|163|126|gmail|hotmail|outlook|yahoo|foxmail|icloud)\.[A-Za-z.]{2,}"), "真实邮箱"),
    ("home_path", re.compile(r"(?<![\w.])/(?:Users|home)/[A-Za-z0-9._-]+"), "POSIX 家目录路径"),
    ("win_home", re.compile(r"[A-Za-z]:[\\/]+Users[\\/]+[^\\/\s\"'<>|]+"), "Windows 家目录路径"),
    ("workbuddy_env", re.compile(r"\.workbuddy|\.claude"), "生成环境目录名（.workbuddy/.claude）"),
    ("internal_host", re.compile(r"\b[A-Za-z0-9-]+\.(?:internal|corp|local|lan)\b", re.I), "内网主机名"),
    ("public_ip", re.compile(r"\b(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)\b"), "公网 IP"),
]
PLACEHOLDER = re.compile(
    r"placeholder|example|示例|占位|<[^>]+>|\{\{[^}]+\}\}|your[_-]?|xxx+|test@|foo@|user@|localhost|127\.0\.0\.1|10\.\d+\.\d+\.\d+",
    re.I,
)


def _collect(root: str):
    """按发布器语义递归收集 (rel, bytes)，跳过软连接与运行态产物。"""
    root = os.path.abspath(root)
    out = []
    for cur, dirs, files in os.walk(root, followlinks=False):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        for fn in files:
            if fn.endswith(EXCLUDE_SUFFIX) or fn in DENY_NAMES:
                continue
            ap = os.path.join(cur, fn)
            if os.path.islink(ap):
                continue
            try:
                with open(ap, "rb") as f:
                    data = f.read()
            except OSError:
                continue
            rel = os.path.relpath(ap, root).replace(os.sep, "/")
            out.append((rel, data))
    return out


def _text_of(data: bytes, rel: str) -> str | None:
    ext = os.path.splitext(rel)[1].lower()
    if ext and ext not in TEXT_EXT:
        return None
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return None


def _scan_text(rel: str, text: str):
    hard, warn = [], []
    for group, bucket in ((HARD_SCAN, hard), (WARN_SCAN, warn)):
        for name, rx, desc in group:
            for m in rx.finditer(text):
                if PLACEHOLDER.search(m.group(0)):
                    continue
                line = text.count("\n", 0, m.start()) + 1
                snip = text[m.start():min(len(text), m.end() + 20)].replace("\n", " ")[:70]
                bucket.append({"file": rel, "line": line, "rule": name,
                               "desc": desc, "evidence": snip})
    return hard, warn


def scan(root: str, config: dict | None = None):
    hard, warn, env_hits, files = [], [], [], 0
    cfg_extra = (config or {}).get("extra_forbidden", [])
    extra = [(f"custom:{i}", re.compile(p, re.I), "自定义禁词") for i, p in enumerate(cfg_extra)]
    for rel, data in _collect(root):
        text = _text_of(data, rel)
        if text is None:
            continue
        files += 1
        h, w = _scan_text(rel, text)
        hard.extend(h)
        warn.extend(w)
        for name, rx, _repl, desc in ENV_REWRITES:
            for m in rx.finditer(text):
                if PLACEHOLDER.search(m.group(0)):
                    continue
                line = text.count("\n", 0, m.start()) + 1
                env_hits.append({"file": rel, "line": line, "rule": name,
                                 "desc": desc, "evidence": m.group(0)[:70]})
        for name, rx, desc in extra:
            for m in rx.finditer(text):
                line = text.count("\n", 0, m.start()) + 1
                hard.append({"file": rel, "line": line, "rule": name,
                             "desc": desc, "evidence": m.group(0)[:70]})
    return {
        "root": os.path.abspath(root), "files_scanned": files,
        "hard": hard, "warn": warn, "env_hits": env_hits,
        "readme_maintainer": _scan_readme_maintainer(root),
    }


def _scan_readme_maintainer(root: str):
    out = []
    for rel, data in _collect(root):
        if not re.search(r"(^|/)readme\.md$", rel, re.I):
            continue
        text = data.decode("utf-8", "replace")
        for i, line in enumerate(text.splitlines(), 1):
            if README_SECTION_KW.search(line) and re.match(r"^\s*#{1,6}\s", line):
                out.append({"file": rel, "line": i, "type": "section", "evidence": line.strip()})
            elif README_LINE_KW.search(line) or README_CONFIG_KW.search(line):
                out.append({"file": rel, "line": i, "type": "line", "evidence": line.strip()[:70]})
    return out


def _rewrite_env(text: str, config: dict | None = None):
    stats = {}
    rules = list(ENV_REWRITES)
    for item in (config or {}).get("extra_rewrites", []):
        try:
            rules.append((f"custom:{item.get('name', 'rule')}",
                          re.compile(item["find"], re.I),
                          item.get("replace", "<请自行填写>"),
                          item.get("note", "自定义改写")))
        except (re.error, KeyError):
            continue
    for name, rx, repl, _desc in rules:
        text, n = rx.subn(repl, text)
        if n:
            stats[name] = stats.get(name, 0) + n
    return text, stats


def _rewrite_readme(text: str):
    stats = {"remove_block": 0, "section": 0, "line": 0}
    text, stats["remove_block"] = REMOVE_BLOCK_RE.subn("", text)
    lines = text.splitlines(keepends=True)
    out, i, removed_section = [], 0, 0
    while i < len(lines):
        line = lines[i]
        m = re.match(r"^(#{1,6})\s+", line)
        if m and README_SECTION_KW.search(line):
            level = len(m.group(1))
            i += 1
            while i < len(lines):
                nxt = re.match(r"^(#{1,6})\s+", lines[i])
                if nxt and len(nxt.group(1)) <= level:
                    break
                i += 1
            removed_section += 1
            continue
        if README_LINE_KW.search(line) or README_CONFIG_KW.search(line):
            i += 1
            stats["line"] += 1
            continue
        out.append(line)
        i += 1
    stats["section"] = removed_section
    return "".join(out), stats


def sanitize(root: str, out_dir: str, config: dict | None = None):
    root = os.path.abspath(root)
    out_dir = os.path.abspath(out_dir)
    if os.path.commonpath([root, out_dir]) == root:
        raise RuntimeError("暂存目录不能位于源 skill 目录内部（会污染源目录）")
    if os.path.exists(out_dir):
        raise RuntimeError("暂存目录已存在，拒绝覆盖：" + out_dir)
    os.makedirs(out_dir, exist_ok=True)
    rewrites: Dict[str, int] = {}
    readme_stats: Dict[str, int] = {}
    n_files = 0
    for rel, data in _collect(root):
        dest = os.path.join(out_dir, rel)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        text = _text_of(data, rel)
        if text is None:
            with open(dest, "wb") as f:
                f.write(data)
            continue
        new, st = _rewrite_env(text, config)
        for k, v in st.items():
            rewrites[k] = rewrites.get(k, 0) + v
        if re.search(r"(^|/)readme\.md$", rel, re.I):
            new, rst = _rewrite_readme(new)
            for k, v in rst.items():
                readme_stats[k] = readme_stats.get(k, 0) + v
        with io.open(dest, "w", encoding="utf-8", newline="") as f:
            f.write(new)
        n_files += 1
    return {
        "source": root, "staging": out_dir, "files_written": n_files,
        "rewrites": rewrites, "readme": readme_stats,
    }


def _fmt(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2)


def main(argv=None):
    ap = argparse.ArgumentParser(description="提交发布前安全检查 · 生成环境信息清理器")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("scan", "sanitize", "verify"):
        p = sub.add_parser(name)
        p.add_argument("path")
        p.add_argument("--json", action="store_true")
        p.add_argument("--config", help="扩展规则 JSON（可选）")
        if name == "sanitize":
            p.add_argument("--out", required=True, help="暂存目录（必须位于源目录之外）")
    args = ap.parse_args(argv)

    config = None
    if getattr(args, "config", None):
        with io.open(args.config, "r", encoding="utf-8") as f:
            config = json.load(f)

    if args.cmd == "scan":
        res = scan(args.path, config)
        if args.json:
            print(_fmt(res))
        else:
            print(f"=== 发布前安全检查 · {res['root']}")
            print(f"  扫描文件: {res['files_scanned']}")
            print(f"  硬问题(阻断): {len(res['hard'])}  报警: {len(res['warn'])}  "
                  f"环境痕迹: {len(res['env_hits'])}  README维护者项: {len(res['readme_maintainer'])}")
            for key in ("hard", "warn", "env_hits", "readme_maintainer"):
                if res[key]:
                    print(f"  ── {key} ──")
                    for h in res[key][:40]:
                        print(f"    {h.get('file')}:{h.get('line')} [{h.get('rule', h.get('type'))}] "
                              f"{h.get('desc', '')} «{h.get('evidence')}»")
        return 1 if res["hard"] else 0

    if args.cmd == "sanitize":
        try:
            res = sanitize(args.path, args.out, config)
        except RuntimeError as e:
            print("ERROR:", e, file=sys.stderr)
            return 2
        if args.json:
            print(_fmt(res))
        else:
            print(f"=== 已生成干净暂存副本 · {res['staging']}")
            print(f"  源文件: {res['source']}")
            print(f"  写入文本: {res['files_written']} 个")
            print(f"  环境路径改写: {res['rewrites'] or '无'}")
            print(f"  README 处理: {res['readme'] or '无'}")
            print("  请对暂存目录再跑一次 scan + verify，确认无残留后再发布。")
        return 0

    # verify
    res = scan(args.path, config)
    residual_hard = res["hard"]
    residual_env = [h for h in res["env_hits"] if "占位" not in h.get("desc", "")
                    and "<" not in h.get("evidence", "")]
    if args.json:
        print(_fmt({"hard": residual_hard, "residual_env": residual_env,
                    "readme_maintainer": res["readme_maintainer"]}))
    else:
        print(f"=== 暂存副本校验 · {res['root']}")
        print(f"  残留硬问题: {len(residual_hard)}  残留环境痕迹: {len(residual_env)}  "
              f"README维护者项: {len(res['readme_maintainer'])}")
        for h in residual_hard[:20]:
            print(f"    HARD {h['file']}:{h['line']} [{h['rule']}] «{h['evidence']}»")
        for h in residual_env[:20]:
            print(f"    ENV  {h['file']}:{h['line']} [{h['rule']}] «{h['evidence']}»")
    return 1 if (residual_hard or residual_env or res["readme_maintainer"]) else 0


if __name__ == "__main__":
    sys.exit(main())
