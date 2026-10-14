---
name: retreaver-campaign-routing-ops
description: Manage Retreaver campaigns, call routing matrices (menu_options_attributes, priority tiers, weights, locked/disabled rows, route-by-bid, route-by-performance), Waiting Room queues, Handler/Buyer Groups (target_groups), and IVR Prompts/Greetings.
metadata:
  role: operator
  allowed_tools: ["bash", "read", "edit", "write"]
---

## Role Contract
The `retreaver-campaign-routing-ops` skill orchestrates Retreaver Campaigns, nested Call Routing trees, Waiting Room hold queues, Handler/Buyer Groups (`target_groups`), and polymorphic IVR Prompts (`prompts`). It executes operations via the Retreaver MCP server or the companion CLI `scripts/campaign_routing_ops.py`.

Core operational domains:
- **Campaign Lifecycle & Toggles:** Create, inspect, update, pause, and resume campaigns; configure repeat-caller routing (`repeat_caller_type`, `new_target_rolling_reset_days`), call recording, deduplication windows, and Geo Data inference (`use_carrier_geo_information`, `use_caller_number_geo_information`).
- **Call Routing Matrix:** Configure `menu_options_attributes` (DTMF keypress branches, default `-1` routes, `-10` unclear-intent fallbacks, and spoken voice `topic` routes) and nested `menu_options_targets_attributes` routing rows (priority tiers, weights, `locked`, `disabled`, `enable_route_by_bid`, and EPC `enable_route_by_performance`).
- **Waiting Room Queueing:** Configure `waiting_room_seconds` and `waiting_room_tries` to hold callers and re-poll buyers every 5 seconds when no endpoint matches on the initial sweep.
- **Handler / Buyer Groups (`target_groups`):** Create, inspect, update, pause/resume, and duplicate buyer groups; manage group-wide concurrency caps, `cap_trigger`, and cross-buyer company deduplication (`dedupe_as_company`).
- **IVR Prompts & Greetings (`prompts`):** Manage TTS greetings, hold music presets, whispers, ZIP collection prompts, and speech-enabled press-or-say prompts across `Campaign`, `Target`, and `Number` resources.

## Strict Invariants
1. **Read-Before-Write on Routing Rows:** `campaigns.routing_settings.manage` uses Rails nested attributes (`menu_options_attributes` -> `menu_options_targets_attributes`) matched by `id`. Omitting an `id` creates a duplicate record; passing `_destroy: true` deletes it. Operators MUST invoke `campaigns.routing_settings.read` first to obtain current option and row `id` values before mutating existing routing tables.
2. **Per-Row Priority/Weight Unlock Requirement:** Setting `priority` or `weight` on a campaign routing row (`menu_options_targets_attributes`) is ignored if `locked: true`. You MUST set `locked: false` on the routing row for campaign-specific priority or weight overrides to take effect.
3. **Target Group Full-Membership Replacement:** In `target_groups.manage`, passing `target_ids` **replaces the entire group membership list**. Always call `target_groups.read` (`action: "show"`) first to fetch existing `target_ids` before adding or removing individual buyers.
4. **Waiting Room Dual Termination:** When both `waiting_room_seconds` and `waiting_room_tries` are populated on a campaign, the caller exits the Waiting Room as soon as **either** threshold is reached. Waiting Room hold time is billed at **2x standard per-minute rate** (rounded up to the next minute) and only re-fires webhooks marked `Re-fireable: ON`.
5. **Voice Recognition Prompt Constraints:** Enabling `voice_recognition_enabled: true` on `prompts.manage` strictly requires `repeat: 0` and `tts_language: "en-US"`. Every delivered speech-enabled Gather (including keypad-only input, silence, and retries) is billable.
6. **Dynamic Token Presence in TTS:** Bracketed tags in prompt `tts` strings (e.g., `[caller_city]`, `[first_name]`) evaluate to an empty string (`""`) if the tag is missing on the call. Ensure upstream enrichment or natural sentence fallbacks before referencing dynamic tokens.
7. **Dry-Run Verification:** Structural routing edits, target group membership replacements, and campaign deletions MUST be previewed with `dry_run: true` (`--dry-run`) prior to live execution when modifying production traffic.

