# First-run setup

Use this when `~/.claude/book-library/config.md` doesn't exist or its data source is gone. The goal is one line of config pointing at the user's book database, plus a property mapping if their names differ from the skill's.

## 1. Look for an existing book database

Search Notion for likely titles: "Library", "Bookshelf", "Books", "Reading list", "Reading". Keep results whose type is `database`, then fetch each one and look at its schema. A book database usually has a title property plus some of: Author, Status (or a select with values like "To read" / "Reading" / "Read"), Rating, Genre.

- **One clear match:** tell the user which database you found (title and path) and confirm it's the one.
- **Several:** list them (title, path, how many matching properties) and ask which to use.
- **None:** go to step 3.

## 2. Map property names

Compare the database's properties with the table in SKILL.md. For each expected property, find the user's equivalent by type and meaning (e.g. `Writer` for Author, `Shelf` or `Reading status` for Status, `Date finished` for Finished). Also map Status *option* names: which option means TBR, Currently Reading, Read and DNF.

- Don't add, rename or delete properties or options in the user's database without asking. If a status option is missing (e.g. no DNF), ask whether to add it or skip that status.
- Properties with no equivalent are simply skipped: the skill works without Format, Genre, Cover and so on.

## 3. No database yet: create one

Ask where it should live ("Which Notion page should hold your Library?"). Search for the page they name, then create a database titled **Library** on it with the properties from the table in SKILL.md and the same select options. If the user wants shelves, add three linked views of it on the same page under the headings "📖 Currently Reading", "📚 TBR Pile" and "⭐ Read & Reviewed", each filtered by Status.

## 4. Save the config

Write `~/.claude/book-library/config.md`:

```markdown
# Book Library config

data_source: collection://<id>
database: <database URL>

## Property names
<!-- only lines that differ from SKILL.md; delete the section if none -->
- Author: Writer
- Status: Shelf
- Status options: TBR = To read, Currently Reading = Reading, Read = Finished, DNF = Abandoned
```

Then carry on with the user's original request.
