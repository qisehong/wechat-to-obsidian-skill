# WeChat to Obsidian Skill

Save WeChat official account articles to your Obsidian vault — one command
downloads, extracts metadata, converts to Markdown, and writes the note.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Agent Skills](https://img.shields.io/badge/Agent%20Skills-compatible-green)](https://agentskills.io)

## Supported Platforms

Any agent that follows the [Agent Skills specification](https://agentskills.io):

| Agent | Installation |
|-------|-------------|
| **Claude Code** | Marketplace or manual clone |
| **Hermes Agent** | `npx skills add` |
| **OpenClaw** | Manual clone |
| **OpenCode** | `git clone ~/.opencode/skills/` |

## Installation

### Option 1: Claude Code Marketplace (easiest)

```
/plugin marketplace add xuhaitao/wechat-to-obsidian-skill
/plugin install wechat-to-obsidian@wechat-to-obsidian-skill
```

### Option 2: npx skills

```bash
npx skills add https://github.com/xuhaitao/wechat-to-obsidian-skill
```

### Option 3: Manual Clone

```bash
# Claude Code / Claude Agent SDK
git clone https://github.com/xuhaitao/wechat-to-obsidian-skill.git ~/.claude/skills/wechat-to-obsidian

# Hermes Agent
git clone https://github.com/xuhaitao/wechat-to-obsidian-skill.git ~/.hermes/skills/wechat-to-obsidian

# OpenClaw
git clone https://github.com/xuhaitao/wechat-to-obsidian-skill.git ~/.openclaw/skills/wechat-to-obsidian

# OpenCode
git clone https://github.com/xuhaitao/wechat-to-obsidian-skill.git ~/.opencode/skills/wechat-to-obsidian-skill
```

## Prerequisites

- **Python 3.8+** — standard library only, no pip installs needed
- **curl** — available on most systems
- **defuddle** (optional) — for non-WeChat web page extraction

## Quick Start

### 1. Configure your vault path

**Windows (PowerShell):**
```powershell
$env:OBSIDIAN_VAULT_INBOX = "D:\MyVault\Inbox"
```

**macOS / Linux / WSL:**
```bash
export OBSIDIAN_VAULT_INBOX="$HOME/Documents/MyVault/Inbox"
```

Make it permanent by adding to your shell profile (`~/.bashrc`, `~/.zshrc`).

### 2. Save an article

```bash
python scripts/save_wechat.py "https://mp.weixin.qq.com/s/xxxxx"
```

Or let the agent handle it — just share a WeChat article URL in conversation.

### 3. Check configuration

```bash
python scripts/save_wechat.py --check
```

## Output Example

```markdown
---
title: "AI Tools Comparison 2026"
author: "TechDaily"
date: 2026-05-25
source: https://mp.weixin.qq.com/s/xxxxx
tags:
  - wechat
---

# AI Tools Comparison 2026

Article content in Markdown...
```

## Configuration Methods

3 ways to set the vault path (highest priority first):

| Method | Example |
|--------|---------|
| CLI argument | `--vault-path "D:/MyVault/Inbox"` |
| Environment variable | `OBSIDIAN_VAULT_INBOX` |
| Config file | `~/.wechat-to-obsidian.conf` |

See [configuration guide](skills/wechat-to-obsidian/references/configuration.md) for details.

## URL Support

| URL Type | Handler | Quality |
|----------|---------|---------|
| `mp.weixin.qq.com` | Built-in WeChat parser | Full Markdown |
| Any web page | defuddle (if installed) | Clean text |
| Any URL | Plain fallback | Title + link |

## Permission Setup (Claude Code)

To skip the permission prompt when the agent runs this script, add to your
`~/.claude/settings.json`:

```json
{
  "permissions": {
    "allow": [
      "Bash(python *save_wechat.py *)",
      "Bash(python3 *save_wechat.py *)"
    ]
  }
}
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "Download too small" | WeChat anti-scraping — retry once |
| Python not found | Install Python 3.8+ from [python.org](https://python.org) |
| curl not found | `brew install curl` / `apt install curl` / `winget install curl` |
| Empty body | Report the issue with the article URL |
| Encoding errors on Windows | Use Python 3.8+ (handles UTF-8 correctly) |

## License

MIT — see [LICENSE](LICENSE).

## Contributing

Issues and pull requests welcome. The skill follows the
[Agent Skills specification](https://agentskills.io/specification).
