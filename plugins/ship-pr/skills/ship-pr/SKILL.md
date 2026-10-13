---
name: ship-pr
description: Commit the current code changes, push them to a feature branch, and open a GitHub pull request. Verifies the destination repo, the branch and the commits on it before pushing. Never merges and never pushes to the default branch. Use when the user says "ship it", "commit and push", "open a PR", or runs /ship-pr.
disable-model-invocation: true
argument-hint: "[optional: branch name, issue number or PR title]"
---

# Ship a PR

Commit → push → open a pull request, with checks before every outward step.

## Hard rules

- **Never merge.** Do not run `gh pr merge`, do not pass `--auto`, do not enable auto-merge,
  and do not approve the PR. The repo owner reviews and merges.
- **Never push to the default branch** (usually `main`), never `--force` / `-f` /
  `--force-with-lease`, and never run a bare `git push`. Always name the remote and branch.
- **Never commit on the default branch.** If on it, move the changes to a new branch first (step 2).
- If any check fails, **stop and tell the user** what failed. Do not work around it.
- The project's own rules (`CLAUDE.md`, contributing docs) win over this skill's defaults
  for branch names, commit style, tests and PR content.

## Step 1 — Verify the repo

Run and show the user the result:

```bash
git rev-parse --show-toplevel
git remote -v
gh repo view --json nameWithOwner,url,defaultBranchRef,isFork,parent
```

Confirm:
- `origin`'s push URL points to the same `owner/repo` as `gh repo view`.
- The default branch (`defaultBranchRef`, called `<base>` below). It is the PR base and the
  branch you must never push to.
- If the repo is a fork, say so and ask whether the PR should target the fork or the parent.
- If there are several remotes or anything looks unexpected, ask before continuing.

## Step 2 — Verify the branch

```bash
git fetch origin
git branch --show-current
git status --short --branch
```

- **Detached HEAD**: stop and ask.
- **On `<base>`**: create a new branch, which carries the uncommitted changes with it:
  `git switch -c <prefix>/<short-name>`. Use the project's prefix convention (commonly
  `feature/`, `fix/`, `docs/`, `chore/`). Use the name from `$ARGUMENTS` if given, otherwise
  propose one and confirm it. If `<base>` has local commits not on `origin/<base>`, stop and
  ask. Don't move them silently.
- **On another branch**: check it is built on the current base:
  `git merge-base --is-ancestor origin/<base> HEAD`. If not, warn that the branch is behind
  `<base>` and ask whether to rebase or merge first.

## Step 3 — Review what will ship

```bash
git log --oneline origin/<base>..HEAD   # commits already on the branch
git diff --stat                         # unstaged
git diff --staged --stat                # staged
git status --short                      # including untracked files
```

Read the actual diffs (`git diff`, `git diff --staged`) so the commit message and PR describe
the real change. Flag these and **do not stage** them without asking:
- secrets or local config (`.env`, keys, tokens, `settings.local.json`)
- large binaries, build output, caches, editor/workspace files, `.DS_Store`
- files unrelated to this change

Stage files by name (`git add <path> ...`), not `git add -A` / `git add .`.

## Step 4 — Run the checks

Find the project's test command in `CLAUDE.md`, the README, or the build config
(`package.json`, `pyproject.toml`, `Makefile`, …) and run it. If tests fail, stop and show
the failure. If there are no tests, say so.

Also check any project-specific rules in `CLAUDE.md` (e.g. specs updated first, tasks ticked,
changelog entry) and mention anything missing.

## Step 5 — Confirm with the user

Before committing, show a short summary and wait for a yes:

```
Repo:    <owner/repo>  (<push URL>)
Branch:  <branch>  →  PR into <base>
Commits already on branch: <n>
Files to commit: <list>
Not staged: <list, if any>
Commit message: <subject line>
Tests: <passed / none found>
```

## Step 6 — Commit

Write a message with a short imperative subject (≤ 72 chars) and a body explaining why.
Add any attribution lines the session requires. Use a heredoc so formatting is kept:

```bash
git commit -m "$(cat <<'EOF'
<subject>

<body>
EOF
)"
```

If a pre-commit hook fails, fix the issue and make a **new** commit. Don't use `--no-verify`
or `--amend` unless the user asks.

## Step 7 — Push

Re-check the branch immediately before pushing, then push it by name:

```bash
BRANCH=$(git branch --show-current)
[ -n "$BRANCH" ] && [ "$BRANCH" != "<base>" ] && git push -u origin "$BRANCH"
```

Then verify the remote has exactly what you pushed:

```bash
git rev-parse HEAD
git ls-remote origin "refs/heads/$BRANCH"
```

The two hashes must match.

## Step 8 — Open the PR

First check whether a PR already exists: `gh pr view --json url,state,baseRefName`.
If one is open, report its URL (the push already updated it) and stop.

Otherwise write the body. If the repo has `.github/pull_request_template.md`, fill in every
section and tick only the checklist items that are actually done. Add `Closes #<n>` for each
issue the PR resolves. Write the body to a temp file and create the PR with the repo and
branches stated explicitly:

```bash
gh pr create \
  --repo <owner/repo> \
  --base <base> \
  --head "$BRANCH" \
  --title "<title>" \
  --body-file <temp file>
```

## Step 9 — Report

Tell the user the repo, branch, commit hash(es) and PR URL. Remind them the PR is waiting for
their review and merge, and that afterwards they can run `git switch <base> && git pull`.
