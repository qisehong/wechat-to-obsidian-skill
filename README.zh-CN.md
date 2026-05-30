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

![](图片链接)
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
    [5] 写入 Obsidian vault Inbox
         │
┌──────────────────┐
│  📄 YYYY-MM-DD-   │  ← Obsidian 中可直接打开
│     标题.md        │
└──────────────────┘
```

## 许可

MIT — 详见 [LICENSE](LICENSE)。

## 贡献

欢迎提 issue 和 PR。本技能遵循 [Agent Skills 规范](https://agentskills.io/specification)。
