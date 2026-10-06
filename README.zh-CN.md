# WeChat to Obsidian 技能 · 微信文章一键保存到 Obsidian

将微信公众号文章保存到你的 Obsidian vault — 一条命令完成下载、提取、转换、写入。

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Agent Skills](https://img.shields.io/badge/Agent%20Skills-compatible-green)](https://agentskills.io)

## 支持平台

任何遵循 [Agent Skills 规范](https://agentskills.io) 的智能体均可使用：

| 智能体 | 安装方式 |
|--------|----------|
| **Claude Code** | 插件市场 或 手动 clone |
| **Hermes Agent** | `npx skills add` |
| **OpenClaw** | 手动 clone |
| **OpenCode** | `git clone ~/.opencode/skills/` |

## 安装

### 方式一：Claude Code 插件市场（推荐）

```
/plugin marketplace add qisehong/wechat-to-obsidian-skill
/plugin install wechat-to-obsidian@wechat-to-obsidian-skill
```

### 方式二：npx skills

```bash
npx skills add https://github.com/qisehong/wechat-to-obsidian-skill
```

### 方式三：手动克隆

```bash
# Claude Code / Claude Agent SDK
git clone https://github.com/qisehong/wechat-to-obsidian-skill.git ~/.claude/skills/wechat-to-obsidian

# Hermes Agent
git clone https://github.com/qisehong/wechat-to-obsidian-skill.git ~/.hermes/skills/wechat-to-obsidian

# OpenClaw
git clone https://github.com/qisehong/wechat-to-obsidian-skill.git ~/.openclaw/skills/wechat-to-obsidian

# OpenCode
git clone https://github.com/qisehong/wechat-to-obsidian-skill.git ~/.opencode/skills/wechat-to-obsidian-skill
```

## 前置条件

- **Python 3.8+** — 仅需标准库，无需 pip 安装额外依赖
- **curl** — 大多数系统自带
- **defuddle**（可选）— 用于提取非微信网页内容

## 快速开始

### 1. 配置 vault 路径

**Windows（PowerShell）：**
```powershell
$env:OBSIDIAN_VAULT_INBOX = "D:\我的笔记库\Inbox"
```

**macOS / Linux / WSL：**
```bash
export OBSIDIAN_VAULT_INBOX="$HOME/Documents/我的笔记库/Inbox"
```

永久生效请将上述命令添加到 `~/.bashrc` 或 `~/.zshrc` 中。

### 2. 保存文章

```bash
python scripts/save_wechat.py "https://mp.weixin.qq.com/s/xxxxx"
```

或者在对话中直接发送微信文章链接，智能体会自动调用该技能。

### 3. 检查配置

```bash
python scripts/save_wechat.py --check
```

成功输出示例：
```
Configuration OK
  Vault inbox:  D:\我的笔记库\Inbox  (from: environment variable)
  Python:       3.12.0
  curl:         curl 8.4.0
```

## 输出格式

```markdown
---
title: "文章标题"
author: "公众号名称"
date: 2026-05-25
source: https://mp.weixin.qq.com/s/xxxxx
tags:
  - wechat
---

# 文章标题

正文内容（已转换为 Markdown）...

![](../attachments/2026-05-25-文章标题-img1.jpg)
```

## 图片本地化

微信图片默认自动下载到 vault 附件目录，笔记中引用本地副本。这解决了微信
防盗链导致的远程图片无法在 Obsidian 中显示、或随时间失效的问题。

- **保存位置**：从 Inbox 向上查找 Obsidian vault 根目录（含 `.obsidian`
  文件夹），图片存入 `<vault根目录>/attachments/`；找不到则存入
  `<Inbox>/attachments/`。
- **命名规则**：`日期-标题-imgN.扩展名`，按首次出现顺序编号，扩展名取自
  `wx_fmt` 参数。
- **失败处理**：下载失败的图片保留远程链接，笔记依然完整；重复运行同一篇
  文章时，已存在的图片自动跳过（缓存）。
- **关闭本地化**：传入 `--no-local-images` 即可保留全部远程链接。

## 非交互模式

智能体和 CI 环境没有终端输入。脚本会自动检测（stdin 非 TTY）并绝不阻塞在
`input()` 上：若 vault 路径未配置，则打印三种配置方式并以退出码 1 结束。
也可用 `--non-interactive` 显式指定该行为。

```bash
# 在智能体 shell 中且未配置：干净地报错退出，不会挂起等待输入
python scripts/save_wechat.py "https://mp.weixin.qq.com/s/xxxxx"   # exit 1

# 先配置好路径即可正常使用
python scripts/save_wechat.py --vault-path "D:/我的笔记库/Inbox" "https://mp.weixin.qq.com/s/xxxxx"
```

## 配置方式

三种方式设置 vault 路径（优先级从高到低）：

| 方式 | 示例 |
|------|------|
| CLI 参数 | `--vault-path "D:/我的笔记库/Inbox"` |
| 环境变量 | `OBSIDIAN_VAULT_INBOX` |
| 配置文件 | `~/.wechat-to-obsidian.conf` |

首次运行时若未配置，脚本会交互式引导你输入路径。详见[配置指南](skills/wechat-to-obsidian/references/configuration.md)。

## URL 支持范围

| URL 类型 | 处理方式 | 质量 |
|----------|----------|------|
| `mp.weixin.qq.com` | 内置微信解析器 | 完整 Markdown |
| 任意网页 | defuddle（需安装） | 干净正文 |
| 任意 URL | 纯文本兜底 | 标题 + 链接 |

## 权限配置（Claude Code）

在对话中免确认运行，可在 `~/.claude/settings.json` 中添加：

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

## 常见问题

| 问题 | 原因 | 解决方法 |
|------|------|----------|
| "下载内容过小" | 微信反爬机制 | 重试一次即可 |
| 正文为空 | 微信页面结构变化 | 请带上文章链接提交 issue |
| 标题乱码 | HTML 实体 | `html.unescape()` 已自动处理 |
| 图片保留远程链接 | 该图下载失败（设计行为） | 重跑同一命令即可，已下载的图片自动跳过 |
| 退出码 1 并提示配置方式 | 未配置 vault 且 stdin 非 TTY | 设置 `OBSIDIAN_VAULT_INBOX`、`--vault-path` 或配置文件 |
| Python 未找到 | 未安装 Python | 从 [python.org](https://python.org) 安装 Python 3.8+ |
| curl 未找到 | 缺少工具 | `brew install curl` / `apt install curl` / `winget install curl` |
| Windows 乱码 | 编码问题 | 使用 Python 3.8+（正确支持 UTF-8），输出文件不乱码 |

## 工作原理

```
┌──────────────────┐
│  mp.weixin.qq.com │  ← 用户在对话中粘贴链接
└────────┬─────────┘
         │
    [1] curl 下载 HTML 页面
         │
    [2] 正则提取元数据（标题/公众号/日期）
         │
    [3] 提取 <div id="js_content"> 正文
         │
    [4] HTML → Markdown 转换
         │
    [5] 下载微信图片到 vault 附件目录，改写为本地引用
         │
    [6] 写入 Obsidian vault Inbox
         │
┌──────────────────┐
│  📄 YYYY-MM-DD-   │  ← Obsidian 中可直接打开，
│     标题.md        │    图片离线可用
└──────────────────┘
```

## 许可

MIT — 详见 [LICENSE](LICENSE)。

## 贡献

欢迎提 issue 和 PR。本技能遵循 [Agent Skills 规范](https://agentskills.io/specification)。
