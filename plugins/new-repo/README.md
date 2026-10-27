# New Repo

A Claude Code skill that turns the current folder into a GitHub repo with a standard set of guard-rails, or hardens an existing repo that has gone public.

Run `/new-repo` (optionally with a repo name and `python` or `node`) and Claude:

- **Asks for what it needs** in one question: name, owner, visibility (private by default), stack and description.
- **Checks first.** Stops if the folder already has commits or a remote, or the repo name is taken, and shows you a summary to confirm before it creates anything.
- **Adds the base layer to every repo:** `CLAUDE.md` rules for branch-only work and PRs, Claude deny rules and a `block-merge.py` hook that blocks merging and pushing to `main`, a PR template, issue templates (bug, feature, user story) and labels, CI tests, and Dependabot alerts and updates. It sets the repo to merge commits only, deletes branches on merge and turns the wiki off.
- **Adds the public layer to public repos only:** branch protection on `main` (PR required, enforced for admins, no force push or delete), required `codeql-analysis` and `dependency-review` checks, and secret scanning with push protection.
- **Gets private repos ready to go public.** They get the same files, so the public layer switches on by itself: `security.yml` skips its checks while the repo is private, a workflow runs on GitHub's `public` event to apply protection (or opens an issue asking you to), and a session-start hook warns if a public repo's `main` isn't protected.
- **Verifies the setup.** It checks the repo settings and labels, tests the hook against merge and push commands, and opens a small PR so you can see CI run.

It never merges a PR, never makes a repo public unless you ask, and never applies the public layer to a private repo. The initial commit is the only one it makes on `main`. It only runs when you type `/new-repo`; Claude won't start it on its own.

Run `/new-repo harden` in an existing public repo to add branch protection and the security checks.

On a private repo, GitHub won't stop direct pushes or merges to `main` (branch protection needs GitHub Pro there). The hook and `CLAUDE.md` rules guard Claude only.

## Setup

Requires [`gh`](https://cli.github.com/), signed in with `gh auth login`, and `python3` for the hook.

To make the public layer apply fully automatically when a private repo goes public, add a `REPO_ADMIN_TOKEN` secret: a fine-grained token limited to that repo with "Administration: write". Set it yourself with `gh secret set REPO_ADMIN_TOKEN`.

### Install the skill

In Claude Code, run:
```
/plugin marketplace add ItsAlwaysRaining/claude-skills
/plugin install new-repo@claude-skills
```

Or copy it manually:
```bash
git clone https://github.com/ItsAlwaysRaining/claude-skills.git
mkdir -p ~/.claude/skills
cp -r claude-skills/plugins/new-repo/skills/new-repo ~/.claude/skills/
```
