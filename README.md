# Claude Skills

A collection of [skills](https://docs.claude.com/en/docs/claude-code/skills) I've built for Claude. Each skill is a packaged set of instructions that teaches Claude a specific workflow.

## Skills

| Skill | What it does |
|---|---|
| [**course-notes**](plugins/course-notes/) | Turns online course transcripts into structured study notes (vocabulary, concepts, how-to steps, review questions), published to Notion and/or saved as Markdown. |

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
