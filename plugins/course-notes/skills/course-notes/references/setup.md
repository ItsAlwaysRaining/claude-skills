# First-time setup

Read this when `~/.claude/course-notes/config.md` doesn't exist yet, or when the user asks to change their course-notes settings. The goal is a working config in under a minute: ask a few questions, check that Notion is reachable if they want it, and write the file.

## 1. Ask where notes should go

Ask the user (one question, with these options):

- **Notion** (recommended): pages in their Notion workspace, organized by class and section, with a searchable glossary.
- **Local files only**: Markdown files in a folder on their computer. Good if they don't use Notion, or want plain files for Obsidian, a git repo, etc.
- **Both**: Notion pages plus a local Markdown copy.

## 2. Notion settings (if they chose Notion or Both)

1. **Check the connection.** Look for Notion tools (names containing `notion`, e.g. `notion-search`). If none are available, Notion isn't connected yet. Explain how to connect it (see "Connecting Notion" below), offer to save notes locally until then, and write the config with `output: local` so their first lecture isn't lost. They can rerun setup once Notion is connected.
2. **Ask for the home page:** the Notion page that should hold all their classes (e.g. "Learning" or "Courses"). Search Notion for it. If there are several matches, ask which one. If it doesn't exist, offer to create it as a private page.
3. Record the page's ID and title in the config.

### Connecting Notion

Tell the user to do **one** of these, then start a new Claude session (connections load at session start):

- **Claude.ai connector** (simplest if they log in to Claude Code with a Claude.ai account): claude.ai → Settings → Connectors → Notion → Connect, and approve access in Notion.
- **Claude Code directly**: in a terminal run
  ```
  claude mcp add --transport http notion https://mcp.notion.com/mcp
  ```
  then start `claude`, type `/mcp`, select **notion** → **Authenticate**, and approve access in the browser.

Notion handles the login itself. The skill never sees or stores a password or token.

## 3. Local settings (if they chose Local or Both)

Ask which folder to use, suggesting `~/Documents/Lecture_Notes`. Create it if it doesn't exist.

## 4. Write the config

Create `~/.claude/course-notes/config.md` in this format:

```markdown
# course-notes settings
Edit by hand or ask Claude to "change my course-notes settings".

## Output
output: notion            # notion | local | both

## Notion
home_page_title: Learning
home_page_id: <id from Notion>
calendar_database_id: <added automatically when the Learning Calendar is created>
calendar_data_source: collection://<id>

## Local
local_folder: ~/Documents/Lecture_Notes

## Known classes (Claude keeps this updated)
<!-- one entry per class Claude has created or found in Notion -->
- Example Class Name
  - page_id: <id>
  - glossary_data_source: collection://<id>
  - sections:
    - Section 1: Getting Started → <page id>
```

Leave out sections that don't apply (no `## Local` for Notion-only users, and so on). Then tell the user in one or two lines what was set up and that they can change it any time.
