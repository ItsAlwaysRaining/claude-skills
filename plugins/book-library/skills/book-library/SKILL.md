---
name: book-library
description: Add books to the user's Notion book database (their Library or Bookshelf) and move them between shelves (TBR, Currently Reading, Read & Reviewed). Every book page gets the user's layout — Summary, "Why I Picked This Book" with guiding prompts, and a "My Notes" section holding a notes sub-page — and the My Review section is added when the book is finished. Fills in author, genre and a summary. Use whenever the user wants to add, log or save a book, put something on their TBR / to-read list, says they started or are reading a book, finished a book, want to review or rate a book, or DNF'd one, e.g. "add Atomic Habits to my TBR", "I just started Project Hail Mary", "I finished Managing Up, 4 stars", "put these three books on my bookshelf" — even if they don't say "Notion" or "Library".
---

# Book Library

The user keeps their reading in a Notion database (the **Library**), usually shown on a Bookshelf page as shelves such as Currently Reading, TBR and Read & Reviewed. This skill creates book pages there with a consistent layout and moves books between shelves. The layout is the point: the user records *why* they picked a book before reading it, keeps notes while reading, and has both still sitting there when they write the review, so they can compare what they expected with what they got.

## Step 0: Find the Library

1. Read `~/.claude/book-library/config.md`. It holds `data_source` (the Library's `collection://` URL) and, if the user's database uses different property or option names from the table below, a `## Property names` mapping.
2. If there's no config, or the data source no longer exists, read `references/setup.md` and follow it. It finds the user's book database (or creates one) and writes the config.
3. Fetch the data source once per run before writing, to confirm the property names and options haven't changed. If they have, use what the database actually has and update the config's mapping.

If the Notion tools aren't available, explain that Notion needs connecting (claude.ai → Settings → Connectors → Notion, or `claude mcp add --transport http notion https://mcp.notion.com/mcp`, then restart Claude) and stop. Don't pretend to have saved anything.

The skill expects these properties. With a mapping in the config, use the user's names instead. A property the user's database doesn't have is simply skipped.

| Property | Type | Values |
|---|---|---|
| Title | title | |
| Author | text | |
| Status | select | `TBR`, `Currently Reading`, `Read`, `DNF` |
| Genre | multi-select | `Fiction`, `Non-fiction`, `Fantasy`, `Sci-Fi`, `Memoir`, `Self-help` |
| Format | select | `Paperback`, `Hardcover`, `Kindle`, `Audiobook` |
| Started / Finished | date | `date:Started:start`, `date:Finished:start` (ISO date) |
| Rating | select | `★★★★★` … `★☆☆☆☆` |
| Review | text | one-line short review; the long review goes on the page |
| Cover | file | leave for the user (see "Finish") |

The user's words map to statuses like this: "to read", "TBR", "want to read" → `TBR`; "started", "reading", "in progress" → `Currently Reading`; "finished", "read", "reviewed" → `Read`; "gave up", "DNF" → `DNF`. If they don't say, use `TBR`.

## Page layout

Sections appear in this order. Only **My Review** depends on status: it is added when the book reaches `Read` (or `DNF`), always *below* Why and Notes.

```
## 📖 Summary
<summary paragraph>
## 🎯 Why I Picked This Book
<callout icon="🎯" color="gray_bg">
	*Who or what pointed me to it?*
	*What do I hope to get out of it?*
	*Why now?*
</callout>
## 📝 My Notes
<the notes sub-page>
## ✍️ My Review                       ← Read / DNF only
<callout icon="✍️" color="gray_bg">
	*Write your review here. Set your star rating in the Rating property above.*
</callout>
```

**Summary.** One paragraph of 3–5 sentences in the style of the user's existing pages: who the author is if relevant, what the book argues or is about, and what it covers, with the few key frameworks or ideas in **bold**. If the book has a subtitle, open with it in italics. Write from what you know of the book; if you don't know it well enough to summarize accurately, say so in the draft and write a shorter, hedged summary rather than inventing content.

**Why I Picked This Book.** Keep the three prompts as italic placeholder lines so the user can type over them. If the user already said why ("my manager recommended it", "for my UX course"), put their reason as a normal (non-italic) first line in the callout, in their words, and keep only the prompts it doesn't already answer.

**My Notes.** The user writes notes on a sub-page inside the book page. Create a child page titled `<Book title> — Notes` with icon 📝 and a single italic line: `*Notes, highlights and quotes as you read.*` It sits directly under the My Notes heading (see "Placing the notes page").

**My Review.** The gray callout with the italic placeholder, as above. If the user gave a review or rating in their message, put the review text in the callout instead of the placeholder, set `Rating`, and put a one-line version in the `Review` property (ask before writing a one-liner they didn't give you, or leave it empty).

Use the Notion enhanced-markdown syntax exactly as shown (tab-indented callout children). Don't put the title in the content and don't add trailing `<empty-block/>`s.

## Creating pages (full width)

Book pages and their notes sub-pages should open in full width. The Notion tools can't set that directly, but a duplicated page keeps it. So when `~/.claude/book-library/config.md` has `full_width_template_id` (or, if it doesn't, `~/.claude/course-notes/config.md` does), make each new page from that template instead of with `notion-create-pages`:

1. `notion-duplicate-page` with the template's ID. One copy at a time: wait until it loads before starting the next, because simultaneous duplicates can leave one stuck as a blank, unmovable block.
2. The duplicate finishes in the background: fetch the returned ID until it loads (a few tries).
3. `notion-move-pages` the copy to its real parent: `{"type": "data_source_id", "data_source_id": "<Library data source id>"}` for a book, or `{"type": "page_id", "page_id": "<book page id>"}` for a notes page.
4. `notion-update-page` with `update_properties` to set the title and the book's properties (for a notes page just the title), plus `icon`.
5. `notion-update-page` with `replace_content` to swap the template's text for the page's layout.

Everywhere below that says "create the page", use this when a template is set; the properties and layout stay the same. The notes page is still appended to the end of the book page, so "Placing the notes page" applies unchanged. If there's no template, or it's gone or a step fails, use `notion-create-pages` as written and tell the user at the end which new pages to set to full width by hand (••• → Full width). If the move or rename fails after the copy exists, tell the user where the stray copy is so they can delete it.

## Adding a book

1. **Identify the book.** Get the exact title and author. If the title is ambiguous (several well-known books share it) ask which one; otherwise don't ask.
2. **Check for duplicates.** Search the Library data source for the title (`notion-search` with `data_source_url`). If it's already there, don't create a second page: tell the user its current shelf and offer to move it instead.
3. **Fill details.** Author, Genre (pick from the existing options only; non-fiction books that are mostly self-improvement can take both `Non-fiction` and `Self-help`), Format only if the user said it, Status, and dates: `Started` = today for `Currently Reading`; for `Read`, `Finished` = today unless they gave dates. Get today's date with `date +%F`.
4. **Create the page** in the data source with the properties and the layout *without* My Review.
5. **Create the notes sub-page** (see below).
6. **If the status is `Read` or `DNF`,** append the My Review section to the end of the page with `insert_content`.

For several books in one request, do them one after another and report them together.

## Placing the notes page

A child page created with `notion-create-pages` (parent = the book page's ID) is appended to the **end** of the parent page. Use that: create the notes page while My Notes is still the last section, so it lands right under the heading, and only add My Review afterwards. Then fetch the book page once and check the `<page>` tag sits between `## 📝 My Notes` and anything after it. If it ended up elsewhere, fix it with `update_content`, moving the existing `<page url="…">` tag (never remove the tag on its own — that deletes the notes page).

If the book page already has content below My Notes (e.g. a My Review section on an older book), the new notes page lands at the very bottom. Move it with **one** `update_content` call that has two replacements: add the `<page url="…">…</page>` tag (same URL and title) under `## 📝 My Notes`, and remove the same tag from the bottom. Notion treats this as a move, and the page keeps its URL and contents. Then fetch the page to confirm the tag appears exactly once, in the right place.

## Moving a book between shelves

When the user says they started, finished or dropped a book:

1. Find the page in the Library (search by title). If it isn't there, offer to add it with the new status.
2. Fetch it and update properties: `Status`; `Started` = today when moving to `Currently Reading` (unless already set); `Finished` = today when moving to `Read` or `DNF`. Set `Rating` and `Review` if the user gave them.
3. Bring the page up to the layout, touching only what's missing:
   - **No 🎯 Why / 📝 My Notes sections** (books added before this skill): add them as described in "Backfilling existing books".
   - **Moving to `Read`/`DNF` and no ✍️ My Review:** append it at the end.
   - **Moving back** (e.g. Read → Currently Reading): change the properties only; never delete the review or anything else the user wrote.
4. Never rewrite text the user has typed into Why, Notes or Review. If they gave review text and the callout still has the placeholder, replace the placeholder; if it already has their writing, add the new text after it.

## Backfilling existing books

Use this when the user asks to bring older books up to the layout, or when a book being moved is missing the sections. To list every book, query the Library's default view (`notion-query-data-sources` in view mode), since keyword search can miss pages. Then for each book:

1. Fetch the page. **Skip it** if it already has `## 🎯 Why I Picked This Book` or `## 📝 My Notes`, or already has a child page whose title ends in "— Notes". This makes the backfill safe to run again.
   - **Blank page** (no content at all): append the Summary, the 🎯 Why section and the `## 📝 My Notes` heading with `insert_content`, then create the notes sub-page. It lands right under My Notes, so you're done; skip to step 4.
2. Create the notes sub-page (parent = the book page). It lands at the bottom.
3. In **one** `update_content` call:
   - Insert the 🎯 Why section and the `## 📝 My Notes` heading, with the notes `<page>` tag under it, directly before `## ✍️ My Review` (use that heading as `old_str` and put the new sections in front of it). If there's no My Review, put them after the Summary paragraph instead. If there's no Summary either, put them at the start of the page.
   - Remove the notes `<page>` tag from the bottom of the page (include the line before it in `old_str` so the match is unique).
4. Fetch the page again and check that the order is Summary → Why → My Notes (with the notes page) → My Review, that the notes page appears once, and that everything the user wrote is unchanged.

Don't add a My Review section to TBR or Currently Reading books during a backfill, and don't remove one that's already there. Report a summary line per book (updated / skipped because already done / failed).

## Finish

Reply with one line per book: title linked to its page, the shelf it's on, and what was done (created / moved from X to Y / sections added). Mention anything left for them:
- the **Cover** property: open the book, click Cover, and upload an image or paste a link (e.g. from Open Library or Goodreads);
- the "Why I Picked This Book" prompts, if still blank;
- a rating, when a book was marked Read without one.

Never report a page as created or updated if the call failed; say which step failed and why.
