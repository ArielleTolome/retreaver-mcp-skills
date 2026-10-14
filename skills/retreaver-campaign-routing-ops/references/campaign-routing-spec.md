# Retreaver Campaign Routing, Waiting Room, Handler Groups & IVR Prompts Specification

This reference documents the complete operational architecture, nested Rails parameter contracts, and failure modes for Retreaver Campaigns (`campaigns`), Call Routing matrices (`campaigns.routing_settings`), Waiting Room queues, Buyer/Handler Groups (`target_groups`), and IVR Prompts/Greetings (`prompts`).

---

## 1. Campaign Architecture & Lifecycle Toggles (`campaigns.read` / `campaigns.manage`)

A Campaign is the root orchestration container in Retreaver. Numbers, Buyers (Targets), Handler Groups, Publishers, Webhooks, and Conversion Criteria attach to or inherit from the Campaign.

### 1.1 Repeat Caller Handling & Rolling Reset Logic
Controlled via `repeat_caller_type`, `auto_route_repeat_calls`, `new_target_rolling_reset_days`, and `repeat_caller_tag_values_inherit`:
- **Default Routing:** Evaluates the caller against standard Priority, Weight, Business Hours, Caps, and Tag Criteria on every call.
- **Previous Call Endpoint (Buyer):** Bypasses IVR prompts and direct-routes the return caller to the last Buyer they connected with.
  - *Operational Hazard:* When testing campaign IVR flows from a single test phone number, repeat caller auto-routing will skip the greeting and menu options on the second dial. Disable `auto_route_repeat_calls` during QA testing.
- **New Call Endpoint (Buyer):** Forces routing to a Buyer that has not previously received a call from this caller, maximizing conversion yield across a buyer tree.
- **Rolling Reset Window (`new_target_rolling_reset_days`):** Defines the number of days of inactivity from a specific caller before a previously contacted Buyer is once again treated as "new" for that caller.
- **Tag Carryover (`repeat_caller_tag_values_inherit`):** Repeat caller handling inherits tags from the caller's prior call record. In dynamic RTB or ping-post environments where temporary transfer numbers or bid values are written per call, tag inheritance can carry stale transfer DIDs into subsequent calls unless configured appropriately.

### 1.2 Geo Data Resolution Precedence
Campaigns expose two boolean toggles for automatic location inference:
- `use_carrier_geo_information` (Default: `true`): Extracts location metadata delivered in carrier signaling headers.
- `use_caller_number_geo_information` (Default: `true`): Infers city, state, and zip from the caller's NPA-NXX area code/prefix.

Location tags (`caller_zip`, `caller_state`, `caller_city`, `geo:us-xxxxx`) resolve in strict precedence order:
1. **RTB Inbound Request** (`caller_zip` / `geo` passed in pre-call ping)
2. **Data Writing API** (pre-call or mid-call injection keyed by caller number or UUID)
3. **Webhook Response Overwrite** (Start or Data-Appending ping JSON payload)
4. **ZIP Prompt IVR** (`zip_code_entry_unless_already_present` or `zip_code_entry_always`)
5. **Carrier-Supplied Geo** (`use_carrier_geo_information`)
6. **Caller Number Geo** (`use_caller_number_geo_information`)

### 1.3 Recording, Deduplication & Conversion Propagation
- `record_calls` (`boolean`) & `record_seconds` (`integer`): Controls inbound call recording and optional max recording length.
- `dedupe_seconds` (`integer`): Campaign-level deduplication window in seconds.
- `conversion_propagation` (`boolean`): Synchronizes forward duration and conversion status when calls route between linked Retreaver accounts.
- `use_global_suppression_list` (`boolean`): Enforces the company-wide DNC/suppression list on inbound calls to the campaign.
- `affiliate_can_pull_number` (`boolean`): Allows invited Publisher collaborators to self-provision tracking numbers on the campaign.
- `click_to_call` (`boolean`): Authorizes programmatic outbound click-to-call initiation.

---

## 2. Call Routing Matrix (`campaigns.routing_settings.read` / `campaigns.routing_settings.manage`)

Campaign routing uses a nested structure mirroring Rails `accepts_nested_attributes_for`:
- Top-level array: `menu_options_attributes` (IVR menu branches or default direct route)
- Nested array under each option: `menu_options_targets_attributes` (ordered routing rows pointing to individual Targets or Target Groups)

