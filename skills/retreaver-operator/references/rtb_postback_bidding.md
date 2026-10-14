# Retreaver Real-Time Bidding (RTB), Postback Keys & Bid Optimization Guide

This reference document synthesizes Retreaver's official operational guides, API contracts, troubleshooting procedures, and bid modification architectures for Real-Time Bidding (RTB), Postback Keys, Pings, and Dynamic Bidding.

---

## 1. RTB Architecture & Endpoint Specifications

### Overview & Workflow
Retreaver's Real-Time Bidding (RTB) engine implements an inbound ping-post routing architecture:
1. **Publisher Ping:** A lead generator or publisher submits an HTTP `POST` ping request with caller identifiers and lead attributes.
2. **Tagging & Ingest:** Retreaver applies the publisher ID, key parameters, and all lead attributes as tags to the session.
3. **Downstream Ping / Evaluation:** Retreaver executes any configured "Passthrough" webhooks to query downstream buyers, checks buyer business hours, geo/state filters, concurrency limits, and cap states.
4. **Reservation & Dynamic Number Return:** When an eligible buyer is selected, Retreaver creates a call reservation, holds an inbound tracking number, computes the payout and conversion duration, and returns a JSON payload containing the reservation UUID and `inbound_number`.
5. **Call Transfer:** The publisher dials the caller into the returned `inbound_number` within the Time-To-Live (TTL) reservation window.
6. **Call Claim & Conversion:** Retreaver matches the inbound phone call to the active reservation via caller ID and assigned tracking number, transitioning status from `reserved` to `claimed`. If the connected call duration satisfies the conversion duration, the call converts.

### Inbound RTB Ping Endpoints

| Environment / Route | URL Format | Method | Auth / Credentials |
| :--- | :--- | :--- | :--- |
| **Standard Campaign RTB** | `https://rtb.retreaver.com/rtbs.json` | `POST` | `?key=POSTBACK_KEY` |
| **Publisher-Specific RTB** | `https://rtb.retreaver.com/rtbs.json` | `POST` | `?key=POSTBACK_KEY` (Publisher ID baked into key or passed in query) |
| **Core API Endpoint** | `https://api.retreaver.com/api/v2/campaigns/:campaign_id/rtbs.json` | `POST` | Company API Key or Bearer Token |

*Note: RTB pings MUST be sent via HTTP `POST`. Browser `GET` requests will not execute routing correctly.*

### Query & Body Parameters

| Parameter | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `key` | `string` | **Yes** | Postback API Key from Campaign or Publisher record. |
| `caller_number` | `string` | **Yes** | E.164 or 10/11-digit caller phone number (e.g., `15555551234`). Must NOT contain unparsed templates like `[caller_number]`. |
| `publisher_id` / `source_id` | `string` | Conditional | Required if the Postback Key is not pre-bound to a specific publisher. |
| `caller_zip` | `string` | Optional | 5-digit ZIP code for geographic radius matching. |
| `caller_state` | `string` | Optional | 2-letter state abbreviation (e.g., `CO`, `TX`). |
| `first_name` / `last_name` | `string` | Optional | Caller name fields appended as call tags. |
| `sub_id` / `affiliate_id` | `string` | Optional | Tracking sub-identifiers for granular reporting and attribution. |
| `status` | `string` | Optional | Send `status="confirmed"` when performing two-step ping confirmation. |

*Arbitrary query string keys (e.g., `credit_score=good`, `owns_home=true`) are automatically parsed and appended as tags on the call session.*

---

## 2. JSON Response Schemas & Status Lifecycles

### Successful Reservation Response (`200 OK`)

```json
{
  "uuid": "66b905ef-bc03-420e-ad43-e8eeae03918f",
  "status": "reserved",
  "retreaver_payout": 1.173,
  "retreaver_seconds": 95,
  "inbound_number": "+18444021146",
  "expires_at": "2024-05-29T16:16:18.246Z",
  "retreaver_availability_count": 3
}
```

