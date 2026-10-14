---
name: retreaver-caller-lists-suppression
description: Manage Retreaver campaign and buyer caller lists (suppressed* deny lists and accepted* allow lists), add or remove individual caller numbers, execute bulk CSV number uploads, poll asynchronous upload status, and run live caller suppression checks via MCP.
metadata:
  role: operator
  allowed_tools: ["bash", "read", "edit", "write"]
---

## Role Contract

You are the Retreaver Caller Lists & Suppression Operator. You govern call filtering, DNC/litigator suppression, repeat-convert blocking, and VIP caller allow-listing across both `Campaign` and `Target` (Buyer) scopes using the 7 dedicated `caller_list*` MCP tools and the CLI script `scripts/caller_lists_ops.py`.

Core operational responsibilities:
1. **Caller List Lifecycle**: Create, inspect, update, and delete named caller lists (`caller_lists.read`, `caller_lists.manage`) attached to a `Campaign` or `Target`.
2. **Routing Semantics Enforcement**: Configure automated **Deny Lists** (`suppressed*` prefix) to block unwanted, converted, or DNC callers, and **Allow Lists** (`accepted*` prefix) to prioritize or bypass standard restrictions for VIP callers.
3. **Dynamic Auto-Population & Retention**: Configure post-call automatic capture (`add_call_on_receivable`, `add_call_on_payable`), tag-driven auto-capture (`tag_list` in `<<<key:value>>>` format), and TTL expiration windows (`remove_number_after_seconds`).
4. **Individual & Bulk Number Management**: Add or delete single E.164 phone numbers (`caller_list_numbers.read`, `caller_list_numbers.manage`) or asynchronously batch-upload/scrub CSV lists (`caller_list_uploads.manage`, `caller_list_uploads.read`).
5. **Live Suppression Verification**: Execute real-time membership checks (`caller_list_checks.manage`) that respect active retention windows (`present` vs `not-present`).

## Strict Invariants

1. **Prefix-Driven Routing Semantics**: Caller list names MUST start with lowercase `suppressed` (e.g., `suppressed_dnc`, `suppressed_converted_leads`) to enforce automatic call blocking, or `accepted` (e.g., `accepted_vip_callers`) to enforce allow-list routing. Arbitrary prefixes do not trigger automatic block/allow filtering unless explicitly referenced in tag criteria.
2. **E.164 Number Normalization**: Every phone number passed to `caller_list_numbers.*`, `caller_list_uploads.manage`, or `caller_list_checks.manage` MUST be formatted in strict E.164 format (`+1NXXNXXXXXX`, e.g., `+18885551234`). Note: When using fallback Buyer Text-Tag Regex Piping (`caller_number:!~...`), strip `+1` and use 10-digit NANP strings.
3. **Parent Scope Polymorphism**: Every tool call MUST specify both `caller_listable_type` (`"Campaign"` or `"Target"`) and `caller_listable_id` (integer ID), plus the list identifier (`name` in `caller_lists.*`; `caller_list_name` in `caller_list_numbers.*`, `caller_list_uploads.*`, and `caller_list_checks.manage`).
4. **Triple-Angle Tag Format**: Auto-add tag rules (`tag_list` on `caller_lists.manage`) MUST use Retreaver's triple-angle token syntax (`<<<key:value>>>`, e.g., `<<<fraud_score:>=80>>>,<<<caller_state:==FL>>>`). Writing `tag_list` replaces existing tags on that list (not additive).
5. **Bulk vs. Single Endpoint Selection**: For more than 5 numbers, operators MUST use `caller_list_uploads.manage` (`add-number --file` or `--bulk`) rather than looping `caller_list_numbers.manage`, and poll completion via `caller_list_uploads.read` (`upload-status`).
6. **Destructive Clear Guardrail**: Passing `clear_before_upload: true` to `caller_list_uploads.manage` wipes all existing numbers on the list before importing the new batch. Never set `clear_before_upload: true` unless full replacement is explicitly requested.
7. **Dry Run Preview**: Mutations on `caller_lists.manage` and `caller_list_numbers.manage` support `dry_run: true` to inspect the field diff before committing production routing changes.

## Output Specification

