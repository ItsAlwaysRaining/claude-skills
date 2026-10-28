#!/usr/bin/env python3
"""Summarise a day of Claude Code sessions, to find what was discussed but not done.

Reads the session transcripts Claude Code keeps in ~/.claude/projects. For each
session on the given day it prints what the user typed and how Claude closed
its last few turns. The closing messages matter most: that's where unfinished work
usually shows up ("still open", "next", offers like "I can also..."). Tool
output, system text and subagent traffic are left out.

The output is grouped by the folder each session ran in, so it can be matched
to a repo. Long prompts are cut short; the opening lines are enough to see the
topic.

Usage: session_digest.py [YYYY-MM-DD] [--user-chars N] [--claude-chars N] [--closing N]
       (the date defaults to today in local time)
"""
import argparse
import json
import re
from datetime import date, datetime
from pathlib import Path

PROJECTS = Path.home() / ".claude" / "projects"
# Blocks the IDE or harness wraps around a message; they aren't anyone's words.
WRAPPER_TAGS = re.compile(
    r"<(ide_[a-z_]+|system-reminder|command-[a-z-]+|local-command-[a-z-]+|bash-[a-z-]+|"
    r"pasted_content|browser_instruction)[^>]*>.*?</\1[^>]*>",
    re.DOTALL,
)
MAX_PROMPTS_SHOWN = 30  # keep the first few and the last many when a session is long


def message_text(content):
    """The text of a message; tool calls and tool results are skipped."""
    if isinstance(content, str):
        parts = [content]
    elif isinstance(content, list):
        parts = [c.get("text", "") for c in content if isinstance(c, dict) and c.get("type") == "text"]
    else:
        return ""
    return WRAPPER_TAGS.sub("", "\n".join(parts)).strip()


def stamp_of(entry):
    raw = entry.get("timestamp")
    return datetime.fromisoformat(raw.replace("Z", "+00:00")).astimezone() if raw else None


def cut(text, limit):
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text if len(text) <= limit else text[:limit].rstrip() + " …[cut]"


def read_session(path, day):
    """Return (cwd, user prompts, closing messages) for one day of one session.

    A closing message is Claude's last text before the user's next prompt: it is
    the one that sums up the turn, unlike the running commentary before it.
    """
    cwd, users, assistants, turn_last = None, [], [], None
    for line in path.open(encoding="utf-8", errors="replace"):
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        kind = entry.get("type")
        if kind not in ("user", "assistant") or entry.get("isMeta") or entry.get("isSidechain"):
            continue
        when = stamp_of(entry)
        if not when or when.date() != day:
            continue
        text = message_text(entry.get("message", {}).get("content"))
        if not text or text.startswith("[Request interrupted"):
            continue
        cwd = cwd or entry.get("cwd")
        if kind == "assistant":
            turn_last = (when, text)
            continue
        if turn_last:  # a new prompt ends the previous turn
            assistants.append(turn_last)
            turn_last = None
        users.append((when, text))
    if turn_last:
        assistants.append(turn_last)
    return cwd, users, assistants


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("day", nargs="?", default=date.today().isoformat())
    parser.add_argument("--user-chars", type=int, default=300)
    parser.add_argument("--claude-chars", type=int, default=1800)
    parser.add_argument("--closing", type=int, default=3, help="how many closing messages to show per session")
    args = parser.parse_args()
    day = date.fromisoformat(args.day)

    by_project = {}
    for path in PROJECTS.glob("*/*.jsonl"):
        if datetime.fromtimestamp(path.stat().st_mtime).date() < day:
            continue
        cwd, users, assistants = read_session(path, day)
        if users:  # no typed prompts means a background job, not a conversation
            by_project.setdefault(cwd or path.parent.name, []).append((path.stem[:8], users, assistants))

    if not by_project:
        print(f"No Claude Code sessions found for {day}.")
        return
    for project, sessions in sorted(by_project.items()):
        print(f"## {project}")
        for sid, users, assistants in sorted(sessions, key=lambda s: (s[1] or s[2])[0][0]):
            times = [t for t, _ in users + assistants]
            print(f"### session {sid} ({min(times):%H:%M} to {max(times):%H:%M}, {len(users)} prompts)")
            shown = users
            if len(users) > MAX_PROMPTS_SHOWN:
                shown = users[:5] + users[-(MAX_PROMPTS_SHOWN - 5):]
                print(f"(showing 5 first and {MAX_PROMPTS_SHOWN - 5} last of {len(users)} prompts)")
            for when, text in shown:
                print(f"- [{when:%H:%M}] " + cut(text, args.user_chars).replace("\n", " "))
            if assistants:
                print("Claude's closing messages (last of each turn):")
                for when, text in assistants[-args.closing:]:
                    print(f"> [{when:%H:%M}] " + cut(text, args.claude_chars).replace("\n", "\n> "))
            print()


if __name__ == "__main__":
    main()
