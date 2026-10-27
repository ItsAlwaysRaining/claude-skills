#!/usr/bin/env python3
"""PreToolUse hook: stop Claude from merging PRs or changing the default branch directly.

Claude Code passes the tool call as JSON on stdin. Exit code 2 blocks the call and
sends stderr back to Claude. Anything else is allowed.

Blocks:
  - gh pr merge (incl. --auto), gh pr review --approve
  - gh api calls that merge a PR, enable auto-merge, or delete branch protection
  - git push to main/master, force pushes, +refspecs, --mirror, deleting main/master
  - git commit / merge / rebase / reset / cherry-pick while on main/master
    (except the very first commit of a new repo)
"""
import json
import os
import re
import shlex
import subprocess
import sys

PROTECTED = {"main", "master"}
GIT_OPTS_WITH_VALUE = {"-C", "-c", "--git-dir", "--work-tree", "--namespace"}
PUSH_OPTS_WITH_VALUE = {"-o", "--push-option", "--repo", "--receive-pack", "--exec"}
WRITES_ON_BRANCH = {"commit", "merge", "rebase", "reset", "cherry-pick", "revert", "am", "pull"}


def block(reason):
    print("Blocked by .claude/hooks/block-merge.py: " + reason
          + " Work on a feature/fix/chore branch and open a PR; the repo owner merges.",
          file=sys.stderr)
    sys.exit(2)


def git(cwd, *args):
    try:
        out = subprocess.run(["git", "-C", cwd, *args], capture_output=True, text=True, timeout=5)
    except Exception:
        return None
    return out.stdout.strip() if out.returncode == 0 else None


def segments(command):
    """Split a shell command line into simple commands (on ; && || | & and newlines)."""
    for part in re.split(r"\|\||&&|[;|&\n]", command):
        try:
            tokens = shlex.split(part, posix=True)
        except ValueError:
            tokens = part.split()
        while tokens and re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", tokens[0]):
            tokens.pop(0)  # leading VAR=value assignments
        while tokens and tokens[0] in {"sudo", "command", "exec", "env", "time", "nohup"}:
            tokens.pop(0)
        if tokens:
            yield tokens


def is_protected_ref(ref):
    ref = ref.lstrip("+")
    if ref.startswith("refs/heads/"):
        ref = ref[len("refs/heads/"):]
    return ref in PROTECTED


def check_gh(tokens):
    args = tokens[1:]
    if args[:2] == ["pr", "merge"]:
        block("Claude may not merge pull requests.")
    if args[:2] == ["pr", "review"] and any(a in ("--approve", "-a") for a in args):
        block("Claude may not approve pull requests.")
    if args[:1] == ["api"]:
        text = " ".join(args)
        upper = text.upper()
        if re.search(r"/pulls/[^/\s]+/merge\b", text) or re.search(r"/merges\b", text):
            block("Claude may not merge through the GitHub API.")
        if re.search(r"mergePullRequest|enablePullRequestAutoMerge|mergeBranch", text):
            block("Claude may not merge through the GraphQL API.")
        if "protection" in text and ("DELETE" in upper.split() or "-XDELETE" in upper.replace(" ", "")):
            block("Claude may not remove branch protection.")
        if re.search(r"/git/refs/heads/(main|master)\b", text):
            block("Claude may not change main/master through the API.")


def check_git(tokens, cwd):
    args = tokens[1:]
    i = 0
    while i < len(args) and args[i].startswith("-"):
        if args[i] == "-C" and i + 1 < len(args):
            cwd = args[i + 1]
        i += 2 if args[i] in GIT_OPTS_WITH_VALUE else 1
    if i >= len(args):
        return
    sub, rest = args[i], args[i + 1:]

    if sub == "push":
        positional = []
        j = 0
        while j < len(rest):
            a = rest[j]
            if a in ("-f", "--force", "--mirror") or a.startswith("--force-with-lease") \
                    or a == "--force-if-includes" or (a.startswith("-") and not a.startswith("--") and "f" in a[1:]):
                block("force pushes are not allowed.")
            if a in PUSH_OPTS_WITH_VALUE:
                j += 2
                continue
            if not a.startswith("-"):
                positional.append(a)
            j += 1
        deleting = any(a in ("-d", "--delete") for a in rest)
        refspecs = positional[1:]
        for spec in refspecs:
            if spec.startswith("+"):
                block("force pushes (+refspec) are not allowed.")
            dst = spec.split(":")[-1] if ":" in spec else spec
            if is_protected_ref(dst) or (deleting and is_protected_ref(spec)):
                block("pushing to main/master is not allowed.")
            if spec.split(":")[0] == "HEAD" and ":" not in spec:
                branch = git(cwd, "branch", "--show-current")
                if branch in PROTECTED:
                    block("pushing to main/master is not allowed.")
        if not refspecs:
            branch = git(cwd, "branch", "--show-current")
            if branch in PROTECTED:
                block("pushing from main/master is not allowed.")
        return

    if sub in WRITES_ON_BRANCH:
        if sub == "pull":
            return  # updating local main from origin is fine
        if sub == "reset" and not any(a == "--hard" for a in rest):
            return
        branch = git(cwd, "branch", "--show-current")
        if branch in PROTECTED and git(cwd, "rev-parse", "--verify", "-q", "HEAD") is not None:
            block("'git %s' on %s is not allowed; create a branch first "
                  "(git switch -c feature/<name>)." % (sub, branch))


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return
    if data.get("tool_name") != "Bash":
        return
    command = (data.get("tool_input") or {}).get("command", "")
    cwd = data.get("cwd") or "."
    for tokens in segments(command):
        name = tokens[0].rsplit("/", 1)[-1]
        if name == "cd" and len(tokens) > 1:
            cwd = os.path.join(cwd, os.path.expanduser(tokens[1]))
        elif name == "gh":
            check_gh(tokens)
        elif name == "git":
            check_git(tokens, cwd)


if __name__ == "__main__":
    main()