- `uuid`: Reservation identifier used to inspect routing traces at `https://retreaver.com/call_reservations/:uuid`.
- `status`: Lifecycle state (`reserved`).
- `retreaver_payout`: Monetary payout amount offered to the publisher if the call converts.
- `retreaver_seconds`: Call duration buffer (in seconds) required to convert the call.
- `inbound_number`: Dynamically assigned dial-in number reserved for this caller ID.
- `expires_at`: ISO-8601 UTC timestamp marking the expiration of the reservation.
- `retreaver_availability_count`: Optional count of eligible buyers capable of receiving this lead right now (enabled via Postback Key setting).

### No-Target Response (`200 OK`)

```json
{
  "uuid": "81fca02d-9472-4d2c-80ea-3e5f4c581a0b",
  "status": "no-target",
  "info": "No available targets matched the criteria"
}
```

*Note: No `inbound_number` is returned on a `no-target` status. Any call directed to a previously cached number will fail or fail to route to a buyer.*

### Rejected Response (`200 OK`)

```json
{
  "uuid": "1212e30a-cff2-4f2f-ae84-dfdf5b952204",
  "status": "rejected",
  "info": "Unable to determine payout until the call converts"
}
```

### Complete RTB Status Terminology Matrix

| Status | Meaning & System Lifecycle Event |
| :--- | :--- |
| `reserved` | System matched a buyer and reserved a routing session with an `inbound_number`. Awaiting incoming call handoff. |
| `claimed` | The caller dialed the reserved `inbound_number` within the TTL window. Call was successfully matched and bridged to the buyer. |
| `expired` | Reservation was created, but no matching call arrived before TTL expired. Number reservation released. |
| `no-target` | No buyers matched due to business hours, tag filters, geographic restrictions, or zero bid returns. |
| `rejected` | Request could not connect to a target; target paused or downstream URL malformatted/unreachable. |
| `considering_targets.single` | Evaluation trace: Target is open, unpaused, and below caps. |
| `target_disqualified` | Disqualified due to tag requirements, negative tags, or operating hours. |
| `target_disqualified_by_cap` | Buyer reached daily, hourly, or monthly volume cap. |
| `target_simulcapped` | Buyer reached maximum simultaneous/concurrency call threshold. |
| `targets_closed` | Buyer operating hours are closed. |
| `targets_paused` | Buyer is manually or programmatically toggled to paused. |
| `targets_duplicate_deprioritized` | Caller ID is a repeat/duplicate within buyer window; fresh buyers prioritized. |
| `undialable_expression` | Buyer failed to provide a valid dialable transfer phone number in its response. |
| `ping_shield_postback_key_claim_based_limited` | Retreaver organic rate limiter throttled this RTB endpoint due to low claim-to-ping ratio. |
| `ping_shield_postback_key_caller_number_already_reserved` | An active unexpired reservation already exists for this `caller_number`. |
| `ping_shield_postback_key_caller_number_already_processing` | An identical `caller_number` is currently being evaluated concurrently. |

---

## 3. Reservation Lifecycles, TTLs & Dynamic Number Returns

### Reservation Timing & TTL Invariants
- **`ttl_seconds` (Time-To-Live):** Configured on the RTB Postback Key. Must be an integer between `10` and `999` seconds.
- **Default Recommendation:** `15` to `30` seconds.
- **Downstream Timeout (`timeout_seconds`):** Configured on the RTB Key (default: `5` seconds). Defines how long Retreaver waits for external buyer passthrough webhooks to respond before proceeding.
- **The TTL Myth:** Extending TTL (e.g., to 60+ seconds) does NOT fix high expiration rates. In live call environments, if a broker does not route the call within 15–30 seconds, the call was either dropped upstream or sold to a competing buyer. Extending TTL merely keeps numbers locked up and inflates concurrency counters.

### Dynamic Number Allocation & Collision Avoidance
- Retreaver assigns an `inbound_number` from the campaign pool matching the reservation.
- Dialing an expired `inbound_number` results in a dropped call or dead line because the binding between `caller_number` and `inbound_number` is destroyed at expiration.
- If `allow_no_caller_number` is enabled (testing only), number collisions occur if multiple callers hit the same inbound number concurrently. In production, always require valid caller IDs.