### 2.1 Menu Options (`menu_options_attributes`)
Each menu option defines what happens when a caller presses a key, speaks a topic, or takes no action:
- `id` (`integer`, optional): Existing menu option ID to update; omit to create a new option.
- `_destroy` (`boolean`, optional): Set `true` alongside `id` to delete the menu option.
- `action` (`integer`, enum `[1, 2, 3, 6, 7]`):
  - `1`: **Dial** — Routes the caller through `menu_options_targets_attributes` (required for buyer/group routing rows).
  - `2`: **Redirect** — Redirects the caller to another campaign specified in `target_campaign_ids`.
  - `3`: **Block Caller** — Immediately blocks and adds the caller to suppression.
  - `6`: **End Call** — Terminates the call politely.
  - `7`: **Route to CAKE** — Dispatches routing integration to CAKE.
- `options` (`array of strings`): Key-presses that trigger this branch:
  - `["-1"]`: **Default Route** (used when there is no IVR keypress menu, or when nothing is pressed).
  - `["-10"]`: **Unclear Spoken Intent** fallback route when voice recognition cannot classify the caller's speech.
  - `["1"]`, `["2", "3"]`, etc.: Standard DTMF digit triggers.
  - Empty array `[]`: Valid only when `topic` is populated for a voice-only route.
- `topic` (`string`, max 64 chars): Spoken phrase that selects this option by voice (e.g., `"Sales"`, `"Customer Support"`). Must be unique per menu and must not be a keypad digit or its spoken name.
- `topic_hint` (`string`, max 500 chars): Optional natural-language guidance for the voice matcher describing when `topic` applies.

### 2.2 Routing Rows (`menu_options_targets_attributes`)
Each entry inside `menu_options_targets_attributes` binds either a single Buyer (`target_id`) or a Handler Group (`target_group_id`) to the menu option:
- `id` (`integer`, optional): Existing routing row ID to modify. **Always run `campaigns.routing_settings.read` first** to retrieve current `id` values before mutating rows.
- `_destroy` (`boolean`, optional): Set `true` with `id` to remove the target/group from the campaign's routing table without deleting the underlying target.
- `target_id` / `target_group_id` (`integer`): Exactly one must be specified when adding a new routing row.
- `locked` (`boolean`):
  - When `true`: The routing row inherits the Target's or Target Group's own global `priority` and `weight`, ignoring any per-row `priority` or `weight` values.
  - When `false`: The campaign routing row overrides the Target/Group's global priority and weight with its own per-campaign `priority` and `weight`.
- `priority` (`integer`): Tier evaluation order (lower integer dials first, e.g., `-1` before `1`, `1` before `2`). Requires `locked: false` to take effect on the row.
- `weight` (`integer`): Proportional traffic share among open, matched rows within the same priority tier. Requires `locked: false`.
- `disabled` (`boolean`): Temporarily excludes this row from routing on this campaign without removing the row or pausing the buyer globally across other campaigns.

### 2.3 Bid-Based & Performance-Based (EPC) Routing
Requires the company's `advanced_routing` feature flag. Configured per routing row (applies across the priority tier):
- `enable_route_by_bid` (`boolean`): Dynamically reorders eligible endpoints in the priority tier from highest RTB/ping bid to lowest bid.
- `enable_route_by_performance` (`boolean`): Dynamically reorders the priority tier by historical Earnings Per Call (EPC).
- `enable_route_by_state_performance` (`boolean`): Evaluates historical EPC segmented by the caller's US state (`caller_state`).
- `performance_type` (`"strict"` | `"weighted"`):
  - `"strict"`: Strictly dials the highest-EPC buyer first.
  - `"weighted"`: Distributes calls via weighted-random probability proportional to EPC.
- `min_calls_required` (`integer`): Minimum call sample size required before performance ordering activates (routes by standard priority/weight during the learning phase).
- `performance_lookback_period_value` (`integer`): Rolling lookback window in days used to compute EPC.
- `default_performance` (`integer`): Assumed baseline performance value while a row is still below `min_calls_required`.

---

## 3. The Waiting Room (`waiting_room_seconds` & `waiting_room_tries`)

When an inbound call completes its initial routing pass and zero buyers are open, uncapped, and tag-matched, the Waiting Room holds the caller with music while polling for capacity.

