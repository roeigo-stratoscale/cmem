# cmem

Keep Claude Code's memory, lessons and skills in git, so they survive new clones, new machines and new jobs.

**Status:** work in progress. Packaging as a Claude Code plugin with a guided `/cmem:setup` is under way; until then cmem is a single Python script (`bin/cmem`, standard library only, macOS and Linux).

## Two layers

| Layer | Default path | What goes there | Travels with you |
|---|---|---|---|
| general | `~/claude-memory` | lessons and skills with no internal names | yes, your own repo |
| workplace | `~/claude-memory-<name>` | full-detail lessons and skills, all per-repo memory (`repos/<owner>/<repo>/`) | no, the employer's repo |

- `~/.claude/projects/<slug>/memory` and `~/.claude/skills/<name>` become symlinks into the layers, so every clone of a repo shares one memory.
- Lessons in either layer's `lessons/` load in every project through one import in `~/.claude/CLAUDE.md`. On the same name, the workplace version wins; drop the workplace layer and the general versions take over.
- `cmem check` refuses a backup if the general layer contains the workplace's internal names (patterns in `workplace.json`) or either layer contains something that looks like a secret.

## Commands

```
cmem link [DIR] [--all]   link a checkout's memory into the workplace layer
cmem skills               move personal skills from ~/.claude/skills into the workplace layer
cmem promote FILE...      move a project memory file into the workplace lessons
cmem sync                 rebuild the lessons index and skill links (workplace wins)
cmem check                internal names in the general layer, secrets in both
cmem status               layers, winners and unlinked memory
cmem backup [-m MSG]      check, then commit and push both layers
cmem restore              new machine: config, links, sync
```

Commands that change files only print what they would do unless given `--apply`.

## License

MIT
