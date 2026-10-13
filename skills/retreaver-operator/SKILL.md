---
name: retreaver-operator
description: Master operator skill for Retreaver call tracking and Real-Time Bidding (RTB) platform. Automates setting up buyers (targets), publishers (affiliates), webhooks/timers, diagnosing failed RTB pings and APIs, and generating call/revenue performance reports via the Retreaver MCP API.
metadata:
  role: operator
  allowed_tools: ["bash", "read", "edit", "write"]
---

## Role Contract
The Retreaver Operator acts as the autonomous systems administrator and campaign manager for the Retreaver platform on behalf of Bull Market Ventures (Company ID: 299115). It executes commands across 5 specialized domains:
1. **Buyer (Target) Management**: Creation, routing, priority, weight, business hours, and caps.
2. **Publisher (Affiliate) Management**: Onboarding, postback keys, number assignment, and payout rules.
3. **Webhook & Integration Configuration**: Passthrough timers, configurator templates, and test firing.
4. **RTB Diagnostics & Troubleshooting**: Ping/post analysis, `no-target` & `expired` resolution, and buyer API failures.
5. **Analytics & Performance Reporting**: Real-time ClickHouse rollups, call logs, and revenue metrics.

## Strict Invariants
1. **Safety & Dry Run**: Destructive mutations (`targets.manage`, `affiliates.manage`, `webhooks.manage`) must support `dry_run: true` previewing diffs before execution.
2. **E.164 Compliance**: All telephone numbers must adhere to E.164 format (e.g. `+1XXXXXXXXXX`).
3. **Tag Invariance**: Numeric and Date comparisons must only be used on registered tags; unregistered tags evaluate lexicographically.
4. **Token Resiliency**: All MCP calls route through `/tmp/retreaver_client.py` or `~/.agents/skills/retreaver-operator/scripts/retreaver_cli.py`, which auto-refreshes OAuth Bearer tokens without user intervention.
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

## Specialized Operator Sub-Skills
When executing dedicated workflows, delegate to or reference the modular child skills:
- **`retreaver-buyer-ops`**: `~/.agents/skills/retreaver-buyer-ops/SKILL.md` (Targets, Caps, Hours, Geo Tags, Caller Lists).
- **`retreaver-publisher-ops`**: `~/.agents/skills/retreaver-publisher-ops/SKILL.md` (Affiliates, Postback Keys, Number Pools, Payouts).
- **`retreaver-webhook-ops`**: `~/.agents/skills/retreaver-webhook-ops/SKILL.md` (Timers, Configurator, CallGrid/Anura Templates, Test-Fires).
- **`retreaver-diagnostics-reporting`**: `~/.agents/skills/retreaver-diagnostics-reporting/SKILL.md` (RTB Logs, Call Detail Records, Drill-Down Rollups, CSV Exports).

## Unified CLI Commands (`scripts/retreaver_cli.py`)

### 1. Account Context
```bash
python3 ~/.agents/skills/retreaver-operator/scripts/retreaver_cli.py whoami
```

### 2. Buyer Management ("Set up this buyer")
```bash
# Create Buyer with priority and weight
python3 ~/.agents/skills/retreaver-operator/scripts/retreaver_cli.py buyer create \
  --name "Alpha Healthcare" --number "+18005550199" --priority 1 --weight 100 --timeout 30

# Set Concurrency and Daily Caps
python3 ~/.agents/skills/retreaver-operator/scripts/retreaver_cli.py buyer caps \
  --target-id 148422 --concurrency 5 --daily 100
```

### 3. Publisher Management ("Set up this publisher")
```bash
# Create Publisher
python3 ~/.agents/skills/retreaver-operator/scripts/retreaver_cli.py publisher create \
  --name "LeadGen Partners" --email "leads@partner.com"
```

### 4. Webhook Management ("Add this webhook")
```bash
# List templates
python3 ~/.agents/skills/retreaver-operator/scripts/retreaver_cli.py webhook templates

# Test-fire webhook
python3 ~/.agents/skills/retreaver-operator/scripts/retreaver_cli.py webhook test-fire --webhook-id 123786
```

### 5. RTB Diagnostics ("Check why it is not working")
```bash
# Analyze last 15 minutes of RTB inbounds
python3 ~/.agents/skills/retreaver-operator/scripts/retreaver_cli.py rtb-diag --minutes 15
```

### 6. Analytics & Stats ("Give me the stats on today")
```bash
# Pull call & revenue rollup for today
python3 ~/.agents/skills/retreaver-operator/scripts/retreaver_cli.py stats --window today
```
