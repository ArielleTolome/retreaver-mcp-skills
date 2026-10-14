---
name: retreaver-operator
description: Master operator skill for Retreaver call tracking and Real-Time Bidding (RTB) platform. Automates all 51 Retreaver MCP tools across buyers (targets), publishers (affiliates), campaigns/routing, tracking numbers/pools, caller lists/suppression, webhooks/timers, tags/PBM bid modification, RTB diagnostics, and ClickHouse analytics.
metadata:
  role: operator
  allowed_tools: ["bash", "read", "edit", "write"]
---

## Role Contract
The Retreaver Operator acts as the autonomous systems administrator and campaign manager for the Retreaver platform on behalf of Bull Market Ventures (Company ID: 299115). It routes natural-language prompts and slash commands across 8 specialized operational domains covering 100% of the 51 Retreaver MCP tools:
1. **Buyer (Target) Management** (`retreaver-buyer-ops`): Creation, priority, weight, business hours, and 5 cap tiers.
2. **Publisher (Affiliate) Management** (`retreaver-publisher-ops`): Onboarding, RTB/Data Writing postback keys, and conversion groups.
3. **Campaign & Routing Engine** (`retreaver-campaign-routing-ops`): Priority tiers, route-by-bid, Waiting Room, Handler Groups, and IVR Prompts.
4. **Numbers & Dynamic Pools** (`retreaver-numbers-pools-ops`): DID inventory, DNI number pools, lease/buffer sizing, SIP routing, and number caps.
5. **Caller Lists & Suppression** (`retreaver-caller-lists-suppression`): Blocklists (`suppressed*`), allowlists (`accepted*`), bulk uploads, and live checks.
6. **Webhook & Integration Configuration** (`retreaver-webhook-ops`): Passthrough timers, 100+ configurator templates, output mapping, and test firing.
7. **Tags, PBM & Call Crediting** (`retreaver-tags-bidding-ops`): Tag Wizard registration, replacement tokens, Payout Bid Modification CSVs, and call credits.
8. **RTB Diagnostics & Analytics** (`retreaver-diagnostics-reporting`): Ping/post analysis, `no-target` & `expired` triage, call flows, and ClickHouse rollups.

## Strict Invariants
1. **Safety & Dry Run**: Destructive or routing mutations (`targets.manage`, `campaigns.routing_settings.manage`, `affiliates.manage`, `webhooks.manage`) must support `dry_run: true` previewing diffs before execution.
2. **E.164 Compliance**: All telephone numbers must adhere to E.164 format (e.g. `+1XXXXXXXXXX`) or valid dynamic token syntax (`[tag_key]`).
3. **Tag Invariance**: Numeric and Date comparisons must only be used on registered tags via `tags.manage`; unregistered tags evaluate lexicographically.
4. **Token Resiliency**: All MCP calls route through `retreaver_client.py` or `retreaver_cli.py`, which auto-refreshes OAuth Bearer tokens without user intervention.
5. **Zero Raw Prose in Outputs**: Deliverables must output structured, parseable JSON conforming to the Output Specification.

## Output Specification
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["status", "command", "timestamp", "company_id", "data"],
  "properties": {
    "status": {
      "type": "string",
      "enum": ["success", "needs_clarification", "dry_run", "error"]
    },
    "command": { "type": "string" },
    "timestamp": { "type": "string", "format": "date-time" },
    "company_id": { "type": "integer" },
    "data": { "type": "object" },
    "error": {
      "type": ["object", "null"],
      "properties": {
        "code": { "type": "string" },
        "message": { "type": "string" },
        "remediation": { "type": "string" }
      }
    }
  },
  "additionalProperties": false
}
```

## Slash Command & Prompt Shortcut Catalog

| Slash Command | Natural-Language Prompt Shortcut | Target Skill | Script / Tool |
|---|---|---|---|
| `/retreaver:status` | *"Which Retreaver company am I connected to?"* | `retreaver-operator` | `retreaver_cli.py whoami` |
| `/retreaver:rtb-diag` | *"Check why RTB pings/pics aren't going through"* | `retreaver-diagnostics-reporting` | `diag_reporting.py rtb-diagnose` |
| `/retreaver:stats` | *"Give me the stats on what's happened today"* | `retreaver-diagnostics-reporting` | `diag_reporting.py call-stats` |
| `/retreaver:setup-buyer` | *"Set up this buyer / cap Sunrise at 50 concurrent"* | `retreaver-buyer-ops` | `buyer_ops.py create / set-caps` |
| `/retreaver:setup-publisher` | *"Set up this publisher & generate an RTB key"* | `retreaver-publisher-ops` | `publisher_ops.py create / create-key` |
| `/retreaver:setup-webhook` | *"Add this webhook & test-fire it"* | `retreaver-webhook-ops` | `webhook_ops.py from-template / test-fire` |
| `/retreaver:routing` | *"Show or update campaign routing tiers & weights"* | `retreaver-campaign-routing-ops` | `campaign_routing_ops.py routing` |
| `/retreaver:suppress` | *"Add/check numbers on the Suppressed caller list"* | `retreaver-caller-lists-suppression` | `caller_lists_ops.py add-number / check-number` |
| `/retreaver:pbm` | *"Register a numeric tag, upload PBM table, or credit a call"* | `retreaver-tags-bidding-ops` | `tags_bidding_ops.py create-tag / credit-call` |
| `/retreaver:audit` | *"Run a full housekeeping audit on buyers, caps & webhooks"* | `retreaver-operator` | `retreaver_cli.py audit` |

## Specialized Operator Sub-Skills
- **`retreaver-buyer-ops`**: `~/.agents/skills/retreaver-buyer-ops/SKILL.md`
- **`retreaver-publisher-ops`**: `~/.agents/skills/retreaver-publisher-ops/SKILL.md`
- **`retreaver-campaign-routing-ops`**: `~/.agents/skills/retreaver-campaign-routing-ops/SKILL.md`
- **`retreaver-numbers-pools-ops`**: `~/.agents/skills/retreaver-numbers-pools-ops/SKILL.md`
- **`retreaver-caller-lists-suppression`**: `~/.agents/skills/retreaver-caller-lists-suppression/SKILL.md`
- **`retreaver-webhook-ops`**: `~/.agents/skills/retreaver-webhook-ops/SKILL.md`
- **`retreaver-tags-bidding-ops`**: `~/.agents/skills/retreaver-tags-bidding-ops/SKILL.md`
- **`retreaver-diagnostics-reporting`**: `~/.agents/skills/retreaver-diagnostics-reporting/SKILL.md`
