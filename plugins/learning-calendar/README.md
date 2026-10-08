# Learning Calendar

A Claude skill that keeps a calendar in Notion of what you learn each day. Each day shows short 1–2 word topics. Click one to see a one- or two-sentence summary and links to that day's notes.

Ask Claude to "add what I learned today to my calendar", optionally with your own list ("…plus CSS grid and flexbox"), and it:

- **Gathers topics** from the questions you asked Claude today, the subjects you worked on in today's Claude Code sessions, any notes published that day, and your list.
- **Shows you a draft table first**, with each topic's summary, links and source. Edit it as much as you like: drop, rename, merge, add, or rewrite summaries.
- **Pushes only after you approve.** Topics already on the calendar for that day get new links, not duplicates.

It shares its calendar with the [course-notes](../course-notes) skill, which adds a topic automatically whenever it publishes lecture notes.

Your Claude Code prompts are read locally from `~/.claude/projects`. Chats on claude.ai aren't stored on your computer, so they aren't included.

## Setup

### 1. Install the skill

In Claude Code, run:
```
/plugin marketplace add ItsAlwaysRaining/claude-skills
/plugin install learning-calendar@claude-skills
```

Or copy it manually:
```bash
git clone https://github.com/ItsAlwaysRaining/claude-skills.git
mkdir -p ~/.claude/skills
cp -r claude-skills/plugins/learning-calendar/skills/learning-calendar ~/.claude/skills/
```

### 2. Connect Notion

- **Claude.ai connector:** claude.ai → Settings → Connectors → Notion → Connect.
- **Claude Code:** `claude mcp add --transport http notion https://mcp.notion.com/mcp`, then run `/mcp`, choose **notion** → **Authenticate**.

Restart Claude afterwards.

### 3. First run

If you already use course-notes with a calendar, it just works. Otherwise, after you approve your first list, Claude asks which Notion page should hold the calendar, creates it at the top of that page, and saves the settings to `~/.claude/learning-calendar/config.md`.
