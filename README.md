# cmem

Keep Claude Code's memory, lessons and skills in git, so they survive new clones, new machines and new jobs.

**Status:** early. One Python script (`bin/cmem`, standard library only, macOS and Linux), packaged as a Claude Code plugin.

## Install

```
/plugin marketplace add roeigo-stratoscale/cmem
/plugin install cmem@cmem
```

Then run `/cmem:setup`. It checks what is missing (layer repos, config, existing memory, the CLAUDE.md block) and asks about each part; it is safe to re-run. Until setup is done, cmem changes nothing and only reminds you once per session.

- `/cmem:doctor`: what is set up and what is missing
- `/cmem:remove`: undo cmem before uninstalling (Claude Code runs nothing on uninstall). Links become real folders again and cmem's CLAUDE.md block is removed; the layer repos stay.

## Two layers

| Layer | Default path | What goes there | Travels with you |
|---|---|---|---|
| general | `~/claude-memory` | lessons and skills with no internal names | yes, your own repo |
| workplace | `~/claude-memory-<name>` | full-detail lessons and skills, all per-repo memory (`repos/<owner>/<repo>/`) | no, the employer's repo |

- `~/.claude/projects/<slug>/memory` and `~/.claude/skills/<name>` become symlinks into the layers, so every clone of a repo shares one memory.
- Lessons in either layer's `lessons/` load in every project through one import in `~/.claude/CLAUDE.md`. On the same name, the workplace version wins; drop the workplace layer and the general versions take over.
- cmem owns only its marked block in `~/.claude/CLAUDE.md` (`<!-- BEGIN cmem ... -->` to `<!-- END cmem -->`). Your own rules and other tools' blocks are never touched.
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
cmem config               show or set the layer folders ('none' drops a layer)
cmem init-layer KIND PATH create a layer's layout; only adds what is missing
cmem doctor [--json]      what is set up and what is missing
cmem remove               undo cmem in this home folder
```

To use `cmem` in a terminal, alias it to the script (setup offers this).

## Tests

```
python3 -m unittest discover -s tests
```

Every test runs cmem against a temporary fake home folder.

Commands that change files only print what they would do unless given `--apply`.

## License

MIT
