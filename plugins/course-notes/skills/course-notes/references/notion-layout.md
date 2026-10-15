# Notion layout for course notes

Read this when publishing notes to Notion (Step 7 of SKILL.md). It describes the page structure and the exact layouts to reproduce, so every lecture looks the same as the ones before it.

Notion uses its own "enhanced Markdown". Before writing page content, read `notion://docs/enhanced-markdown-spec` once per session with the Notion fetch tool (the Notion tools require this). Rules that matter here: indent children with tabs; escape `\ * ~ ` $ [ ] < > { } | ^` in plain text (not inside code spans or code blocks); table cells hold rich text only.

## Hierarchy

```
<Home page>                     from config: home_page_id
├── Learning Calendar           inline database at the top of the page, one entry per class per day
└── <Class page>                page, one per class, icon = an emoji fitting the subject
    ├── <Section page>          page, one per course section
    │   └── <Lecture page>      page, one per lecture
    └── Glossary                inline database, one per class
```

Look up classes in the config's "Known classes" cache first. If a class isn't there, fetch the home page and check its child `<page>` tags (the user may have created or renamed pages by hand). Add anything you create or find to the cache.

## Creating pages (full width)

Class, section, and lecture pages should open in full width. The Notion tools can't set that directly, but a duplicated page keeps it. So when the config has a `full_width_template_id`, make every new class, section, and lecture page from that template:

1. `duplicate-page` with the template's ID. The copy lands next to the template, on the home page. Make one copy at a time: wait until a copy loads before starting the next, because simultaneous duplicates can leave one stuck as a blank, unmovable block.
2. The duplicate finishes in the background: fetch the returned ID until it loads (a few tries).
3. `move-pages` the copy to its real parent (home page for a class, class page for a section, section page for a lecture).
4. `update-page` with `update_properties` to set the title, plus `icon` for the page's emoji.
5. `update-page` with `replace_content` to swap the template's text for the page's layout below.

If there's no `full_width_template_id`, or the template is gone or a step fails, create the page with `create-pages` as usual, and at the end tell the user which new pages to set to full width by hand (••• → Full width). If the move or rename fails after the copy exists, tell the user where the stray copy is so they can delete it (the Notion tools can't delete pages).

Database rows (glossary terms, calendar entries) are created directly; this applies only to the three page types.

## Placing new pages

New child pages are appended to the **end** of their parent. That's fine on the home page and on section pages (their children are the last thing on the page). On a **class page**, though, the end is below the Glossary, so a new section would land in the wrong place. After creating a section page:

1. Fetch the class page.
2. Use `update-page` with `replace_content`, sending the same content with the new section's `<page>` tag moved to the end of the list under "📚 Sections" (keep numeric section order). Keep every other `<page>` and `<database>` tag exactly as fetched; dropping one would delete it.

## Class page (only when the class is new)

Create under the home page (see "Creating pages"), icon = an emoji that fits the subject:

```
<callout icon="🎓" color="purple_bg">
	**<Platform> course** · Notes generated from lecture transcripts with the course-notes skill. Each section below holds its lecture notes; every term lands in the glossary at the bottom.
</callout>
## 📚 Sections {color="purple"}
```

Then append the glossary heading with `insert_content` at the end:

```
---
## 📖 Glossary {color="purple"}
Every vocabulary term from this class. Search, sort, or filter by section.
```

Then create the database with parent = the class page, title `Glossary`:

```
CREATE TABLE ("Term" TITLE, "Definition" RICH_TEXT, "Section" SELECT('<section name>':purple), "Lecture" SELECT('<short lecture name>':purple))
```

Finally fetch the class page and change that database tag's `inline="false"` to `inline="true"` with `update_content`, so the table shows on the page itself.

## Section page (only when the section is new)

Create it as described in "Creating pages". Title: `Section N: <Name>` when the number is known, otherwise just `<Name>`. Pick a fitting emoji icon. Content:

```
<callout icon="🧭" color="gray_bg">
	<One sentence on what this section covers.>
</callout>
## Lectures {color="purple"}
```

## Lecture page

Create it as described in "Creating pages". Title = lecture title (prefix the lecture number if known, e.g. `12. Auto Layout Basics`). Pick a fitting emoji icon. Convert the Markdown notes to this layout, keeping the same section order and omitting any section the notes don't have:

```
<callout icon="<class emoji>" color="gray_bg">
	**Class:** <class name> · **Section N:** <section name>