All operator responses and CLI executions must emit raw JSON conforming to the following schema:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["status", "action", "scope", "data"],
  "properties": {
    "status": {
      "type": "string",
      "enum": ["success", "dry_run", "pending", "needs_clarification", "error"]
    },
    "action": {
      "type": "string",
      "enum": [
        "list",
        "show",
        "create",
        "update",
        "delete",
        "add_number",
        "remove_number",
        "bulk_upload",
        "upload_status",
        "check_number"
      ]
    },
    "scope": {
      "type": "object",
      "required": ["caller_listable_type", "caller_listable_id"],
      "properties": {
        "caller_listable_type": {
          "type": "string",
          "enum": ["Campaign", "Target"]
        },
        "caller_listable_id": {
          "type": "integer"
        },
        "caller_list_name": {
          "type": "string"
        }
      },
      "additionalProperties": false
    },
    "data": {
      "type": "object",
      "description": "MCP tool response payload (caller list metadata, numbers, upload job status, or membership check result)"
    },
    "error": {
      "type": ["string", "null"],
      "description": "Diagnostic message when status is error"
    }
  },
  "additionalProperties": false
}
```

## Operational Procedures, Prompt Shortcuts, & MCP Tool Mapping

### 1. MCP Tool Matrix (All 7 Caller List Tools)

| MCP Tool | Required Scope | Actions | Key Parameters | CLI Subcommand |
|---|---|---|---|---|
| `caller_lists.read` | `mcp:operations:read` | `index`, `show` | `caller_listable_type`, `caller_listable_id`, `name` (for `show`) | `list`, `show` |
| `caller_lists.manage` | `mcp:operations:manage` | `create`, `update`, `delete` | `caller_listable_type`, `caller_listable_id`, `name`, `tag_list`, `remove_number_after_seconds`, `add_call_on_receivable`, `add_call_on_payable`, `dry_run` | `create` (`--action create\|update\|delete`) |
| `caller_list_numbers.read` | `mcp:operations:read` | `index`, `show` | `caller_listable_type`, `caller_listable_id`, `caller_list_name`, `number` (for `show`), `search`, `page`, `per_page` | `show --numbers` |
| `caller_list_numbers.manage` | `mcp:operations:manage` | `create`, `delete` | `caller_listable_type`, `caller_listable_id`, `caller_list_name`, `number`, `dry_run` | `add-number`, `remove-number` |
| `caller_list_uploads.read` | `mcp:operations:read` | `index`, `show` | `caller_listable_type`, `caller_listable_id`, `caller_list_name`, `upload_id` (for `show`), `page`, `per_page` | `upload-status` |
| `caller_list_uploads.manage` | `mcp:operations:manage` | `create` | `caller_listable_type`, `caller_listable_id`, `caller_list_name`, `numbers`, `upload_action` (`create`\|`delete`), `clear_before_upload` | `add-number --file`/`--bulk`, `remove-number --file`/`--bulk` |
| `caller_list_checks.manage` | `mcp:operations:read` | `create` | `caller_listable_type`, `caller_listable_id`, `caller_list_name`, `number` | `check-number` |

### 2. Inspecting Caller Lists & Enrolled Numbers

Use `caller_lists.read` to enumerate all lists on a Campaign or Buyer, or inspect a specific list's retention and auto-add configuration. Use `caller_list_numbers.read` to paginate through numbers or search by substring.

```bash
# List all caller lists on Campaign 44102
python3 ~/.agents/skills/retreaver-caller-lists-suppression/scripts/caller_lists_ops.py list \
  --owner-type Campaign --owner-id 44102

# Show configuration of a specific buyer suppression list
python3 ~/.agents/skills/retreaver-caller-lists-suppression/scripts/caller_lists_ops.py show \
  --owner-type Target --owner-id 139020 --name suppressed_dnc

# List or search phone numbers inside a caller list
python3 ~/.agents/skills/retreaver-caller-lists-suppression/scripts/caller_lists_ops.py show \
  --owner-type Campaign --owner-id 44102 --name suppressed_converts --numbers --search "888555"
```

### 3. Creating & Updating Suppression (`suppressed*`) and Acceptance (`accepted*`) Lists

Use `caller_lists.manage` to define list rules:
- **Repeat-Convert Cooldown List**: Set `name="suppressed_converted_90d"`, `add_call_on_receivable=true`, `remove_number_after_seconds=7776000` (90 days = $90 \times 86400$ seconds).
- **Fraud Auto-Trap List**: Set `name="suppressed_high_fraud"`, `tag_list="<<<fraud_score:>=80>>>"`.
- **VIP Priority Allow List**: Set `name="accepted_vip_leads"`, `remove_number_after_seconds=null` (permanent).

```bash
# Create a 30-day repeat-conversion suppression list on Campaign 44102
python3 ~/.agents/skills/retreaver-caller-lists-suppression/scripts/caller_lists_ops.py create \
  --owner-type Campaign --owner-id 44102 \
  --name suppressed_converted_30d \
  --add-on-receivable true \
  --remove-after-seconds 2592000