### Reservation Confirmation & Caps (`add_to_caps_on_status_reserved`)
- By default, RTB reservations do not count against buyer concurrency or caps until the physical call arrives.
- When `add_to_caps_on_status_reserved: true` is configured on the Postback Key, a reservation immediately decrements concurrency, hourly, daily, and monthly caps.
- Alternatively, publishers can issue a two-step ping:
  1. Initial RTB Ping -> receives quote & availability.
  2. Confirm Ping -> send request with `status="confirmed"` to lock capacity before dialing.

### Retreaver Availability Count (`retreaver_availability_count`)
- Activated per RTB Postback Key: "Return retreaver availability count".
- Returns the total count of buyers matching the caller lead criteria at that exact moment.
- **Publisher Decision Logic:**
  - `count >= 2`: Send call immediately to `inbound_number`. If primary buyer fails, Retreaver can failover to secondary buyers.
  - `count == 1`: Only reserved buyer exists; confirm reservation or hold call if answer rates are low.
  - *Note:* Fallback failover is bypassed if `route_only_to_reserved_target` is `true`.

---

## 4. Postback Keys: Complete Matrix & Configuration

Postback keys act as scoped bearer tokens tied to specific entity endpoints.

### Postback Key Scopes & Types

| Scope Level | Key Type | Hostname / Path Format | Allowed Actions / Primary Function |
| :--- | :--- | :--- | :--- |
| **Campaign** | **Real Time Bidding (RTB)** | `https://rtb.retreaver.com/rtbs.json?key=KEY&caller_number=[caller_number]` | Accept publisher pings, evaluate buyers, return reservation & dial-in number. |
| **Campaign** | **Caller List Management** | `https://api.retreaver.com/api/v2/campaigns/:id/caller_lists/:name/caller_list_numbers.json?key=KEY` | Sync campaign-wide suppression (`suppressed*`) and acceptance (`accepted*`) lists. |
| **Publisher** | **Real Time Bidding (RTB)** | `https://rtb.retreaver.com/rtbs.json?key=KEY&caller_number=[caller_number]` | RTB ping scoped to a single publisher entity. |
| **Publisher** | **Call Data Writing** | `https://retreaverdata.com/data_writing?key=KEY&caller_number=[caller_number]&k1=v1` | Inject landing page form data / CRM tags into live call record. |
| **Buyer** | **Conversion** | `https://retreaverdata.com/postbacks/KEY?caller_number=[caller_number]&call_uuid=[uuid]&value=[revenue]` | Mark call converted from buyer CRM/telephony (key placed in URL path). |
| **Buyer** | **Caller List Management** | `https://api.retreaver.com/api/v2/targets/:id/caller_lists/:name/caller_list_numbers.json?key=KEY` | Sync buyer-scoped DNC or opt-out lists without exposing campaign lists. |
| **Buyer Group** | **Call Rejection** | `https://api.retreaver.com/handler_groups/:id/call_control/reject?key=KEY&caller_number=[caller_number]` | Reject call back to group within **90 seconds** of answer; Retreaver reroutes. |
| **Buyer Group** | **Call Transfer** | `https://api.retreaver.com/handler_groups/:id/transfers/interface?key=KEY&caller_number=[caller_number]` | Transfer call to numbers in a configured Directory (requires `live_call_control`). |
| **Buyer Group** | **Call Data Reading** | `https://retreaverdata.com/data_reading?key=KEY&caller_number=[caller_number]&map_keys=...` | Read call tags across accounts via Start Ping data sharing. |

