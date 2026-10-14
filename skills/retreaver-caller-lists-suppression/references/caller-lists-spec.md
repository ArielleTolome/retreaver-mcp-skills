# Retreaver Caller Lists & Suppression Specification

This reference manual documents the architecture, routing mechanics, retention policies, asynchronous upload pipelines, external REST Postback Key synchronization, and alternative regex tag suppression patterns for Retreaver Caller Lists.

---

## 1. Architecture & Polymorphic Ownership

Caller Lists in Retreaver attach polymorphically to two parent entities via `caller_listable_type` and `caller_listable_id`:

1. **`Campaign` Scope (`caller_listable_type: "Campaign"`)**:
   - Evaluates immediately when an inbound call or RTB ping enters the campaign.
   - A caller matching a campaign-level `suppressed*` list is rejected before any buyer evaluation or webhook ping occurs.
2. **`Target` / Buyer Scope (`caller_listable_type: "Target"`)**:
   - Evaluates during candidate buyer arbitration.
   - A caller matching a buyer's `suppressed*` list skips only that specific buyer while remaining eligible for other buyers in the same campaign.

### Parameter Naming Convention Across MCP Tools
- In `caller_lists.read` and `caller_lists.manage`, the list name parameter is `name`.
- In `caller_list_numbers.read`, `caller_list_numbers.manage`, `caller_list_uploads.read`, `caller_list_uploads.manage`, and `caller_list_checks.manage`, the list name parameter is `caller_list_name`.

---

## 2. Prefix-Driven Routing Semantics (`suppressed*` vs `accepted*`)

Retreaver inspects the prefix of the caller list's `name` to determine its enforcement mode:

| Prefix Pattern | Routing Role | Enforcement Behavior | Typical Use Cases |
|---|---|---|---|
| `suppressed*` | **Deny List** | Automatically blocks calls from numbers currently active on the list. | `suppressed_dnc`, `suppressed_litigators`, `suppressed_converted_leads`, `suppressed_fraud` |
| `accepted*` | **Allow List** | Explicitly permits or prioritizes matching callers across campaign/buyer filters. | `accepted_vip_callers`, `accepted_existing_customers`, `accepted_test_numbers` |
| Other prefixes | **Passive / Tag-Referenced** | Does not automatically block or allow unless paired with explicit campaign/buyer routing rules. | Custom segmentation lists |

---

## 3. Automated Population & Retention Mechanics

Caller lists can be populated statically (via API/MCP/CSV upload) or dynamically from live call traffic via `caller_lists.manage`:

### 3.1 Post-Call Financial Triggers
- **`add_call_on_receivable: true`**: Automatically appends `caller_number` when a call converts and generates receivable revenue from a buyer.
- **`add_call_on_payable: true`**: Automatically appends `caller_number` when a call qualifies for a publisher payout.
- **Both Enabled**: Captures callers whenever either financial qualification triggers, preventing repeat payouts or double-billing on converted leads.

### 3.2 Tag-Match Auto-Capture (`tag_list`)
- Configured via `tag_list` using comma-separated triple-angle tokens: `<<<key:operator+value>>>`.
- When an active call's tags satisfy all conditions in `tag_list`, the caller's E.164 number is automatically inserted into the list.
- Examples:
  - Auto-suppress callers flagged by Anura: `<<<anura_code:==bad>>>`
  - Auto-suppress callers pressing opt-out digit 9: `<<<keys_pressed:=~9>>>`
  - Auto-suppress short-duration repeat spammers: `<<<call_duration:<10>>>`

### 3.3 Sliding Retention Window (`remove_number_after_seconds`)
- **`null` (Never remove)**: Permanent membership (standard for statutory DNC and known TCPA litigators).
- **Integer Seconds**: Rolling TTL measured from the timestamp the number was added to the list:
  - 24 Hours: `86400`
  - 7 Days: `604800`
  - 30 Days: `2592000`
  - 60 Days: `5184000`
  - 90 Days: `7776000`
- `caller_list_checks.manage` evaluates the expiration window at query time: if `now - added_at > remove_number_after_seconds`, the check returns `"not-present"` even before background garbage collection purges the row.

---

## 4. Bulk Upload Pipeline (`caller_list_uploads.*`)

When adding or scrubbing batches of numbers:
1. Invoke `caller_list_uploads.manage` with:
   - `action: "create"`
   - `caller_listable_type`: `"Campaign"` or `"Target"`
   - `caller_listable_id`: integer ID
   - `caller_list_name`: target list name
   - `numbers`: string of E.164 numbers separated by `\n` or `,`
   - `upload_action`: `"create"` (append numbers) or `"delete"` (remove numbers)
   - `clear_before_upload`: `true` (wipe existing list prior to import) or `false` (incremental)
2. Poll `caller_list_uploads.read` (`action: "show"`, `upload_id: <id>`) until processing completes and verify zero formatting errors.

---

## 5. External Partner Sync via Postback Keys

When external publishers or buyers need to sync suppression lists directly from their CRM without MCP credentials, issue a dedicated **Caller List Management Postback Key**:

- **Campaign-Scoped Endpoint**:
  `https://api.retreaver.com/api/v2/campaigns/:id/caller_lists/:name/caller_list_numbers.json?key=KEY`
- **Buyer-Scoped Endpoint**:
  `https://api.retreaver.com/api/v2/targets/:id/caller_lists/:name/caller_list_numbers.json?key=KEY`

This isolates partner access strictly to the designated caller list without exposing campaign configurations or other buyers' lists.

---

## 6. Alternative: Buyer-Level Text-Tag Regex Suppression

For small, static client exclusion lists (<250 numbers) on a single buyer where a dedicated Caller List is not desired:
1. Strip `+1` and all punctuation so every number is a 10-digit NANP string (`NXXNXXXXXX`).
2. Join numbers with pipe delimiters: `2125550100|2125550101|3125550199`.
3. Add a standard tag on the buyer (`targets.manage` `tag_list`):
   `<<<caller_number:!~2125550100|2125550101|3125550199>>>`

---

## 7. Troubleshooting Matrix

| Symptom | Root Cause | Fix |
|---|---|---|
| Caller on suppression list still routes to campaign/buyer | List name does not begin with `suppressed` (e.g. named `dnc_list`) or number was uploaded without `+1` E.164 prefix. | Rename/recreate list with `suppressed_` prefix and ensure numbers are stored as `+1NXXNXXXXXX`. |
| `caller_list_checks.manage` returns `not-present` for an uploaded number | Either the bulk upload is still queued/processing, or the number exceeded `remove_number_after_seconds`. | Check `caller_list_uploads.read` for job completion and inspect `remove_number_after_seconds` on `caller_lists.read`. |
| Bulk upload wiped existing DNC numbers unexpectedly | `clear_before_upload: true` was passed on an incremental batch. | Omit `clear_before_upload` (or set `false`) for additive uploads. |