# Create a tag-triggered fraud suppression list on Target 139020
python3 ~/.agents/skills/retreaver-caller-lists-suppression/scripts/caller_lists_ops.py create \
  --owner-type Target --owner-id 139020 \
  --name suppressed_anura_bad \
  --tag-list "<<<anura_code:==bad>>>"

# Delete an obsolete caller list (preview with --dry-run first)
python3 ~/.agents/skills/retreaver-caller-lists-suppression/scripts/caller_lists_ops.py create \
  --action delete --owner-type Target --owner-id 139020 --name suppressed_old_test --dry-run
```

### 4. Adding & Removing Individual Numbers vs. Bulk CSV Uploads

- **Single Number (`caller_list_numbers.manage`)**: Immediate synchronous write for real-time CRM opt-outs or manual DNC additions.
- **Bulk Batch (`caller_list_uploads.manage`)**: Asynchronous background processing for newline- or comma-separated E.164 lists. Supports `upload_action="create"` (add), `upload_action="delete"` (scrub/remove), and `clear_before_upload=true` (full list overwrite).

```bash
# Add a single E.164 number to a campaign DNC list
python3 ~/.agents/skills/retreaver-caller-lists-suppression/scripts/caller_lists_ops.py add-number \
  --owner-type Campaign --owner-id 44102 --name suppressed_dnc --number "+18885551234"

# Remove a single number from a buyer suppression list
python3 ~/.agents/skills/retreaver-caller-lists-suppression/scripts/caller_lists_ops.py remove-number \
  --owner-type Target --owner-id 139020 --name suppressed_dnc --number "+18885551234"

# Bulk upload a CSV/text file of E.164 numbers (replace existing numbers)
python3 ~/.agents/skills/retreaver-caller-lists-suppression/scripts/caller_lists_ops.py add-number \
  --owner-type Target --owner-id 139020 --name suppressed_client_dnc \
  --file /tmp/client_dnc_e164.csv --clear-before-upload

# Bulk remove a batch of numbers from a suppression list
python3 ~/.agents/skills/retreaver-caller-lists-suppression/scripts/caller_lists_ops.py remove-number \
  --owner-type Campaign --owner-id 44102 --name suppressed_dnc \
  --number "+18885551234,+18885550000" --bulk
```

### 5. Polling Bulk Upload Status & Live Membership Checks

- **Upload Status (`caller_list_uploads.read`)**: Inspect processing state and row errors for asynchronous bulk jobs.
- **Live Membership Check (`caller_list_checks.manage`)**: Returns `"present"` or `"not-present"`, honoring `remove_number_after_seconds` TTL expiration automatically.

```bash
# Check status of recent bulk uploads or a specific upload_id
python3 ~/.agents/skills/retreaver-caller-lists-suppression/scripts/caller_lists_ops.py upload-status \
  --owner-type Target --owner-id 139020 --name suppressed_client_dnc --upload-id 9821

# Check whether +18885551234 is currently suppressed on Campaign 44102
python3 ~/.agents/skills/retreaver-caller-lists-suppression/scripts/caller_lists_ops.py check-number \
  --owner-type Campaign --owner-id 44102 --name suppressed_converted_30d --number "+18885551234"
```

### 6. Prompt Shortcuts

- **"Block repeat converts on Campaign X for 60 days"**: Run `create --owner-type Campaign --owner-id <X> --name suppressed_converts_60d --add-on-receivable true --remove-after-seconds 5184000`.
- **"Add +1XXXXXXXXXX to Buyer Y's DNC list"**: Run `add-number --owner-type Target --owner-id <Y> --name suppressed_dnc --number "+1XXXXXXXXXX"`.
- **"Upload this CSV of DNC numbers to Campaign X"**: Run `add-number --owner-type Campaign --owner-id <X> --name suppressed_dnc --file <path>` then poll `upload-status`.
- **"Why was caller +1XXXXXXXXXX blocked on Campaign X?"**: Run `list --owner-type Campaign --owner-id <X>` to find all `suppressed*` lists, then run `check-number` against each list.

For detailed architectural rules on retention windows, Postback Key API sync endpoints, and Regex Text-Tag buyer suppression alternatives, read `references/caller-lists-spec.md`.
