# Notion layout for course notes

Read this when publishing notes to Notion (Step 7 of SKILL.md). It describes the page structure and the exact layouts to reproduce, so every lecture looks the same as the ones before it.

Notion uses its own "enhanced Markdown". Before writing page content, read `notion://docs/enhanced-markdown-spec` once per session with the Notion fetch tool (the Notion tools require this). Rules that matter here: indent children with tabs; escape `\ * ~ ` $ [ ] < > { } | ^` in plain text (not inside code spans or code blocks); table cells hold rich text only.

## Hierarchy

```
<Home page>                     from config: home_page_id
└── <Class page>                page, one per class, icon = an emoji fitting the subject
    ├── <Section page>          page, one per course section
    │   └── <Lecture page>      page, one per lecture
    └── Glossary                inline database, one per class
```

Look up classes in the config's "Known classes" cache first. If a class isn't there, fetch the home page and check its child `<page>` tags (the user may have created or renamed pages by hand). Add anything you create or find to the cache.

## Placing new pages

New child pages are appended to the **end** of their parent. That's fine on the home page and on section pages (their children are the last thing on the page). On a **class page**, though, the end is below the Glossary, so a new section would land in the wrong place. After creating a section page:

1. Fetch the class page.
2. Use `update-page` with `replace_content`, sending the same content with the new section's `<page>` tag moved to the end of the list under "📚 Sections" (keep numeric section order). Keep every other `<page>` and `<database>` tag exactly as fetched; dropping one would delete it.

## Class page (only when the class is new)

Create under the home page, icon = an emoji that fits the subject:

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

Title: `Section N: <Name>` when the number is known, otherwise just `<Name>`. Pick a fitting emoji icon. Content:

```
<callout icon="🧭" color="gray_bg">
	<One sentence on what this section covers.>
</callout>
## Lectures {color="purple"}
```

## Lecture page

Title = lecture title (prefix the lecture number if known, e.g. `12. Auto Layout Basics`). Pick a fitting emoji icon. Convert the Markdown notes to this layout, keeping the same section order and omitting any section the notes don't have:

```
<callout icon="<class emoji>" color="gray_bg">
	**Class:** <class name> · **Section N:** <section name>
</callout>
## 🔤 Vocabulary {color="purple"}
<table fit-page-width="true" header-row="true">
	<colgroup>
		<col color="purple_bg">
		<col>
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
<table fit-page-width="true" header-row="true"> … Action | How, first column gray_bg; shortcuts in `code` …</table>
(code blocks for code/commands go here too)
---
## 📌 Tips & Gotchas {color="purple"}
<callout icon="⚠️" color="orange_bg">
	Warning text
</callout>
<callout icon="💡" color="blue_bg">
	Tip text
</callout>
## 🔗 Resources Mentioned {color="purple"}
- bullets
---
## ✅ Key Takeaways {color="purple"}
<callout icon="⭐" color="green_bg">
	- takeaway
	- takeaway
</callout>
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

## Glossary rows

Add one row per vocabulary term to the class's Glossary data source (`create-pages` with parent `data_source_id`):

- **Term**, **Definition** (short, plain text; keep the *(not defined in this lecture)* marker as plain parentheses), **Section**, **Lecture**.
- Skip terms already in the glossary (query or fetch the data source first).
- **Select options can't contain commas.** Use a short lecture name without commas for the Lecture tag (e.g. `Fills / Gradients / Strokes`).
- If row creation rejects a new section or lecture value, add the option to the data source schema with `update-data-source` first.

## Replacing a lecture

If the user chose to replace existing notes (Step 6 of SKILL.md), replace the lecture page's content with `replace_content` instead of creating a new page, and update its glossary rows rather than adding duplicates.
