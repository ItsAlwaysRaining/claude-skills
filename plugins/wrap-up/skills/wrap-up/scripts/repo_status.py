#!/usr/bin/env python3
"""Report the git state of every project folder under one root, as JSON.

For each project it finds: work that needs a commit (staged or unstaged
changes), untracked files, commits that aren't pushed, branches whose work has
no pull request yet, open PRs and issues, stashes, and in-progress spec
changes. Linked git worktrees are grouped under the repo they belong to, since
each can hold its own uncommitted work. Folders that aren't git repos are
listed too, because nothing is tracking them.

The script only reads. The one thing it writes is `git fetch --prune`, which
refreshes remote-tracking branches so "ahead" and "behind" are accurate; pass
--no-fetch to skip it.

Usage: repo_status.py [--root DIR] [--no-fetch] [--no-github]
       (root defaults to ~/Documents/claude_projects)
"""
import argparse
import json
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

LIST_CAP = 25  # file names shown per category; the count is always exact


def run(args, cwd, timeout=30):
    """Run a command; return stdout, or None if it failed."""
    try:
        out = subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return out.stdout if out.returncode == 0 else None


def git(cwd, *args, timeout=30):
    return run(["git", *args], cwd, timeout)


def default_branch(repo):
    ref = git(repo, "symbolic-ref", "--short", "refs/remotes/origin/HEAD")
    if ref:
        return ref.strip().split("/", 1)[-1]
    for name in ("main", "master"):
        if git(repo, "rev-parse", "--verify", "--quiet", f"refs/remotes/origin/{name}"):
            return name
    return None


def capped(items):
    return {"count": len(items), "files": items[:LIST_CAP]}


