# Retreaver Tags, Replacement Tokens, Payout Bid Modification (PBM) & Call Crediting Specification

This reference documents the complete technical specifications, schemas, deterministic hashing formulas, comparator semantics, and operational side effects for `retreaver-tags-bidding-ops`.

---

## 1. Company Tag Catalog (`tags.read`, `tags.manage`)

### 1.1 Tag Value Types & Evaluation Semantics
Retreaver evaluates call routing criteria and buyer filter rules according to the tag key's registered `type` in the Company Tag Catalog:

| MCP `type` Enum | CLI Alias | Storage & Parsing | Supported Operators | Unregistered Fallback Risk |
| :--- | :--- | :--- | :--- | :--- |
| `Tags::Types::String` | `string`, `text` | UTF-8 text (default) | `==`, `!=`, `=~` (regex), `!~` (negated regex) | Default behavior if tag key is unregistered. |
| `Tags::Types::Numeric` | `numeric`, `number` | Integer / floating-point | `==`, `!=`, `>`, `>=`, `<`, `<=` | **CRITICAL:** Unregistered numeric tags compare lexicographically as ASCII (`"100"` < `"20"`). |
| `Tags::Types::Date` | `date` | ISO Date (`YYYY-MM-DD`) | `==`, `!=`, `>`, `>=`, `<`, `<=` | Evaluates as raw text unless registered as `Tags::Types::Date`. |
| `Tags::Types::DateTime` | `datetime` | ISO-8601 Timestamp | `==`, `!=`, `>`, `>=`, `<`, `<=` | Evaluates as raw text unless registered as `Tags::Types::DateTime`. |
| `Tags::Types::Boolean` | `boolean`, `bool` | Boolean (`true` / `false`) | `==`, `!=` | Inconsistent truthy coercion unless typed as Boolean. |

### 1.2 Tag Schema Attributes (`tags.manage`)
- **`key`** (`string`): Identifier consisting exclusively of lowercase letters, digits, and underscores (`[a-z0-9_]+`).
- **`type`** (`string`): One of the five `Tags::Types::*` variants above. Set at creation time.
- **`acceptable_tags_enabled`** (`boolean`): Restricts tag ingestion to an explicitly enumerated allowlist of values.
- **`prompt_enabled`** (`boolean`): Enables the tag key to be populated directly from caller DTMF input in Campaign IVR Prompts.
- **`values_report`** (`boolean`): Indexes the tag for aggregation in the Retreaver Tag Values Report.
- **`ai_prompt`** (`string`): Natural-language extraction instruction executed by Retreaver AI Analyst post-call (e.g., `"Extract the caller's estimated home value in USD"` or `"Did the agent read the TCPA disclosure?"`).
- **`color`** (`string`): Badge color in the Call Log UI.

---

## 2. Replacement Tokens (`tags.replacement_tokens.read`)

Replacement tokens (`[token_name]`) interpolate live call attributes into:
- Outbound Webhook URLs and JSON bodies
- Outbound SIP INVITE URIs and custom `X-*` SIP headers
- Whisper / Greeting TTS prompts
- Dynamic Conversion Criteria (`[buyer_tag]_bid`, `[buyer_tag]_timer`)

### 2.1 Token Scopes
1. **System Built-In Tokens:** Always available across all campaigns:
   - `[uuid]` / `[call_uuid]`: Unique call identifier
   - `[caller_number]`: Caller phone number (E.164)
   - `[caller_state]`, `[caller_zip]`, `[caller_city]`, `[caller_country]`: Resolved caller geo attributes
   - `[affiliate_id]` / `[system_affiliate_id]`: Publisher external and internal IDs
   - `[sub_id]`: Sub-affiliate tracking identifier
   - `[campaign_id]`, `[target_id]`, `[number_id]`: Entity identifiers
   - `[revenue]`, `[payout]`: Financial conversion values
2. **Company Custom Tag Tokens:** Every tag key registered via `tags.manage` is exposed as `[<tag_key>]`.
3. **Campaign-Scoped Tokens (`campaign_id` parameter):** Passing `campaign_id` to `tags.replacement_tokens.read` additionally returns:
   - Connected third-party integration tokens (e.g., Retreaver IQ demographic enrichment fields, AI Analyst disposition tokens `[disposition_positive_outcome]`, `[disposition_stage_reached]`, `[disposition_disposition_code]`).
   - Static custom tokens defined on that campaign's tracking numbers.

---

## 3. Payout Bid Modification (PBM) / Bid Shading

### 3.1 Execution Architecture
Payout Bid Modification adjusts the publisher payout on Real-Time Bidding (RTB) pings **after** the campaign's conversion criteria and buyer passthrough responses have established the base revenue and payout:
- Runs **100% in-memory** in microseconds during step 6 of the RTB ping lifecycle (zero network latency).
- Alters **publisher payout only**; buyer `revenue` remains unchanged (`Network Margin = Revenue - Shaded Payout`).
- Exactly **one** PBM table can be `active: true` per campaign at any moment. Activating a table automatically sets `active: false` on whichever table was previously active.

### 3.2 Deterministic SHA-256 Hash Bucketing
Every inbound RTB request is assigned to a deterministic bucket in the range `0` to `9999`:

$$\text{bucket} = \text{int}\left(\text{SHA256}(\text{salt} \mathbin{\Vert} \text{":"} \mathbin{\Vert} \text{call\_uuid})[0..7]_{\text{hex}}, 16\right) \bmod 10000$$

