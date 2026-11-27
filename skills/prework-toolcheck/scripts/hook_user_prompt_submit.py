#!/usr/bin/env python3
"""
WorkBuddy UserPromptSubmit hook —— 开工自动触发引擎。

作用：每个新会话的第一次实质任务提交时，向模型注入一段上下文，
提醒它先调用 prework-toolcheck 技能做开工扫描。

设计要点：
- 每个 session 只触发一次（靠 state 文件去重），不打扰后续追问。
- 纯打招呼、极短输入、明显是确认/续话的输入不触发。
- 可用 DISABLE 文件一键关闭：~/.workbuddy/skills/prework-toolcheck/scripts/.disabled
- 任何异常都 fail-open（continue: true），绝不阻断用户输入。
"""
import json
import os
import sys
import time

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_DIR = os.path.join(SKILL_DIR, ".trigger-state")
DISABLE_FILE = os.path.join(SKILL_DIR, "scripts", ".disabled")

os.makedirs(STATE_DIR, exist_ok=True)

# 这些输入不是"开始干活"，不触发
SKIP_EXACT = {
    "你好", "您好", "hi", "hello", "hey", "在吗", "在么", "早", "早上好",
    "谢谢", "好的", "好", "嗯", "ok", "okay", "yes", "收到", "明白", "继续",
    "是的", "对", "行", "可以", "不用了", "取消", "test", "测试",
}

# 明显是续话/确认的短句前缀
SKIP_PREFIX = ("继续", "然后", "接着", "刚才", "上面", "这个", "那个", "再", "还是")


def emit(additional_context=None):
    out = {"continue": True, "suppressOutput": True}
    if additional_context:
        out["hookSpecificOutput"] = {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": additional_context,
        }
    sys.stdout.write(json.dumps(out, ensure_ascii=False))
    sys.exit(0)


def main():
    try:
        raw = sys.stdin.read()
        data = json.loads(raw) if raw.strip() else {}
    except Exception:
        emit()

    prompt = str(data.get("prompt", "") or "").strip()
    session_id = str(data.get("session_id", "") or "default")

    # 一键关闭
    if os.path.exists(DISABLE_FILE):
        emit()
    # 空输入 / 打招呼 / 极短确认 → 跳过
    if not prompt or len(prompt) < 5 or prompt.lower() in SKIP_EXACT:
        emit()
    if prompt.startswith(SKIP_PREFIX) and len(prompt) < 12:
        emit()

    # 每个会话只触发一次
    state_file = os.path.join(STATE_DIR, f"{session_id}.json")
    if os.path.exists(state_file):
        emit()

    try:
        with open(state_file, "w", encoding="utf-8") as f:
            json.dump({"ts": time.time(), "prompt": prompt[:120]}, f, ensure_ascii=False)
    except Exception:
        pass  # 去重失败也要 fail-open

    context = (
        "【开工工具检查·自动触发】这是一次新任务的开始。\n"
        "请在动手前先调用 prework-toolcheck 技能：运行其 scripts/scan.sh 按本次任务扫描现成工具，"
        "对照 references/beginner-musthave.md，列出「已装可用 / 建议安装 / 可选」三档清单"
        "（每档最多 3 项、用大白话说明能帮用户干什么），然后用一句话明确询问用户要不要装或用。\n"
        "红线：只推荐不安装；用户说不用就直接开工，本会话不再重复扫描。\n"
        f"（触发于用户任务：{prompt[:80]}）"
    )
    emit(context)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        emit()
