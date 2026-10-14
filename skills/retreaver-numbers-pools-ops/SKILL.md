---
name: retreaver-numbers-pools-ops
description: Manage Retreaver tracking numbers (DIDs), dynamic number pools (DNI), lease/buffer sizing, surgical campaign overrides, SIP URI routing, and number-level caps.
metadata:
  role: operator
  allowed_tools: ["bash", "read", "edit", "write"]
---

## Role Contract

The `retreaver-numbers-pools-ops` skill manages the lifecycle, provisioning, attribution tagging, surgical campaign inheritance overrides, SIP URI routing, and Dynamic Number Insertion (DNI) pool sizing for Retreaver tracking numbers and number pools.

Operations are executed via the Retreaver MCP server (`numbers.read`, `numbers.manage`, `number_pools.read`, `number_pools.manage`) or the `scripts/numbers_pools_ops.py` CLI wrapper backed by `scripts/retreaver_client.py`.

Key operational domains:
- **Tracking Numbers (`numbers.read`, `numbers.manage`):** Inspect, provision, update, pause/resume, release, and stamp static context tags (`tag_list`) on toll-free and local DIDs.
- **Surgical Inheritance Overrides:** Control lock/unlock flags (`greeting_use_cs`, `routing_use_cs`, `timers_use_cs`, `conversions_use_cs`, `locked`) so individual placements inherit from their parent Campaign or execute custom standalone behavior.
- **Dynamic Number Pools (`number_pools.read`, `number_pools.manage`):** Configure `Retreaver.js` landing page number pools, size concurrency caps (`max_pool_size`, `reserve_size`), tune lease recycling windows (`buffer_seconds`, `max_lease_seconds`), and toggle visitor-level tracking (`per_visitor`) and Google Analytics attribution (`google_analytics`).
- **SIP URI Routing (`sip:...`) & Number-Level Caps:** Route inbound/outbound SIP traffic (`sip:+1[E164]@retreaver.sip.twilio.com` or `sip:endpoint@domain.com`) and enforce granular connection/conversion throttling schedules per tracking number.

## Strict Invariants

1. **Triple Angle Bracket Tag Format:** All static context tags written to `tag_list` on a number MUST use comma-separated exact-value `<<<key:value>>>` tokens (e.g., `<<<affiliate_id:61956>>>,<<<sub_id:tv_spot_1>>>`). Comparison operators are prohibited in `tag_list`. Passing `tag_list` replaces all existing tags on the number (non-additive); pass `""` to clear.
2. **DNI Pool Concurrency Sizing:** Number pool `max_pool_size` MUST satisfy $\text{Pool Size} \ge \text{Peak Concurrent Visitors in Lease Window} \times \text{Unique Attribute Factor}$. When `per_visitor: true` is enabled (required for Step-in IVR and native Google Analytics goals), every concurrent visitor leases a dedicated number.
3. **Local Number Reserve Sizing:** Local DID acquisition from carrier pools can take >1 second. When provisioning local number pools (`toll_free: false`) exposed to traffic spikes, `reserve_size` MUST be set $>0$ to pre-acquire standby inventory and prevent fallback overflow.
4. **Decommissioning & Release Quarantine:** Deleting a tracking number via `numbers.manage` (`action: "delete"`) releases it into a carrier cooling-off quarantine to drain residual caller traffic. Destructive releases and bulk pool capacity reductions MUST be previewed with `dry_run: true` first.
5. **Campaign Inheritance Lock Semantics:** By default, numbers inherit Greeting Prompts (`greeting_use_cs: true`), Routing (`routing_use_cs: true`), Timers (`timers_use_cs: true`), and Conversions (`conversions_use_cs: true`) from their parent Campaign. Unlocking any block (`false`) detaches that number from future parent Campaign edits for that block.
6. **Strict JSON Output:** All CLI invocations and operator actions MUST emit structured JSON to stdout and restrict diagnostics to stderr.

## Output Specification

