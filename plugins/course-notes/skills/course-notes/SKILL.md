---
name: course-notes
description: Turn online course lecture transcripts (Udemy, Coursera, Skillshare, LinkedIn Learning, YouTube courses, etc.) into structured study notes with vocabulary first, then main concepts, how-to steps, tips, and takeaways, published to Notion (class → section → lecture, plus a class glossary) and/or saved as Markdown files. Use this whenever the user pastes or points to a lecture/video transcript and wants notes, a summary, key points, study material, or "the important stuff" pulled out of it, even if they don't say "notes" — e.g. "here's the transcript from lecture 12", "what do I need to know from this video", or a raw pasted transcript with little explanation.
---

# Course Notes

The user takes self-paced online courses and copies transcripts from the platform's transcript panel. They want notes they can review later **instead of rewatching the video**, so the notes must capture everything worth knowing, in a predictable layout, and nothing that wasn't actually taught.

## Step 0: Load the user's settings

Settings live outside the skill, in `~/.claude/course-notes/config.md`, so the skill itself contains nothing personal and can be shared or updated freely.

- **If the file exists**, read it and follow it.
- **If it doesn't**, run first-time setup (read `references/setup.md`), then continue with the transcript the user gave you.

The config says where notes go (`notion`, `local`, or `both`), the Notion home page, the local folder, and a cache of known Notion page IDs. Whenever you create a new class page or glossary in Notion, add its IDs to the config's cache so future runs can go straight to it.

## Step 1: Read the transcript like a caption file, not prose

Text copied from a transcript panel has predictable problems. Fix them mentally before extracting anything:

- **Broken lines.** Captions are split into fragments, often mid-sentence. Rejoin them into full sentences.
- **No timestamps, titles, or speaker labels.** If the user gave a class/section/lecture title, use it. If not, write a short descriptive title from the content.
- **Garbled terms.** Auto-captions mishear jargon, names, and keyboard shortcuts (e.g. "pie torch" → PyTorch, "get hub" → GitHub, "the jason file" → the JSON file). Correct these silently when context makes the right term obvious. When you're genuinely unsure, write your best guess followed by `[?]` so the user knows to check the video.
- **Several lectures pasted together.** Treat each transcript as its own lecture with its own notes.

## Step 2: Work out which class this belongs to

Notes are filed by class, so identify the class before writing. In order of preference:

1. **The user said it**: a course name, a course URL, or "this is from my Figma course".
2. **Existing classes**: check the classes listed in the config cache, the class pages under the Notion home page, and/or the class folders in the local folder. If the lecture's subject clearly matches one, use it. Reusing a class matters more than picking a perfect name; a class split in two is annoying to study from.
3. **The content**: the tool or subject being taught usually suggests a sensible class name.

If after this you're still unsure (no matching class exists and the content could plausibly belong to more than one course), **ask the user for the class name**, suggesting your best guess so they can just confirm. If they don't provide a name, use `Undetermined Class`.

## Step 3: Decide what's signal and what's filler

Drop anything that doesn't teach: greetings, "welcome back", "in the next video we'll…", "please leave a review", "check the resources section", recaps of previous lectures, and the instructor narrating their own mouse ("let's scroll in here"). The one exception: a one-line teaser of what's coming next is worth keeping as a "Next up" note, because it helps the user see how lectures connect.

Keep anything the instructor emphasizes ("the key thing is…", "a common mistake…", "you might want to check with your developer…"). Those are often the most valuable lines in the lecture.

## Step 4: Write the notes using this template

Use this layout for every lecture. Omit a section entirely if the lecture has nothing for it (a theory lecture usually has no How-to steps; a software demo may have no debate). Empty headings are noise.

```markdown
# [Lecture title]
*Class: [class name] · Section: [if known]*

## Vocabulary
- **Term**: definition in plain words, as the instructor used it.

## Main Concepts
### [Concept name]
Short explanation (2–5 sentences or bullets). Include the instructor's
examples, evidence, and reasoning: the "why", not just the "what".

## How-to Steps
### [Task name]
1. Concrete step, naming the exact panel/menu/button.
2. ...

## Shortcuts, Settings & Code
| Action | How |
|---|---|
| Open command palette | Cmd + Shift + P |

(Use fenced code blocks for code or commands.)

## Tips & Gotchas
- ⚠️ Warnings and common mistakes the instructor flagged.
- 💡 Pro tips and recommendations.

## Resources Mentioned
- People, tools, studies, websites, books, with any detail given (date, version, link).

## Key Takeaways
- 3–5 bullets: what someone should remember a month from now.

## Review Questions
1. Question testing understanding (not trivia)?
   <details><summary>Answer</summary>Answer drawn from the lecture.</details>

**Next up:** [one line, only if the instructor previewed the next lecture]
```

