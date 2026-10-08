# Creating the Learning Calendar

Read this when neither `~/.claude/course-notes/config.md` nor `~/.claude/learning-calendar/config.md` has a `calendar_data_source`. Run it after the user has approved their first list, so they see their topics before answering setup questions.

## 1. Pick the home page

Ask which Notion page the calendar should sit at the top of (e.g. "Learning"). If the course-notes config has a `home_page_id`, suggest that page. Search Notion for the page; if there are several matches, ask which one; if it doesn't exist, offer to create it as a private page.

## 2. Create the database

1. `create-database` with parent = the home page, title `Learning Calendar`, schema:
   ```
   CREATE TABLE ("Topic" TITLE, "Date" DATE)
   ```
2. Make it inline: `update-data-source` with `is_inline: true`.
3. Add a calendar view: `create-view` with `database_id`, type `calendar`, name `Calendar`, configure `CALENDAR BY "Date"; SHOW "Topic"`.
4. Fetch the database, then rename its default table view to `All topics` with configure `SORT BY "Date" DESC` (`update-view`).

## 3. Move it to the top of the page

New databases land at the end of the page. Fetch the home page, then `replace_content` with this block first, followed by the page's existing content. Keep every `<page>` and `<database>` tag exactly as fetched, since dropping one deletes it.

```
## 📅 What I'm Learning {color="purple"}
Each day's topics. Click one for a quick summary and links to that day's notes.
<database ...the calendar's tag exactly as fetched...>Learning Calendar</database>
---
```

## 4. Save the settings

- **If `~/.claude/course-notes/config.md` exists**, add these lines to its `## Notion` section so both skills share the calendar:
  ```
  calendar_database_id: <database id>
  calendar_data_source: collection://<id>
  ```
- **Otherwise** create `~/.claude/learning-calendar/config.md`:
  ```markdown
  # learning-calendar settings
  Edit by hand or ask Claude to "change my learning-calendar settings".

  home_page_title: <title>
  home_page_id: <id>
  calendar_database_id: <id>
  calendar_data_source: collection://<id>
  ```

Tell the user the table tab shows first. To open on the calendar, they can drag the **Calendar** tab to the left in Notion (the tools can't reorder tabs).