### RTB Postback Key Settings Checklist
- **`name`**: Descriptive identifier (convention: `PublisherName_CampaignName_RTB`).
- **`source_id` / `publisher_id`**: Associated publisher profile.
- **`tag_prefix`**: Optional prefix applied to all inbound tags from this ping source.
- **`ttl_seconds`**: Reservation duration (10–999s, recommended 15s).
- **`timeout_seconds`**: Downstream webhook wait limit (recommended 5s).
- **`inbound_number`**: Constrain to specific campaign tracking number.
- **`return_dba`**: Include buyer DBA business name in JSON response.
- **`add_to_caps_on_status_reserved`**: Decrement caps upon reservation.
- **`route_only_to_reserved_target`**: Restrict call bridging exclusively to the winning buyer.
- **`allow_no_caller_number`**: Bypass caller ID validation (dev/testing only).
- **`retreaver_availability_count`**: Return eligible buyer count in payload.
- **Ping Shield Parameters**:
  - `ping_shield_outbound_count_limit`
  - `ping_shield_outbound_ms_limit`
  - `claim_percent_threshold`
  - `blocked_inbound_percent`

---

## 5. Ping Shield & Organic Rate Limiting

### The Problem: High Ping vs Low Call Volume
In call brokering, publishers ping multiple buyers concurrently without having secured the call, or route the live caller elsewhere. This causes massive reservation spikes with zero call conversions.

### Retreaver Built-In Protection
Retreaver monitors the **Claim-to-Ping Ratio** (`claimed / reserved`):
1. **Organic Rate Limiter Activation:** If a publisher's postback key generates excessive reservations that expire without connected calls, Retreaver automatically triggers:
   `ping_shield_postback_key_claim_based_limited`
2. **Impact on Publisher:** Inbound pings are throttled and rejected with rate-limit errors until traffic quality normalizes.
3. **Protection for Buyers:** Downstream buyers are shielded from unfillable ping bursts, preventing buyers from blocking the network.
4. **Duplicate Safeguards:**
   - `ping_shield_postback_key_caller_number_already_reserved`: Blocks duplicate pings for the same caller number while a reservation is pending.
   - `ping_shield_postback_key_caller_number_already_processing`: Prevents race conditions from simultaneous duplicate pings.

---

## 6. Route By Bid Winner & Downstream Bidding Webhooks

### Route By Bid Winner Setup
Allows Retreaver to compare static buyer conversion values against dynamic bid amounts returned from buyer APIs and route calls to the highest paying bidder:
1. In Campaign **Route Settings**, expand the target priority group and click **Advanced**.
2. Toggle **Route By Bid Winner** to ON.
3. In Campaign **Conversion Criteria**, create dynamic criteria matching buyer tags:
   - Dynamic Revenue Tag: `[buyer_tag]_bid` (e.g., `retreaver_rtb_44407_bid`)
   - Dynamic Timer Tag: `[buyer_tag]_timer` (e.g., `retreaver_rtb_44407_timer`)
   - Payout Percentage: Set revshare percentage (e.g., 70% of bid).
   - Target Tag: Assign to specific buyer.

### Downstream Passthrough Webhooks
- Webhook trigger MUST be set to **Passthrough** (not "When a call starts").
- Passthrough triggers execute during the publisher RTB ping, querying the buyer before the reservation is finalized.

---

## 7. Payout Bid Modification (PBM) / Bid Shading

### Concept & Mechanics
Payout Bid Modification allows networks to shade dynamic payouts to publishers to capture higher margins without sacrificing call volume:
- Operates entirely **in-memory** in microseconds (no webhook latency, zero network hops).
- Applied in step 6 of the RTB flow: after buyer bid return, Retreaver adjusts the publisher payout percentage based on an uploaded rule table.
- Does NOT alter buyer revenue; only alters publisher payout (`Margin = Revenue - Payout`).

### Deterministic Hash Bucketing (Control vs. Treatment)
PBM uses deterministic SHA-256 hashing to split incoming traffic into 10,000 buckets (`0` to `9999`):
```text
bucket = SHA256("<salt>:<call_uuid>")[0..3].hex_to_int() % 10000
```
- **Control (Buckets 0–4999):** Standard conversion criteria; payouts unmodified.
- **Treatment (Buckets 5000–9999):** Evaluated against the active Payout Bid Modification table.
- **Reproducibility:** Any party knowing the table `salt` and `call_uuid` can independently verify bucket placement down to the exact hex calculation.

