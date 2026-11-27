#!/usr/bin/env python3
"""共享扫描缓存的公共协议：关键词提取、缓存 key、有效期。

这个文件刻意不依赖 skill-radar：生产者（维护者本机定时扫描）和消费者
（别人装了技能后直接下载结果）必须用完全相同的算法算 key，否则命中不了。
"""
import hashlib
import re
import time

SCHEMA_VERSION = 1
TTL_SECONDS = 3 * 24 * 60 * 60  # 共享结果 3 天后过期
DOWNLOAD_TTL_SECONDS = 6 * 60 * 60  # 公共清单本身 6 小时检查一次更新

ZH_TO_EN = {
    "调研": "research", "市场": "market", "报告": "report", "生成": "generate",
    "搜索": "search", "检索": "search", "查资料": "research", "写作": "writing",
    "文档": "documentation", "翻译": "translation", "总结": "summarize",
    "分析": "analysis", "数据": "data", "表格": "spreadsheet", "excel": "excel",
    "PPT": "presentation", "幻灯片": "presentation", "网页": "web",
    "前端": "frontend", "后端": "backend", "编程": "coding", "代码": "code",
    "测试": "testing", "部署": "deployment", "浏览器": "browser",
    "图片": "image", "视频": "video", "设计": "design", "邮件": "email",
    "日程": "calendar", "脱敏": "privacy redaction", "敏感": "privacy",
    "论文": "paper", "学术": "academic", "PubMed": "pubmed", "医学": "medical",
    "AI": "ai", "智能": "agent", "智能体": "agent", "技能": "skill",
    "工具": "tool", "自动化": "automation", "爬虫": "scraper",
    "监控": "monitoring", "安全": "security", "办公": "office",
    "财务": "finance", "股票": "stock", "投资": "investment",
}

STOPWORDS = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "can", "to", "of", "in", "for", "on",
    "with", "at", "by", "from", "up", "about", "into", "over", "after", "all",
    "also", "and", "but", "or", "so", "if", "then", "than", "that", "this",
    "these", "those", "i", "me", "my", "we", "you", "he", "she", "it", "they",
    "its", "their", "them", "what", "which", "who", "how", "when", "where",
    "why", "not", "no", "nor", "just", "very", "too", "much", "more", "most",
    "some", "any", "each", "every", "both", "few", "such", "only", "own",
    "same", "please", "need", "want", "like", "make", "get", "use", "create",
    "find", "help", "work", "new", "one", "two", "three",
}


def extract_keywords_from_task(task):
    """从任务描述提取关键词（中英都支持），与 skill-radar 补丁版保持一致。"""
    zh_hits = []
    for zh, en in ZH_TO_EN.items():
        if zh.strip() and zh.strip().lower() in task.lower():
            zh_hits.append(en)
    if zh_hits:
        return sorted(set(zh_hits))[:10]
    words = re.findall(r"\b[a-zA-Z][a-zA-Z0-9]{2,}\b", task.lower())
    return sorted(set(w for w in words if w not in STOPWORDS), key=len, reverse=True)[:10]


def cache_key(task):
    """返回 (key, keywords)。同类任务用词略有不同也能命中同一份结果。"""
    kws = extract_keywords_from_task(task)
    norm = " ".join(kws) if kws else task.strip().lower()
    return hashlib.md5(norm.encode("utf-8")).hexdigest()[:16], kws


def is_fresh(ts, now=None):
    """共享条目是否还在有效期内。"""
    now = now or time.time()
    try:
        return 0 <= now - float(ts) < TTL_SECONDS
    except (TypeError, ValueError):
        return False