*(Takes the first 4 bytes / 8 hex characters of the SHA-256 digest of `"<salt>:<call_uuid>"`, converts to an unsigned 32-bit integer, modulo 10,000).*

- **Standard A/B Split Convention:**
  - **Buckets `0`–`4999` (Control):** Unmodified payout (`current`).
  - **Buckets `5000`–`9999` (Treatment):** Shaded payout rules applied via `pbm_bucket` range filters.
- **Auditability:** Because `salt` and `call_uuid` are persisted, any party can independently recompute and verify the exact bucket assignment for any RTB ping.

### 3.3 PBM CSV Rule Table Format & Operator Syntax
- **Limits:** Up to **1,000 rows** and **1 MB** per CSV upload.
- **Evaluation Order:** Top-to-bottom; **first matching row wins**. Place specific overrides at the top and catch-all defaults at the bottom.
- **Immutability:** `csv_data`, `salt`, and `table_version` cannot be edited after upload (`create`). Any rule change requires uploading a new table.

#### Reserved Columns
| Column Header | Required | Values & Semantics |
| :--- | :--- | :--- |
| `rule_id` | **Yes** | Arbitrary string/integer logged in call exports as `pbm_rule_id` when the row matches. |
| `payout_pct` | **Yes** | Percentage of buyer revenue to pay the publisher (e.g., `70` = 70% of revenue), OR literal `"current"` to leave the campaign's calculated payout untouched. |
| `pbm_bucket` | Optional | Matches the deterministic hash bucket (`0`–`9999`). Can appear twice in the header to define a lower and upper bound (e.g., `>=5000` and `<7500`). |

#### Criteria Columns & Cell Operators
- Every non-reserved column header must be a valid Retreaver tag key (e.g., `caller_state`, `sub_id`, `revenue`, `system_affiliate_id`, `system_target_id`).
- **System ID Invariant:** Always use `system_affiliate_id`, `system_campaign_id`, `system_target_id`, and `system_number_id` for platform entities rather than unverified query parameters.
- **Operators Live in Cells, Never Headers:**
  - `==` (or bare value, e.g. `TX`): Exact equality
  - `!=`: Inequality (e.g. `!=CA`)
  - `=~`: Regular expression match (e.g. `=~^(CO|NY|TX)$`)
  - `!~`: Negative regular expression match
  - `>`, `>=`, `<`, `<=`: Numeric/Date comparisons (e.g. `>=20`, `<50`)
  - `*`: Wildcard (no constraint on this column for this row)
- **Range ANDing via Duplicate Headers:** Repeat the same column header twice in the CSV to combine two comparators with logical AND (e.g., `revenue,revenue` with cells `>=25,<60`).

#### Canonical PBM CSV Example
```csv
rule_id,caller_state,system_affiliate_id,revenue,revenue,pbm_bucket,pbm_bucket,payout_pct
tier1_states,=~^(CO|NY|TX)$,*,*,*,>=5000,<10000,70
pub_482_ontario,ON,482,*,*,>=5000,<10000,55
mid_rev_slice_a,*,*,>=20,<40,>=5000,<7500,60
mid_rev_slice_b,*,*,>=20,<40,>=7500,<10000,50
control_passthrough,*,*,*,*,*,*,current
```

### 3.4 PBM Telemetry Fields in Call Exports
When a campaign has an active PBM table, RTB records and CSV exports include:
- `pbm_table_version`: Active table's `table_version` (or table `id`).
- `pbm_bucket`: Computed integer bucket (`0`–`9999`).
- `pbm_variant`: `"control"` or `"treatment"`.
- `pbm_rule_id`: Matched row's `rule_id`.

---

## 4. Call Crediting & Revenue Adjustments (`calls.manage`)

`calls.manage` (`action: "update"`) modifies financial and conversion state on an existing call identified by `uuid`.

### 4.1 Parameter Matrix & Coupling Rules
| Field | Type | Coupling & Side Effects |
| :--- | :--- | :--- |
| `uuid` | `string` | **Required.** Target call's unique UUID. |
| `revenue` | `number \| null` | Buyer revenue amount. Setting `revenue > 0` automatically sets `receivable = true`. Setting `revenue = 0` clears the revenue amount. **Immediately adjusts Buyer volume cap counters.** |
| `payout` | `number \| null` | Publisher payout amount. Setting `payout > 0` automatically sets `payable = true`. Setting `payout = 0` clears the payout amount. |
| `receivable` | `boolean \| null` | Marks whether the call earned buyer revenue. **Transitioning `receivable` to `true` immediately fires any previously unfired Conversion webhooks on the call.** |
| `payable` | `boolean \| null` | Marks whether the publisher is owed a payout for the call. |
| `session_notes` | `string \| null` | Free-text operator audit log stored on the call record. |
| `dry_run` | `boolean` | Returns a `{from, to}` diff without mutating the call, caps, or webhooks. |

### 4.2 Safe Call Crediting Runbook
1. **Preview with Dry Run:** Always invoke `credit-call --uuid <UUID> ... --dry-run` first to inspect the current vs. proposed `revenue`, `payout`, `receivable`, and `payable` state.
2. **Verify Webhook Impact:** If `receivable` is transitioning from `false` to `true`, confirm downstream publisher/CRM conversion webhooks are expected to fire.
3. **Verify Buyer Cap Impact:** Crediting `revenue > 0` on a buyer whose `cap_trigger` is `conversion` increments that buyer's daily/hourly/monthly/hard conversion counters, which can cap the buyer for live traffic if near threshold.
4. **Attach Audit Note:** Always populate `--session-notes` with the ticket, dispute, or CRM reconciliation reference.
