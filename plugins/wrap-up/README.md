# Wrap up

A Claude Code skill for the end of the day. It tells you where every project stands, what's still sitting uncommitted, what needs a pull request, and what you talked about but never got to, then lets you turn any of those to-dos into GitHub issues.

Run `/wrap-up` (optionally with a date, or a folder to scan) and Claude gives you a report with:

- **Where you are.** One line per project: branch, last commit, open PRs and issues, and any in-progress spec work (OpenSpec changes, Spec Kit features).
- **Needs a commit.** Staged, unstaged and conflicted changes, in every repo and every linked worktree.
- **Needs a push.** Commits that exist only on your machine.
- **Needs a PR.** Branches with work the default branch doesn't have and no pull request.
- **Awaiting review.** Your open PRs.
- **Untracked.** New files git doesn't know about, stashes, and project folders that aren't git repos at all.
- **Still to do.** A numbered list of things asked for or agreed in the day's Claude Code sessions that never got finished, matched to the repo they belong to.

Then it asks which to-dos you'd like as GitHub issues. It drafts each one (title, body, labels), checks for duplicates, shows you every draft, and creates the issues only after you approve.

## What it never does

It reads; it doesn't ship. It never commits, pushes, opens a PR, merges, stashes or deletes anything, and points to [`/ship-pr`](../ship-pr/) for that. The only thing it creates is a GitHub issue, and only after you've seen and approved the draft. The one write it makes is `git fetch --prune`, which refreshes remote branch information so "ahead" and "behind" are accurate (skip it with `--no-fetch`).

## How it works

Two scripts do the exact parts, and Claude does the judgment:

- `scripts/repo_status.py` scans every folder under `~/Documents/claude_projects` and reports git state as JSON. It groups linked worktrees under their repo and lists folders that aren't under git.
- `scripts/session_digest.py` prints what you typed in each Claude Code session that day, plus how Claude closed each of its last few turns. Those closing messages are where "still open" lists show up.

Claude reads both, decides which items are really unfinished (leaving out anything done later in the day), and writes the report.

## Setup

Requires [`gh`](https://cli.github.com/), signed in with `gh auth login`, and Python 3. Without `gh` the report still works but leaves out PRs and issues.

### Install the skill

In Claude Code, run:
```
/plugin marketplace add ItsAlwaysRaining/claude-skills
/plugin install wrap-up@claude-skills
```

Or copy it manually:
```
cp -r plugins/wrap-up/skills/wrap-up ~/.claude/skills/
```

### Scanning a different folder

The default is `~/Documents/claude_projects`. Name another folder when you run it (`/wrap-up ~/code`), or edit `--root` in `scripts/repo_status.py`.

## Limits

- Claude Code only keeps session transcripts for a while, so a wrap-up for a date weeks ago may have little to go on.
- Chats on claude.ai aren't stored on your machine, so they can't be included.
- The to-do list is Claude's reading of your conversations. It can miss an item or include one that was settled somewhere else, so skim it before turning anything into an issue.
