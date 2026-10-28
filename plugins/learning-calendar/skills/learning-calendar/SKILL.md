---
name: learning-calendar
description: Log what the user learned today, or on any of the past 7 days, to their Notion Learning Calendar, grouped into a few entries a day (one per class, one for Claude & AI, and one per computing concept such as App Hosting, Databases or GitHub) with each topic as a short subtopic inside, tagged by category with a short note, and linked to any notes from that day. Pulls topics from the questions they asked Claude today, the subjects covered in today's sessions, and any list they give, then shows a draft list to edit and approve before anything is pushed. Use whenever the user wants to log, record, track or add today's learning or topics to their calendar, e.g. "add what I learned today to my calendar", "log today's topics", "put CSS grid and flexbox on my learning calendar", "log what I learned on Monday", or "what did I learn today?" when they keep a learning calendar.
---

# Learning Calendar

The user keeps a calendar in Notion of what they learn each day. Each day has a few entries, one per class, one for Claude & AI, and one per computing concept or broad subject; clicking one opens a short summary, links to that day's notes, and the day's topics as subtopic pages inside it. This skill turns a day of questions, sessions and the user's own list into calendar entries, but **only after the user has approved the list**. The calendar is their record, so nothing goes on it they didn't sign off on.

## Step 0: Find the calendar

Calendar settings are shared with the course-notes skill, so both write to the same calendar.

1. Read `~/.claude/course-notes/config.md`. If it has `calendar_data_source`, use it, and note `home_page_id`, the "Known classes" cache, any `## Topic groups`, and any `## Area icons`.
2. Otherwise read `~/.claude/learning-calendar/config.md` for the same keys.
3. If neither has a calendar, set one up: read `references/calendar-setup.md`. Do this after the list is approved (Step 3), so the user isn't held up before they've seen anything.
4. Read `learning-calendar-history.md` in the same folder as that config. It lists the calendar's entries for the last 10 days, so you can check what's already there without querying Notion (the free plan limits queries). The format and rules are in `references/calendar-entries.md` under "History file".

If the Notion tools aren't available, still build and approve the list, then give the user the approved list in chat and explain that Notion needs connecting (claude.ai → Settings → Connectors → Notion, or `claude mcp add --transport http notion https://mcp.notion.com/mcp`, then restart Claude).

## Step 1: Gather candidate topics

### Pick the day

The user can log any day from today back to 7 days ago. Get today's date in their local time (`date +%F`) first.

- **They named a day** ("yesterday", "for Monday", "Oct 3"): use it, as long as it's within the last 7 days.
- **They didn't:** ask which day before gathering anything. Use the AskUserQuestion tool if it's available, with options **Today (<date>)**, **Yesterday (<date>)** and **Earlier this week**, where the user can also type a date. If they pick "Earlier this week", ask which day and list the remaining dates with their weekdays (e.g. "Mon Oct 5"). Without the tool, ask the same thing in one short chat message.
- **More than 7 days ago, or in the future:** say the calendar can only be filled for the past 7 days, and ask for another day.

Use that date for every step below, and put it in the draft's heading so the user can see which day they're approving.

For a past day, this conversation only counts if it happened that day. The session script and that day's notes are the main sources.

Collect from every source that applies:

- **The user's own list.** Anything they typed after the command or in their message ("add React hooks, CSS grid"). Always include these. They're the one source that never gets filtered.
- **This conversation.** Questions the user asked and subjects you explained or worked through together.
- **Today's other Claude Code sessions.** Run `python3 scripts/todays_prompts.py <date>` (path relative to this skill's folder). It prints what the user typed in every Claude Code session that day, grouped by project. Claude.ai chats on the web or in the app aren't stored on this machine, so they can't be included; mention this if the user expects them.
- **Notes from that day.** If the course-notes skill published lecture notes that day, they're a topic source and the links for the calendar. Check that date's existing calendar entries in the history file (not with a Notion query, unless the log says it doesn't cover that day), and look for lecture pages under the home page created that day (Notion search, or fetch the section pages in the config cache and check each lecture's last-edited time).

If the user says "just my list" or "only this", skip the other sources.

### What counts as a topic

A topic is a subject the user learned about or worked in, named in **1–2 words** (`Flexbox`, `Git Rebase`, `Design Aesthetics`), not a task description ("fixed the build").

