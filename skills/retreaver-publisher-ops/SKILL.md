---
name: retreaver-publisher-ops
description: Manage Retreaver publishers and affiliates, tracking numbers, postback keys (RTB and Data Writing), publisher payouts, and conversion groups.
metadata:
  role: operator
  allowed_tools: ["bash", "read", "edit", "write"]
---

## Role Contract

The `retreaver-publisher-ops` skill automates the configuration, provisioning, and ongoing maintenance of traffic sources (affiliates/publishers) on the Retreaver call tracking platform. The operator manages publisher profiles, assigns static and pooled tracking numbers, issues authenticated postback keys for Real-Time Bidding (RTB) and Call Data Writing, configures payout terms via Conversion Groups, and enforces Ping Shield anti-fraud rate limits.

Operations are executed via the Retreaver MCP server or the `scripts/publisher_ops.py` CLI wrapper backed by `/tmp/retreaver_client.py`.

## Strict Invariants

1. **Tag Token Format:** Tag assignments, match criteria, and overrides MUST use the strict triple angle bracket syntax `<<<key:value>>>` (e.g., `<<<affiliate_id:61956>>>`). Bare key-value pairs or single brackets are prohibited.
2. **Tag Prefixing on External Keys:** Every postback key issued to a publisher for RTB or Data Writing MUST define a `tag_prefix` ending with an underscore (e.g., `pub12_`) to prevent third-party parameters from clobbering internal routing keys (`campaign_id`, `buyer_id`, `revenue`).
3. **Dry-Run Validation:** Destructive actions (`delete`), financial payout modifications, or bulk number reassignments MUST be previewed first with `dry_run: true` before applying live changes.
4. **Business Hours Invariant:** When configuring weekly business hours on an affiliate, all 7 days of the week (`day_of_week` 0 through 6) MUST be accounted for, using valid 24-hour integer representations (`0` to `2400`).
5. **Strict JSON Output:** Scripts and automated invocations MUST emit valid JSON to stdout. Human-readable diagnostics or debug traces are restricted to stderr.

## Output Specification

All operator procedures and CLI scripts return responses adhering to this JSON schema:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["status", "data"],
  "properties": {
    "status": {
      "type": "string",
      "enum": ["ok", "dry_run", "error", "needs_clarification"]
    },
    "message": {
      "type": "string"
    },
    "data": {
      "type": "object",
      "properties": {
        "affiliate": { "type": "object" },
        "affiliates": { "type": "array", "items": { "type": "object" } },
        "postback_key": { "type": "object" },
        "postback_keys": { "type": "array", "items": { "type": "object" } },
        "number": { "type": "object" },
        "numbers": { "type": "array", "items": { "type": "object" } },
        "conversion_group": { "type": "object" },
        "conversion_groups": { "type": "array", "items": { "type": "object" } },
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
      "items": { "type": "string" }
    }
  },
  "additionalProperties": false
}
```

## Operational Procedures & MCP Tool Mapping

### 1. Publisher / Affiliate Management
- **List Affiliates:** Call MCP `affiliates.read` with `action: "index"`, `page`, `per_page`.
  ```bash
  python3 ~/.agents/skills/retreaver-publisher-ops/scripts/publisher_ops.py list --page 1 --per-page 25
  ```
- **Inspect Affiliate:** Call MCP `affiliates.read` with `action: "show"`, `affiliate_id: <ID>`.
  ```bash
  python3 ~/.agents/skills/retreaver-publisher-ops/scripts/publisher_ops.py show --affiliate-id 61956
  ```
- **Create Affiliate:** Call MCP `affiliates.manage` with `action: "create"`, `company_name`, `first_name`, `last_name`, `time_zone`.
  ```bash
  python3 ~/.agents/skills/retreaver-publisher-ops/scripts/publisher_ops.py create --company-name "Acme Media" --time-zone "Eastern Time (US & Canada)"
  ```
- **Update or Pause Affiliate:** Call MCP `affiliates.manage` with `action: "update"`, `affiliate_id`, and fields to modify (`paused: true/false`, `static_number_cap`).
  ```bash
  python3 ~/.agents/skills/retreaver-publisher-ops/scripts/publisher_ops.py update --affiliate-id 61956 --paused
  ```

### 2. Postback Keys (RTB & Data Writing)
- **Create RTB Key:** Call MCP `postback_keys.manage` with `action: "create"`, `postbackable_type: "Affiliate"`, `postbackable_id: <AFFILIATE_ID>`, `postback_action: "rtb"`.
  - Recommended defaults: `ttl_seconds: 15`, `timeout: 5.0`, `tag_prefix: "<prefix>_"`.
  ```bash
  python3 ~/.agents/skills/retreaver-publisher-ops/scripts/publisher_ops.py create-key \
    --postbackable-type Affiliate --postbackable-id 61956 \
    --postback-action rtb --name "Acme_Inbound_RTB" --tag-prefix "acme_"
  ```
- **Create Call Data Writing Key:** Call MCP `postback_keys.manage` with `action: "create"`, `postbackable_type: "Affiliate"`, `postbackable_id: <AFFILIATE_ID>`, `postback_action: "data_writing"`.
  - Set `start_seconds` (post-call edit window) and `end_seconds` (pre-call tag storage window).
- **List Postback Keys:** Call MCP `postback_keys.read` with `action: "index"`, `postbackable_type: "Affiliate"`, `postbackable_id: <AFFILIATE_ID>`.
  ```bash
  python3 ~/.agents/skills/retreaver-publisher-ops/scripts/publisher_ops.py list-keys \
    --postbackable-type Affiliate --postbackable-id 61956
  ```

### 3. Tracking Number Assignment & Number Pools
- **Assign Static Number to Affiliate:** Call MCP `numbers.manage` with `action: "update"` (or `"create"` with `campaign_id`), `affiliate_id: <AFFILIATE_ID>`, and `tag_list: "<<<affiliate_id:<ID>>>>"`.
- **Provision Affiliate Number Pool:** Call MCP `number_pools.manage` with `action: "create"`, `campaign_id: <CAMPAIGN_ID>`, `affiliate_id: <AFFILIATE_ID>`, `max_pool_size`, `buffer_seconds`.

### 4. Publisher Payouts & Conversion Groups
- **Inspect Payouts:** Call MCP `conversion_groups.read` with `action: "index"`, `conversionable_type: "Affiliate"`, `conversionable_id: <AFFILIATE_ID>`.
- **Set Publisher Payout Rule:** Call MCP `conversion_groups.manage` with `action: "create"`, `conversionable_type: "Affiliate"`, `conversionable_id: <AFFILIATE_ID>`, `conversion_type: "timer"`, `conversions: [{"seconds": 90, "payout": 45.00}]`.