</callout>
## ✅ Key Takeaways {color="purple"}
<callout icon="⭐" color="green_bg">
	- takeaway
	- takeaway
</callout>
## 🔗 Resources Mentioned {color="purple"}
- bullets
---
## 🔤 Vocabulary {color="purple"}
<table fit-page-width="true" header-row="true">
	<colgroup>
		<col color="purple_bg" width="220">
		<col width="888">
	</colgroup>
	<tr>
		<td>Term</td>
		<td>Definition</td>
	</tr>
	<tr>
		<td>**Term**</td>
		<td>Definition</td>
	</tr>
</table>
---
## 🧠 Main Concepts {color="purple"}
### <Concept>
<text and bullets>
---
## 🛠️ How-to Steps {color="purple"}
### <Task> {toggle="true"}
	1. Step
	2. Step
## ⌨️ Shortcuts & Settings {color="purple"}
<table fit-page-width="true" header-row="true"> … Action | How, columns gray_bg width="220" and width="888"; shortcuts in `code` …</table>
(code blocks for code/commands go here too)
---
## 📌 Tips & Gotchas {color="purple"}
<callout icon="⚠️" color="orange_bg">
	Warning text
</callout>
<callout icon="💡" color="blue_bg">
	Tip text
</callout>
---
## ❓ Review Questions {color="purple"}
<details>
<summary>1. Question?</summary>
	Answer.
</details>
<callout icon="⏭️" color="purple_bg">
	**Next up:** <teaser>
</callout>
*Note: <any faithfulness note>* {color="gray"}
```

Use one callout per tip, not one callout holding all of them; separate cards are easier to read.

Always give both table columns explicit widths as shown. Without them Notion auto-sizes the columns narrow and the table doesn't span the page, even with `fit-page-width="true"`.

## Glossary rows

Add one row per vocabulary term to the class's Glossary data source (`create-pages` with parent `data_source_id`):

- **Term**, **Definition** (short, plain text; keep the *(not defined in this lecture)* marker as plain parentheses), **Section**, **Lecture**.
- Skip terms already in the glossary: query the data source for the lecture's terms (case-insensitive) before creating rows, every time. The Notion tools can't delete rows, so a duplicate has to be removed by hand.
- **Select options can't contain commas.** Use a short lecture name without commas for the Lecture tag (e.g. `Fills / Gradients / Strokes`).
- If row creation rejects a new section or lecture value, add the option to the data source schema with `update-data-source` first.

## Learning Calendar

A calendar at the top of the home page showing what the user learned each day. To keep busy days readable, each class gets **one entry per day**, named with the class's short name, and each lecture topic is a **subtopic** sub-page inside it. Clicking the entry opens a one-sentence summary of the day's lectures and the subtopics. Update it after every lecture published to Notion. (The learning-calendar skill groups the user's other topics the same way: Claude & AI, and computing concepts such as App Hosting or GitHub.)

### Adding today's lecture

1. Get today's date in the user's local time (`date +%F`).
2. Find today's entries in the history file (see "Calendar history file" below), not with a Notion query: the free plan limits queries. Fetch an entry only when you're about to edit it.
3. **Find or create today's class entry.** If today already has an entry for this class (its short name, or a by-hand entry clearly about the class), use it. Otherwise create one (`create-pages` with parent `data_source_id`):
   - **Topic**: the class's short name, up to 3 words (e.g. `Product Design` for "Mastering Digital Product Design: UX Research & UI Design"). Use the same short name every day; save it as `calendar_name:` under the class in the config's "Known classes" cache the first time.
   - **Date**: today (`date:Date:start`, `date:Date:is_datetime` = 0).
   - **category** (if the calendar has it): `["class", "<subject tag>"]`, where the subject tag is the existing option that fits the class (`design` for Product Design). The tag list is under "Tags and note" in the learning-calendar skill's `references/calendar-entries.md`.
   - **note** (if the calendar has it): 1–5 lowercase words naming today's lecture subjects, comma-separated (e.g. `aesthetics, balance`).
   - Icon: an emoji fitting the class.
   - Content:
     ```
     <callout icon="💬" color="purple_bg">
     	<One sentence on what today's lectures covered.>
     </callout>
     ## 🔹 Subtopics {color="purple"}
     ```
4. **Add the lecture as a subtopic.** If the entry already has a subtopic covering this lecture's topic (a second lecture on the same subject usually fits), append its new points to that sub-page with `insert_content` and add the lecture link under its "📝 Related notes". Otherwise create a sub-page of the class entry (`create-pages` with parent `{"type": "page_id", "page_id": "<class entry id>"}`):
   - **title**: 1–2 words naming the subject (e.g. `Design Aesthetics`, `Figma Fills`), not the lecture title.
   - Content: bullets of the points covered, each with a one- or two-sentence sub-bullet, then `## 📝 Related notes {color="purple"}` and `- <mention-page url="<lecture page url>"/>`. Only one level deep, so never a page inside a subtopic (format: the learning-calendar skill's `references/calendar-entries.md`, "Group entry").
