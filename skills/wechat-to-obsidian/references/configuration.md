# Configuration Guide

Three ways to tell the script where your Obsidian vault inbox is located.

## Method 1: Environment Variable (recommended)

Set `OBSIDIAN_VAULT_INBOX` before running the script.

### Permanent setup

**Windows (PowerShell profile):**
```powershell
# Add to $PROFILE
[Environment]::SetEnvironmentVariable("OBSIDIAN_VAULT_INBOX", "D:\MyVault\Inbox", "User")
```

**macOS / Linux:**
```bash
# Add to ~/.bashrc or ~/.zshrc
export OBSIDIAN_VAULT_INBOX="$HOME/Documents/MyVault/Inbox"
```

### One-time (per session)

**Windows PowerShell:**
```powershell
$env:OBSIDIAN_VAULT_INBOX = "D:\MyVault\Inbox"
```

**Windows Command Prompt:**
```cmd
set OBSIDIAN_VAULT_INBOX=D:\MyVault\Inbox
```

**macOS / Linux / WSL:**
```bash
export OBSIDIAN_VAULT_INBOX="$HOME/Documents/MyVault/Inbox"
```

## Method 2: Configuration File

Create `~/.wechat-to-obsidian.conf` (in your home directory):

```ini
[obsidian]
vault_inbox = D:\MyVault\Inbox
```

Or on macOS / Linux:

```ini
[obsidian]
vault_inbox = /home/username/Documents/MyVault/Inbox
```

This file is read on every run. Edit it any time to change the target directory.

## Method 3: Command-Line Argument

Pass `--vault-path` (or `-v`) directly:

```bash
python save_wechat.py --vault-path "D:\MyVault\Inbox" "https://mp.weixin.qq.com/s/xxxxx"
```

This overrides the environment variable and config file for that single run.

## Priority

```
--vault-path argument  >  OBSIDIAN_VAULT_INBOX env var  >  ~/.wechat-to-obsidian.conf  >  interactive prompt
```

If none of the above are set, the script asks for the path interactively and
offers to save it to the config file for future use.

## Verifying Your Setup

Run with the `--check` flag to verify configuration without downloading anything:

```bash
python save_wechat.py --check
```

Expected output:
```
Configuration OK
  Vault inbox: D:\MyVault\Inbox (from: environment variable)
  Python:       3.12.0
  curl:         curl 8.4.0
```
