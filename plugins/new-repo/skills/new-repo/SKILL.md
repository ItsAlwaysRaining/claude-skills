---
name: new-repo
description: Create a new GitHub repo with the user's standard setup, or harden an existing repo that has gone public. Every repo gets PR-only workflow rules, a Claude hook that blocks merging and pushing to main, branch-only work, GitHub Issues (templates and labels), CI tests and Dependabot. Public repos also get branch protection, required CodeQL and dependency review, and secret scanning with push protection. Those are applied automatically if a private repo later goes public. Supports Python and Node/TypeScript. Use when the user runs /new-repo or asks to set up a new repo.
disable-model-invocation: true
argument-hint: "[repo-name] [python|node]  |  harden"
---

# New repo

Turn the current (empty or new) folder into a GitHub repo with the user's standard guard-rails.
Templates live next to this file in `templates/`. `common/` applies to every repo, and
`python/` or `node/` add the stack-specific files. Folders called `claude/` and `github/`
in the templates become `.claude/` and `.github/` in the repo, and `gitignore` becomes `.gitignore`.

If `$ARGUMENTS` is `harden`, skip to **Harden an existing repo** at the end.

## Two layers

| Layer | Applies to | What |
|---|---|---|
| **Base** | every repo | `CLAUDE.md` rules, Claude deny rules and `block-merge.py` hook, PR template, issue templates, labels, CI tests, Dependabot alerts and updates, merge commits only, delete branch on merge |
| **Public** | public repos only | branch protection on `main` (PR required, enforced for admins, no force push or delete), required checks `codeql-analysis` and `dependency-review`, secret scanning with push protection |

The public layer uses GitHub features that are free only on public repos, so it is **never
applied to a private repo**. Every repo still gets the files for it, so it switches on when a
repo goes public:
- `security.yml` checks the repo's visibility and skips CodeQL and dependency review while it's private.
- `.github/scripts/harden-public.sh` applies the public layer, and does nothing on a private repo.
- `public-hardening.yml` runs on GitHub's `public` event (private → public). With a
  `REPO_ADMIN_TOKEN` secret it runs the script. Without one, it opens an issue asking the owner to.
- A Claude `SessionStart` hook runs the script with `--check` and warns if the repo is public
  but `main` isn't protected.

## Hard rules

- **Never merge a PR**, approve one, or enable auto-merge. The user merges.
- The initial commit is the **only** commit ever made on `main`. Everything after it goes on a branch.
- **Never make a repo public, or create a public one, without the user asking.**
- Never apply the public layer to a private repo.
- Never print, log or commit secrets. If the user wants `REPO_ADMIN_TOKEN`, they set it themselves
  with `gh secret set REPO_ADMIN_TOKEN` (it prompts for the value).
- If any `git` or `gh` command fails, **stop and report** the error. Don't work around it.
- Don't overwrite existing files without asking. If the folder already has a `CLAUDE.md`,
  `.gitignore` or `.github/`, merge the template content into them and show the user the result.

## Step 1: Gather inputs

Take what's given in `$ARGUMENTS`, then ask for the rest in **one** AskUserQuestion:

| Input | Default |
|---|---|
| Repo name | current folder name, with spaces changed to `-` |
| Owner | the `gh` user (`gh api user -q .login`), or an org the user names |
| Visibility | **private** (public only if the user says so) |
| Stack | `python` or `node` (look for `pyproject.toml` / `requirements.txt` / `package.json` first) |
| Description | none |

Stack values:

| Placeholder | python | node |
|---|---|---|
| `{{TEST_COMMAND}}` | `python -m unittest discover -s tests -v` (or `pytest` if the project uses it) | `npm test` |
| `{{CODEQL_LANGUAGES}}` | `python, actions` | `javascript-typescript, actions` |
| `{{PYTHON_VERSION}}` / `{{NODE_VERSION}}` | `3.12` | `22` |

Use the project's own versions and test command if the folder already has them.

## Step 2: Check and confirm

```bash
gh auth status
pwd && ls -la
git rev-parse --is-inside-work-tree 2>/dev/null && git log --oneline -3
gh repo view <owner>/<name> 2>&1 | head -1   # must say "not found"
```

- If the folder is already a git repo with commits, or already has a remote, stop and ask.
- If the repo name is taken, ask for another.

Show a summary and **wait for a yes**:

```
Repo:        <owner>/<name> (<visibility>)
Folder:      <path>
Stack:       <python|node>, tests: <test command>
Base layer:  Claude merge/push guard, PR + issue templates, labels, CI tests, Dependabot,
             merge commits only, delete branch on merge, wiki off
Public layer: <public: applied now | private: not applied; switches on automatically if the repo goes public>
```

For a private repo, also tell the user plainly that GitHub won't stop direct pushes or merges to
`main`. Only the Claude hook and `CLAUDE.md` rules do, and those apply to Claude only.

## Step 3: Add the files

The same files go into every repo, public or private.

```bash
SKILL=<folder this SKILL.md is in>/templates   # absolute path; differs for a plugin install
STACK=<python|node>
mkdir -p .claude/hooks .github/ISSUE_TEMPLATE .github/workflows .github/scripts
cp "$SKILL/common/CLAUDE.md" CLAUDE.md
cp "$SKILL/common/claude/settings.json" .claude/settings.json
cp "$SKILL/common/claude/hooks/block-merge.py" .claude/hooks/block-merge.py
cp "$SKILL/common/github/scripts/harden-public.sh" .github/scripts/
chmod +x .claude/hooks/block-merge.py .github/scripts/harden-public.sh
cp "$SKILL/common/github/pull_request_template.md" .github/
cp "$SKILL"/common/github/ISSUE_TEMPLATE/*.yml .github/ISSUE_TEMPLATE/
cp "$SKILL"/common/github/workflows/*.yml .github/workflows/      # security.yml, public-hardening.yml
cp "$SKILL/$STACK/github/workflows/ci.yml" .github/workflows/
cp "$SKILL/$STACK/github/dependabot.yml" .github/
cp "$SKILL/$STACK/gitignore" .gitignore
```

