#!/usr/bin/env python3
"""List what the user typed in Claude Code sessions on a given day.

Reads the session transcripts Claude Code keeps in ~/.claude/projects and
prints each prompt the user typed (not tool output, system text or subagent
traffic), grouped by project, oldest first. Long prompts, such as pasted
transcripts, are cut short; the opening lines are enough to spot the topic.

Usage: todays_prompts.py [YYYY-MM-DD] [--max-chars N]
       (the date defaults to today in local time)
"""
import argparse
import json
import re
from datetime import date, datetime
from pathlib import Path

PROJECTS = Path.home() / ".claude" / "projects"
# Blocks the IDE or harness wraps around a prompt; they aren't the user's words.
WRAPPER_TAGS = re.compile(
    r"<(ide_[a-z_]+|system-reminder|command-[a-z-]+|local-command-[a-z-]+|bash-[a-z-]+)>.*?</\1>",
    re.DOTALL,
)


def prompt_text(content):
    if isinstance(content, str):
        parts = [content]
    elif isinstance(content, list):
        # Tool results come back as user messages too; skip them.
        parts = [c.get("text", "") for c in content if isinstance(c, dict) and c.get("type") == "text"]
    else:
        return ""
    return WRAPPER_TAGS.sub("", "\n".join(parts)).strip()


def local_date(timestamp):
    return datetime.fromisoformat(timestamp.replace("Z", "+00:00")).astimezone().date()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("day", nargs="?", default=date.today().isoformat())
    parser.add_argument("--max-chars", type=int, default=400)
    args = parser.parse_args()
    day = date.fromisoformat(args.day)

    found = {}
    for path in PROJECTS.glob("*/*.jsonl"):
        if datetime.fromtimestamp(path.stat().st_mtime).date() < day:
            continue
        for line in path.open(encoding="utf-8", errors="replace"):
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if entry.get("type") != "user" or entry.get("isMeta") or entry.get("isSidechain"):
                continue
            stamp = entry.get("timestamp")
            if not stamp or local_date(stamp) != day:
                continue
            text = prompt_text(entry.get("message", {}).get("content"))
            if not text or text.startswith("[Request interrupted"):
                continue
            if len(text) > args.max_chars:
                text = text[: args.max_chars].rstrip() + " …[cut]"
            project = entry.get("cwd") or path.parent.name
            found.setdefault(project, []).append((stamp, text))

    if not found:
        print(f"No Claude Code prompts found for {day}.")
        return
    for project, prompts in sorted(found.items()):
        print(f"## {project}")
        for stamp, text in sorted(prompts):
            time = datetime.fromisoformat(stamp.replace("Z", "+00:00")).astimezone().strftime("%H:%M")
            print(f"- [{time}] " + text.replace("\n", " "))
        print()


if __name__ == "__main__":
    main()
