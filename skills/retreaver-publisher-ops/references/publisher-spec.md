# Retreaver Publisher & Affiliate Technical Specification

## 1. Overview and Core Architecture

In Retreaver, **Publishers** (also referenced as **Affiliates** or **Sources**) are traffic partners who direct inbound calls to campaigns via:
1. **Dedicated Static Tracking Numbers (DIDs)** assigned to an affiliate entity.
2. **Dynamic Number Pools (DNI)** populated via `Retreaver.js` on landing pages.
3. **Real-Time Bidding (RTB) Inbound Pings** providing dynamic reservations and SIP/PSTN bridge endpoints.
4. **Call Data Writing Endpoints** injecting pre-call or post-call attributes (CRM data, web form submissions).

Every publisher is assigned an internal database integer ID (`id`) and an immutable 8-character hexadecimal identifier (`afid`).

---

## 2. Affiliate / Publisher Profile Attributes

| Field | Type | Description |
| :--- | :--- | :--- |
| `id` | Integer | System primary key for the publisher entity. |
| `afid` | String | Unique 8-character hex affiliate code (e.g., `f22101b9`). |
| `client_afid` | String / Null | Custom user-facing affiliate identifier or partner slug. |
| `alternative_id`| String / Null | External CRM or partner reference ID. |
| `company_name` | String / Null | Primary business name of the affiliate network or broker. |
| `first_name` | String / Null | Contact person first name. |
| `last_name` | String / Null | Contact person last name. |
| `time_zone` | String | Display time zone (e.g., `"Eastern Time (US & Canada)"`). |
| `iana_time_zone`| String | Standard IANA time zone identifier (e.g., `"America/New_York"`). |
| `static_number_cap` | Integer / Null | Maximum static tracking numbers the publisher can self-provision. |
| `paused` | Boolean | Administrative lock halting all inbound traffic from this publisher. |
| `business_hours`| Array[Object] | Weekly operating schedule containing 7 day records (Sunday = 0 to Saturday = 6). |

### Business Hours Object Structure
```json
{
  "id": 3734123,
  "day_of_week": 1,
  "work_day": true,
  "time_open": 900,
  "time_close": 1730,
  "invert": false
}
```
- `time_open` / `time_close`: Represented as integer 24-hour `HHMM` (e.g., `900` = 09:00, `1730` = 17:30, `2400` = midnight).
- `invert`: When `true`, inverts the window so the specified range represents closed hours instead of open hours.

---

## 3. Postback Keys Architecture

Postback keys provide authenticated API entry points for publishers and downstream platforms to interact with Retreaver call sessions.

### Key Types for Publishers
1. **Real-Time Bidding (`rtb`)**:
   - Accepts inbound HTTP pings with caller ID and qualification tags.
   - Evaluates buyers, business hours, and caps in real time.
   - Returns a temporary dynamic tracking number, reservation token, quoted publisher payout, and required buffer seconds.
2. **Call Data Writing (`data_writing`)**:
   - Allows publishers to inject tags into active or upcoming call records.
   - Pre-call matching: matches on `caller_number` within the `end_seconds` storage window.
   - Post-call matching: matches on `call_uuid` or `caller_number` within the `start_seconds` post-call window.

### Postback Key Parameters
- `postbackable_type`: `"Affiliate"` (or `"Campaign"` with pre-bound `affiliate_id`).
- `postbackable_id`: ID of the target Affiliate or Campaign.
- `postback_action`: `"rtb"` or `"data_writing"`.
- `name`: Human-readable identifier (Convention: `PubName_Campaign_RTB`).
- `tag_prefix`: Namespace prefix applied to all tags sent by this publisher (e.g., `p12_`). Must end in an underscore. Prevents overwriting system routing tags.
- `ttl_seconds`: Reservation validity duration (default: 15s; range: 10–999s).
- `timeout`: Maximum timeout (in seconds) Retreaver will wait for downstream buyer pings (default: 5.0s).
- `inbound_number`: Manual static phone number override instead of generating dynamic pool numbers.
- `claim_percent_threshold`: Ping Shield threshold. When the ratio of claimed calls to reserved pings falls below this percentage, Ping Shield initiates throttling.
- `blocked_inbound_percent`: Percentage of incoming requests to reject when Ping Shield activates.
- `add_to_caps_on_status_reserved`: If `true`, decrements buyer caps immediately on ping reservation rather than waiting for call connection or confirmation.
- `allow_no_caller_number`: Allows SIP-based transfers without caller PSTN numbers.
- `sip_auth_method`: `"ip_whitelist"` or `"credentials"`.

---

## 4. Tracking Numbers & Tagging Contract

### Number Allocation
- Static numbers are bound to a publisher by setting `affiliate_id` during number creation or update via `numbers.manage`.
- Dynamic number pools (`number_pools.manage`) can also be bound to a publisher using `affiliate_id` and `campaign_id`.

### Tag Triple Angle Bracket Convention
All tag definitions, matching criteria, and replacement tokens passed to Retreaver must adhere to triple angle bracket syntax:
- Format: `<<<key:value>>>`
- Multiple tags: Comma-separated (e.g., `<<<affiliate_id:61956>>>,<<<channel:inbound_seo>>>`).
- Tag replacement: Passing `tag_list` replaces existing tags completely (non-additive).

---

## 5. Publisher Payouts & Conversion Groups

Conversion groups govern whether a call converts, the revenue recognized from buyers, and the payout remitted to publishers.

### Ownership
Conversion groups can be attached to:
- `Campaign`: Campaign-wide fallback conversion rules.
- `Affiliate`: Publisher-specific payout overrides.
- `Target`: Buyer-specific conversion and revenue rules.
- `Number`: Number-specific rules.

### Conversion Types
1. `timer`: Converts after connected call duration exceeds `seconds`.
2. `postback`: Converts upon receiving a webhook from the buyer/CRM.
3. `attempt`: Converts upon routing attempt or ring.
4. `multicall`: Converts on repeated calls matching `secondary_tag_list`.
5. `revshare`: Splits buyer revenue based on percentage.

### Financial Fields
- `revenue`: Monetary revenue credited to the campaign owner.
- `payout`: Monetary payout credited to the publisher.
- `payout_percent`: Boolean indicating whether `payout` is a fixed dollar amount or a percentage of revenue.
- `payout_modifier`: Mathematical expression applied to postback payouts (e.g., `*0.80`, `-5.00`).
- `dedupe_seconds`: Duplicate suppression window. Repeat callers within this window do not trigger secondary payouts.

---

## 6. Ping Shield & Anti-Fraud Protection

Retreaver monitors the **Claim-to-Ping Ratio** (`claimed / reserved`):
1. **Excessive Unclaimed Pings:** Triggers `ping_shield_postback_key_claim_based_limited`.
2. **Duplicate Protection:**
   - `ping_shield_postback_key_caller_number_already_reserved`: Blocks duplicate pings for a caller number with an active pending reservation.
   - `ping_shield_postback_key_caller_number_already_processing`: Prevents race conditions during simultaneous identical pings.
3. **Tag Shielding:** Using `tag_prefix` prevents malicious or accidental overwrite of critical routing variables (`buyer_id`, `campaign_id`, `revenue`).