- **Include** concepts they asked to have explained, subjects of lectures, and the subject areas of substantial work ("set up a Notion database with calendar views" → `Notion Databases`).
- **Skip** pure chores with nothing learned: "commit this", permission prompts, renaming files, retries.
- **Merge** closely related questions into one topic. Five questions about CSS layout are one or two entries, not five.
- **Lean inclusive.** The user prunes the list next, and dropping an item is easier than remembering one you left out.

### Group topics into umbrella entries

The user doesn't want a calendar day with 20 entries. **Grouping is the default:** sort every candidate topic into an **umbrella entry**, and keep the topics themselves as **subtopics** inside it (sub-pages of the entry, not calendar rows). A typical day should end up with a handful of entries, not one per topic.

Put each topic in the **first** bucket that fits:

1. **A class.** The topic came from a course: a lecture, its notes, or questions about the lecture material. One entry per class, named with the class's short name (e.g. `Product Design` for "Mastering Digital Product Design: UX Research & UI Design"). Its subtopics are that day's lecture topics, and the lecture notes are linked from them. Classes are listed in the config's "Known classes" cache; use a class's `calendar_name` if it has one, and otherwise pick a short name and save it there as `calendar_name:` after approval, so course-notes uses the same entry.
2. **Claude & AI.** The topic is about Claude, Claude Code or AI tools in general, wherever it was asked: skills and plugins, artifacts, hooks, permissions, Monitor, MCP connectors, prompting, models. One entry per day, named `Claude & AI`. A question about Claude asked inside a repo session still goes here, because it's about the tool, not the project.
3. **A computing concept.** Everything learned while working in a repo or project is grouped by **what it's about, not which project it came from**: `App Hosting`, `Databases`, `GitHub`, `Frontend`, `Spec-Driven Design`, `APIs`, `Security`. One entry per concept per day, with the topics as subtopics (e.g. `GitHub Secrets` and `Issue Writing` under `GitHub`). Mention the project in a subtopic's points where it helps ("in the Spotify music app"), but never make a project its own entry.
4. **Everything else.** Non-computing topics with no class or AI link. If two or more share a broad subject (`Design`, `Writing`), group them under that subject. A single unrelated topic can be its own entry.

**Concept and subject names.** Reuse the names already on the calendar (check the history file) so the same concept is named the same way every day: `Databases` every time, not `Database` one day and `DB Design` the next. Pick a new name only for a concept that isn't there yet.

**Saved topic groups.** The config's `## Topic groups` section, one line each: `- <Umbrella topic>: <what belongs in it>`, holds groupings the user asked for. They take precedence over the buckets above. A saved group that falls inside a bucket (for example `Claude Skills`, which is about Claude) becomes a **subtopic** of that bucket's entry, collecting all its points, so the calendar doesn't get a second entry for it. Only save a new group when the user asks for one ("group all X together").

**Area icons.** The config's `## Area icons` section, one line each: `- <Umbrella name>: <emoji>`, gives every umbrella entry a fixed icon, so an area looks the same on the calendar every day (`- GitHub: 🌿`). Use the listed emoji for a listed umbrella. For an umbrella not on the list, pick a fitting emoji that no other line uses, show it in the draft next to the entry's name, and after the push append its line to the section (create the section if the config has none). Subtopic pages aren't on the calendar, so they keep a free choice of emoji.

**Writing them up:**

- **Umbrella names** are the class, concept or subject name (up to 3 words). **Subtopic names** are 1–2 words.
- **The calendar is public**, and people who might hire the user may read it. Write everything in the voice set out under "Voice" in `references/calendar-entries.md`: show the skills being built, keep a professional lean, and let the user's curiosity come through. Read that section and "Tags and note" before writing the draft.
- The umbrella's summary is one sentence covering the whole entry for that day. It says what skill was built and how it was applied, e.g. "Built a reusable component library in Figma and used it to rebuild one dashboard at three screen sizes."
- Each entry gets 1–3 **category** tags (e.g. `git`, `claude, AI`, `class, design`, `project, web-dev`) and a **note** of 1–5 words naming the skills it shows (`interactive data visualization`, `CI/CD with GitHub Actions`), with no project prefix.
- Each subtopic gets a bullet list of the **skills or concepts** learned. Each bullet's bold label names the skill, and its sub-bullet gives one or two sentences on what it is and how it was applied. Write about the lesson, not a log of the edits made. Draw them from what was actually discussed or taught, not general knowledge. For a topic from the user's list with nothing else to go on, write one plain point and mark it *(from your list; edit if you like)* in the draft.
- **One level deep only:** calendar entry → subtopic pages, and nothing below that. More detail goes into a subtopic's bullets, never into a deeper page.
- Merge closely related subtopics within an entry rather than listing near-duplicates.

