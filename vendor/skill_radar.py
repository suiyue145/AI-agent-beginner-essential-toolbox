#!/usr/bin/env python3
"""
Skill Radar — AI Agent Skill Discovery Tool

Scans external sources (GitHub, MCP registries, skill directories) for
skills, tools, and MCP servers relevant to a given task or your tech stack,
then presents them for human approval (never auto-installs).

Modes:
  discover <task description>  — Search for skills relevant to a task
  cron-scan                    — Periodic discovery (run from cron)
  list-sources                 — Show configured sources
  add-source <name> <url>      — Add a custom source
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from datetime import datetime

# ── Config ──────────────────────────────────────────────────────────
CONFIG_DIR = Path.home() / ".skill-radar"
SOURCES_FILE = CONFIG_DIR / "sources.json"
CACHE_FILE = CONFIG_DIR / "cache.json"
HISTORY_FILE = CONFIG_DIR / "history.json"
KNOWN_SKILLS_FILE = CONFIG_DIR / "known_skills.json"
DEFAULT_MIN_STARS = 100

DEFAULT_SOURCES = {
    "github:top-agent-skills": {
        "type": "github_search",
        "query": "claude-code skill OR agent skill OR MCP server",
        "sort": "stars",
        "url": "https://api.github.com/search/repositories",
        "enabled": True
    },
    "github:hermes-skills": {
        "type": "github_search",
        "query": "hermes agent skill",
        "sort": "stars",
        "url": "https://api.github.com/search/repositories",
        "enabled": True
    },
    "github:mcp-servers": {
        "type": "github_search",
        "query": "MCP server OR model-context-protocol",
        "sort": "stars",
        "url": "https://api.github.com/search/repositories",
        "enabled": True
    },
    "github:cursor-rules": {
        "type": "github_search",
        "query": ".cursorrules OR CLAUDE.md agent skill",
        "sort": "stars",
        "url": "https://api.github.com/search/repositories",
        "enabled": True
    },
    "hermes-skills-hub": {
        "type": "url",
        "url": "https://hermes-agent.nousresearch.com/docs/skills",
        "query": "Hermes Agent Skills Hub",
        "enabled": True
    },
    "hermes-skills-sitemap": {
        "type": "url",
        "url": "https://hermes-agent.nousresearch.com/docs/sitemap.xml",
        "query": "Hermes Agent skill sitemap",
        "enabled": True
    },
    # ── Cross-platform SKILL.md catalog (covers ALL agent platforms) ──
    "skillsh-hot": {
        "type": "skills_sh",
        "pages": ["/hot", "/agent/codex", "/agent/claude-code", "/agent/cursor"],
        "per_page": 40,
        "query": "skills.sh hot + per-agent popular skills",
        "enabled": True
    },
    # ── Official / authoritative skill catalogs ──
    "github:official-catalogs": {
        "type": "github_repos",
        "repos": ["anthropics/skills", "openai/skills", "vercel-labs/skills",
                  "deepseek-ai/deepseek-harness", "NousResearch/hermes-agent",
                  "addyosmani/agent-skills", "antfu/skills",
                  "affaan-m/ECC", "callstackincubator/agent-skills"],
        "query": "official skill catalogs: Anthropic / Codex / Vercel / DeepSeek Harness / Hermes",
        "enabled": True
    },
    # ── WorkBuddy (Tencent) — no official GitHub repo; community uses topic ──
    "github:workbuddy-skills": {
        "type": "github_search",
        "query": "topic:workbuddy",
        "sort": "stars",
        "url": "https://api.github.com/search/repositories",
        "enabled": True
    }
}


def ensure_config():
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if not SOURCES_FILE.exists():
        with open(SOURCES_FILE, "w") as f:
            json.dump(DEFAULT_SOURCES, f, indent=2)
    for fn in [CACHE_FILE, HISTORY_FILE, KNOWN_SKILLS_FILE]:
        if not fn.exists():
            with open(fn, "w") as f:
                json.dump([], f)


def load_json(path):
    with open(path) as f:
        return json.load(f)


def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def gh_token():
    """Read an optional GitHub token to raise the API rate limit.

    Never hard-coded: checks env GITHUB_TOKEN, then an optional local config
    (path from GITHUB_PUBLISH_CONFIG, default ~/.config/skill-radar/github-publish.json).
    Returns "" if none — scanning still works anonymously at 60 req/hour.
    """
    tok = os.environ.get("GITHUB_TOKEN", "").strip()
    if tok:
        return tok
    try:
        cfg = Path(os.environ.get(
            "GITHUB_PUBLISH_CONFIG",
            str(Path.home() / ".config" / "skill-radar" / "github-publish.json"),
        ))
        if cfg.exists():
            tok = str(json.loads(cfg.read_text()).get("token", "")).strip()
            if tok and not tok.startswith("PLACEHOLDER"):
                return tok
    except Exception:
        pass
    return ""


def gh_curl_args():
    """Base curl args for GitHub API with optional auth (5000 req/h)."""
    args = ["-H", "Accept: application/vnd.github+json",
            "-H", "User-Agent: skill-radar"]
    tok = gh_token()
    if tok:
        args += ["-H", f"Authorization: Bearer {tok}"]
    return args


def github_search(query, sort="stars", per_page=15):
    """Search GitHub repositories via curl (no gh CLI needed)."""
    import urllib.parse
    params = urllib.parse.urlencode({"q": query, "sort": sort, "per_page": per_page})
    url = "https://api.github.com/search/repositories?" + params
    result = subprocess.run(
        ["curl", "-sL", "--max-time", "30"] + gh_curl_args() + [url],
        capture_output=True, text=True, timeout=40
    )
    if result.returncode != 0:
        print(f"  ⚠ GitHub search failed: {result.stderr.strip()}", file=sys.stderr)
        return []

    try:
        data = json.loads(result.stdout)
        if "items" not in data:
            print(f"  ⚠ GitHub search error: {str(data.get('message', data))[:200]}", file=sys.stderr)
            return []
        items = data.get("items", [])
        results = []
        for item in items:
            desc = item.get("description") or ""
            topics = item.get("topics", [])
            results.append({
                "name": item["full_name"],
                "url": item["html_url"],
                "description": desc[:250],
                "stars": item["stargazers_count"],
                "language": item.get("language"),
                "topics": topics,
                "updated_at": item.get("updated_at", ""),
                "source": "github",
            })
        return results
    except (json.JSONDecodeError, KeyError) as e:
        print(f"  ⚠ Could not parse GitHub response: {e}", file=sys.stderr)
        return []


def fetch_named_repos(repos):
    """Fetch metadata for a fixed list of known-good repos.

    Uses GET /repos/{owner}/{repo} (higher rate limit, more reliable than
    search) — ideal for official catalogs like anthropics/skills,
    openai/skills, deepseek-ai/deepseek-harness.
    """
    import concurrent.futures
    if not repos:
        return []
    def one(full):
        try:
            p = subprocess.run(
                ["curl", "-sL", "--max-time", "12"] + gh_curl_args() + [f"https://api.github.com/repos/{full}"],
                capture_output=True, text=True, timeout=15)
            d = json.loads(p.stdout)
            if not d.get("full_name"):
                return None
            return {
                "name": d["full_name"],
                "url": d.get("html_url", f"https://github.com/{full}"),
                "description": (d.get("description") or "")[:250],
                "stars": d.get("stargazers_count", 0),
                "language": d.get("language"),
                "topics": d.get("topics", []),
                "updated_at": d.get("updated_at", ""),
                "source": "official-catalog",
            }
        except Exception:
            return None

    out = []
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:
            for item in ex.map(one, repos):
                if item:
                    out.append(item)
    except Exception:
        pass
    return out


def fetch_skills_sh_hot(pages=None, per_page=40, fetch_meta=True):
    """Fetch popular skills from skills.sh public pages.

    skills.sh is the cross-platform SKILL.md catalog (Claude Code / Codex /
    Cursor / Gemini CLI / WorkBuddy / DeepSeek Harness ... all read SKILL.md).
    Its JSON API needs a Vercel OIDC token, but the leaderboard pages are
    public. We scrape owner/repo links and enrich them via the GitHub API.
    """
    import concurrent.futures
    import urllib.parse

    pages = pages or ["/hot"]
    # Words that appear as CSS/paths, not owner/repo pairs
    noise = {"_next", "static", "application", "www", "api", "agent", "topic",
             "docs", "rgb", "bg", "text", "hover", "border", "flex", "grid",
             "href", "svg", "img", "javascript", "font", "image", "video"}

    repos = []
    seen = set()
    for page in pages:
        url = "https://skills.sh" + (page if page.startswith("/") else "/" + page)
        try:
            r = subprocess.run(["curl", "-sL", "--max-time", "25", url],
                               capture_output=True, text=True, timeout=30)
            if r.returncode != 0:
                continue
            html = r.stdout
            # Primary: the page embeds JSON with "source":"owner/repo"
            found = re.findall(r'"source"\s*:\s*"([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)"', html)
            # Secondary: href="/owner/repo/skill-name" links
            found += re.findall(r'href="/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)/[A-Za-z0-9_.-]+"', html)
            # Tertiary: github.com/owner/repo links
            found += re.findall(r'github\.com/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)', html)
            for full in found:
                parts = full.split("/")
                if len(parts) != 2:
                    continue
                owner_l, repo_l = parts[0].lower(), parts[1].lower()
                if owner_l in noise or repo_l in noise:
                    continue
                if "." in repo_l and repo_l.split(".")[-1] in ("svg", "png", "css", "js", "ico"):
                    continue
                if full in seen:
                    continue
                seen.add(full)
                repos.append(full)
        except Exception as e:
            print(f"  ⚠ skills.sh fetch failed for {page}: {e}", file=sys.stderr)
            continue

    repos = repos[:per_page]
    if not repos:
        return []

    def enrich(full):
        try:
            p = subprocess.run(
                ["curl", "-sL", "--max-time", "12"] + gh_curl_args() + [f"https://api.github.com/repos/{full}"],
                capture_output=True, text=True, timeout=15)
            d = json.loads(p.stdout)
            if not d.get("full_name"):
                return None
            return {
                "name": d["full_name"],
                "url": d.get("html_url", f"https://github.com/{full}"),
                "description": (d.get("description") or "")[:250],
                "stars": d.get("stargazers_count", 0),
                "language": d.get("language"),
                "topics": d.get("topics", []),
                "updated_at": d.get("updated_at", ""),
                "source": "skills.sh",
            }
        except Exception:
            return None

    results = []
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
            for item in ex.map(enrich, repos):
                if item:
                    results.append(item)
    except Exception:
        pass
    return results


def search_mcp_registry(task_desc=""):
    """Search for MCP servers. Uses keyword extraction from task."""
    mcp_sources = [
        ("https://raw.githubusercontent.com/punkpeye/awesome-mcp-servers/main/README.md",
         "awesome-mcp-servers"),
        ("https://raw.githubusercontent.com/wong2/awesome-mcp-servers/main/README.md",
         "awesome-mcp-servers-alt"),
    ]

    # Use curl to fetch and grep for relevant entries
    results = []
    for url, name in mcp_sources:
        try:
            result = subprocess.run(
                ["curl", "-sL", url],
                capture_output=True, text=True, timeout=15
            )
            if result.returncode != 0:
                continue
            content = result.stdout

            # Extract MCP entries (markdown links)
            entries = re.findall(r'\[([^\]]+)\]\(([^)]+)\)\s*[-–—]\s*(.*)', content)
            for entry_name, entry_url, entry_desc in entries:
                entry_desc = entry_desc.strip()[:250]
                relevance = 0
                if task_desc:
                    words = set(task_desc.lower().split())
                    desc_words = set(entry_desc.lower().split())
                    name_words = set(entry_name.lower().split())
                    overlap = len(words & desc_words) + len(words & name_words)
                    relevance = overlap

                results.append({
                    "name": entry_name.strip(),
                    "url": entry_url.strip(),
                    "description": entry_desc,
                    "source": "mcp-registry",
                    "registry": name,
                    "relevance": relevance,
                    "stars": 0,
                })
        except Exception as e:
            print(f"  ⚠ MCP search failed for {name}: {e}", file=sys.stderr)

    # Sort by relevance if task given, otherwise alphabetically
    if task_desc:
        results.sort(key=lambda x: x["relevance"], reverse=True)
    return results[:30]


def score_relevance(item, task_desc, keywords=None):
    """Score how relevant a result is to the task description."""
    text = f"{item.get('name','')} {item.get('description','')} {' '.join(item.get('topics',[]))} {item.get('language','')}".lower()
    task_lower = task_desc.lower() if task_desc else ""

    score = 0
    # Direct keyword match
    if keywords:
        for kw in keywords:
            if kw.lower() in text:
                score += 3

    # Task word overlap
    if task_desc:
        task_words = set(re.findall(r'\w+', task_lower))
        text_words = set(re.findall(r'\w+', text))
        overlap = len(task_words & text_words)
        score += overlap

    # Stars bonus (popularity signal)
    stars = item.get("stars", 0)
    if stars >= 1000:
        score += 3
    elif stars >= 100:
        score += 2
    elif stars >= 10:
        score += 1

    # Trusted cross-platform catalogs get a small boost so authoritative
    # sources (Anthropic / Codex / DeepSeek Harness / skills.sh trending)
    # are not pushed out purely by unrelated task-word matches.
    if item.get("source") == "official-catalog":
        score += 2
    elif item.get("source") == "skills.sh":
        score += 1

    return score


def categorize(item):
    """Categorize a result based on its name and description."""
    topics_text = " ".join(item.get("topics", []))
    text = f"{item.get('name','')} {item.get('description','')} {topics_text}".lower()

    if "skill" in text:
        if "claude" in text:
            return "Claude Skill"
        return "Agent Skill"
    if "plugin" in text:
        return "Plugin"
    if ".cursorrules" in text or "cursor" in text:
        return "Cursor Rule"
    if "mcp" in text or "model-context" in text:
        return "MCP Server"
    if "tool" in text or "cli" in text:
        return "Tool"
    if "claude" in text:
        return "Claude Skill"
    return "Other"


ZH_TO_EN = {
    "调研": "research", "市场": "market", "报告": "report", "生成": "generate",
    "搜索": "search", "检索": "search", "查资料": "research", "写作": "writing",
    "文档": "documentation", "翻译": "translation", "总结": "summarize",
    "分析": "analysis", "数据": "data", "表格": "spreadsheet", "excel": "excel",
    "PPT": "presentation", "幻灯片": "presentation", "网页": "web",
    "前端": "frontend", "后端": "backend", "编程": "coding", "代码": "code",
    "测试": "testing", "部署": "deployment", "浏览器": "browser",
    "图片": "image", "视频": "video", "设计": "design", "写作": "writing",
    "邮件": "email", "日程": "calendar", "脱敏": "privacy redaction",
    "敏感": "privacy", "论文": "paper", "学术": "academic", " PubMed": "pubmed",
    "医学": "medical", "AI": "ai", "智能": "agent", "智能体": "agent",
    "技能": "skill", "工具": "tool", "自动化": "automation",
    "爬虫": "scraper", "监控": "monitoring", "安全": "security",
    "办公": "office", "财务": "finance", "股票": "stock", "投资": "investment",
}


def extract_keywords_from_task(task):
    """Extract meaningful keywords from a task description (EN + ZH)."""
    # Map Chinese task phrasing to English search terms
    zh_hits = []
    for zh, en in ZH_TO_EN.items():
        if zh.strip() and zh.strip() in task:
            zh_hits.append(en)
    if zh_hits:
        return sorted(set(zh_hits))[:10]

    # Remove common words
    stopwords = {"a", "an", "the", "is", "are", "was", "were", "be", "been",
                 "being", "have", "has", "had", "do", "does", "did", "will",
                 "would", "could", "should", "may", "might", "shall", "can",
                 "to", "of", "in", "for", "on", "with", "at", "by", "from",
                 "up", "about", "into", "over", "after", "all", "also", "and",
                 "but", "or", "so", "if", "then", "than", "that", "this",
                 "these", "those", "i", "me", "my", "we", "you", "he", "she",
                 "it", "they", "its", "their", "them", "what", "which", "who",
                 "how", "when", "where", "why", "not", "no", "nor", "just",
                 "very", "too", "much", "more", "most", "some", "any", "each",
                 "every", "both", "few", "such", "only", "own", "same", "so",
                 "please", "need", "want", "like", "make", "get", "use",
                 "create", "find", "help", "work", "new", "one", "two", "three"}

    words = re.findall(r'\b[a-zA-Z][a-zA-Z0-9]{2,}\b', task.lower())
    return sorted(set(w for w in words if w not in stopwords), key=len, reverse=True)[:10]


def deduplicate(results):
    """Remove duplicate results by URL."""
    seen = set()
    unique = []
    for r in results:
        key = r.get("url", r.get("name"))
        if key not in seen:
            seen.add(key)
            unique.append(r)
    return unique


def filter_by_min_stars(results, min_stars=DEFAULT_MIN_STARS):
    """Filter out repositories/items with fewer than min_stars.
    
    Items with source == 'github' are strictly filtered if stars < min_stars.
    Items without GitHub URLs (e.g. non-GitHub docs/registries) are preserved.
    """
    filtered = []
    for r in results:
        stars = r.get("stars", 0)
        source = r.get("source", "")
        url = r.get("url", "")
        is_github = source == "github" or "github.com" in url
        if is_github:
            if stars >= min_stars:
                filtered.append(r)
        else:
            filtered.append(r)
    return filtered


# ── Main discovery function ─────────────────────────────────────────
def discover(task_desc, max_results=15, min_stars=DEFAULT_MIN_STARS):
    """Run discovery across all enabled sources for a given task."""
    ensure_config()
    sources = load_json(SOURCES_FILE)
    task_keywords = extract_keywords_from_task(task_desc)

    print(f"🔍 Skill Radar — Searching for: {task_desc}")
    print(f"   Keywords: {', '.join(task_keywords[:6])}")
    if min_stars > 0:
        print(f"   Min Stars: ★{min_stars}+")
    print()

    all_results = []
    enabled = {k: v for k, v in sources.items() if v.get("enabled", True)}

    for name, source in enabled.items():
        source_type = source.get("type")
        print(f"  📡 Scanning: {name} ({source_type})")

        results = []
        if source_type == "github_search":
            # Platform query is the anchor. Task keywords are used for
            # relevance SCORING (below), not as a hard AND filter — otherwise
            # category sources like "codex skills" return nothing for tasks
            # whose words never appear in a repo description.
            query = source["query"]
            if min_stars > 0:
                # Parentheses are only safe around OR-expressions; wrapping a
                # bare qualifier like "topic:workbuddy" makes GitHub return 0.
                if " OR " in query:
                    query = f"({query}) stars:>={min_stars}"
                else:
                    query = f"{query} stars:>={min_stars}"
            results = github_search(query)
        elif source_type == "skills_sh":
            results = fetch_skills_sh_hot(
                pages=source.get("pages", ["/hot"]),
                per_page=source.get("per_page", 40),
            )
        elif source_type == "github_repos":
            results = fetch_named_repos(source.get("repos", []))
        elif source_type == "mcp":
            results = search_mcp_registry(task_desc)
        elif source_type == "url":
            # Fetch from URL and parse links
            try:
                r = subprocess.run(["curl", "-sL", source["url"]],
                                   capture_output=True, text=True, timeout=15)
                if r.returncode == 0:
                    content = r.stdout
                    # Try markdown links first [text](url)
                    links = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', content)
                    # If few markdown links, try HTML links <a href="url">text</a>
                    if len(links) < 5:
                        html_links = re.findall(
                            r'<a\s+(?:[^>]*?\s+)?href="([^"]+)"[^>]*>([^<]+)</a>',
                            content, re.IGNORECASE
                        )
                        for url, text in html_links:
                            if not url.startswith(('javascript:', '#', 'mailto:')):
                                links.append((text.strip(), url))
                    # Try XML sitemap <loc> entries
                    if len(links) < 5:
                        locs = re.findall(r'<loc>([^<]+)</loc>', content)
                        for loc_url in locs[:50]:
                            # Extract a readable name from the URL
                            name = loc_url.rstrip('/').split('/')[-1].replace('-', ' ').title()
                            links.append((name, loc_url))
                    for link_name, link_url in links[:50]:
                        results.append({
                            "name": link_name,
                            "url": link_url,
                            "description": "",
                            "source": "url",
                            "stars": 0,
                        })
            except Exception:
                pass

        # Score relevance
        for r in results:
            r["relevance"] = score_relevance(r, task_desc, task_keywords)
            r["category"] = categorize(r)

        all_results.extend(results)
        print(f"     → {len(results)} results found")

    # Filter by minimum stars for GitHub repositories
    if min_stars > 0:
        all_results = filter_by_min_stars(all_results, min_stars=min_stars)

    # Deduplicate, sort by relevance, limit
    all_results = deduplicate(all_results)
    all_results.sort(key=lambda x: (x.get("relevance", 0), x.get("stars", 0)), reverse=True)
    top = all_results[:max_results]

    # Save to history
    history = load_json(HISTORY_FILE)
    history.append({
        "timestamp": datetime.now().isoformat(),
        "task": task_desc,
        "results_count": len(top),
        "results": top[:10],  # keep top 10 in history
    })
    save_json(HISTORY_FILE, history[-50:])

    return top


def present_results(results, task_desc):
    """Format and display results to the user."""
    if not results:
        print("\n❌ No relevant skills/tools found.")
        print("   Try a different task description or check your sources.")
        return

    print("\n" + "=" * 72)
    print(f"📋 SKILL RADAR — Recommendations for: \"{task_desc}\"")
    print("=" * 72)

    # Group by category
    by_category = {}
    for r in results:
        cat = r.get("category", "Other")
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(r)

    count = 0
    for category in ["MCP Server", "Agent Skill", "Claude Skill", "Tool", "Plugin", "Cursor Rule", "Other"]:
        if category not in by_category:
            continue
        items = by_category[category]
        print(f"\n  ┌─ {category}s ({len(items)}) ───────────────────────────────")
        for item in items:
            count += 1
            stars_str = f" ★{item.get('stars',0)}" if item.get('stars', 0) else ""
            relevance_str = f" [score:{item.get('relevance',0)}]" if item.get('relevance', 0) else ""
            print(f"  │ {count}. {item['name']}{stars_str}{relevance_str}")
            print(f"  │    {item.get('description', '')[:120]}")
            print(f"  │    🔗 {item['url']}")
        print(f"  └{'─' * 40}")

    print()
    print("=" * 72)
    print("  Approve any item by name to install.")
    print("  Run with --install <name> to install the chosen item.")
    print("=" * 72)


# ── Cron scan mode ──────────────────────────────────────────────────
def cron_scan(min_stars=DEFAULT_MIN_STARS):
    """Periodic discovery — finds NEW skills not seen before."""
    ensure_config()
    known = set()
    if KNOWN_SKILLS_FILE.exists():
        known = set(load_json(KNOWN_SKILLS_FILE))

    # Search broadly across multiple query vectors (filtered by min_stars)
    star_filter = f"stars:>={min_stars}" if min_stars > 0 else ""
    searches = [
        # AGENT SKILLS & Skill collections first (stars & updated vectors)
        (f"topic:agent-skills {star_filter}".strip(), "stars", 25),
        (f"topic:agent-skills {star_filter}".strip(), "updated", 25),
        (f"topic:claude-code-skills {star_filter}".strip(), "stars", 25),
        (f"topic:claude-code-skills {star_filter}".strip(), "updated", 25),
        (f"topic:claude-code-skill {star_filter}".strip(), "stars", 25),
        (f"topic:claude-skills {star_filter}".strip(), "updated", 25),
        (f"topic:agent-skill {star_filter}".strip(), "stars", 25),
        (f"topic:agent-skill {star_filter}".strip(), "updated", 25),
        (f"awesome \"agent skills\" {star_filter}".strip(), "stars", 25),
        (f"awesome \"agent skills\" {star_filter}".strip(), "updated", 25),
        (f"awesome \"claude skills\" {star_filter}".strip(), "stars", 25),
        (f"awesome \"claude code\" {star_filter}".strip(), "updated", 25),
        (f"\"agent skills\" {star_filter}".strip(), "stars", 25),
        (f"\"agent skills\" {star_filter}".strip(), "updated", 25),
        (f"\"claude code\" skills {star_filter}".strip(), "updated", 25),
        (f"hermes agent skill OR plugin OR tool {star_filter}".strip(), "updated", 25),
        # Standalone tools / CLIs for agents
        (f"\"coding agent\" CLI OR tool {star_filter}".strip(), "stars", 20),
        (f"\"coding agent\" CLI OR tool {star_filter}".strip(), "updated", 20),
        # MCP Servers (kept to a minimum)
        (f"topic:mcp-server {star_filter}".strip(), "updated", 10),
    ]

    new_discoveries = []
    seen_urls = set()

    for query, sort_by, per_page in searches:
        try:
            results = github_search(query, sort=sort_by, per_page=per_page)
            if min_stars > 0:
                results = filter_by_min_stars(results, min_stars=min_stars)
            for r in results:
                name = r["name"]
                url = r["url"]
                if name not in known and url not in seen_urls:
                    r["discovery_date"] = datetime.now().isoformat()
                    r["category"] = categorize(r)
                    new_discoveries.append(r)
                    seen_urls.add(url)
        except Exception:
            continue

    # Update known list
    for r in new_discoveries:
        known.add(r["name"])
    save_json(KNOWN_SKILLS_FILE, sorted(known))

    # Save to history
    if new_discoveries:
        history = load_json(HISTORY_FILE)
        history.append({
            "timestamp": datetime.now().isoformat(),
            "task": "cron-scan",
            "results_count": len(new_discoveries),
            "results": new_discoveries,
        })
        save_json(HISTORY_FILE, history[-50:])

    # Present new discoveries grouped by category (Skills first, MCPs capped at 2)
    if new_discoveries:
        print("\n📡 SKILL RADAR — New Discoveries\n")
        by_category = {}
        for r in new_discoveries:
            cat = r.get("category", "Other")
            by_category.setdefault(cat, []).append(r)

        for cat in ["Agent Skill", "Claude Skill", "Tool", "Plugin", "Cursor Rule", "MCP Server", "Other"]:
            if cat not in by_category:
                continue
            items = sorted(by_category[cat], key=lambda x: x.get("stars", 0), reverse=True)
            if cat == "MCP Server":
                items = items[:2]
            print(f"=== {cat}s ({len(items)}) ===")
            for item in items:
                print(f"  🆕 {item['name']} ★{item.get('stars',0)}")
                print(f"     {item.get('description','')[:140]}")
                print(f"     🔗 {item['url']}")
                print()

        print(f"Total new discoveries this scan: {len(new_discoveries)}")
        print("Run with --install <name> to install any item.")
    else:
        print("No new discoveries found.")

    return new_discoveries


# ── Install mode ────────────────────────────────────────────────────
def install_item(name, url):
    """Present install instructions for an item (no auto-install)."""
    print(f"\n📦 To install '{name}':")
    print(f"   Source: {url}")
    print()
    print("   Options:")
    print(f"     1) Install as Hermes skill: hermes skill install <url>")
    print(f"     2) Clone manually: git clone {url}")
    print(f"     3) Add MCP server: hermes config set mcp.servers.{name.replace('/','-')} {url}")
    print()
    print("   Run the install command yourself to proceed.")
    print("   (Skill Radar never auto-installs — safety by design)")


# ── CLI ─────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Skill Radar — AI Agent Skill Discovery Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  skill-radar discover "Build a React dashboard with real-time data"
  skill-radar discover "Set up CI/CD pipeline"
  skill-radar cron-scan
  skill-radar list-sources
  skill-radar add-source my-skills https://myskills.dev/registry
        """
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # discover
    disc = subparsers.add_parser("discover", help="Search for skills relevant to a task")
    disc.add_argument("task", type=str, nargs="+", help="Task description")
    disc.add_argument("--max", type=int, default=15, help="Max results (default: 15)")
    disc.add_argument("--min-stars", type=int, default=DEFAULT_MIN_STARS, help=f"Minimum GitHub stars (default: {DEFAULT_MIN_STARS})")
    disc.add_argument("--install", type=str, metavar="NAME", help="Show install instructions for a result")
    disc.add_argument("--json", action="store_true", help="Output as JSON")

    # cron-scan
    cron_p = subparsers.add_parser("cron-scan", help="Periodic discovery scan (cron-friendly)")
    cron_p.add_argument("--min-stars", type=int, default=DEFAULT_MIN_STARS, help=f"Minimum GitHub stars (default: {DEFAULT_MIN_STARS})")

    # list-sources
    subparsers.add_parser("list-sources", help="Show configured sources")

    # add-source
    add_src = subparsers.add_parser("add-source", help="Add a custom source")
    add_src.add_argument("name", type=str, help="Source name")
    add_src.add_argument("url", type=str, help="Source URL")
    add_src.add_argument("--type", type=str, default="url", choices=["url", "github_search", "mcp"],
                         help="Source type (default: url)")

    # remove-source
    rm_src = subparsers.add_parser("remove-source", help="Remove a source")
    rm_src.add_argument("name", type=str, help="Source name to remove")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    if args.command == "discover":
        task = " ".join(args.task)
        results = discover(task, max_results=args.max, min_stars=args.min_stars)

        if args.json:
            print(json.dumps(results, indent=2))
        elif args.install:
            # Find the named item
            for r in results:
                if args.install.lower() in r["name"].lower():
                    install_item(r["name"], r["url"])
                    return
            print(f"'{args.install}' not found in results.")
        else:
            present_results(results, task)

    elif args.command == "cron-scan":
        cron_scan(min_stars=args.min_stars)

    elif args.command == "list-sources":
        ensure_config()
        sources = load_json(SOURCES_FILE)
        print("Configured sources:")
        for name, src in sources.items():
            status = "✅" if src.get("enabled", True) else "⏸"
            print(f"  {status} {name} ({src.get('type','?')})")
            print(f"      {src.get('query', src.get('url', ''))}")

    elif args.command == "add-source":
        ensure_config()
        sources = load_json(SOURCES_FILE)
        sources[args.name] = {
            "type": args.type,
            "url": args.url,
            "query": args.name,
            "enabled": True,
        }
        save_json(SOURCES_FILE, sources)
        print(f"✅ Added source: {args.name}")

    elif args.command == "remove-source":
        ensure_config()
        sources = load_json(SOURCES_FILE)
        if args.name in sources:
            del sources[args.name]
            save_json(SOURCES_FILE, sources)
            print(f"✅ Removed source: {args.name}")
        else:
            print(f"Source '{args.name}' not found.")


if __name__ == "__main__":
    main()