### 3.1 Mechanics & Dual Termination Rule
- **Polling Interval:** Retreaver re-evaluates all routing rows and re-fires eligible ping webhooks every **5 seconds**.
- **Configuration Fields (on `campaigns.manage`):**
  - `waiting_room_seconds` (`integer` | `null`): Maximum hold duration in seconds (e.g., `30`).
  - `waiting_room_tries` (`integer` | `null`): Maximum re-ping/routing cycles attempted while holding (e.g., `3`).
- **Dual Termination Rule:** When both `waiting_room_seconds` and `waiting_room_tries` are set, the caller exits the Waiting Room as soon as **either** limit is reached, cascading to the `no_targets_match` prompt or fallback action.
- **Re-fireable Webhooks:** Only webhooks marked `Re-fireable: ON` (plus buyer-selected hold webhooks) re-execute during Waiting Room cycles.
- **Billing Impact:** Waiting Room hold duration is billed at **2x the standard per-minute rate**, rounded up to the next whole minute.

---

## 4. Handler / Buyer Groups (`target_groups.read`, `target_groups.manage`, `target_groups.duplicates.manage`)

Handler Groups (`target_groups`) bundle multiple Buyers (`targets`) into a single logical unit that can be placed onto a campaign routing row, capped collectively, or deduplicated as a single company.

### 4.1 Group Membership & Replacement Invariant
- `target_ids` (`array of integers`): The complete list of member Buyer IDs belonging to the group.
- **Full-Replacement Semantics:** Passing `target_ids` to `target_groups.manage` (`action: "update"`) **replaces the entire membership list**. Always inspect the group via `target_groups.read` (`action: "show"`) first if appending or removing a single buyer from an existing group.

### 4.2 Group Caps, Priority & Company Deduplication
- `concurrency_cap` (`integer` | `null`): Maximum simultaneous live calls across all buyers in the group combined.
- `cap_trigger` (`"connection"` | `"conversion"`): Lifecycle event that increments group period counters (`filled`, `hourly_filled`, `daily_filled`, `monthly_filled`).
- `priority` & `weight` (`integer`): Default group-level priority and weight when attached to a campaign with `locked: true`.
- `dedupe_as_company` (`boolean`): When `true`, an inbound call to the group is flagged as a duplicate if **any** member buyer in the group has previously converted that caller within the conversion deduplication window. Prevents paying or routing duplicate conversions across multiple endpoints owned by the same parent buyer organization.
- `paused` (`boolean`): Pauses or resumes all routing through the group.

### 4.3 Duplicating a Handler Group (`target_groups.duplicates.manage`)
- Invoking `target_groups.duplicates.manage` (`action: "create"`, `target_group_id: <id>`) clones the group's settings into a new group named `"<name> copy"` and **re-links the exact same member `target_ids`** (member buyers are shared, not cloned).

---

## 5. IVR Prompts & Greetings (`prompts.read` / `prompts.manage`)

IVR Prompts attach polymorphically to a `Campaign`, `Target` (Buyer whisper/greeting), or `Number` (surgical DID override) via `promptable_type` and `promptable_id`.

### 5.1 Polymorphic Ownership
- `promptable_type`: `"Campaign"`, `"Target"`, or `"Number"`.
- `promptable_id`: Integer ID of the owning Campaign, Target, or Number.
- `prompt_id`: Integer ID of the specific prompt (required for `show`, `update`, `delete`).

### 5.2 Prompt Actions (`prompt_action` Catalog)
Required on `create`. Determines when in the call lifecycle the prompt plays:
- **Core Call Lifecycle:**
  - `greeting`: Main campaign/number IVR message played upon answer.
  - `click_to_call_greeting`: Greeting played on outbound click-to-call legs.
  - `please_hold` / `please_hold_tcpa`: Spoken hold notice before bridging.
  - `music_on_hold` / `music_on_agent_hold`: Waiting Room or agent hold audio preset.
  - `whisper`: Spoken to the receiving Buyer agent before bridging the caller.
  - `target_greeting` / `previous_target_greeting`: Played to the caller when routing to a standard or repeat buyer.
- **ZIP Code Collection:**
  - `zip_code_entry_unless_already_present`: Prompts US callers for 5-digit ZIP only when no `geo:us-xxxxx` tag exists from RTB, Data Writing, Webhook, Carrier, or NPA-NXX.
  - `zip_code_entry_always`: Forces 5-digit DTMF ZIP entry for all US callers and overwrites prior geo tags.
  - `zip_entry_failed` / `zip_entry_too_many_attempts`: Error feedback for invalid ZIP DTMF input.
