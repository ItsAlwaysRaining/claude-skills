# Claude Skills

A collection of [skills](https://docs.claude.com/en/docs/claude-code/skills) I've built for Claude. Each skill is a packaged set of instructions that teaches Claude a specific workflow.

## Skills

| Skill | What it does |
|---|---|
| [**course-notes**](plugins/course-notes/) | Turns online course transcripts into structured study notes (vocabulary, concepts, how-to steps, review questions), published to Notion and/or saved as Markdown. |
| [**learning-calendar**](plugins/learning-calendar/) | Logs what you learned each day to a Notion calendar, grouped into a few entries a day (one per class, Claude & AI, and computing concept) with short topics inside, gathered from your Claude sessions and your own list, and pushed only after you approve them. |
| [**brand-palette**](plugins/brand-palette/) | Builds an accessible brand color palette for light and dark mode, checked against WCAG AA and color-blindness simulations, with Dark, Light and Surface steps for each brand color, labeled neutrals, and plain-language notes. Its second skill, **brand-builder**, turns the palette into a full brand reference page: story and motifs, chart colors, a signature move, typography, layout, live components and CSS tokens. |
| [**ship-pr**](plugins/ship-pr/) | Commits your changes, pushes them to a branch and opens a GitHub pull request, after checking the destination repo, the branch and what's on it. Never merges and never pushes to `main`. |
| [**book-library**](plugins/book-library/) | Adds books to your Notion Library and moves them between shelves (TBR, Currently Reading, Read & Reviewed). Each page gets a summary, a "Why I Picked This Book" section, a notes sub-page, and a review section once you finish. |

[![course-notes class page in Notion](plugins/course-notes/examples/notion-class-page.png)](plugins/course-notes/)

## Install

This repo is a Claude Code plugin marketplace. To add it and install a skill:

```
/plugin marketplace add ItsAlwaysRaining/claude-skills
/plugin install course-notes@claude-skills
```

Each skill's README has setup details and a manual install option.

## Repo layout

```
claude-skills/
├── .claude-plugin/marketplace.json   lists every skill in this repo
└── plugins/
    └── <skill-name>/
        ├── .claude-plugin/plugin.json
        ├── README.md
        ├── skills/<skill-name>/SKILL.md
        └── examples/
```

To add a new skill, create a folder under `plugins/` and add an entry to `marketplace.json`.

## License

[MIT](LICENSE)
