---
name: wechat-to-obsidian
description: >
  This skill should be used when the user wants to save a WeChat official account
  article (mp.weixin.qq.com) to their Obsidian vault. It downloads the article,
  extracts metadata (title, author, publish date), converts the HTML body to
  Markdown, and writes it to the vault. Also triggered by phrases like "save this
  WeChat article", "export to Obsidian", "微信公众号保存", "微信文章导出",
  "wechat to obsidian", "微信转Obsidian".
---

# Save WeChat Articles to Obsidian

Download a WeChat official account article and save it as a Markdown note in an
Obsidian vault. A single command handles download, extraction, conversion, and
cleanup.

## Quick Start

```bash
python scripts/save_wechat.py "https://mp.weixin.qq.com/s/xxxxx"
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
3. Extracts the article body using HTMLParser depth tracking (not regex — WeChat HTML
   attributes often span multiple lines, which causes regex to fail silently)
4. Converts the body HTML to Markdown (preserves images, links, headings, code blocks)
5. Writes a `.md` file with Obsidian frontmatter to the vault inbox
6. Removes temporary files

## Output Format

```markdown
---
title: "Article Title"
author: "Account Name"
date: 2026-05-25
source: https://mp.weixin.qq.com/s/xxxxx
tags:
  - 公众号
---

# Article Title

Content in Markdown...

![](image-url)
```

## Prerequisites

- Python 3.8 or later (standard library only, no pip installs needed)
- `curl` available on PATH
- An Obsidian vault directory writable by the current user

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

## Troubleshooting

| Issue | Likely Cause | Fix |
|---|---|---|
| "下载内容过小" | WeChat anti-scraping | Retry once; the second attempt usually succeeds |
| Empty body | Page structure changed | Uses HTMLParser with regex fallback; check page source |
| Garbled title | HTML entities | `html.unescape()` is applied automatically |
| Python not found | Missing install | Install Python 3.8+ from python.org |
| curl not found | Missing tool | Install curl or use the package manager for your OS |