5. Update the class entry's one-sentence summary if it no longer covers all of today's lectures. If the entry's `category` or `note` is blank, fill it as in step 3. Never overwrite values the user typed. If a new lecture's subject isn't in a note you wrote earlier today, add it (keep it under 5 words); leave the user's own note as it is.
6. Keep summaries faithful to the lectures (Step 5 of SKILL.md) and no longer than two sentences, even after adding more notes to an entry.
7. Record the class entry in the calendar history file, with the lecture under `notes:` and the subtopic under `subtopics:`.

### Calendar history file

`~/.claude/course-notes/learning-calendar-history.md` lists every calendar entry from the last 10 days, so neither this skill nor learning-calendar has to query Notion to see what's already there. It's shared with the learning-calendar skill, which uses the same format.

```markdown
# Learning Calendar history
Entries on the Notion Learning Calendar for the last 10 days, kept by the course-notes and learning-calendar skills so they don't have to query Notion. Safe to edit by hand.

covers_from: 2026-10-12

2026-10-13 | Minimalism | 3f8bd4600b7981d4b87ef3a513288cce | notes: 3f8bd4600b798196b40ce173a08b9fa0, 3f8bd4600b79814ebe8cd98edf844fe7
2026-10-12 | Claude Skills | 3f8bd4600b7981acbdc0d6cde93f2f98 | subtopics: Brand Palette Skill
```

- One line per entry, newest day first: date, topic, entry page ID, then `notes:` (linked note page IDs) and `subtopics:` (a group's sub-page names), each left off when empty. `covers_from` is the earliest day the log is complete for.
- **Reading:** for today (or any day on or after `covers_from`) the log is the full list, so don't query. If the log is missing or doesn't cover the day, query `calendar_data_source` once for every entry from 9 days ago to today, write them all to the log, and set `covers_from` to 9 days ago. If that query is refused (usage limit), search the calendar data source instead and leave `covers_from` unchanged.
- **Writing:** after each successful create or update, add or update the entry's line; never log a failed call. Then remove lines older than 10 days and move `covers_from` up to 9 days ago if it's older.
- Entries the user adds by hand in Notion aren't in the log. If they mention one, search for it and add it.

### Creating the calendar (only when the config has no `calendar_data_source`)

1. Create the database with parent = the home page, title `Learning Calendar`:
   ```
   CREATE TABLE ("Topic" TITLE, "Date" DATE, "category" MULTI_SELECT('git':orange, 'AI':red, 'database':brown, 'claude':green, 'web-dev':default, 'ui':purple, 'ux':yellow, 'design':blue, 'automation':pink, 'communication':default, 'project':gray, 'class':pink), "note" RICH_TEXT)
   ```
2. Set it inline (`update-data-source` with `is_inline: true`).
3. Add a calendar view: `create-view` with `database_id`, type `calendar`, name `Calendar`, configure `CALENDAR BY "Date"; SHOW "Topic"`. Rename the default table view to `All topics` with `SORT BY "Date" DESC`.
4. The database lands at the end of the home page. Fetch the page and `replace_content` with this block first, followed by the existing content, keeping every `<page>` and `<database>` tag exactly as fetched:
   ```
   ## 📅 What I'm Learning {color="purple"}
   Each day's topics. Click one for a quick summary and links to that day's notes.
   <database ...the calendar's tag as fetched...>Learning Calendar</database>
   ---
   ```
5. Save `calendar_database_id` and `calendar_data_source` to the config's `## Notion` section, and create the calendar history file with `covers_from: <today>`.
6. Tell the user the table tab shows first; to open on the calendar, drag the **Calendar** tab to the left in Notion (the tools can't reorder tabs).

## Replacing a lecture

If the user chose to replace existing notes (Step 6 of SKILL.md), replace the lecture page's content with `replace_content` instead of creating a new page, and update its glossary rows rather than adding duplicates. Its calendar link already points to the same page, so leave the calendar alone.