- **DTMF & Voice Gather Menus:**
  - `key_press_0` through `key_press_9`, `key_press_#`, `key_press_*`: Prompt played when the corresponding key is pressed.
  - `no_key_press` / `any_other_key_press`: Timeout or invalid key fallback prompts.
  - `press_1_to_accept` / `press_1_too_slow`: Buyer agent or caller confirmation prompts.
  - `ivr_data_question` / `keypad_menu_instructions`: Structured IVR data gathering prompts.
  - `voice_response_not_understood` / `voice_recognition_unavailable` / `voice_response_ambiguous`: Speech gather fallback prompts.
- **Dispositions & Exceptions:**
  - `all_targets_closed`: Played when all matching buyers are outside business hours.
  - `no_targets_match` / `tag_validation_failed`: Played when zero buyers match routing criteria or tags.
  - `no_target_answered` / `caller_not_available`: Carrier/endpoint no-answer fallbacks.
  - `caller_previously_converted`: Played when repeat converted callers are blocked.
  - `enter_extension` / `extension_failed`: Extension dialing prompts.
  - `offer_resubscribe` / `caller_resubscribed` / `resubscribe_failed` / `cannot_resubscribe`: Opt-in/resubscribe flows.
  - `resolve_caller_number` / `resolve_caller_number_failed` / `caller_number_confirmation`: Anonymous/blocked ANIs resolution flow.

### 5.3 TTS, Dynamic Tokens, Timing & Voice Recognition Constraints
- `tts` (`string`): Text-to-speech script. Supports dynamic bracketed tag tokens (e.g., `"Thank you for calling from [caller_city], please press 1 for sales."`). Ensure referenced tags exist on the call or fallback cleanly, as missing tags render as empty strings (`""`).
- `tts_gender`: `"Female"` or `"Male"`.
- `tts_language`: Language locale (e.g., `"en-US"`).
- `preset` (`string`): Pre-configured hold music or audio preset (audio file binary uploads are not supported via MCP).
- `moment`: `"before_data_appending"` or `"before_start"` — controls whether the prompt executes before or after data-appending webhooks fire.
- `repeat` (`integer`): Number of times to repeat the prompt if no input is received.
- `max_attempts` (`integer`): Maximum retry attempts for input collection prompts.
- **Voice Recognition Invariants (`voice_recognition_enabled: true`):**
  1. Allows callers to press a key or speak their menu choice (`topic` on `menu_options_attributes`).
  2. **Strict Parameter Requirements:** Requires `repeat: 0` and `tts_language: "en-US"`.
  3. **Transcript Requirement for Uploaded Audio:** If attached to a greeting with uploaded audio, `voice_recognition_transcript` (max 4,000 chars) is required.
  4. **Billing Warning:** Every delivered speech-enabled Gather (including keypad-only responses, silence, and retries) incurs per-gather speech recognition charges.

---

## 6. Diagnostic & Troubleshooting Matrix

| Symptom | Root Cause | Resolution |
| :--- | :--- | :--- |
| Row `priority` or `weight` update in `routing_settings.manage` has no effect | `locked` is set to `true` on the routing row, causing it to inherit the Target's global priority/weight. | Set `"locked": false` on the `menu_options_targets_attributes` row alongside `"priority"` and `"weight"`. |
| Adding a buyer to a `TargetGroup` wiped out all existing buyers in the group | `target_ids` in `target_groups.manage` replaces the entire membership array. | Run `target_groups.read` (`action: "show"`) first, append the new `target_id` to the existing `target_ids` list, and pass the full array. |
| Enabling `voice_recognition_enabled` on a prompt fails validation | `repeat` is non-zero or `tts_language` is not `"en-US"`. | Set `repeat: 0` and `tts_language: "en-US"` when enabling speech recognition. |
| Test calls skip the IVR greeting and route straight to a buyer | Campaign `auto_route_repeat_calls` / `repeat_caller_type` is routing the test ANI to its previous endpoint. | Set `auto_route_repeat_calls: false` or `repeat_caller_type: "default"` while testing IVR flows. |
| Waiting Room holds callers indefinitely or drops too early | Misaligned `waiting_room_seconds` vs `waiting_room_tries` or ping webhooks lack `Re-fireable: ON`. | Set both `waiting_room_seconds` (e.g., `30`) and `waiting_room_tries` (e.g., `3`), and verify ping webhooks are marked re-fireable. |