### PBM CSV Rule Table Specification
- File format: CSV, uploaded per campaign.
- **First matching rule wins** (ordered top to bottom: specific rules first, catch-alls last).
- Mandatory columns:
  - `rule_id`: User-defined string tracking the rule in logs/exports.
  - `payout_pct`: Integer percentage (e.g., `70`) or `current` (abstain from modification).
- Criteria columns: Any valid Retreaver tag key.
  - System IDs MUST be used for platform entities: `system_affiliate_id`, `system_campaign_id`, `system_target_id`, `system_number_id` (do NOT use client-supplied `affiliate_id`).
  - Operators: Equality default (`CO`), negation (`!=CA`), numeric comparison (`>=20`, `<30`), regex (`=~^(CO|NY|TX)$`), wildcard (`*`).
  - Multi-column ANDing: Multiple columns with the same header (e.g., two `revenue` columns with `>=20` and `<30`).
  - Special bucket targeting: `pbm_bucket` column for testing specific traffic slices.

#### Example PBM CSV Table
```csv
rule_id,caller_state,system_affiliate_id,revenue,revenue,pbm_bucket,pbm_bucket,payout_pct
1,=~^(CO|NY|TX)$,*,*,*,*,*,70
2,ON,482,*,*,*,*,55
3,*,*,>=20,<30,>=5000,<7500,60
4,*,*,*,*,>=7500,<10000,50
5,*,*,*,*,*,*,current
```

### Export Attributes (`pbm_*` Fields)
When PBM is enabled, RTB inbound exports include:
- `pbm_table_version`: Version string of the active rule table.
- `pbm_bucket`: Integer bucket (0–9999).
- `pbm_variant`: `"control"` or `"treatment"`.
- `pbm_rule_id`: Identifier of the matched rule (or absent if unmatched).

### Automatic Market Safeguards
- **Route-By-Performance:** Retreaver recalculates buyer performance (`revenue / total calls`) every few minutes. If a broker shades payouts too aggressively, the performance score drops, and Retreaver automatically steers traffic to better-performing buyers.

---

## 8. Operator Troubleshooting & Diagnostic Runbook

### Diagnostic Matrix: RTB Log vs. Call Log

| Scenario Observed | Root Cause | Operator Action |
| :--- | :--- | :--- |
| **High `expired` in RTB Log, zero calls in Call Log** | Publisher receives reservations but does not dial `inbound_number`. | Inspect publisher handoff logic. Verify publisher uses returned `inbound_number`. Check if caller dropped upstream. |
| **High `no-target` responses** | No buyers eligible for lead data. | Check buyer business hours, geo/state filters, concurrency limits, and daily caps. Test buyer phone lines. |
| **`ping_shield_*` errors** | Rate limiter tripped due to poor claim ratio or duplicate caller pings. | Review RTB Drilldown (`Reserved` vs `Claimed`). Pause low-quality broker publishers. |
| **`status: rejected`** | Campaign conversion criteria missing or buyer target paused. | Verify conversion criteria contains dynamic revshare tags (`retreaver_rtb_*_bid`). |
| **Call exists in RTB Log but missing in Call Log** | Call never hit Retreaver telephony infrastructure. | Verify dialed number matches returned `inbound_number` within TTL window. Expand date/time filter in Call Log. |
| **Calls blocked despite open campaign** | Tracking number-level business hours. | Check number settings; set number-level hours to 24/7 during troubleshooting. |

### Operator Verification Workflow: Step-by-Step
1. **Trace UUID:** Copy reservation UUID from ping response and inspect:
   `https://retreaver.com/call_reservations/:uuid`
2. **Review Call Flow:** Click on the linked call flow to inspect buyer routing evaluation, tag checks, and cap verifications.
3. **Audit Publisher Performance:** In the RTB Dashboard, drill down:
   `Publisher -> Postback Key -> Status`
   Calculate: `Connection Rate = Claimed / Reserved`.
   *Action:* If connection rate is <5%, reach out to publisher with UUIDs or revoke/pause the RTB Postback Key.