Then replace every `{{...}}` placeholder with the Edit tool, and check none are left:
`grep -rn '{{' CLAUDE.md .github .claude` must print nothing except `${{ ... }}` workflow expressions.

If there's no `README.md`, write a short one: the name, the description, how to run the tests,
and a "Contributing" section saying work goes on branches and through PRs.

## Step 4: Initial commit and create the repo

```bash
git init -b main
git add CLAUDE.md README.md .gitignore .claude .github <any existing project files the user confirmed>
git status --short        # show the user; no secrets, .env, settings.local.json or build output
git commit -m "Initial repo setup"   # add the session's attribution lines
gh repo create <owner>/<name> --<private|public> --source . --remote origin --push \
  [--description "<description>"]
```

## Step 5: Base layer settings (every repo)

```bash
R=<owner>/<name>
gh repo edit $R --enable-merge-commit --enable-squash-merge=false --enable-rebase-merge=false \
  --delete-branch-on-merge --enable-wiki=false --enable-issues
gh api -X PUT repos/$R/vulnerability-alerts            # Dependabot alerts (free on private too)
gh api -X PUT repos/$R/automated-security-fixes        # Dependabot security PRs
```

Labels:

```bash
gh label create bug           --color d73a4a --description "Something isn't working" --force -R $R
gh label create enhancement   --color a2eeef --description "New feature or request" --force -R $R
gh label create user-story    --color 1D76DB --description "A user story with acceptance criteria" --force -R $R
gh label create security      --color b60205 --description "Security issue or hardening" --force -R $R
gh label create chore         --color c5def5 --description "Tooling, docs, maintenance" --force -R $R
gh label create dependencies  --color 0366d6 --description "Dependency updates" --force -R $R
gh label create priority:high --color e99695 --description "Do this soon" --force -R $R
gh label create priority:low  --color f9d0c4 --description "Nice to have" --force -R $R
```

## Step 6: Public layer (public repos only)

**Private repo: skip this step.**

Public repo:

```bash
bash .github/scripts/harden-public.sh $R
```

`required_approving_review_count` is 0 because a solo owner can't approve their own PR.
Claude is kept from merging by `.claude/settings.json` and the hook. GitHub can't tell Claude
from the user, since both use the same token.

## Step 7: Verify

```bash
gh repo view $R --json visibility,deleteBranchOnMerge,mergeCommitAllowed,squashMergeAllowed,rebaseMergeAllowed
gh label list -R $R
bash .github/scripts/harden-public.sh --check $R      # must print nothing
```

Public repo only:

```bash
gh api repos/$R/branches/main/protection \
  -q '{checks: .required_status_checks.contexts, admins: .enforce_admins.enabled, force: .allow_force_pushes.enabled}'
```

Test the Claude hook without running anything. Each of these must print `2`:

```bash
for c in "gh pr merge 1" "git push origin main" "git push origin HEAD:main" "git push -f origin x" \
         "gh api -X PUT repos/$R/pulls/1/merge" "git commit -m x"; do
  printf '{"tool_name":"Bash","tool_input":{"command":"%s"},"cwd":"%s"}' "$c" "$PWD" \
    | python3 .claude/hooks/block-merge.py 2>/dev/null; echo "$? $c"
done
```

Then show that the checks run: `git switch -c chore/verify-ci`, make a trivial README change, and
open a PR (follow `/ship-pr` if it's installed). Wait with `gh pr checks --watch` and report the
results. On a private repo, `codeql-analysis` and `dependency-review` show as skipped, which is
expected. Leave the PR for the user to merge or close.

## Step 8: Report

Tell the user:
- the repo URL, its visibility, and which layers were applied
- anything that failed
- the verify PR URL and its check results
- for a private repo: what happens if it goes public (the workflow, the issue it opens, the
  session-start warning), and that adding a `REPO_ADMIN_TOKEN` secret makes it fully automatic.
  This is a fine-grained token limited to this repo, with "Administration: write".
- that the hooks take effect in new Claude Code sessions in this folder, and guard Claude only
- next steps: open issues with `gh issue create`, and start work with `git switch -c feature/<name>`

## Harden an existing repo

For `/new-repo harden`, or when the session-start check warns that a public repo is unprotected.

1. `R=$(gh repo view --json nameWithOwner -q .nameWithOwner)` and
   `gh repo view --json visibility`. If it's private, say the public layer only applies to public
   repos and stop.
2. Show the user what will change (the public layer table above) and wait for a yes.
3. If `.github/scripts/harden-public.sh` exists, run it. Otherwise run the template copy:
   `bash <folder this SKILL.md is in>/templates/common/github/scripts/harden-public.sh $R`.
4. If `security.yml`, `public-hardening.yml` or the script are missing from the repo, offer to add
   them on a `chore/public-hardening` branch with a PR. Until `security.yml` is on `main`, the
   required checks can't pass, so mention that PRs will be blocked until that PR is merged.
5. Run the checks from step 7 and report.
