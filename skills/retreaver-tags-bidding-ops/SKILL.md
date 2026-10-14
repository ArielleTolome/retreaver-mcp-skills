---
name: retreaver-tags-bidding-ops
description: Manage Retreaver company tag catalogs (String, Numeric, Date, DateTime, Boolean), replacement tokens, Payout Bid Modification (PBM) CSV bid-shading tables, and retroactive call crediting / revenue adjustments.
metadata:
  role: operator
  allowed_tools: ["bash", "read", "edit", "write"]
---

## Role Contract

The `retreaver-tags-bidding-ops` skill governs four foundational data, bidding, and financial adjustment subsystems in Retreaver:
1. **Company Tag Catalog (`tags.read`, `tags.manage`):** Define and maintain persisted tag key schemas (`Tags::Types::String`, `Tags::Types::Numeric`, `Tags::Types::Date`, `Tags::Types::DateTime`, `Tags::Types::Boolean`), AI Analyst extraction prompts (`ai_prompt`), IVR prompt flags, and reporting visibility.
2. **Replacement Token Discovery (`tags.replacement_tokens.read`):** Inspect all built-in system tokens, custom company tags, and campaign-scoped integration tokens (`[token]`) before authoring webhook URLs, SIP headers, prompts, or PBM tables.
3. **Payout Bid Modification / Bid Shading (`payout_bid_modification_tables.read`, `payout_bid_modification_tables.manage`):** Upload, inspect, version, and activate in-memory CSV rule sets that dynamically shade publisher payouts on RTB pings using deterministic SHA-256 hash bucketing (`0`–`9999`).
4. **Call Crediting & Revenue Adjustments (`calls.manage`):** Retroactively adjust call `revenue`, `payout`, `receivable`, `payable`, and `session_notes` on individual call UUIDs.

Operations execute via the Retreaver MCP server or the `scripts/tags_bidding_ops.py` CLI wrapper backed by `scripts/retreaver_client.py`.

## Strict Invariants

1. **Pre-Registration of Non-String Tags:** Numeric (`<`, `<=`, `>`, `>=`), Date, DateTime, and Boolean tags MUST be registered in the company Tag Catalog (`tags.manage`) with their exact `Tags::Types::*` class prior to routing evaluation. Unregistered numeric tags evaluate as ASCII strings (`"1000"` < `"200"`), silently breaking numeric threshold routing and bid rules.
2. **Tag Key Naming Discipline:** Tag keys (`key`) MUST contain only lowercase ASCII letters, digits, and underscores (`^[a-z0-9_]+$`).
3. **PBM Immutability & Single Active Table:** Once uploaded via `payout_bid_modification_tables.manage` (`action: "create"`), a table's `csv_data`, `salt`, and `table_version` are immutable. Modifying rules requires uploading a new table. Only `active` can be toggled via `action: "update"`, and activating a table automatically deactivates the previously active table for that campaign.
4. **PBM CSV Structural Rules:**
   - Maximum 1,000 rows and 1 MB per CSV upload; evaluated top-to-bottom (**first matching rule wins**).
   - Mandatory columns: `rule_id` (audit identifier) and `payout_pct` (integer percentage e.g. `70`, or literal `current` to leave payout unmodified).
   - Platform entities in PBM columns MUST use `system_affiliate_id`, `system_campaign_id`, `system_target_id`, or `system_number_id` (never untrusted client-supplied `affiliate_id`).
   - Comparison operators (`==`, `!=`, `=~`, `!~`, `>`, `>=`, `<`, `<=`) belong inside cell values, NEVER in column headers. Duplicate column headers (e.g., two `pbm_bucket` or two `revenue` columns) are ANDed together to express ranges.
5. **Call Crediting Side Effects (`calls.manage`):**
   - Adjusting `revenue` immediately recalculates and impacts active **Buyer volume caps**.
   - Setting `revenue > 0` automatically sets `receivable: true` and **fires any previously unfired conversion webhooks** for that call. Setting `payout > 0` automatically sets `payable: true`. Setting `0` clears the monetary amount.
6. **Dry-Run Mandate:** All destructive mutations (`delete` on tags/PBM tables) and financial adjustments (`calls.manage`, PBM activation) SHOULD be previewed with `dry_run: true` (`--dry-run`) before live execution when impact is uncertain.
7. **Strict JSON Output:** CLI executions emit structured JSON to `stdout`; diagnostics are restricted to `stderr`.

## Output Specification

