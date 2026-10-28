# Turning to-dos into GitHub issues

Read this when the user has picked to-dos in Step 5. The aim is issues that make sense to someone who wasn't in the conversation, including the user a month from now, and that are safe to publish.

## 1. Check where each issue will go

For each picked to-do, find its repo (the folder its session ran in, mapped to the repo root) and run:

```bash
gh repo view --json nameWithOwner,visibility,hasIssuesEnabled
```

- If issues are off for the repo, skip that to-do and say why.
- **Check `visibility`.** An issue on a public repo is public. The body must not contain local file paths, tokens, email addresses, or anything private from the conversation. Describe the work in terms of the project, not the session.
- A to-do under "No repo" can't become an issue until the user names a repo. Ask once; if they don't, leave it on the list.

## 2. Look for duplicates

Compare against `open_issues` from the repo status output, then run `gh issue list --repo <owner/repo> --state open --search "<key words>"`. If an issue already covers it, show the link and ask whether to skip it or comment instead. Don't create a near-duplicate.

## 3. Draft each issue

If the repo has issue templates (`.github/ISSUE_TEMPLATE/`), read them and use their headings. Otherwise use this body:

```markdown
## What
<One or two sentences: the change to make.>

## Why
<The reason, in plain terms, taken from the conversation.>

## Context
<Where this came up and anything already decided, such as options that were ruled out. Link related issues or PRs.>

## Done when
- [ ] <One to three checkable outcomes.>
```

- **Title:** a short imperative phrase under 70 characters ("Make the second Oct 23 UX Design entry a subtopic"), not a sentence about the conversation.
- **Labels:** run `gh label list --repo <owner/repo>` and use a label only if it clearly fits and already exists (`bug`, `enhancement`, `documentation`). Never create labels. Skip labels when unsure.
- **The repo's own rules win.** If its `CLAUDE.md` or contributing notes say how issues are written or that changes start with a spec, follow that, and add a line saying so when it applies.
- Don't assign people, set milestones or add projects.

## 4. Show the drafts and wait

Show every draft in full: repo, title, labels and body. Ask for approval or edits. Drafts are cheap to change and issues are not, which is why this step comes first. Create nothing until the user says yes. If they approve some and change others, create only the approved ones.

## 5. Create them

One at a time, so a failure doesn't leave the rest in doubt:

```bash
gh issue create --repo <owner/repo> --title "<title>" --body-file - <<'EOF'
<body>
EOF
```

Add `--label` only for labels checked in step 3. If a command fails, stop, show the error, and don't retry with different options. Never edit or close existing issues.

## 6. Report back

List each created issue as `owner/repo#N` with its link, plus any to-dos skipped and why. The to-dos with issues can come off the day's list; tell the user which are still open with no issue.
