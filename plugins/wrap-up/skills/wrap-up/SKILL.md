---
name: wrap-up
description: End-of-day check-in across all the user's projects. Scans every project folder for work that needs a commit, work that needs a pull request, commits that aren't pushed, untracked files and folders, open PRs and open issues, then builds a to-do list of what was discussed in today's Claude Code sessions but never got done, and offers to turn any of those to-dos into GitHub issues on the right repos. Use whenever the user says "wrap up", "end of day", "where am I", "where did I leave off", "what's left", "what's uncommitted", "anything to commit or PR", "what didn't we get to", or runs /wrap-up, even if they don't use those exact words.
argument-hint: "[optional: a date like 2026-10-27, or a folder to scan]"
---

# Wrap up

Give the user a clear picture of where every project stands at the end of the day, so nothing is left half-done and forgotten overnight. The report has two halves: the **git state** of every project (read from the repos themselves, so it's exact) and the **unfinished to-dos** (read from the day's conversations, so it needs judgment).

## Rules

- **This skill reads; it doesn't ship.** It never commits, pushes, opens a PR, merges, stashes, switches branches or deletes anything. If work needs a commit or a PR, say so and point to `/ship-pr` in that folder. The user reviews and ships their own work.
- **The only thing it ever creates is a GitHub issue, and only after the user has approved the drafts** (Step 5). An issue is public if the repo is public, and it can't be fully unsent, so nothing goes out on inference.
- If a script fails, say which one and why, and carry on with the other half of the report. A partial report is better than none.

## Step 1: Pick the day and the folder

- **Day:** today unless the user gave a date. The scripts take any date; sessions older than a few weeks may have been cleaned up by Claude Code.
- **Folder:** `~/Documents/claude_projects`, where the user keeps their projects, unless they named another. Pass it as `--root`.

## Step 2: Read the git state

Run `python3 scripts/repo_status.py` (path relative to this skill's folder). It takes about 10 seconds because it fetches from GitHub first, so the "ahead" and "behind" counts are current. Add `--no-fetch` if offline, `--root <folder>` for another folder, and `--no-github` to skip PR and issue lookups.

It prints JSON, one entry per repo. Linked **worktrees** are grouped under their repo as extra `working_trees`, because each can hold its own uncommitted work. Sort what you find into these sections:

| Section | What to look for |
|---|---|
| **Needs a commit** | Any working tree with `staged`, `unstaged` or `conflicted` files. Say which tree (folder and branch) and how many files. |
| **Needs a push** | A tree with `ahead_of_upstream` above 0, or a branch in `branches_with_unmerged_work` with `pushed: false`. |
| **Needs a PR** | A branch in `branches_with_unmerged_work` whose `pr` is `none`: it has commits the default branch lacks and no pull request was ever opened for it. |
| **Awaiting review** | `open_prs`. These need the user to review and merge; nothing for Claude to do. |
| **Untracked** | `untracked` files in a tree, `stashes`, and every entry in `folders_not_under_git`, which no repo is tracking at all. |
| **On the default branch** | A tree on `main` with uncommitted changes or unpushed commits. These repos expect work on a branch, so flag it. `/ship-pr` moves it onto one. |

Read the numbers with care, since they can mislead:

- A large `commits_ahead_of_default` usually means branches stacked on one another, not 35 commits of new work. Report the count and let the user judge.
- `pr: closed_or_merged_only` means a PR existed for that branch. Don't list it under "Needs a PR"; mention it only if the branch has fresh commits after the merge.
- If `github` is `unavailable`, PR and issue information is missing: say so instead of reporting "no PRs".

For **where the user is** in each project, give one line: the branch, the last commit (subject and how long ago), open PRs and open issues, and any in-progress spec work (`openspec_active_changes`, or the latest `spec_kit_features`). Collapse repos with nothing pending into a single "all clear" line.

## Step 3: Find the unfinished to-dos

Run `python3 scripts/session_digest.py [YYYY-MM-DD]`. For each Claude Code session that day it prints what the user typed and **Claude's closing message of each recent turn**. Closing messages matter most: they hold the "still open", "next" and "I can also…" lists. This conversation is included, and the output is grouped by the folder each session ran in.

A to-do is something that was **asked for or agreed and not finished**:

- Something the user asked for that no later message shows done.
- An item in a closing message's "still open" or "next steps" list.
- A deferral from the user: "for now", "later", "let's leave this as a placeholder", "next time".
- An offer from Claude that the user never accepted or declined. Count these only when it's a real piece of work, not a passing "let me know if you'd like more".

Leave out anything **finished later in the day** (check later prompts, closing messages, and `git log --since=midnight` in the repo) and anything the user declined. Merge duplicates. Write each to-do as one plain line starting with a verb.

Match each to-do to a repo by the session's folder; a worktree counts as its main repo. To-dos about things that aren't in a repo, such as a Notion page, a résumé or a design file, go under **No repo**. They can stay on the list, but they can't become GitHub issues unless the user names a repo.

If a session's digest is too thin to tell, say so instead of guessing. A shorter, accurate list beats a long one with invented items.

## Step 4: Print the report

Use this order. Show every section, with "Nothing" on a single line when it's empty, so the user can see it was checked.

```
# Wrap-up for <weekday, date>

## Where you are
<one line per project: branch, last commit, PRs, issues, spec work>

## Needs a commit
## Needs a push
## Needs a PR
## Awaiting review
## Untracked

## Still to do
1. <to-do> (<repo>)
2. <to-do> (<repo>)
No repo: 3. <to-do>
```

Keep it scannable: counts and at most five file names per tree, never file contents. Number the to-dos continuously, across repos, so the user can pick by number. End with one line pointing to `/ship-pr` for anything that needs a commit or PR.

## Step 5: Offer GitHub issues

Ask which to-dos should become issues: "Reply with numbers (for example `1, 3`), `all with a repo`, or `none`." Don't use a multiple-choice prompt, because the list can be longer than it allows.

For the numbers chosen, follow `references/issues.md`: draft every issue, show the drafts, wait for approval, then create them one at a time and give back the links.