All operator workflows and `scripts/tags_bidding_ops.py` commands return raw JSON conforming to the Retreaver MCP read/write envelope schema:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["status", "action"],
  "properties": {
    "status": {
      "type": "string",
      "enum": [
        "ok",
        "validated",
        "dry_run",
        "proposal_required",
        "validation_failed",
        "denied",
        "response_too_large"
      ]
    },
    "action": {
      "type": "string",
      "description": "MCP tool action executed (e.g. tags.create, payout_bid_modification_tables.update, calls.update)"
    },
    "result": {
      "type": "object",
      "description": "Affected resource or query payload (tags, replacement_tokens, payout_bid_modification_tables, call)"
    },
    "diff": {
      "type": "object",
      "description": "Field-by-field {from, to} preview returned when dry_run is true"
    },
    "read_meta": {
      "type": "object",
      "properties": {
        "page": { "type": "integer" },
        "per_page": { "type": "integer" },
        "total_pages": { "type": "integer" },
        "total_count": { "type": "integer" }
      }
    },
    "errors": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "field": { "type": "string" },
          "code": { "type": "string" },
          "message": { "type": "string" }
        }
      }
    }
  },
  "additionalProperties": true
}
```

## Operational Procedures, Prompt Shortcuts, & MCP Tool Mapping

### 1. Tag Catalog Management (`tags.read`, `tags.manage`)

- **List or Inspect Tag Keys:**
  - **MCP Tool:** `tags.read` (`action: "index"` with `page`, `per_page`; or `action: "show"` with `tag_id`)
  - **CLI:**
    ```bash
    # List first 50 tags in company catalog
    python3 ~/.agents/skills/retreaver-tags-bidding-ops/scripts/tags_bidding_ops.py list-tags --page 1 --per-page 50

    # Inspect a specific tag definition by ID
    python3 ~/.agents/skills/retreaver-tags-bidding-ops/scripts/tags_bidding_ops.py list-tags --tag-id 412
    ```

- **Create, Update, or Delete a Tag Definition:**
  - **MCP Tool:** `tags.manage`
    - `action`: `"create"`, `"update"`, or `"delete"`
    - `tag_id`: Integer ID (required for `update` / `delete`)
    - `key`: Lowercase snake_case identifier (e.g., `credit_score`, `age`, `is_homeowner`)
    - `type`: One of:
      - `"Tags::Types::String"` (default free-text / regex matching)
      - `"Tags::Types::Numeric"` (decimal/integer math comparisons)
      - `"Tags::Types::Date"` (`YYYY-MM-DD` date comparisons)
      - `"Tags::Types::DateTime"` (timestamp comparisons)
      - `"Tags::Types::Boolean"` (`true`/`false` flags)
    - `ai_prompt`: Custom instruction for AI Analyst post-call tag extraction
    - `prompt_enabled`: Boolean for IVR DTMF prompt binding
    - `acceptable_tags_enabled`: Boolean restricting tag to predefined values
    - `values_report`: Boolean enabling breakdown in Tag Values Report
    - `color`: Hex or named UI color string
    - `dry_run`: Preview diff without applying
  - **CLI:**
    ```bash
    # Create a Numeric tag for RTB bid or credit score filtering
    python3 ~/.agents/skills/retreaver-tags-bidding-ops/scripts/tags_bidding_ops.py create-tag \
      --action create --key credit_score --type numeric --values-report true

    # Create a Boolean tag with an AI Analyst prompt
    python3 ~/.agents/skills/retreaver-tags-bidding-ops/scripts/tags_bidding_ops.py create-tag \
      --action create --key medicare_part_ab --type boolean \
      --ai-prompt "Did the caller confirm enrollment in both Medicare Part A and Part B?"

    # Update an existing tag (dry-run preview)
    python3 ~/.agents/skills/retreaver-tags-bidding-ops/scripts/tags_bidding_ops.py create-tag \
      --action update --tag-id 412 --values-report true --dry-run
    ```

### 2. Replacement Token Discovery (`tags.replacement_tokens.read`)

- **Inspect Available `[token]` Placeholders:**
  - **MCP Tool:** `tags.replacement_tokens.read` (`action: "index"`, optional `campaign_id`)
  - Returns system tokens (e.g., `[caller_number]`, `[uuid]`, `[revenue]`, `[payout]`), company custom tags, and campaign-specific integration tokens with data types and sample matched values.
  - **CLI:**
    ```bash
    # List company-wide replacement tokens
    python3 ~/.agents/skills/retreaver-tags-bidding-ops/scripts/tags_bidding_ops.py list-tokens

    # Include campaign-specific integration and static custom tokens
    python3 ~/.agents/skills/retreaver-tags-bidding-ops/scripts/tags_bidding_ops.py list-tokens --campaign-id 8840
    ```

### 3. Payout Bid Modification (PBM) Rule Tables (`payout_bid_modification_tables.read`, `payout_bid_modification_tables.manage`)

- **List or Show Campaign PBM Tables:**
  - **MCP Tool:** `payout_bid_modification_tables.read` (`action: "index"` or `"show"`, `campaign_id`, optional `id`)
  - **CLI:**
    ```bash
    # List all uploaded PBM tables for campaign 8840 (newest first)
    python3 ~/.agents/skills/retreaver-tags-bidding-ops/scripts/tags_bidding_ops.py list-pbm --campaign-id 8840

    # Show full PBM table including raw csv_data
    python3 ~/.agents/skills/retreaver-tags-bidding-ops/scripts/tags_bidding_ops.py list-pbm --campaign-id 8840 --id 19
    ```

- **Upload, Activate, or Delete a PBM Rule Table:**
  - **MCP Tool:** `payout_bid_modification_tables.manage`
    - `action`: `"create"` (upload new CSV), `"update"` (toggle `active` only), `"delete"`
    - `campaign_id`: Target campaign integer ID
    - `id`: PBM table ID (required on `update` and `delete`)
    - `csv_data`: Full CSV string on `create`
    - `salt`: Hash salt for deterministic 0–9999 bucketing (`SHA256("<salt>:<call_uuid>")[0..3].hex_to_int() % 10000`)
    - `table_version`: Optional campaign-unique version number on `create`
    - `active`: Boolean (`true` activates this table and deactivates any prior active table on the campaign)
  - **CLI:**
    ```bash
    # Upload and immediately activate a new PBM CSV table from a file
    python3 ~/.agents/skills/retreaver-tags-bidding-ops/scripts/tags_bidding_ops.py activate-pbm \
      --action create --campaign-id 8840 --csv-file /tmp/pbm_rules.csv \
      --salt "acme_2026_q4" --table-version 3 --active true

    # Activate an existing PBM table version (deactivates current active table)
    python3 ~/.agents/skills/retreaver-tags-bidding-ops/scripts/tags_bidding_ops.py activate-pbm \
      --action update --campaign-id 8840 --id 19 --active true

    # Deactivate a PBM table (dry-run preview)
    python3 ~/.agents/skills/retreaver-tags-bidding-ops/scripts/tags_bidding_ops.py activate-pbm \
      --action update --campaign-id 8840 --id 19 --active false --dry-run
    ```

### 4. Call Crediting & Revenue Adjustments (`calls.manage`)

- **Credit or Adjust a Call Record:**
  - **MCP Tool:** `calls.manage`
    - `action`: `"update"`
    - `uuid`: Call UUID string
    - `revenue`: Numeric buyer revenue (`>0` marks call `receivable: true` and updates Buyer caps; `0` clears revenue)
    - `payout`: Numeric publisher payout (`>0` marks call `payable: true`; `0` clears payout)
    - `receivable`: Boolean (`true` triggers previously unfired conversion webhooks)
    - `payable`: Boolean
    - `session_notes`: Audit note explaining why the call was credited or adjusted
    - `dry_run`: Boolean preview
  - **CLI:**
    ```bash
    # Preview crediting a call with $65 revenue and $45 payout
    python3 ~/.agents/skills/retreaver-tags-bidding-ops/scripts/tags_bidding_ops.py credit-call \
      --uuid "66b905ef-bc03-420e-ad43-e8eeae03918f" \
      --revenue 65.00 --payout 45.00 \
      --session-notes "CRM manual conversion match ticket #409" --dry-run

    # Zero out disputed buyer revenue and publisher payout
    python3 ~/.agents/skills/retreaver-tags-bidding-ops/scripts/tags_bidding_ops.py credit-call \
      --uuid "66b905ef-bc03-420e-ad43-e8eeae03918f" \
      --revenue 0 --payout 0 --receivable false --payable false \
      --session-notes "Disputed duplicate lead return"
    ```

### Prompt Shortcuts

| User Intent | Mapped Command / Procedure |
| :--- | :--- |
| *"List all tags in our Retreaver account"* | `tags_bidding_ops.py list-tags` (`tags.read` action `index`) |
| *"Register `bid_amount` as a numeric tag"* | `tags_bidding_ops.py create-tag --key bid_amount --type numeric` (`tags.manage` action `create`) |
| *"What replacement tokens can I use in campaign 123?"* | `tags_bidding_ops.py list-tokens --campaign-id 123` (`tags.replacement_tokens.read`) |
| *"Show the active PBM bid shading rules on campaign 123"* | `tags_bidding_ops.py list-pbm --campaign-id 123` then `--id <active_id>` |
| *"Roll back campaign 123 to PBM table 14"* | `tags_bidding_ops.py activate-pbm --action update --campaign-id 123 --id 14 --active true` |
| *"Credit call UUID `abc-...` for $50 revenue and $35 payout"* | `tags_bidding_ops.py credit-call --uuid abc-... --revenue 50 --payout 35` (`calls.manage`) |

For detailed PBM SHA-256 bucket math, CSV comparator syntax, tag type evaluation rules, and call crediting webhook/cap side effects, read `references/tags-bidding-spec.md`.
