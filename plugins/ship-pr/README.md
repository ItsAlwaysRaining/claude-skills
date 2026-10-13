# Ship PR

A Claude Code skill that commits your changes, pushes them to a branch and opens a GitHub pull request, checking where everything is going first.

Run `/ship-pr` (optionally with a branch name, issue number or PR title) and Claude:

- **Checks the repo.** Shows the `origin` URL next to what GitHub reports, and stops on a fork, extra remotes or a mismatch.
- **Checks the branch.** Moves changes off `main` onto a new branch, stops if git isn't on a branch or the branch's PR was already merged, and tells you how far behind `main` it is.
- **Reviews what will ship.** Lists commits already on the branch and every changed or new file, stages files by name, and won't stage secrets, build output or unrelated files without asking.
- **Asks you to confirm** the repo, branch, files and commit message before committing.
- **Brings the branch up to date.** After committing, pulls any new commits on the branch from GitHub, then merges in the latest `main`. It resolves merge conflicts by keeping both sides' intent, asks you when the right fix is unclear, and stops without pushing if it can't resolve them. It merges rather than rebases, so it never needs a force push.
- **Runs the project's tests** on the merged result, plus any rules in its `CLAUDE.md`.
- **Pushes the branch by name**, checks again that `main` hasn't moved, and confirms the commit hash on GitHub matches your local one.
- **Opens the PR**, filling in the repo's PR template if there is one, or reports the existing PR. Then it checks that GitHub reports no conflicts.

It **never merges the PR**, approves or turns on auto-merge, and never force-pushes or pushes to `main`. It only runs when you type `/ship-pr`; Claude won't start it on its own.

## Setup

Requires [`gh`](https://cli.github.com/), signed in with `gh auth login`.

### Install the skill

In Claude Code, run:
```
/plugin marketplace add ItsAlwaysRaining/claude-skills
/plugin install ship-pr@claude-skills
```

Or copy it manually:
```bash
git clone https://github.com/ItsAlwaysRaining/claude-skills.git
mkdir -p ~/.claude/skills
cp -r claude-skills/plugins/ship-pr/skills/ship-pr ~/.claude/skills/
```

### Optional: a hard guard

The skill's rules are instructions. To also block merges and pushes to `main` at the permission level, add this to a project's `.claude/settings.json`:

```json
{
  "permissions": {
    "deny": [
      "Bash(gh pr merge *)",
      "Bash(git push origin main*)",
      "Bash(git push -f *)",
      "Bash(git push --force *)"
    ]
  }
}
```
