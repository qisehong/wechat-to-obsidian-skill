#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Save WeChat official account articles to an Obsidian vault.

Usage:
    python save_wechat.py "https://mp.weixin.qq.com/s/xxxxx"
    python save_wechat.py --vault-path "D:/MyVault/Inbox" "https://..."
    python save_wechat.py --check

Configuration:
    See references/configuration.md or run with --help for details.
"""

import re
import html as html_mod
from html.parser import HTMLParser
import sys
import os
import subprocess
import tempfile
import argparse
from pathlib import Path
from configparser import ConfigParser

VERSION = "0.2.0"
USER_AGENT = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148"
)
CONFIG_FILE = Path.home() / ".wechat-to-obsidian.conf"


# ---------------------------------------------------------------------------
# HTMLParser-based js_content extractor
# ---------------------------------------------------------------------------

class JsContentExtractor(HTMLParser):
    """Extract inner HTML of id="js_content" div using depth tracking.

    WeChat HTML often has attributes spanning multiple lines, which causes
    regex-based extraction to fail silently. This parser tracks tag depth
    and reliably captures the full body regardless of attribute formatting.
    """

    def __init__(self):
        super().__init__()
        self.in_content = False
        self.depth = 0
        self.capture = []

    def handle_starttag(self, tag, attrs):
        attrs_d = dict(attrs)
        if tag == "div" and attrs_d.get("id") == "js_content":
            self.in_content = True
            self.depth = 1
            return
        if self.in_content:
            if tag == "div":
                self.depth += 1
            self.capture.append(self.get_starttag_text() or f"<{tag}>")

    def handle_endtag(self, tag):
        if self.in_content:
            if tag == "div":
                self.depth -= 1
                if self.depth == 0:
                    self.in_content = False
                    return
            self.capture.append(f"</{tag}>")

    def handle_data(self, data):
        if self.in_content:
            self.capture.append(data)

    def get_html(self):
        return "".join(self.capture)


# ---------------------------------------------------------------------------
# Configuration resolution
# ---------------------------------------------------------------------------

def resolve_vault_path(cli_value=None):
    """Determine the vault inbox path from available sources.

    Priority: CLI argument > env var > config file > None
    """
    if cli_value:
        source = "command-line argument"
        return Path(cli_value), source

    env_val = os.environ.get("OBSIDIAN_VAULT_INBOX")
    if env_val:
        source = "environment variable"
        return Path(env_val), source

    if CONFIG_FILE.exists():
        cp = ConfigParser()
        cp.read(CONFIG_FILE, encoding="utf-8")
        cfg_val = cp.get("obsidian", "vault_inbox", fallback=None)
        if cfg_val:
            source = str(CONFIG_FILE)
            return Path(cfg_val), source

    return None, "none"


def interactive_config():
    """Ask user for vault path and offer to persist it."""
    print("No vault inbox configured.")
    print()
    print("Configure now by setting one of:")
    print("  1. Environment variable: OBSIDIAN_VAULT_INBOX")
    print("  2. Config file:          ~/.wechat-to-obsidian.conf")
    print()
    path_str = input("Enter your Obsidian vault Inbox path: ").strip()
    if not path_str:
        print("No path entered. Exiting.")
        sys.exit(0)

    vault_path = Path(path_str).expanduser()
    if not vault_path.exists():
        create = input(f"Directory '{vault_path}' does not exist. Create it? [Y/n]: ").strip().lower()
        if create in ("", "y", "yes"):
            vault_path.mkdir(parents=True, exist_ok=True)
            print(f"Created: {vault_path}")
        else:
            print("Exiting.")
            sys.exit(0)

    save = input("Save this path to ~/.wechat-to-obsidian.conf for future use? [Y/n]: ").strip().lower()
    if save in ("", "y", "yes"):
        cp = ConfigParser()
        cp["obsidian"] = {"vault_inbox": str(vault_path)}
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            cp.write(f)
        print(f"Saved to {CONFIG_FILE}")

    return vault_path


# ---------------------------------------------------------------------------
# Article download
# ---------------------------------------------------------------------------

def download_article(url, dest_path):
    """Download article HTML via curl. Returns True on success."""
    print("[1/4] Downloading article...")
    result = subprocess.run(
        [
            "curl", "-s", "--max-time", "60", "-L",
            "-A", USER_AGENT,
            "-H", "Accept-Language: zh-CN,zh;q=0.9",
            "-o", str(dest_path),
            url,
        ],
        capture_output=True,
        text=True,
        timeout=90,
    )
    if result.returncode != 0:
        raise RuntimeError(f"curl failed: {result.stderr or 'unknown error'}")

    size = os.path.getsize(dest_path)
    if size < 1000:
        # Read a snippet to help debug
        with open(dest_path, "r", encoding="utf-8") as f:
            snippet = f.read(300)
        raise RuntimeError(
            f"Download too small ({size} bytes). "
            f"Content preview: {snippet[:200]}"
        )

    print(f"   Downloaded: {size:,} bytes")
    return True


# ---------------------------------------------------------------------------
# Metadata extraction (WeChat-specific)
# ---------------------------------------------------------------------------

def extract_wechat_metadata(html_path):
    """Extract title, account name, date, and body HTML from WeChat page."""
    print("[2/4] Extracting metadata...")

    with open(html_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Title
    title = None
    for pattern in [
        r"var\s+msg_title\s*=\s*'([^']*)'",
        r'"msg_title"\s*:\s*"([^"]*)"',
        r'var\s+msg_title\s*=\s*"([^"]*)"',
        r'class="rich_media_title[^"]*"[^>]*>\s*([^<]+)',
    ]:
        m = re.search(pattern, content)
        if m:
            title = html_mod.unescape(m.group(1).strip())
            break
    if not title:
        title = "Untitled"

    # Account name
    account = None
    for pattern in [
        r'nickname\s*=\s*"([^"]*)"',
        r"var\s+nickname\s*=\s*'([^']*)'",
        r'id="js_name"[^>]*>\s*([^<]*)',
    ]:
        m = re.search(pattern, content)
        if m:
            account = m.group(1).strip()
            if account:
                break
    if not account:
        account = "Unknown Account"

    # Date
    date = "Unknown Date"
    m = re.search(r"create_time:\s*'([^']+)'", content)
    if m:
        date = m.group(1).strip().split(" ")[0]

    # Body HTML — use HTMLParser depth tracking (regex fails when
    # WeChat HTML attributes span multiple lines)
    parser = JsContentExtractor()
    parser.feed(content)
    body_html = parser.get_html()

    if not body_html:
        # Fallback: try regex as last resort
        m = re.search(
            r'id="js_content"[^>]*>(.+?)(?:<script\s|</div>\s*<script)',
            content,
            re.DOTALL,
        )
        body_html = m.group(1).strip() if m else ""

    print(f"   Title:    {title[:60]}{'...' if len(title) > 60 else ''}")
    print(f"   Account:  {account}")
    print(f"   Date:     {date}")
    print(f"   Body:     {len(body_html):,} chars")

    return title, account, date, body_html


# ---------------------------------------------------------------------------
# HTML to Markdown conversion (WeChat-specific)
# ---------------------------------------------------------------------------

def wechat_html_to_markdown(raw_html):
    """Convert WeChat article HTML body to Markdown."""
    md = raw_html

    # Images — prefer data-src over src
    md = re.sub(r'<img[^>]*data-src="([^"]+)"[^>]*/?>', r"\n\n![](\1)\n\n", md)
    md = re.sub(r'<img[^>]*src="([^"]+)"[^>]*/?>', r"\n\n![](\1)\n\n", md)

    # Strip span tags, keep content
    md = re.sub(r"<span[^>]*>", "", md)
    md = re.sub(r"</span>", "", md)

    # Headings
    for tag, prefix in [("h1", "#"), ("h2", "##"), ("h3", "###"), ("h4", "####"), ("h5", "#####"), ("h6", "######")]:
        md = re.sub(rf"<{tag}[^>]*>", f"{prefix} ", md)
        md = re.sub(rf"</{tag}>", "\n\n", md)

    # Inline formatting
    md = re.sub(r"<strong[^>]*>(.*?)</strong>", r"**\1**", md)
    md = re.sub(r"<b[^>]*>(.*?)</b>", r"**\1**", md)
    md = re.sub(r"<em[^>]*>(.*?)</em>", r"*\1*", md)
    md = re.sub(r"<i[^>]*>(.*?)</i>", r"*\1*", md)
    md = re.sub(r"<code[^>]*>(.*?)</code>", r"`\1`", md)
    md = re.sub(r"<pre[^>]*>(.*?)</pre>", r"\n```\n\1\n```\n", md, flags=re.DOTALL)

    # Links
    md = re.sub(r'<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>', r"[\2](\1)", md)

    # Horizontal rules and line breaks
    md = re.sub(r"<hr[^>]*/?>", "\n\n---\n\n", md)
    md = re.sub(r"<br\s*/?>", "\n", md)

    # Container tags — remove tags, keep content
    for tag in ("section", "div", "p", "article", "main"):
        md = re.sub(rf"<{tag}[^>]*>", "", md)
        suffix = "\n\n" if tag in ("p", "section") else ""
        md = re.sub(rf"</{tag}>", suffix, md)

    # Lists
    md = re.sub(r"<li[^>]*>", "- ", md)
    md = re.sub(r"</li>", "\n", md)
    for tag in ("ul", "ol"):
        md = re.sub(rf"<{tag}[^>]*>", "\n", md)
        md = re.sub(rf"</{tag}>", "\n", md)

    # WeChat-specific: mp-common-profile
    md = re.sub(
        r"<mp-common-profile[^>]*>.*?</mp-common-profile>",
        "",
        md,
        flags=re.DOTALL,
    )

    # Clean remaining HTML tags
    md = re.sub(r"<[^>]+>", "", md)

    # Decode HTML entities — explicit common ones + html.unescape for the rest
    replacements = {
        "&nbsp;": " ", "&lt;": "<", "&gt;": ">",
        "&amp;": "&", "&quot;": '"', "&apos;": "'",
        "&#39;": "'", "&#x27;": "'", "&#34;": '"',
        "&#8217;": "'", "&#8220;": '"', "&#8221;": '"',
        "&#8230;": "…", "&#x2F;": "/",
        "&#60;": "<", "&#62;": ">",
        "&#40;": "(", "&#41;": ")",
    }
    for k, v in replacements.items():
        md = md.replace(k, v)
    md = html_mod.unescape(md)

    # Whitespace normalization
    md = re.sub(r"\n{3,}", "\n\n", md)
    md = re.sub(r" +", " ", md)
    return md.strip()


# ---------------------------------------------------------------------------
# Save to vault
# ---------------------------------------------------------------------------

def save_to_vault(title, author, date, source_url, markdown_body, vault_inbox):
    """Write the Markdown file into the vault inbox directory."""
    print("[3/4] Writing to vault...")

    safe_title = re.sub(r'[<>:"/\\|?*]', "_", title)
    filename = f"{date}-{safe_title}.md"
    filepath = vault_inbox / filename

    output = (
        f"---\n"
        f'title: "{title}"\n'
        f'author: "{author}"\n'
        f"date: {date}\n"
        f"source: {source_url}\n"
        f"tags:\n"
        f"  - wechat\n"
        f"---\n"
        f"\n"
        f"# {title}\n"
        f"\n"
        f"{markdown_body}\n"
    )

    vault_inbox.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(output)

    print(f"   Saved to: {filepath}")
    print(f"   Size:     {len(output):,} chars")
    return filepath


# ---------------------------------------------------------------------------
# Fallback: defuddle for non-WeChat URLs
# ---------------------------------------------------------------------------

def save_via_defuddle(url, vault_inbox):
    """Use defuddle CLI to extract clean content from a generic web page."""
    print("[*] Attempting defuddle extraction (non-WeChat URL)...")
    result = subprocess.run(
        ["defuddle", url],
        capture_output=True,
        text=True,
        timeout=60,
    )
    if result.returncode != 0:
        raise RuntimeError(f"defuddle failed: {result.stderr}")

    markdown_body = result.stdout.strip()
    title = url.rstrip("/").split("/")[-1] or "Web Clip"
    date = "unknown-date"

    return save_to_vault(title, "Web", date, url, markdown_body, vault_inbox)


def save_fallback(url, vault_inbox):
    """Last resort: save URL and title without full content."""
    print("[*] Using fallback: saving URL reference only...")
    title = url.rstrip("/").split("/")[-1] or "Web Clip"
    markdown_body = f"Source: {url}\n\nContent could not be extracted automatically."
    date = "unknown-date"
    return save_to_vault(title, "Web", date, url, markdown_body, vault_inbox)


# ---------------------------------------------------------------------------
# Check mode
# ---------------------------------------------------------------------------

def run_check(vault_path, source_label):
    """Verify the environment and print status."""
    print("Configuration Check")
    print("===================")
    print(f"  Vault inbox:  {vault_path}  (from: {source_label})")

    # Python version
    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    print(f"  Python:       {py_ver}")

    # curl
    cur_result = subprocess.run(["curl", "--version"], capture_output=True, text=True)
    if cur_result.returncode == 0:
        cur_ver = cur_result.stdout.strip().split("\n")[0].split()[1]
        print(f"  curl:         {cur_ver}")
    else:
        print("  curl:         NOT FOUND")

    # defuddle (optional)
    try:
        def_result = subprocess.run(
            ["defuddle", "--version"], capture_output=True, text=True, timeout=5
        )
        if def_result.returncode == 0:
            print(f"  defuddle:     {def_result.stdout.strip()}")
        else:
            print("  defuddle:     not installed (optional)")
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        print("  defuddle:     not installed (optional)")

    print()
    if vault_path:
        print("Configuration OK")
    else:
        print("Configuration incomplete — vault path not set.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Save a WeChat article to an Obsidian vault.",
        epilog="Configuration: https://github.com/qisehong/wechat-to-obsidian-skill",
    )
    parser.add_argument(
        "url",
        nargs="?",
        help="WeChat article URL (mp.weixin.qq.com) or any web page URL",
    )
    parser.add_argument(
        "-v", "--vault-path",
        help="Path to the Obsidian vault Inbox directory",
    )
    parser.add_argument(
        "--version", action="version", version=f"wechat-to-obsidian {VERSION}"
    )
    parser.add_argument(
        "--check", action="store_true",
        help="Check configuration and exit (no download)",
    )
    args = parser.parse_args()

    # --check mode
    if args.check:
        vault_path, source = resolve_vault_path(args.vault_path)
        run_check(vault_path, source)
        return

    # Require URL for normal operation
    if not args.url:
        parser.print_help()
        print("\nError: a URL is required (unless using --check).")
        sys.exit(1)

    url = args.url.strip()

    # Resolve vault path
    vault_path, source = resolve_vault_path(args.vault_path)
    if vault_path is None:
        vault_path = interactive_config()
        source = "interactive setup"

    print(f"Vault inbox: {vault_path} (from: {source})")
    print(f"URL: {url}")
    print()

    # Temporary file for downloaded HTML
    tmp_html = Path(tempfile.gettempdir()) / "wechat_article.html"

    try:
        # Step 1: Download
        download_article(url, tmp_html)

        # Step 2: Extract (WeChat-specific parser)
        is_wechat = "mp.weixin.qq.com" in url
        if is_wechat:
            title, author, date, body_html = extract_wechat_metadata(tmp_html)
            if not body_html or len(body_html) < 50:
                raise RuntimeError("Body extraction failed or content too short")
            markdown_body = wechat_html_to_markdown(body_html)
        else:
            # Non-WeChat: try defuddle first
            try:
                filepath = save_via_defuddle(url, vault_path)
                print(f"\n[Done] {filepath.name}")
                return
            except Exception:
                filepath = save_fallback(url, vault_path)
                print(f"\n[Done] {filepath.name}")
                return

        # Step 3: Save
        filepath = save_to_vault(title, author, date, url, markdown_body, vault_path)

        # Step 4: Cleanup
        print("[4/4] Cleaning up...")
        tmp_html.unlink(missing_ok=True)

        print(f"\n[Done] {filepath.name}")
        print(f"       {filepath}")

    except Exception as exc:
        # Clean up temp file on failure
        tmp_html.unlink(missing_ok=True)
        print(f"\n[Error] {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
