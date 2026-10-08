---
name: learning-calendar
description: Log what the user learned today to their Notion Learning Calendar as short 1–2 word topics with a one- or two-sentence summary each, linked to any notes from that day. Pulls topics from the questions they asked Claude today, the subjects covered in today's sessions, and any list they give, then shows a draft list to edit and approve before anything is pushed. Use whenever the user wants to log, record, track or add today's learning or topics to their calendar, e.g. "add what I learned today to my calendar", "log today's topics", "put CSS grid and flexbox on my learning calendar", or "what did I learn today?" when they keep a learning calendar.
---

# Learning Calendar

The user keeps a calendar in Notion of what they learn each day. Each entry is a 1–2 word topic; clicking it opens a short summary and links to that day's notes. This skill turns a day of questions, sessions and the user's own list into calendar entries, but **only after the user has approved the list**. The calendar is their record, so nothing goes on it they didn't sign off on.

## Step 0: Find the calendar

Calendar settings are shared with the course-notes skill, so both write to the same calendar.

1. Read `~/.claude/course-notes/config.md`. If it has `calendar_data_source`, use it, and note `home_page_id`, the "Known classes" cache, and any `## Topic groups`.
2. Otherwise read `~/.claude/learning-calendar/config.md` for the same keys.
3. If neither has a calendar, set one up: read `references/calendar-setup.md`. Do this after the list is approved (Step 3), so the user isn't held up before they've seen anything.

If the Notion tools aren't available, still build and approve the list, then give the user the approved list in chat and explain that Notion needs connecting (claude.ai → Settings → Connectors → Notion, or `claude mcp add --transport http notion https://mcp.notion.com/mcp`, then restart Claude).

## Step 1: Gather candidate topics

The date is today in the user's local time (`date +%F`) unless they name another day ("yesterday", "for Monday"). Use that date throughout.

Collect from every source that applies:

- **The user's own list.** Anything they typed after the command or in their message ("add React hooks, CSS grid"). Always include these. They're the one source that never gets filtered.
- **This conversation.** Questions the user asked and subjects you explained or worked through together.
- **Today's other Claude Code sessions.** Run `python3 scripts/todays_prompts.py <date>` (path relative to this skill's folder). It prints what the user typed in every Claude Code session that day, grouped by project. Claude.ai chats on the web or in the app aren't stored on this machine, so they can't be included; mention this if the user expects them.
- **Notes from that day.** If the course-notes skill published lecture notes that day, they're a topic source and the links for the calendar. Check that date's existing calendar entries (query `calendar_data_source` for rows whose `Date` is that date, then fetch each one), and look for lecture pages under the home page created that day (Notion search, or fetch the section pages in the config cache and check each lecture's last-edited time).

If the user says "just my list" or "only this", skip the other sources.

### What counts as a topic

A topic is a subject the user learned about or worked in, named in **1–2 words** (`Flexbox`, `Git Rebase`, `Design Aesthetics`), not a task description ("fixed the build").

- **Include** concepts they asked to have explained, subjects of lectures, and the subject areas of substantial work ("set up a Notion database with calendar views" → `Notion Databases`).
- **Skip** pure chores with nothing learned: "commit this", permission prompts, renaming files, retries.
- **Merge** closely related questions into one topic. Five questions about CSS layout are one or two entries, not five.
- **Lean inclusive.** The user prunes the list next, and dropping an item is easier than remembering one you left out.

### Topic groups

The user can ask for related topics to share one calendar entry (e.g. everything about building, connecting and sharing Claude skills goes under `Claude Skills`). A group is **one umbrella topic** on the calendar, and its pieces are **subtopics** kept inside that entry as sub-pages, each with its own short summary. This keeps a busy day's calendar readable.

- Groups are saved in the config's `## Topic groups` section, one line each: `- <Umbrella topic>: <what belongs in it>`. Check every candidate against them, and put any that fit under that umbrella rather than listing them as separate topics.
- If several of the day's candidates clearly share a broader subject with no saved group, you may suggest grouping them in the draft. Only save a new group when the user asks for one (e.g. "group all X together"). Add the line to the same config file the calendar settings came from, so the grouping is remembered next time.
- The umbrella's summary covers the whole group in one sentence. Each subtopic gets a 1–2 word name and a bullet list of the high-level points covered, each with a one- or two-sentence description as a sub-bullet. Draw them from what was actually discussed.
- **One level deep only:** calendar entry → subtopic pages, and nothing below that. More detail goes into a subtopic's bullets, never into a deeper page.

For each topic, write a summary of **one or two sentences**, drawn from what was actually discussed or taught, not general knowledge. For a topic from the user's list with nothing else to go on, write a plain one-sentence description and mark it *(from your list; edit if you like)* in the draft.

## Step 2: Show the draft and get approval

Show the list in chat as a numbered table. Nothing is pushed yet, and say so.

```markdown
**Learning Calendar draft for 2026-10-08** (not on the calendar yet)

| # | Topic | Summary | Links | From |
|---|---|---|---|---|
| 1 | Design Aesthetics | One or two sentences. | 3 lecture notes | notes · already on calendar |
| 2 | CSS Grid | One or two sentences. | none | your list |
| 3 | Git Rebase | One or two sentences. | none | asked in UI-practice |
| 4 | Claude Skills | One sentence on the whole group. **Subtopics:** Skill Basics · Sharing Skills (details below) | none | group · asked · covered here |

**4. Claude Skills: subtopics**
- **Skill Basics**
  - **SKILL.md**: one or two sentences.
  - **Reference files**: one or two sentences.
- **Sharing Skills**
  - **Plugin marketplace**: one or two sentences.

Edit anything: e.g. "drop 3", "rename 2 to Grid Layout", "add Flexbox", "merge 2 and 3", "change 1's summary to …", or "add a link to my Figma notes".
Say **approve** to push these to the calendar.
```

- **From** says where the topic came from (your list / asked / covered here / notes / another session's project), so the user can judge it.
- For groups, list each subtopic's points under the table (as in the example), since they don't fit in a table cell. The user can edit those too.
- Flag topics that are **already on the calendar** for that day. On push, they only get new links or summary changes, never a duplicate entry.
- Apply each round of edits, then show the **whole updated table** again. Repeat until the user approves.
- Only an explicit approval of the latest table counts ("approve", "looks good, push it", "yes"). A reply that includes edits is not approval, even if it says "fine": apply the edits and show the table again. Approval in an earlier run doesn't carry over.
- If the user approves only some items ("push 1 and 2"), push just those.

## Step 3: Push to the calendar

Read `references/calendar-entries.md` for the exact entry format, then for each approved topic:

- **Already on the calendar that day** (same or clearly same subject, including entries the user added by hand): add any new note links under "📝 Related notes", and update the summary only if the user changed it or it no longer covers everything linked.
- **New:** create the entry with the topic, date, icon, summary and links.
- **Group:** one calendar entry for the umbrella topic, with each subtopic as a sub-page inside it. If the umbrella entry already exists that day, add only the subtopics it doesn't have yet.

Never claim an entry was created if the call failed. Say which ones failed and why.

## Finish

Reply with the calendar link and one line per topic: created, updated, or skipped (with the reason).