## Output Specification
All CLI invocations and programmatic operations emit raw JSON to stdout conforming to this schema:
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["status", "action", "data"],
  "properties": {
    "status": {
      "type": "string",
      "enum": ["success", "error", "dry_run", "partial", "needs_clarification"]
    },
    "action": {
      "type": "string",
      "description": "Operation executed: list, show, create, update, pause, resume, routing_show, routing_update, groups_list, groups_show, groups_create, groups_update, groups_delete, groups_duplicate, prompts_list, prompts_show, prompts_create, prompts_update, prompts_delete"
    },
    "data": {
      "type": "object",
      "description": "MCP tool response payload, resource attributes, or dry_run diff envelope"
    },
    "error_details": {
      "type": "string",
      "description": "Diagnostic error message when status is error"
    }
  },
  "additionalProperties": false
}
```

## Operational Procedures, Prompt Shortcuts, & MCP Tool Mapping

### 1. Campaign Lifecycle, Waiting Room & Geo Toggles
- **MCP Tools:**
  - `campaigns.read`: `action: "index"` (paginated list) or `action: "show"` (with `campaign_id`).
  - `campaigns.manage`: `action: "create" | "update" | "delete"`. Key fields: `name`, `client_cid`, `paused`, `waiting_room_seconds`, `waiting_room_tries`, `dedupe_seconds`, `record_calls`, `repeat_caller_type`, `new_target_rolling_reset_days`, `auto_route_repeat_calls`, `conversion_propagation`, `use_global_suppression_list`, `use_carrier_geo_information`, `use_caller_number_geo_information`, `dry_run`.
- **CLI Commands:**
  ```bash
  # List and inspect campaigns
  python3 scripts/campaign_routing_ops.py list --per-page 25
  python3 scripts/campaign_routing_ops.py show 4812

  # Create a campaign with Waiting Room (30s / 3 tries) and call recording
  python3 scripts/campaign_routing_ops.py create --name "Medicare Inbound Q4" --client-cid "MED-Q4" \
    --waiting-room-seconds 30 --waiting-room-tries 3 --record-calls true

  # Update Waiting Room or Geo settings on an existing campaign
  python3 scripts/campaign_routing_ops.py create --campaign-id 4812 \
    --waiting-room-seconds 45 --waiting-room-tries 5 --use-carrier-geo-information true

  # Pause and resume a campaign
  python3 scripts/campaign_routing_ops.py pause 4812
  python3 scripts/campaign_routing_ops.py resume 4812
  ```

### 2. Campaign Call Routing Settings (`menu_options_attributes`)
- **MCP Tools:**
  - `campaigns.routing_settings.read`: `action: "show"`, `campaign_id: <int>`. Returns `menu_options` and nested `menu_options_targets` with current IDs.
  - `campaigns.routing_settings.manage`: `action: "update"`, `campaign_id: <int>`, `menu_options_attributes: [...]`.
    - Menu option `action`: `1` (dial targets/groups), `2` (redirect to `target_campaign_ids`), `3` (block caller), `6` (end call), `7` (route to CAKE).
    - Menu option `options`: `["-1"]` for default route (no keypress), `["-10"]` for unclear spoken intent, or digit strings `["1"]`, `["2"]`.
    - Routing row fields (`menu_options_targets_attributes`): `id`, `_destroy`, `target_id` or `target_group_id`, `priority`, `weight`, `locked` (`false` to override), `disabled` (`true` to exclude without pausing target), `enable_route_by_bid`, `enable_route_by_performance`, `enable_route_by_state_performance`, `performance_type` (`"strict"` | `"weighted"`), `min_calls_required`, `performance_lookback_period_value`, `default_performance`.
- **CLI Commands:**
  ```bash
  # 1. Inspect current routing options and row IDs first
  python3 scripts/campaign_routing_ops.py routing show 4812

  # 2. Override a routing row's priority, weight, and enable Route-by-Bid (unlocked)
  python3 scripts/campaign_routing_ops.py routing update 4812 \
    --option-id 901 --row-id 5512 --priority 1 --weight 3 --locked false --route-by-bid true

  # 3. Enable EPC performance routing on a row (strict mode, 50 min calls, 14-day lookback)
  python3 scripts/campaign_routing_ops.py routing update 4812 \
    --option-id 901 --row-id 5512 --locked false \
    --route-by-performance true --performance-type strict --min-calls-required 50 --lookback-days 14

  # 4. Complex multi-branch update via raw JSON with dry-run preview
  python3 scripts/campaign_routing_ops.py routing update 4812 --dry-run --menu-options-json '[
    {
      "id": 901,
      "action": 1,
      "options": ["-1"],
      "menu_options_targets_attributes": [
        {"id": 5512, "priority": 1, "weight": 2, "locked": false, "disabled": false},
        {"target_group_id": 310, "priority": 2, "weight": 1, "locked": false}
      ]
    }
  ]'
  ```

### 3. Handler / Buyer Groups (`target_groups`)
- **MCP Tools:**
  - `target_groups.read`: `action: "index"` or `action: "show"` (with `target_group_id`).
  - `target_groups.manage`: `action: "create" | "update" | "delete"`. Fields: `name`, `target_ids` (full array replacement), `priority`, `weight`, `concurrency_cap`, `cap_trigger` (`"connection"` | `"conversion"`), `dedupe_as_company`, `paused`, `dry_run`.
  - `target_groups.duplicates.manage`: `action: "create"`, `target_group_id: <int>`. Clones group settings and re-links the same member targets into `"<name> copy"`.
- **CLI Commands:**
  ```bash
  # List and show handler groups
  python3 scripts/campaign_routing_ops.py groups list
  python3 scripts/campaign_routing_ops.py groups show --target-group-id 310

  # Create a buyer group with company-wide deduplication and concurrency cap
  python3 scripts/campaign_routing_ops.py groups create --name "Tier-1 Carrier Group" \
    --target-ids "139020,139021,139025" --priority 1 --weight 1 \
    --concurrency-cap 25 --cap-trigger connection --dedupe-as-company true

  # Update group membership or pause state
  python3 scripts/campaign_routing_ops.py groups update --target-group-id 310 \
    --target-ids "139020,139021,139025,140110" --paused false

  # Duplicate an existing handler group
  python3 scripts/campaign_routing_ops.py groups duplicate --target-group-id 310
  ```

### 4. IVR Prompts & Greetings (`prompts`)
- **MCP Tools:**
  - `prompts.read`: `action: "index" | "show"`, `promptable_type: "Campaign" | "Target" | "Number"`, `promptable_id: <int>`, optional `prompt_id: <int>`.
  - `prompts.manage`: `action: "create" | "update" | "delete"`, `promptable_type`, `promptable_id`, `prompt_id` (on update/delete), `prompt_action` (e.g., `greeting`, `whisper`, `music_on_hold`, `zip_code_entry_unless_already_present`, `key_press_1`, `no_targets_match`, `all_targets_closed`), `tts`, `tts_gender` (`"Female"` | `"Male"`), `tts_language`, `preset`, `repeat`, `moment` (`"before_data_appending"` | `"before_start"`), `max_attempts`, `voice_recognition_enabled`, `voice_recognition_transcript`, `dry_run`.
- **CLI Commands:**
  ```bash
  # List all IVR prompts on a campaign
  python3 scripts/campaign_routing_ops.py prompts list --promptable-type Campaign --promptable-id 4812

  # Create a main TTS greeting with voice recognition enabled (requires repeat=0, en-US)
  python3 scripts/campaign_routing_ops.py prompts create --promptable-type Campaign --promptable-id 4812 \
    --prompt-action greeting \
    --tts "Thank you for calling Medicare Helpline. Press 1 or say Sales to speak with a licensed agent." \
    --tts-gender Female --tts-language en-US --repeat 0 --voice-recognition-enabled true

  # Add conditional 5-digit ZIP collection prompt before data appending
  python3 scripts/campaign_routing_ops.py prompts create --promptable-type Campaign --promptable-id 4812 \
    --prompt-action zip_code_entry_unless_already_present \
    --tts "Please enter your 5 digit zip code on your keypad." \
    --tts-gender Female --tts-language en-US --moment before_data_appending --max-attempts 3

  # Configure a Buyer agent whisper on a Target
  python3 scripts/campaign_routing_ops.py prompts create --promptable-type Target --promptable-id 139020 \
    --prompt-action whisper --tts "Qualified lead from [caller_state], zip [caller_zip]." --tts-gender Male
  ```

### 5. Operator Prompt Shortcuts
- *"Show routing table for campaign <ID>"* -> `campaign_routing_ops.py routing show <ID>`
- *"Set waiting room to <S> seconds and <N> tries on campaign <ID>"* -> `campaign_routing_ops.py create --campaign-id <ID> --waiting-room-seconds <S> --waiting-room-tries <N>`
- *"Enable route-by-bid on campaign <ID> option <OPT_ID> row <ROW_ID>"* -> `campaign_routing_ops.py routing update <ID> --option-id <OPT_ID> --row-id <ROW_ID> --locked false --route-by-bid true`
- *"Group buyers <IDs> with company dedupe"* -> `campaign_routing_ops.py groups create --name "<Name>" --target-ids "<IDs>" --dedupe-as-company true`

For complete nested attribute schemas, geo resolution precedence, and diagnostic matrices, read `references/campaign-routing-spec.md`.
