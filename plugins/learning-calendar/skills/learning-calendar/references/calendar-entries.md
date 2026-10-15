# Calendar entry format

Read this before pushing approved topics (Step 3 of SKILL.md). Every entry should look the same, whether this skill or course-notes created it.

Notion uses its own "enhanced Markdown". Before writing page content, read `notion://docs/enhanced-markdown-spec` once per session with the Notion fetch tool. Indent children with tabs, and escape `\ * ~ ` $ [ ] < > { } | ^` in plain text.

## Schema

The calendar database has two properties:

- **Topic** (title): the umbrella entry's name, i.e. the class, computing concept or subject (up to 3 words), or a 1–2 word topic for a lone entry.
- **Date** (date): the day learned, no time.

## New entry

`create-pages` with parent `{"type": "data_source_id", "data_source_id": "<calendar_data_source without collection://>"}`:

- properties: `"Topic": "<topic>"`, `"date:Date:start": "<YYYY-MM-DD>"`, `"date:Date:is_datetime": 0`
- icon: an emoji that fits the topic
- content:

```
<callout icon="💬" color="purple_bg">
	<One or two sentences: the approved summary.>
</callout>
## 📝 Related notes {color="purple"}
- <mention-page url="<note page url>"/>
```

With no notes to link, leave out the "Related notes" heading and list entirely. Several approved topics can go in one `create-pages` call.

## Group entry (umbrella topic with subtopics)

This is the usual shape: class, Claude & AI, concept and subject entries are all group entries. Only a lone "other" topic uses the plain entry above.

1. Create the umbrella entry in the calendar as above. Its callout holds one sentence covering the whole group, then add any "📝 Related notes", then end the page with this heading:
   ```
   ## 🔹 Subtopics {color="purple"}
   ```
2. Create each subtopic as a sub-page of the umbrella entry (`create-pages` with parent `{"type": "page_id", "page_id": "<umbrella entry id>"}`), so it doesn't appear on the calendar on its own:
   - properties: `"title": "<subtopic>"` (1–2 words). Sub-pages aren't calendar rows, so they have no Topic or Date.
   - icon: an emoji that fits the subtopic
   - content: a bullet list of the high-level points covered, each with a sub-bullet description of one or two sentences. No callout or extra headings. Add a "📝 Related notes" list at the end only if it has notes.
     ```
     - **<Point covered>**
     	- <One or two sentences describing it.>
     - **<Point covered>**
     	- <One or two sentences describing it.>
     ```

**Only one level deep.** The calendar entry is the top level and its subtopic pages are the only level below it. Never create a page inside a subtopic page. More detail on a subtopic means more bullets on that page, or another subtopic page next to it. (Links to lecture notes are fine; they're mentions, not sub-pages.)

New sub-pages land at the end of the umbrella page, which is why "Subtopics" is the last section. To add a subtopic to an existing umbrella entry, just create another sub-page. To add to a subtopic that already exists, append bullets to its page with `insert_content` and skip points already there. If the umbrella page has no "Subtopics" heading yet, append it first with `insert_content`.

**Converting existing entries into a group** (the user groups entries already on the calendar): use `move-pages` to move those entries under the umbrella entry, with new parent = `{"type": "page_id", "page_id": "<umbrella entry id>"}`. They leave the calendar. Never delete entries. Then rewrite each moved page into the subtopic bullet format above, and flatten anything nested inside it (move its pages up to the umbrella or turn them into bullets). If the umbrella was itself one of the topics, turn its old content into a subtopic page too, so every subtopic looks the same.

## History file (use instead of querying Notion)

Notion's free plan limits how often a database can be queried, so both skills keep a plain-text log of recent calendar entries and read it instead of querying the calendar.

**Where:** `learning-calendar-history.md`, in the same folder as the config the calendar settings came from (`~/.claude/course-notes/` or `~/.claude/learning-calendar/`).

**Format:**

```markdown
# Learning Calendar history
Entries on the Notion Learning Calendar for the last 10 days, kept by the course-notes and learning-calendar skills so they don't have to query Notion. Safe to edit by hand.

covers_from: 2026-10-12

2026-10-13 | Minimalism | 3f8bd4600b7981d4b87ef3a513288cce | notes: 3f8bd4600b798196b40ce173a08b9fa0, 3f8bd4600b79814ebe8cd98edf844fe7
2026-10-12 | Claude Skills | 3f8bd4600b7981acbdc0d6cde93f2f98 | subtopics: Brand Palette Skill
2026-10-12 | Color Contrast | 3f8bd4600b798150b8d1c23425517313
```

- One line per calendar entry, newest day first: date, topic, the entry's page ID, then `notes:` (IDs of linked note pages) and `subtopics:` (names of a group's sub-pages), each left off when empty.
- `covers_from` is the earliest day the log is complete for. Days before it may have entries the log doesn't know about.

**Reading.** To find a day's entries, read the log:

- **Day on or after `covers_from`:** the log is the full list, so don't query. Fetch an entry's page only when you're about to edit it (fetching doesn't count against the query limit).
- **Day before `covers_from`, or no log yet:** query `calendar_data_source` once for every entry from 9 days ago to today, write them all to the log, and set `covers_from` to 9 days ago. If the query is refused (usage limit), search the calendar data source instead, tell the user the list may be incomplete, and leave `covers_from` unchanged.
- **Entries added by hand in Notion** aren't in the log. If the user mentions one, or a draft topic might already be on the calendar, search for it and add what you find to the log.

**Writing.** After each successful create or update, add the entry's line or update it (new note IDs, new subtopics, renamed topic). Never log a call that failed. Then remove lines older than 10 days, and if `covers_from` is more than 9 days ago, move it up to 9 days ago.

## Updating an existing entry

Fetch the entry first, then use `update-page` with `update_content`:

- **Add a link:** append `- <mention-page url="…"/>` after the last item under "📝 Related notes". If the entry has no such heading yet, add the heading and list after the callout.
- **Change the summary:** replace the text inside the callout. Keep it to two sentences.
- **Rename:** `update_properties` with the new `Topic`.

Don't add a link that's already there.