def tree_state(path, base):
    """State of one working tree: branch, changes, untracked files, push status."""
    branch = (git(path, "branch", "--show-current") or "").strip() or None
    state = {"path": str(path), "branch": branch or "(detached HEAD)"}

    staged, unstaged, untracked, conflicted = [], [], [], []
    for line in (git(path, "status", "--porcelain=v1", "--untracked-files=all") or "").splitlines():
        code, name = line[:2], line[3:]
        if code == "??":
            untracked.append(name)
        elif "U" in code or code in ("AA", "DD"):
            conflicted.append(name)
        else:
            if code[0] != " ":
                staged.append(name)
            if code[1] != " ":
                unstaged.append(name)
    state.update(staged=capped(staged), unstaged=capped(unstaged),
                 untracked=capped(untracked), conflicted=capped(conflicted))

    last = (git(path, "log", "-1", "--format=%h%x09%cI%x09%s") or "").strip().split("\t")
    if len(last) == 3:
        state["last_commit"] = {"hash": last[0], "date": last[1], "subject": last[2]}

    upstream = (git(path, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}") or "").strip()
    if upstream:
        counts = (git(path, "rev-list", "--left-right", "--count", f"{upstream}...HEAD") or "0\t0").split()
        state["upstream"] = upstream
        state["behind_upstream"], state["ahead_of_upstream"] = int(counts[0]), int(counts[1])
    else:
        state["upstream"] = None
    if base and branch and branch != base:
        n = (git(path, "rev-list", "--count", f"origin/{base}..HEAD") or "0").strip()
        state["commits_ahead_of_default"] = int(n)
    return state


def github_info(repo):
    """Open PRs, all PRs by branch, and open issues, via the gh CLI."""
    prs = run(["gh", "pr", "list", "--state", "all", "--limit", "100", "--json",
               "number,title,state,isDraft,headRefName,url,reviewDecision"], repo, 40)
    issues = run(["gh", "issue", "list", "--state", "open", "--limit", "30", "--json",
                  "number,title,url"], repo, 40)
    if prs is None or issues is None:
        return None
    return {"prs": json.loads(prs), "issues": json.loads(issues)}


def local_branches(repo, base):
    """Every local branch with commits not yet in the default branch."""
    rows = git(repo, "for-each-ref", "--format=%(refname:short)\t%(upstream:short)\t%(upstream:track)",
               "refs/heads") or ""
    found = []
    for row in rows.splitlines():
        name, upstream, track = (row.split("\t") + ["", ""])[:3]
        if name == base:
            continue
        ahead = int((git(repo, "rev-list", "--count", f"origin/{base}..{name}") or "0").strip())
        if ahead == 0:
            continue  # already merged into the default branch
        found.append({"branch": name, "commits_ahead_of_default": ahead,
                      "pushed": bool(upstream) and "ahead" not in track and "gone" not in track,
                      "upstream_gone": "gone" in track})
    return found


def spec_progress(repo):
    """In-progress spec changes, for projects that use OpenSpec or Spec Kit."""
    out = {}
    changes = Path(repo, "openspec", "changes")
    if changes.is_dir():
        active = sorted(p.name for p in changes.iterdir() if p.is_dir() and p.name != "archive")
        if active:
            out["openspec_active_changes"] = active
    specs = Path(repo, "specs")
    if specs.is_dir():
        folders = sorted(p.name for p in specs.iterdir() if p.is_dir())
        if folders:
            out["spec_kit_features"] = folders[-3:]
    return out


def repo_report(main_path, tree_paths, fetch, use_github):
    base = default_branch(main_path)
    if fetch:
        git(main_path, "fetch", "--quiet", "--prune", "origin", timeout=45)
        base = base or default_branch(main_path)
    remote = (git(main_path, "remote", "get-url", "origin") or "").strip() or None
    report = {"name": main_path.name, "path": str(main_path), "remote": remote,
              "default_branch": base,
              "working_trees": [tree_state(p, base) for p in tree_paths]}
    stashes = (git(main_path, "stash", "list") or "").splitlines()
    if stashes:
        report["stashes"] = stashes[:10]
    report.update(spec_progress(main_path))

    if base:
        report["branches_with_unmerged_work"] = local_branches(main_path, base)
    gh = github_info(main_path) if (use_github and remote and "github.com" in remote) else None
    if gh is None:
        report["github"] = "unavailable" if use_github else "skipped"
    else:
        report["open_prs"] = [p for p in gh["prs"] if p["state"] == "OPEN"]
        report["open_issues"] = gh["issues"]
        by_branch = {}
        for p in gh["prs"]:
            by_branch.setdefault(p["headRefName"], []).append(p["state"])
        for b in report.get("branches_with_unmerged_work", []):
            states = by_branch.get(b["branch"], [])
            b["pr"] = "open" if "OPEN" in states else ("none" if not states else "closed_or_merged_only")
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=str(Path.home() / "Documents" / "claude_projects"))
    parser.add_argument("--no-fetch", action="store_true")
    parser.add_argument("--no-github", action="store_true")
    args = parser.parse_args()
    root = Path(args.root).expanduser()
    use_github = not args.no_github and shutil.which("gh") is not None

    repos, not_git = {}, []
    for entry in sorted(p for p in root.iterdir() if p.is_dir() and not p.name.startswith(".")):
        if not (entry / ".git").exists():
            items = [p for p in entry.iterdir() if not p.name.startswith(".")]
            if items:
                newest = max(p.stat().st_mtime for p in items)
                not_git.append({"path": str(entry), "items": len(items),
                                "newest_change": datetime.fromtimestamp(newest).isoformat(timespec="minutes")})
            continue
        common = (git(entry, "rev-parse", "--path-format=absolute", "--git-common-dir") or "").strip()
        main_path = Path(common).parent if common else entry
        repos.setdefault(main_path, []).append(entry)

    reports = []
    for main_path in sorted(repos):
        trees = sorted(set(repos[main_path] + [main_path]), key=lambda p: (p != main_path, str(p)))
        reports.append(repo_report(main_path, trees, not args.no_fetch, use_github))
    print(json.dumps({"generated": datetime.now().isoformat(timespec="minutes"), "root": str(root),
                      "repos": reports, "folders_not_under_git": not_git}, indent=1))


if __name__ == "__main__":
    main()