**Entries already on the calendar that day.** If an umbrella entry already exists that day, new subtopics go into it. If standalone entries exist that now belong under an umbrella (for example from before this grouping rule), suggest in the draft moving them inside it, and do it only if the user approves (see "Converting existing entries into a group" in `references/calendar-entries.md`).

## Step 2: Show the draft and get approval

Show the calendar entries in chat as a numbered table, one row per umbrella entry, with its subtopics numbered under it (`2a`, `2b`) so the user can edit each one. Nothing is pushed yet, and say so.

```markdown
**Learning Calendar draft for 2026-10-08** (not on the calendar yet): 4 entries

| # | Entry | Kind | Tags | Note | Summary | Subtopics | Links |
|---|---|---|---|---|---|---|---|
| 1 | Product Design | class | class, design | visual balance, composition | One sentence on the skills from the day's lectures. | 1a Aesthetics · 1b Balance | 3 lecture notes |
| 2 | GitHub | concept | git | secrets management, issue writing | One sentence on the skill built and how it was applied. | 2a GitHub Secrets · 2b Issue Writing | none |
| 3 | Claude & AI | Claude & AI | claude, AI | AI workflow automation | One sentence. | 3a Claude Skills · 3b Claude Monitor | none |
| 4 | CSS Grid | other | web-dev, design | CSS grid layout | One sentence. | (none) | none |

**1. Product Design** (from: notes · already on calendar)
- **1a Aesthetics**
  - **Skill or concept**: what it is and how it was applied, in one or two sentences.
- **1b Balance**
  - **Skill or concept**: what it is and how it was applied, in one or two sentences.

**2. GitHub** (from: asked in spotify-music-analysis)
- **2a GitHub Secrets**
  - **Skill or concept**: what it is and how it was applied, in one or two sentences.
…

Edit anything: e.g. "drop 2b", "move 3b to 2", "rename 2 to Git & GitHub", "add Flexbox to 4", "merge 1a and 1b", "change 1's summary to …", "tag 2 as automation", "note 3: AI workflow automation", or "add a link to my Figma notes".
Say **approve** to push these to the calendar.
```

- **Kind** is class, Claude & AI, concept, a saved group, or other. **From** (after each entry's heading) says where its topics came from (your list / asked / covered here / notes / another session's project), so the user can judge them.
- Flag entries and subtopics **already on the calendar** for that day. On push, they only get new subtopics, links or summary changes, never a duplicate entry.
- For an entry already on the calendar, fetch it and show its current tags and note. Propose values only for blank fields. A change to a field the user filled is shown as a suggestion ("add `automation`?"), and a tag that isn't an existing option is marked **new tag**.
- Apply each round of edits, then show the **whole updated table** again. Repeat until the user approves.
- Only an explicit approval of the latest table counts ("approve", "looks good, push it", "yes"). A reply that includes edits is not approval, even if it says "fine": apply the edits and show the table again. Approval in an earlier run doesn't carry over.
- If the user approves only some items ("push 1 and 2"), push just those.

## Step 3: Push to the calendar

Read `references/calendar-entries.md` for the exact entry format, then for each approved entry:

- **New umbrella entry:** create the calendar entry (name, date, category tags, note, icon, one-sentence summary, any links), then each subtopic as a sub-page inside it.
- **Umbrella entry already on the calendar that day** (same or clearly same class, concept or subject, including entries the user added by hand): add only the subtopics it doesn't have yet, append new points to subtopics it has, add any new note links, and fill its tags and note if they're blank (plus any approved suggestions).
- **Entry with no subtopics** (a lone "other" topic): create it with the tags, note, summary and links, as a plain entry.
- **Approved moves** of existing standalone entries under an umbrella: follow "Converting existing entries into a group" in `references/calendar-entries.md`. Never delete entries.
After each successful create or update, record it in the history file (see "History file" in `references/calendar-entries.md`).

Never claim an entry was created if the call failed. Say which ones failed and why.

## Finish

Reply with the calendar link and one line per entry: created, updated, or skipped (with the reason), listing the subtopics added to it.