### Section guidance

- **Vocabulary goes first** because it's what the user needs to understand everything below it. Include terms the lecture introduces or relies on: named concepts, technical terms, tool features. Use the instructor's framing. If the instructor uses a term without defining it (e.g. it was covered in an earlier lecture), give a brief standard definition and mark it *(not defined in this lecture)* so the user knows where it came from.
- **Main Concepts** are the ideas, arguments, and mental models. Attribute contestable opinions to the instructor ("The instructor argues…") so the user can tell taught fact from viewpoint.
- **How-to Steps** should be followable without the video: name the panel, the option, the value. Merge rambling demo narration into clean numbered steps.
- **Shortcuts, Settings & Code**: capture exactly. Translate spoken shortcuts into standard notation ("hold command and shift and press P" → `Cmd + Shift + P`).
- **Review Questions**: 3–5 questions that make the user recall and apply, with answers hidden in `<details>` so they can self-test.

## Step 5: Stay faithful to the lecture

These are notes on *what was taught*. Don't pad them with outside knowledge, extra tips, or "further reading" the instructor never mentioned; the user is trusting these notes to reflect the course. The only additions allowed are: fixing caption errors, defining terms the lecture relied on (marked as above), and clarifying wording so a sentence makes sense. If something in the transcript seems factually wrong, keep it as taught and add a short *Note:* rather than silently correcting it.

## Step 6: Check for existing notes on the same lecture

Before saving anywhere, look for notes that already cover this lecture: in Notion (the class's section pages) and/or the local class folder, depending on the config. A match is the same title, or a different title that's clearly the same content (same topic, same section).

If one exists, ask the user whether to **replace** it or **keep both** before writing anything; duplicate notes for one lecture make studying confusing. Replace means overwrite the existing page/file (renaming it if the new notes have better info, like a lecture number). Keep both means save the new notes with `-2` (local) or `(2)` (Notion) added to the name. A genuinely different lecture that happens to share a name gets the suffix without asking.

## Step 7: Save the notes

Do whichever of these the config's `output` setting calls for.

### Notion (`notion` or `both`)

```
<Notion home page> → <Class page> → <Section page> → <Lecture page>
                   → Glossary (inline database, one per class)
```

**Read `references/notion-layout.md` before doing this.** It has the exact layout for each kind of page and a few Notion quirks (where new pages land, select options can't contain commas). Following it keeps every lecture page looking like the others, which is what makes the notes pleasant to browse.

In short:
1. Find the class page under the home page (check the config cache first); create it, with its Glossary, if the class is new.
2. Find the section page under the class; create it if new, keeping sections in order above the glossary.
3. Create the lecture page under the section, converting the notes into the Notion layout.
4. Add the lecture's new vocabulary terms as rows in the class Glossary.

If the Notion tools aren't available or a call keeps failing, tell the user Notion publishing was skipped and why, and point them to the Notion section of `references/setup.md`. If `output` is `notion` only, give them the notes in chat so nothing is lost. Never claim a publish succeeded when it didn't.

### Local files (`local` or `both`)

Save to `<local folder>/<Class_Name>/<file-name>.md`:

- Class folder names: Title_Case with underscores, no special characters (e.g. `UI_UX_Design`).
- File name: lowercase, hyphens, prefixed with the lecture number when known (`12-auto-layout-basics.md`), otherwise just the title.
- Create the folders if they don't exist.
- **Class glossary:** also add each lecture's vocabulary to `<local folder>/<Class_Name>/glossary.md` (create it if missing). Alphabetical, one line per term, source lecture in parentheses, no duplicates.

If you can't write files (e.g. a chat-only environment), output the notes in the chat instead.

## Finish

Tell the user where the notes went (Notion link and/or file path) and give a 2–3 line summary in chat. Don't repeat the full notes; they're already saved.