All operator procedures and CLI scripts emit raw JSON conforming to this schema:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["status", "action", "data"],
  "properties": {
    "status": {
      "type": "string",
      "enum": ["ok", "dry_run", "validated", "proposal_required", "validation_failed", "denied", "error", "needs_clarification"]
    },
    "action": {
      "type": "string",
      "description": "Executed operation: list-numbers, show-number, update-number, list-pools, show-pool, create-pool, update-pool"
    },
    "data": {
      "type": "object",
      "properties": {
        "number": { "type": "object" },
        "numbers": { "type": "array", "items": { "type": "object" } },
        "number_pool": { "type": "object" },
        "number_pools": { "type": "array", "items": { "type": "object" } },
        "result": { "type": "object" },
        "diff": { "type": "object" },
        "read_meta": {
          "type": "object",
          "properties": {
            "page": { "type": "integer" },
            "per_page": { "type": "integer" },
            "total_pages": { "type": "integer" },
            "total_count": { "type": "integer" }
          }
        }
      }
    },
    "errors": {
      "type": "array",
      "items": { "type": "object" }
    },
    "error_details": {
      "type": "string"
    }
  },
  "additionalProperties": false
}
```

## Operational Procedures, Prompt Shortcuts, & MCP Tool Mapping

### 1. Tracking Number Inspection (`numbers.read`)
- **List Numbers:** Call MCP `numbers.read` with `action: "index"`, `page`, `per_page`.
  ```bash
  python3 ~/.agents/skills/retreaver-numbers-pools-ops/scripts/numbers_pools_ops.py list-numbers --page 1 --per-page 25
  ```
- **Show Number:** Call MCP `numbers.read` with `action: "show"`, `number_id: <ID>`.
  ```bash
  python3 ~/.agents/skills/retreaver-numbers-pools-ops/scripts/numbers_pools_ops.py show-number --number-id 481920
  ```

### 2. Tracking Number Updates, Tagging & Surgical Overrides (`numbers.manage`)
- **Update Number Attributes / Tags / Pause State:** Call MCP `numbers.manage` with `action: "update"`, `number_id`, and target fields (`name`, `campaign_id`, `affiliate_id`, `tag_list`, `paused`, `target_number`, `greeting_use_cs`, `routing_use_cs`, `timers_use_cs`, `conversions_use_cs`, `extensions_enabled`, `locked`, `dry_run`).
  ```bash
  # Stamp static attribution tags and assign to publisher
  python3 ~/.agents/skills/retreaver-numbers-pools-ops/scripts/numbers_pools_ops.py update-number \
    --number-id 481920 \
    --affiliate-id 61956 \
    --tag-list "<<<affiliate_id:61956>>>,<<<channel:radio>>>,<<<sub_id:morning_drive>>>" \
    --dry-run

  # Pause a tracking number or unlock campaign routing inheritance
  python3 ~/.agents/skills/retreaver-numbers-pools-ops/scripts/numbers_pools_ops.py update-number \
    --number-id 481920 --paused true --routing-use-cs false
  ```

### 3. Dynamic Number Pool Inspection & Management (`number_pools.read`, `number_pools.manage`)
- **List Number Pools:** Call MCP `number_pools.read` with `action: "index"`, `page`, `per_page`.
  ```bash
  python3 ~/.agents/skills/retreaver-numbers-pools-ops/scripts/numbers_pools_ops.py list-pools --page 1 --per-page 25
  ```
- **Show Number Pool:** Call MCP `number_pools.read` with `action: "show"`, `number_pool_id: <ID>`.
  ```bash
  python3 ~/.agents/skills/retreaver-numbers-pools-ops/scripts/numbers_pools_ops.py show-pool --pool-id 9102
  ```
- **Create Number Pool:** Call MCP `number_pools.manage` with `action: "create"`, `campaign_id`, and pool sizing parameters (`affiliate_id`, `max_pool_size`, `reserve_size`, `buffer_seconds`, `max_lease_seconds`, `toll_free`, `country`, `area_code_id`, `per_visitor`, `google_analytics`, `google_analytics_account`, `hide_embedded_access`, `dry_run`).
  ```bash
  python3 ~/.agents/skills/retreaver-numbers-pools-ops/scripts/numbers_pools_ops.py create-pool \
    --campaign-id 14200 \
    --affiliate-id 61956 \
    --max-pool-size 25 \
    --reserve-size 3 \
    --buffer-seconds 120 \
    --max-lease-seconds 900 \
    --toll-free true \
    --per-visitor true
  ```
- **Update Number Pool:** Call MCP `number_pools.manage` with `action: "update"`, `number_pool_id: <ID>`, and updated sizing or lease parameters.
  ```bash
  python3 ~/.agents/skills/retreaver-numbers-pools-ops/scripts/numbers_pools_ops.py update-pool \
    --pool-id 9102 \
    --max-pool-size 50 \
    --buffer-seconds 180 \
    --max-lease-seconds 600 \
    --dry-run
  ```

### 4. SIP URI Routing & Number-Level Throttling
- **Inbound SIP Termination:** Any active Retreaver tracking number accepts inbound SIP INVITEs worldwide when addressed in E.164 format (`+1NXXNXXXXXX`):
  - Digest Credentials: `sip:+1[E164Number]@retreaver.sip.twilio.com`
  - IP Whitelisted: `sip:+1[E164Number]@retreaver-ip.sip.twilio.com`
- **Outbound SIP Forwarding:** Buyers/Targets can dial SIP endpoints using `sip:endpoint@domain.com` (with dynamic token interpolation such as `sip:[buyer_id]@[tag_company].com`) and automatic context headers (`X-PH-RetreaverUUID`, `X-PH-RetreaverKey`, `X-PH-RetreaverAFID`, `X-PH-RetreaverSID`).
- **Number-Level Caps:** Configure 1-minute to full-day Business Hours time blocks on individual tracking numbers to cap either **Connections** (immediate bridge count) or **Conversions** (qualified payout count) per window.

### 5. Prompt Shortcuts
- *"List all tracking numbers and check which ones are paused"* -> `numbers_pools_ops.py list-numbers`
- *"Inspect number 481920 and see its tags and campaign inheritance locks"* -> `numbers_pools_ops.py show-number --number-id 481920`
- *"Stamp sub_id=google_ppc and affiliate_id=61956 on number 481920"* -> `numbers_pools_ops.py update-number --number-id 481920 --affiliate-id 61956 --tag-list "<<<affiliate_id:61956>>>,<<<sub_id:google_ppc>>>"`
- *"Create a toll-free DNI number pool for campaign 14200 with max 30 numbers, 120s buffer, and 15m max lease"* -> `numbers_pools_ops.py create-pool --campaign-id 14200 --max-pool-size 30 --buffer-seconds 120 --max-lease-seconds 900 --toll-free true --per-visitor true`

For full DNI concurrency math, SIP header specifications, fallback overflow tagging, and surgical override architecture, read `references/numbers-pools-spec.md`.
