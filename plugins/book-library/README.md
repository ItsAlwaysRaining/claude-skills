# Book Library

A Claude skill that keeps your reading in a Notion database: your Library, with shelves for **TBR**, **Currently Reading** and **Read & Reviewed**.

Say "add Atomic Habits to my TBR", "I just started Project Hail Mary" or "I finished Managing Up, 4 stars", and Claude:

- **Creates the book page** with author, genre and a short summary filled in, after checking the book isn't already there.
- **Adds a "Why I Picked This Book" section** with a few prompts to fill in (who recommended it, what you hope to get from it, why now). If you mention your reason, it's filled in for you.
- **Adds a "My Notes" section** containing a notes sub-page for highlights and quotes while you read.
- **Moves books between shelves**, setting the Started and Finished dates, and adds a **My Review** section when you finish. Why and Notes stay above the review, so you can compare what you expected with what you got.
- **Backfills older books** on request, adding the sections without touching anything you've already written.

Every book page ends up like this:

```
📖 Summary
🎯 Why I Picked This Book
📝 My Notes        → "<Title> — Notes" sub-page
✍️ My Review       (added once the book is Read)
```

## Setup

### 1. Install the skill

In Claude Code, run:
```
/plugin marketplace add ItsAlwaysRaining/claude-skills
/plugin install book-library@claude-skills
```

Or copy it manually:
```bash
git clone https://github.com/ItsAlwaysRaining/claude-skills.git
mkdir -p ~/.claude/skills
cp -r claude-skills/plugins/book-library/skills/book-library ~/.claude/skills/
```

### 2. Connect Notion

- **Claude.ai connector:** claude.ai → Settings → Connectors → Notion → Connect.
- **Claude Code:** `claude mcp add --transport http notion https://mcp.notion.com/mcp`, then run `/mcp`, choose **notion** → **Authenticate**.

Restart Claude afterwards.

### 3. First run

The first time you add a book, Claude looks for your book database in Notion (titles like "Library", "Bookshelf" or "Books"), confirms it with you, and works out how its properties line up (e.g. your `Shelf` property for Status). If you don't have one yet, it offers to create a Library database on a page you choose. The settings are saved to `~/.claude/book-library/config.md`.
