# Retreaver MCP Operator Skills, Slash Commands & CLI Suite

[![MCP Compatible](https://img.shields.io/badge/MCP-Streamable%20HTTP-blue.svg)](https://modelcontextprotocol.io)
[![Retreaver API](https://img.shields.io/badge/Retreaver-51%2F51%20MCP%20Tools-green.svg)](https://learn.retreaver.com/guides/install-mcp-server)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-brightgreen.svg)](https://python.org)

Production-grade agentic operator skills, **10 slash-command prompt shortcuts (`/retreaver:*`)**, and a **9-module CLI suite** covering **100% of the 51 tools** on the official [Retreaver Model Context Protocol (MCP) server](https://learn.retreaver.com/guides/install-mcp-server) (`https://ai.retreaver.com/mcp`).

Designed for AI coding harnesses (**OMP, Claude Code, Cursor, OpenAI Codex, xAI Grok, Nous Hermes**) so an assistant can operate Retreaver call-tracking and Real-Time Bidding (RTB) campaigns end-to-end.

---

## Quick Navigation

- [Slash Commands & Prompt Shortcuts](#slash-commands--prompt-shortcuts)
- [Multi-Step Operator Recipes](#multi-step-operator-recipes)
- [9 Modular Skills (51/51 MCP Tools)](#9-modular-skills-5151-mcp-tools)
- [Client Setup Guide](#client-setup-guide)
- [CLI Reference](#cli-reference)
- [Operational Invariants & Troubleshooting](#operational-invariants--troubleshooting)
- [Installation](#installation)

---

## Slash Commands & Prompt Shortcuts

`./install.sh` installs 10 slash commands into `~/.claude/commands/retreaver/`, `~/.omp/agent/commands/retreaver/`, and `~/.cursor/commands/` so you can invoke complex workflows with a single command or natural-language phrase:

| Slash Command | Natural-Language Prompt Shortcut | Target Skill | CLI / MCP Action |
|---|---|---|---|
| **`/retreaver:status`** | *"Which Retreaver company am I connected to?"* | `retreaver-operator` | `account.whoami` + active campaign/buyer count |
| **`/retreaver:rtb-diag`** | *"Check why RTB pings/pics aren't going through"* | `retreaver-diagnostics-reporting` | `rtb_inbounds.read` + `no-target`/`expired` root cause |
| **`/retreaver:stats`** | *"Give me the stats on what's happened today"* | `retreaver-diagnostics-reporting` | `calls_drill_down_tables.read` + RTB bid rollups |
| **`/retreaver:setup-buyer`** | *"Set up this buyer & cap at 50 concurrent"* | `retreaver-buyer-ops` | `targets.manage` (`dry_run` first) + `targets.caps.manage` |
| **`/retreaver:setup-publisher`** | *"Set up this publisher & generate an RTB key"* | `retreaver-publisher-ops` | `affiliates.manage` + `postback_keys.manage` |
| **`/retreaver:setup-webhook`** | *"Add this webhook & test-fire it"* | `retreaver-webhook-ops` | `webhooks.configurations.manage` + `webhooks.test_fires.manage` |
| **`/retreaver:routing`** | *"Show or edit campaign routing tiers & weights"* | `retreaver-campaign-routing-ops` | `campaigns.routing_settings.read` / `manage` (`dry_run`) |
| **`/retreaver:suppress`** | *"Check or upload numbers to the Suppressed list"* | `retreaver-caller-lists-suppression` | `caller_list_checks.manage` / `caller_list_uploads.manage` |
| **`/retreaver:pbm`** | *"Register a numeric tag, upload PBM table, or credit a call"* | `retreaver-tags-bidding-ops` | `tags.manage` / `payout_bid_modification_tables.manage` / `calls.manage` |
| **`/retreaver:audit`** | *"Run a full housekeeping audit on caps, numbers & webhooks"* | `retreaver-operator` | `retreaver_cli.py audit` (uncapped buyers, orphaned DIDs, token targets) |

---

## Multi-Step Operator Recipes

Use these chained prompts directly in chat:

### 1. Stand Up a Buyer & Prove the Webhook Works
> 1. *"Add a buyer called 'Sunrise Insurance' to the 'Auto Insurance' campaign, cap it at 50 concurrent calls and 200 daily, business hours 9–5 Eastern weekdays — show me a dry run first."*
> 2. *"Apply that. Create the CallGrid or CRM ping webhook on that buyer from the configurator template."*
> 3. *"Test-fire that webhook and show me the exact URL it hit and the response payload."*
> 4. *"Put Sunrise Insurance in the top routing tier for California and Texas — dry run first."*

### 2. Diagnose Why RTB Pings ("Pics") Aren't Converting
> 1. *"/retreaver:rtb-diag 15"* (or *"Analyze the RTB logs for the last 15 minutes and tell me why pings aren't going through."*)
> 2. *"Break down `no-target` vs `expired` by caller state and buyer."*
> 3. *"Test the buyer's passthrough bid endpoint directly to check if capacity is full (`code: 4004`) or caller ID is blocked."*
> 4. *"Check if the campaign has a fallback tracking number pool or if reservations are returning SIP-only URIs."*

### 3. Diagnose a Conversion Drop
> 1. *"Converted calls for the ACA campaign this week vs last week, broken down by buyer."*
> 2. *"For the buyer that dropped the most, show me connected vs converted, and the longest converting call."*
> 3. *"What caps and routing weight does that buyer have right now? Did its hard cap fire?"*

### 4. Company Switch & Housekeeping Audit
> 1. *"/retreaver:audit"*
> 2. *"Which active buyers have no caps set at all?"*
> 3. *"Which campaigns are paused but still have active tracking numbers pointed at them?"*
> 4. *"List every webhook posting to a URL containing 'staging' or 'test'."*

---

## 9 Modular Skills (51/51 MCP Tools)

```text
skills/
├── retreaver-operator/                  # 1. Master orchestrator & unified CLI (whoami, audit, rtb-diag, stats)
├── retreaver-buyer-ops/                 # 2. Buyers/Targets, 5 cap tiers, hard-cap resets, business hours, duplicates
├── retreaver-publisher-ops/             # 3. Publishers/Affiliates, RTB & Data Writing postback keys, conversion groups
├── retreaver-campaign-routing-ops/      # 4. Campaigns, priority/weight routing ladders, Waiting Room, Handler Groups, IVR Prompts
├── retreaver-numbers-pools-ops/         # 5. Tracking DIDs, Dynamic Number Pools (DNI), SIP URI routing, number caps
├── retreaver-caller-lists-suppression/  # 6. Suppressed/Accepted caller lists, bulk CSV uploads, live number checks
├── retreaver-webhook-ops/               # 7. Passthrough/HTTP/Postback timers, 100+ configurator templates, test-firing
├── retreaver-tags-bidding-ops/          # 8. Tag Wizard (Text/Numeric/Date), Replacement Tokens, PBM CSV tables, call credits
└── retreaver-diagnostics-reporting/     # 9. ClickHouse RTB inbound logs, call detail flows, drill-down rollups, CSV exports
```

| Skill | Covered MCP Tools |
|---|---|
| **`retreaver-operator`** | `account.whoami`, `catalog.search`, `docs.search`, `docs.fetch` + cross-domain orchestration |
| **`retreaver-buyer-ops`** | `targets.read`, `targets.manage`, `targets.caps.manage`, `targets.cap_resets.manage`, `targets.duplicates.manage` |
| **`retreaver-publisher-ops`** | `affiliates.read`, `affiliates.manage`, `postback_keys.read`, `postback_keys.manage`, `conversion_groups.read`, `conversion_groups.manage` |
| **`retreaver-campaign-routing-ops`** | `campaigns.read`, `campaigns.manage`, `campaigns.routing_settings.read`, `campaigns.routing_settings.manage`, `target_groups.read`, `target_groups.manage`, `target_groups.duplicates.manage`, `prompts.read`, `prompts.manage` |
| **`retreaver-numbers-pools-ops`** | `numbers.read`, `numbers.manage`, `number_pools.read`, `number_pools.manage` |
| **`retreaver-caller-lists-suppression`** | `caller_lists.read`, `caller_lists.manage`, `caller_list_numbers.read`, `caller_list_numbers.manage`, `caller_list_uploads.read`, `caller_list_uploads.manage`, `caller_list_checks.manage` |
| **`retreaver-webhook-ops`** | `webhooks.read`, `webhooks.manage`, `webhooks.test_fires.manage`, `webhooks.templates.read`, `webhooks.configurations.manage` |
| **`retreaver-tags-bidding-ops`** | `tags.read`, `tags.manage`, `tags.replacement_tokens.read`, `payout_bid_modification_tables.read`, `payout_bid_modification_tables.manage`, `calls.manage` |
| **`retreaver-diagnostics-reporting`** | `rtb_inbounds.read`, `rtb_inbound_drill_down_tables.read`, `calls.read`, `calls_drill_down_tables.read`, `exports.rtb_inbounds.manage` |

---

## Client Setup Guide

The Retreaver MCP server speaks **streamable HTTP** and authenticates via **OAuth 2.0 PKCE**:

```text
https://ai.retreaver.com/mcp
```

- **Claude Code:** `claude mcp add --transport http retreaver --scope user https://ai.retreaver.com/mcp`
- **OpenAI Codex:** `codex mcp add retreaver --url https://ai.retreaver.com/mcp`
- **xAI Grok:** `grok mcp add --transport http retreaver https://ai.retreaver.com/mcp`
- **AGY:** `agy mcp add --type http retreaver https://ai.retreaver.com/mcp`
- **Nous Hermes:** `hermes config set mcp_servers.retreaver.url "https://ai.retreaver.com/mcp" && hermes config set mcp_servers.retreaver.auth "oauth" && hermes config set mcp_servers.retreaver.enabled true`
- **OMP / Cursor:** Add `"retreaver": {"type": "http", "url": "https://ai.retreaver.com/mcp"}` to `~/.omp/agent/mcp.json` or `~/.cursor/mcp.json`.

---

## CLI Reference

Every skill ships with a standalone Python CLI wrapper in `scripts/` that supports `--help` and auto-refreshes OAuth tokens:

```bash
# Master Unified CLI (whoami, audit, buyer, publisher, webhook, rtb-diag, stats)
python3 skills/retreaver-operator/scripts/retreaver_cli.py audit

# Campaign & Routing Operations
python3 skills/retreaver-campaign-routing-ops/scripts/campaign_routing_ops.py routing --campaign-id 54098

# Numbers & Dynamic Pools
python3 skills/retreaver-numbers-pools-ops/scripts/numbers_pools_ops.py list-numbers

# Caller Lists & Suppression
python3 skills/retreaver-caller-lists-suppression/scripts/caller_lists_ops.py list --owner-type Campaign --owner-id 54098

# Tags, Replacement Tokens, PBM & Call Crediting
python3 skills/retreaver-tags-bidding-ops/scripts/tags_bidding_ops.py list-tags

# Buyer Operations
python3 skills/retreaver-buyer-ops/scripts/buyer_ops.py list --per-page 25

# Publisher Operations
python3 skills/retreaver-publisher-ops/scripts/publisher_ops.py list --per-page 25

# Webhook Operations
python3 skills/retreaver-webhook-ops/scripts/webhook_ops.py templates

# Diagnostics & ClickHouse Rollups
python3 skills/retreaver-diagnostics-reporting/scripts/diag_reporting.py rtb-summary --group-by status
```

---

## Operational Invariants & Troubleshooting

1. **One Connection = One Company**: Every MCP OAuth grant is bound to whichever company your browser session was switched into when you clicked **Approve**. Always confirm with `account.whoami` (`/retreaver:status`) before writing.
2. **Always Dry-Run First**: Pass `dry_run: true` on `campaigns.manage`, `campaigns.routing_settings.manage`, `targets.manage`, and `affiliates.manage` to inspect field-level diffs before applying changes.
3. **`no-target` vs `expired` in RTB**:
   - **`no-target`**: Buyer disqualified due to missing `geo` state tag, cap exhaustion, closed business hours, or buyer webhook returning a non-matching bid code (e.g. CallGrid `code: 4004`).
   - **`expired`**: Buyer bid succeeded and reserved a slot (`ttl_seconds`), but the publisher never bridged the live phone call before the reservation expired.
4. **Numeric & Date Tag Registration**: Always register numeric/date tags via `tags.manage` (`retreaver-tags-bidding-ops`) so `<` and `>` operators evaluate numerically instead of lexicographically.

---

## Installation

```bash
git clone https://github.com/ArielleTolome/retreaver-mcp-skills.git
cd retreaver-mcp-skills
./install.sh
```

`./install.sh` installs all **9 skills** to `~/.agents/skills/` (linking into `~/.omp`, `~/.claude`, `~/.codex`, `~/.grok`, and `~/.hermes`) and installs all **10 `/retreaver:*` slash commands**.

---

## License

MIT License. See [LICENSE](LICENSE) for details.
