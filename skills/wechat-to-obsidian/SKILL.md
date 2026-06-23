---
name: wechat-to-obsidian
description: >
  This skill should be used when the user wants to save a WeChat official account
  article (mp.weixin.qq.com) to their Obsidian vault. It downloads the article,
  extracts metadata (title, author, publish date), converts the HTML body to
  Markdown, and writes it to the vault. Also triggered by phrases like "save this
  WeChat article", "export to Obsidian", "微信公众号保存", "微信文章导出",
  "wechat to obsidian", "微信转Obsidian".
version: 0.3.0
---

# Save WeChat Articles to Obsidian

Download a WeChat official account article and save it as a Markdown note in an
Obsidian vault. A single command handles download, extraction, conversion, and
cleanup. Optionally auto-syncs to a Git remote.

## Quick Start

```bash
python scripts/save_wechat.py "https://mp.weixin.qq.com/s/xxxxx"

# With Git auto-sync (commit + push after saving)
python scripts/save_wechat.py --git-sync "https://mp.weixin.qq.com/s/xxxxx"
```

The script saves to the vault inbox configured via one of these methods (highest
priority first):

1. `--vault-path` command-line argument
2. `OBSIDIAN_VAULT_INBOX` environment variable
3. `~/.wechat-to-obsidian.conf` configuration file
4. Interactive prompt on first run

See `references/configuration.md` for detailed setup instructions.

## What the Script Does

1. Downloads the article HTML via curl (iOS Safari User-Agent for WeChat compatibility)
2. Extracts title, account name, and publish date from the page metadata
3. Extracts the article body using **JsContentExtractor** (HTMLParser depth tracking — see [Why not regex?](#why-not-regex))
4. Converts the body HTML to Markdown (preserves images, links, headings, code blocks, lists)
5. Writes a `.md` file with Obsidian frontmatter to the vault inbox
6. Optionally commits and pushes to a Git remote (`--git-sync`)
7. Removes temporary files

### Why not regex?

> ⚠️ **Pitfall: regex-based `js_content` extraction fails silently on WeChat HTML.**
>
> WeChat HTML frequently has `<div>` attributes that span multiple lines:
> ```html
> <div class="rich_media_content
>   js_underline_content"
>   id="js_content">
> ```
> A regex like `id="js_content"(.*?)</div>` will **not** match this — the
> `id` attribute is on a different line from the tag opening. The result is
> a silently empty body with no error message.
>
> **JsContentExtractor** uses Python's `HTMLParser` to track tag nesting depth
> and reliably captures the full body regardless of attribute formatting.
> Regex is kept only as a last-resort fallback.

## Output Format

```markdown
---
title: "Article Title"
author: "Account Name"
date: 2026-05-25
source: https://mp.weixin.qq.com/s/xxxxx
tags:
  - wechat
---

# Article Title

Content in Markdown...

![](image-url)
```

## Git Auto-Sync

When `--git-sync` is passed, the script automatically syncs to a Git remote
after saving. The vault directory must be a Git repository.

```bash
# Set the vault inbox path
export OBSIDIAN_VAULT_INBOX="$HOME/.obsidian-vault/Inbox"

# Save with auto-sync
python scripts/save_wechat.py --git-sync "https://mp.weixin.qq.com/s/xxxxx"
```

The sync workflow is: `git pull --rebase` → `git add <file>` → `git commit` → `git push`.
This handles cases where other devices (e.g., Obsidian on Windows/macOS) have
also pushed changes.

To make Git push work without password prompts, use a GitHub PAT in the remote URL:

```bash
cd ~/.obsidian-vault
git remote set-url origin https://username:TOKEN@github.com/username/repo.git
```

## Prerequisites

- Python 3.8 or later (standard library only, no pip installs needed)
- `curl` available on PATH
- An Obsidian vault directory writable by the current user
- (Optional) Git, for `--git-sync` mode

## Configuration

Set the vault inbox path before first use. The recommended way is an environment
variable:

```bash
# Windows PowerShell
$env:OBSIDIAN_VAULT_INBOX = "D:\MyVault\Inbox"

# macOS / Linux
export OBSIDIAN_VAULT_INBOX="$HOME/Documents/MyVault/Inbox"
```

To make it permanent, add the export line to `~/.bashrc`, `~/.zshrc`, or set it
as a system environment variable.

See `references/configuration.md` for alternative methods and platform-specific
instructions.

## Supported URL Types

| URL Pattern | Handler | Notes |
|---|---|---|
| `mp.weixin.qq.com/s/...` | Built-in parser | Full HTML→Markdown conversion |
| Other web pages | `defuddle` CLI (if installed) | Clean content extraction |
| Any URL | Plain text fallback | Title + URL saved as note |

## Limitations

- **Images**: WeChat image URLs (mmbiz.qpic.cn) are preserved as remote links;
  images may not display outside WeChat due to hotlink protection.
- **Video/audio**: Embedded media is not extracted.
- **Rich formatting**: Complex CSS layouts may be simplified.
- **Paywalled articles**: Only publicly accessible portions are captured.
- **Image extraction**: WeChat `<img>` tags often lack direct `src` attributes;
  image URLs are scattered in JS code. The script extracts `mmbiz.qpic.cn` URLs
  via regex and maps them to `<img>` tags in order.
- **HTML entities**: WeChat articles use extensive `&#xxxx;` numeric entities
  (e.g., `&#8217;` → `'`, `&#8220;` → `"`). The script decodes 18 common
  entities explicitly and falls back to `html.unescape()`.

## Troubleshooting

| Issue | Likely Cause | Fix |
|---|---|---|
| "下载内容过小" | WeChat anti-scraping | Retry once; the second attempt usually succeeds |
| Empty body | js_content div attributes span lines | Script uses HTMLParser; if still empty, check page source |
| Garbled title | HTML entities | `html.unescape()` is applied automatically |
| Python not found | Missing install | Install Python 3.8+ from python.org |
| curl not found | Missing tool | Install curl via your OS package manager |
| Git push fails (--git-sync) | No credentials | Set up GitHub PAT in remote URL or use SSH |
| Merge conflict (--git-sync) | Concurrent edits on other devices | Resolve manually, then re-run with `--git-sync` |
