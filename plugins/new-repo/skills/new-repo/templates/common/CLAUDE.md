# Project rules

## Git workflow

- Every change goes through a pull request. On a public repo GitHub enforces this with
  branch protection. On a private repo only these rules and the hook enforce it, so follow them
  just as strictly.
- Start each piece of work on a new branch off an up-to-date `main`:
  `feature/<name>` for features, `fix/<name>` for bug fixes, `chore/<name>` for tooling and docs.
  Never commit on `main`.
- Track work in GitHub Issues. Before starting, find or create the issue
  (`gh issue create --label <bug|enhancement|chore>`) and use its number in the branch name
  when it helps, e.g. `fix/42-login-timeout`.
- Push the branch and open a PR with `gh pr create`, filling in `.github/pull_request_template.md`.
  Put `Closes #<n>` in the PR description for each issue the PR resolves.
- Never merge a PR, approve one, or enable auto-merge. The repo owner reviews and merges every PR.
  `.claude/settings.json` and `.claude/hooks/block-merge.py` enforce this.
  After a merge: `git switch main && git pull`.
- CI runs the tests (`ci.yml`) on every PR. On a public repo, CodeQL and dependency review
  (`security.yml`) also run and must pass before merge. They're skipped while the repo is private.
- If the repo is public but `main` isn't protected (the session-start check warns about this),
  tell the user and offer to run `bash .github/scripts/harden-public.sh`. Don't make a repo
  public without the user asking.
- Run the tests with `{{TEST_COMMAND}}`.
