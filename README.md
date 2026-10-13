# Retreaver MCP Operator Skills & CLI Suite

[![MCP Compatible](https://img.shields.io/badge/MCP-Streamable%20HTTP-blue.svg)](https://modelcontextprotocol.io)
[![Retreaver API](https://img.shields.io/badge/Retreaver-MCP%20v1-green.svg)](https://learn.retreaver.com/guides/install-mcp-server)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-brightgreen.svg)](https://python.org)

Production-grade agentic operator skills, automation playbooks, and unified CLI for the official [Retreaver Model Context Protocol (MCP) server](https://learn.retreaver.com/guides/install-mcp-server) (`https://ai.retreaver.com/mcp`).

This repository provides **natural-language shortcuts**, **strict code contracts**, and **executable tooling** so AI coding assistants (OMP, Claude Code, Cursor, Codex, Grok, Hermes, and more) can operate Retreaver call-tracking and Real-Time Bidding (RTB) campaigns as autonomous platform operators.

---

## Quick Navigation

- [Agent Shortcut Matrix](#agent-shortcut-matrix)
- [Client Setup Guide](#client-setup-guide)
- [Skills Architecture](#skills-architecture)
- [CLI Reference](#cli-reference)
- [Operational Invariants & Safety](#operational-invariants--safety)
- [Installation](#installation)

---

## Agent Shortcut Matrix

When installed, AI assistants automatically map common operator intents to the corresponding specialized skill and tool actions:

| What you ask the AI assistant | Target Skill | CLI / MCP Action | Under the Hood |
|---|---|---|---|
| **"Set up this buyer..."** | `retreaver-buyer-ops` | `buyer_ops.py create` | Calls `targets.manage` with E.164 number, priority, weight, timeout, and business hours. |
| **"Set buyer caps..."** | `retreaver-buyer-ops` | `buyer_ops.py set-caps` | Calls `targets.caps.manage` for concurrency, hourly, daily, monthly, and hard caps. |
| **"Set up this publisher..."** | `retreaver-publisher-ops` | `publisher_ops.py create` | Calls `affiliates.manage` to provision publisher accounts and assign payout terms. |
| **"Generate RTB postback key..."** | `retreaver-publisher-ops` | `publisher_ops.py create-key` | Calls `postback_keys.manage` creating campaign-bound RTB pings and data writing keys. |
| **"Add this webhook here..."** | `retreaver-webhook-ops` | `webhook_ops.py from-template` | Calls `webhooks.configurations.manage` using CallGrid, TrackDrive, Anura, or custom templates. |
| **"Test fire this webhook..."** | `retreaver-webhook-ops` | `webhook_ops.py test-fire` | Calls `webhooks.test_fires.manage` to simulate real pixel delivery and response tags. |
| **"Check why it's not working..."** | `retreaver-diagnostics-reporting` | `diag_reporting.py rtb-diagnose` | Reads `rtb_inbounds.read` to diagnose `no-target`, `expired`, cap limits, or buyer API errors. |
| **"Give me stats on today..."** | `retreaver-diagnostics-reporting` | `diag_reporting.py call-stats` | Queries `calls_drill_down_tables.read` across campaigns, publishers, targets, and revenue. |
| **"Show RTB ping/post summary..."** | `retreaver-diagnostics-reporting` | `diag_reporting.py rtb-summary` | Aggregates ClickHouse RTB reservation logs to reveal bid rates, duplicate volume, and EPC. |

---

## Client Setup Guide

The Retreaver MCP server operates over **streamable HTTP** with **OAuth 2.0 PKCE** authentication:

```text
Endpoint: https://ai.retreaver.com/mcp
```

### 1. Claude Code
```bash
claude mcp add --transport http retreaver --scope user https://ai.retreaver.com/mcp
```
Run `claude /mcp`, select **retreaver**, and authorize in your browser.

### 2. OpenAI Codex
```bash
codex mcp add retreaver --url https://ai.retreaver.com/mcp
```
Codex starts the OAuth authorization flow and saves credentials locally.

### 3. xAI Grok
```bash
grok mcp add --transport http retreaver https://ai.retreaver.com/mcp
```

### 4. Nous Hermes
```bash
hermes config set mcp_servers.retreaver.url "https://ai.retreaver.com/mcp"
hermes config set mcp_servers.retreaver.auth "oauth"
hermes config set mcp_servers.retreaver.enabled true
```
Authenticate interactively via `hermes mcp login retreaver`.

### 5. Cursor
Add to `~/.cursor/mcp.json`:
```json
{
  "mcpServers": {
    "retreaver": {
      "url": "https://ai.retreaver.com/mcp"
    }
  }
}
```

### 6. Claude Desktop
Because Claude Desktop uses stdio transports, use the `mcp-remote` bridge in `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "retreaver": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "https://ai.retreaver.com/mcp"]
    }
  }
}
```

### 7. OMP (Oh My Pi)
Add to `~/.omp/agent/mcp.json`:
```json
{
  "mcpServers": {
    "retreaver": {
      "type": "http",
      "url": "https://ai.retreaver.com/mcp"
    }
  }
}
```

---

## Skills Architecture

The repository contains 5 modular operator skills adhering to strict agent code contracts:

```text
skills/
├── retreaver-operator/               # Master orchestrator & unified CLI
│   ├── SKILL.md
│   ├── scripts/retreaver_cli.py
│   └── references/operator-spec.md
├── retreaver-buyer-ops/              # Target & buyer lifecycle management
│   ├── SKILL.md
│   ├── scripts/buyer_ops.py
│   └── references/buyer-spec.md
├── retreaver-publisher-ops/          # Affiliate & publisher management
│   ├── SKILL.md
│   ├── scripts/publisher_ops.py
│   └── references/publisher-spec.md
├── retreaver-webhook-ops/            # Webhooks, timers & third-party integrations
│   ├── SKILL.md
│   ├── scripts/webhook_ops.py
│   └── references/webhook-spec.md
└── retreaver-diagnostics-reporting/  # RTB diagnostics & ClickHouse rollups
    ├── SKILL.md
    ├── scripts/diag_reporting.py
    └── references/diag-reporting-spec.md
```

### Skill Invariants
1. **Safety First**: All mutation actions support `dry_run: true` to return diff previews without modifying live campaign state.
2. **E.164 Standards**: Phone numbers must be formatted in standard E.164 (e.g. `+18005550199`).
3. **Tag Strictness**: Numeric and date comparisons require registered tag keys via the Tag Wizard; unregistered keys evaluate lexicographically.
4. **Structured JSON Output**: All scripts output clean, parseable JSON suitable for piping and subagent handoffs.

---

## CLI Reference

All scripts support `--help` and accept either flags or JSON inputs.

### Master Unified CLI (`retreaver_cli.py`)
```bash
# Check company identity and role
python3 skills/retreaver-operator/scripts/retreaver_cli.py whoami

# Create a buyer
python3 skills/retreaver-operator/scripts/retreaver_cli.py buyer create \
  --name "Health Insurance Buyer" \
  --number "+18885550123" \
  --priority 1 \
  --weight 100 \
  --timeout 30

# Set buyer caps
python3 skills/retreaver-operator/scripts/retreaver_cli.py buyer caps \
  --target-id 148422 \
  --concurrency 5 \
  --daily 250

# Diagnose RTB inbounds over the last 15 minutes
python3 skills/retreaver-operator/scripts/retreaver_cli.py rtb-diag --minutes 15

# Pull real-time call performance for today
python3 skills/retreaver-operator/scripts/retreaver_cli.py stats --window today
```

### Buyer Operations CLI (`buyer_ops.py`)
```bash
# List all active targets
python3 skills/retreaver-buyer-ops/scripts/buyer_ops.py list --per-page 25

# Show specific buyer details and business hours
python3 skills/retreaver-buyer-ops/scripts/buyer_ops.py show --target-id 148422

# Reset hard cap
python3 skills/retreaver-buyer-ops/scripts/buyer_ops.py reset-cap --target-id 148422
```

### Publisher Operations CLI (`publisher_ops.py`)
```bash
# List publishers
python3 skills/retreaver-publisher-ops/scripts/publisher_ops.py list

# Create an RTB postback key for a publisher
python3 skills/retreaver-publisher-ops/scripts/publisher_ops.py create-key \
  --campaign-id 54098 \
  --publisher-id 71327 \
  --name "Affiliate RTB Key" \
  --ttl 60
```

### Webhook Operations CLI (`webhook_ops.py`)
```bash
# Browse 100+ pre-built integration templates
python3 skills/retreaver-webhook-ops/scripts/webhook_ops.py templates

# Test-fire a webhook to verify pixel responses
python3 skills/retreaver-webhook-ops/scripts/webhook_ops.py test-fire --webhook-id 123786
```

### Diagnostics & Reporting CLI (`diag_reporting.py`)
```bash
# Inspect RTB reservation breakdown by status
python3 skills/retreaver-diagnostics-reporting/scripts/diag_reporting.py rtb-summary --group-by status

# Diagnose failed reservations for a campaign
python3 skills/retreaver-diagnostics-reporting/scripts/diag_reporting.py rtb-diagnose \
  --campaign-id 54098 \
  --time-frame last_24h

# Pull call stats grouped by publisher and status
python3 skills/retreaver-diagnostics-reporting/scripts/diag_reporting.py call-stats \
  --window today \
  --group-by "affiliate_id,status"
```

---

## Operational Invariants & Safety

When troubleshooting RTB and call routing:

1. **`no-target` Status**:
   - Indicates no buyer qualified for the inbound ping.
   - Common causes: State not present in buyer's `geo` tag whitelist; buyer capacity full (`code: 4004` from dynamic ping endpoints like CallGrid); concurrency caps reached; or outside business hours.
2. **`expired` Status**:
   - A buyer returned a valid bid and Retreaver created a reservation (`status: reserved`), but the publisher **never placed the matching voice call** within the `ttl_seconds` window (typically 60–75s).
   - Verify that the publisher receives the response payload and dials the returned dynamic DID or SIP URI.
3. **`ping_shield_already_reserved`**:
   - Duplicate pings for the same caller number within the active reservation window are automatically suppressed to protect buyer endpoints from spam.

---

## Installation

### Automatic Install
Clone the repository and run `install.sh` to install all skills directly into your global agent skills directory:

```bash
git clone https://github.com/ArielleTolome/retreaver-mcp-skills.git
cd retreaver-mcp-skills
./install.sh
```

By default, this installs skills to `~/.agents/skills/` (and automatically links `~/.omp/agent/skills` if present).

### Manual Install
Copy the desired skill directories into your harness's skill folder:
```bash
cp -r skills/retreaver-* ~/.agents/skills/
```

---

## License

MIT License. See [LICENSE](LICENSE) for details.
