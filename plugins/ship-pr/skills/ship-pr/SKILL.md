---
name: ship-pr
description: Commit the current code changes, bring the branch up to date with the remote and the default branch (resolving any merge conflicts), push it, and open a GitHub pull request. Verifies the destination repo, the branch and the commits on it before pushing. Never merges the PR and never pushes to the default branch. Use when the user says "ship it", "commit and push", "open a PR", or runs /ship-pr.
disable-model-invocation: true
argument-hint: "[optional: branch name, issue number or PR title]"
---

# Ship a PR

Commit → sync with the remote and the base branch → test → push → open a pull request, with
checks before every outward step.

## Hard rules

- **Never merge the PR.** Do not run `gh pr merge`, do not pass `--auto`, do not enable
  auto-merge, and do not approve the PR. The repo owner reviews and merges.
- **Never push to the default branch** (usually `main`), never `--force` / `-f` /
  `--force-with-lease`, and never run a bare `git push`. Always name the remote and branch.
- **Never commit on the default branch.** If on it, move the changes to a new branch first (step 2).
- **Bring in the base by merging, not rebasing.** Rebasing a branch that's already pushed
  rewrites its history and would need a force push.
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
- **On another branch**: if its PR has already been merged or closed
  (`gh pr view --json state`), stop and ask. New work should go on a fresh branch off `<base>`.

Note how far behind the branch is. Step 6 brings it up to date:

```bash
git rev-list --count HEAD..origin/<base>                        # commits on base not on branch
git rev-list --count HEAD..@{u} 2>/dev/null                     # commits on the remote branch not here
```

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

## Step 4 — Confirm with the user

Before committing, show a short summary and wait for a yes:

```
Repo:    <owner/repo>  (<push URL>)
Branch:  <branch>  →  PR into <base>
Commits already on branch: <n>
Behind <base> by: <n> commits   (will be merged in before pushing)
Files to commit: <list>
Not staged: <list, if any>
Commit message: <subject line>
```

## Step 5 — Commit

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

Commit before syncing so that a merge never runs on top of uncommitted work.

## Step 6 — Bring the branch up to date

```bash
git fetch origin
BRANCH=$(git branch --show-current)
```

**a. Pull the branch's own remote commits** (e.g. pushed from another machine, or a
suggestion applied on GitHub). Skip this if the branch has never been pushed:

```bash
git ls-remote --exit-code --heads origin "$BRANCH" >/dev/null && git pull --no-rebase origin "$BRANCH"
```

**b. Merge in the latest base** so the PR is tested against what it will land on, and
conflicts get fixed here instead of on GitHub:

```bash
git merge --no-edit origin/<base>
```

If both say "Already up to date", go to step 7.

**c. If there are conflicts**, resolve them. Don't abort at the first conflict.

1. List them: `git diff --name-only --diff-filter=U`.
2. For each file, understand both sides before editing:
   - `git diff` (shows the conflict hunks)
   - `git log --oneline HEAD..origin/<base> -- <file>` and `git show <commit> -- <file>`
     to see *why* the base changed it
3. Edit the file so it keeps **both** intents: the base's change and this branch's change.
   Never resolve by taking one side for a whole file (`git checkout --ours/--theirs`)
   unless that's clearly correct and you tell the user.
4. If the right result is ambiguous (both sides changed the same logic in different ways,
   or one side deleted what the other edited), show the user both versions and your
   proposed resolution, and ask.
5. Check that no conflict markers remain:
   `git diff --check` and `grep -rnE '^(<<<<<<<|=======|>>>>>>>)( |$)' -- <files>`
6. `git add <resolved files>` and `git commit --no-edit` to finish the merge.

If you can't resolve it, run `git merge --abort`, report which files conflict and why, and
stop. Don't push.

**d. Re-read lockfiles and generated files** that merged cleanly but may now be stale
(`package-lock.json`, `poetry.lock`, generated code). Regenerate them with the project's tool
if needed and commit the result.

Tell the user what was pulled and merged: number of commits, any conflicts and how each was
resolved.

## Step 7 — Run the checks

Run the tests **after** syncing, so they cover the merged result. Find the project's test
command in `CLAUDE.md`, the README, or the build config (`package.json`, `pyproject.toml`,
`Makefile`, …) and run it. If tests fail, stop and show the failure. If the failure only
appeared after the merge, say so. Merged code that tests clean on each side can still
conflict in meaning. If there are no tests, say so.

Also check any project-specific rules in `CLAUDE.md` (e.g. specs updated first, tasks ticked,
changelog entry) and mention anything missing.

## Step 8 — Push

Re-check the branch and that it contains the latest base immediately before pushing, then
push it by name:

```bash
git fetch origin
BRANCH=$(git branch --show-current)
git merge-base --is-ancestor origin/<base> HEAD || echo "BASE MOVED: go back to step 6"
[ -n "$BRANCH" ] && [ "$BRANCH" != "<base>" ] && git push -u origin "$BRANCH"
```

If the base moved, repeat step 6 and step 7 before pushing. If the push is rejected as
non-fast-forward, repeat step 6a. Never force-push.

Then verify the remote has exactly what you pushed:

```bash
git rev-parse HEAD
git ls-remote origin "refs/heads/$BRANCH"
```

The two hashes must match.

## Step 9 — Open the PR

First check whether a PR already exists: `gh pr view --json url,state,baseRefName`.
If one is open, the push already updated it. Skip to the conflict check below.

Otherwise write the body. If the repo has `.github/pull_request_template.md`, fill in every
section and tick only the checklist items that are actually done. Add `Closes #<n>` for each
issue the PR resolves, and mention any merge conflicts you resolved. Write the body to a temp
file and create the PR with the repo and branches stated explicitly:

```bash
gh pr create \
  --repo <owner/repo> \
  --base <base> \
  --head "$BRANCH" \
  --title "<title>" \
  --body-file <temp file>
```

Then confirm GitHub sees no conflicts:

```bash
gh pr view --json mergeable,mergeStateStatus
```

`mergeable` can read `UNKNOWN` for a few seconds while GitHub computes it. Check again.
If it's `CONFLICTING`, go back to step 6.

## Step 10 — Report

Tell the user the repo, branch, commit hash(es), what was merged in from the remote and
`<base>` (and any conflicts resolved), the test result, and the PR URL. Remind them the PR is
waiting for their review and merge, and that afterwards they can run
`git switch <base> && git pull`.
