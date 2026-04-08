# TOOLS.md - Local Notes

Skills define _how_ tools work. This file is for _your_ specifics — the stuff that's unique to your setup.

## What Goes Here

Things like:

- Camera names and locations
- SSH hosts and aliases
- Preferred voices for TTS
- Speaker/room names
- Device nicknames
- Anything environment-specific

## Examples

```markdown
### Cameras

- living-room → Main area, 180° wide angle
- front-door → Entrance, motion-triggered

### SSH

- home-server → 192.168.1.100, user: admin

### TTS

- Preferred voice: "Nova" (warm, slightly British)
- Default speaker: Kitchen HomePod
```

## Why Separate?

Skills are shared. Your setup is yours. Keeping them apart means you can update skills without losing your notes, and share skills without leaking your infrastructure.

---

Add whatever helps you do your job. This is your cheat sheet.

## Content Strategy

### LinkedIn
- Professional posts: leadership, banking tech, exec insights
- Fewer technical posts
- Cross-post to personal site

### Personal Site (andrewmccall.com)
- Technical + personal focus
- More technical than LinkedIn
- Topics: data engineering, platform engineering, Kubernetes, what Andrew is actually doing
- I can suggest, draft, and schedule articles
- Cross-post LinkedIn content here too

### Engagement workflow
- Pull saved items from X and Reddit → know what Andrew cares about
- Use saved content for: reposts, short comments with takes, longer-form articles
- Morning brief includes a LinkedIn reminder

## Trello

- **Board:** https://trello.com/b/69b858fb60e454ec6cbeb664 (Ada Tasks)
- **API Key:** c6c87888270853a308ad8e72c698e266
- **Token:** <REDACTED>
- **Lists:** Backlog / To Do / In Progress / Done
- **Workflow:** Andrew prioritizes, Ada picks up from To Do, works, moves to Done

## Git / GitHub

- **GitHub user:** andrewmccall
- **Identity:** Ada (`ada@andrewmccall.com`)
- **Auth:** env var `GITHUB_TOKEN` (fine-grained PAT, scoped to selected repos)
- **Git config:** `/home/openclaw/.openclaw/.gitconfig`
- **Git command prefix:** `GIT_CONFIG_GLOBAL=/home/openclaw/.openclaw/.gitconfig git ...`
- **Clone auth:** `https://x-access-token:${GITHUB_TOKEN}@github.com/<owner>/<repo>`
- **Commit convention:** prefix with `[ada]` to mark my work
- **Workflow:** always branch + PR, never push to main directly

## Trello

- **API Key:** stored in env `TRELLO_API_KEY`
- **Token:** stored in env `TRELLO_TOKEN`
- **Main board:** https://trello.com/b/69b858fb60e454ec6cbeb664 (Ada Tasks)
- **Board ID:** 69b858fb60e454ec6cbeb664
- **Lists:** Backlog / To Do / In Progress / Done
