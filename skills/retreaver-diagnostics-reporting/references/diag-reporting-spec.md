# Retreaver Diagnostics, Telemetry, and Reporting Specification

This specification provides the operational procedures, diagnostic taxonomies, failure modes, ClickHouse rollup architectures, and API mappings for diagnosing Retreaver RTB pings, webhook errors, call flow routing, real-time/daily performance stats, and CSV exports.

---

## 1. RTB Ping Diagnostics & Status Codes

Retreaver's Real-Time Bidding (RTB) engine evaluates incoming buyer and publisher pings through synchronous passthrough webhooks, tag criteria, cap limits, and geographic rules.

### 1.1 Resolution Status Taxonomy

| Status Code | Severity | Operational Meaning | Root Causes | Remediations |
| :--- | :--- | :--- | :--- | :--- |
| `reserved` | Info | Inbound reservation created; dynamic DID assigned; TTL timer active. | Normal flow; waiting for inbound phone handoff. | Monitor claim rate; ensure publisher forwards call within configured `ttl_seconds`. |
| `claimed` | Success | Caller dialed `inbound_number` within TTL; bridged to target. | Normal conversion lifecycle. | None required. |
| `expired` | Warning | Reservation created, but no matching call arrived before TTL expired. | 1. Publisher broker shopping call to other buyers.<br>2. Caller dropped upstream.<br>3. Broker latency exceeded TTL.<br>4. Publisher dialing wrong number. | 1. Audit publisher claim ratio (`claimed / reserved`).<br>2. If <5%, flag or pause publisher postback key.<br>3. Verify publisher is dialing the exact returned `inbound_number`. |
| `no-target` | Warning | No eligible buyers matched the lead/call criteria. | 1. All targets closed (outside operating hours).<br>2. All targets capped (concurrency, daily, hourly).<br>3. Tag criteria mismatch (state, zip, custom tags).<br>4. Passthrough bidding webhooks returned 0 or no bids. | 1. Check target operating hours and schedules.<br>2. Check target concurrency and volume caps.<br>3. Verify tag matching logic (e.g., negative tag rules `!~`).<br>4. Inspect buyer passthrough webhook responses. |
| `rejected` | Error | Request could not connect to a target, or campaign setup incomplete. | 1. Target paused or disabled.<br>2. Downstream passthrough webhook URL malformatted or 5xx error.<br>3. Missing dynamic revenue/timer conversion criteria. | 1. Inspect webhook endpoint health.<br>2. Check conversion criteria dynamic tags (`retreaver_rtb_*_bid`).<br>3. Verify target active state. |
| `ping_shield_postback_key_claim_based_limited` | Error | Organic rate limiter throttled RTB endpoint due to low claim-to-ping ratio. | Publisher flooded RTB with reservations without delivering live calls (`claimed / reserved` fell below threshold). | 1. Pause publisher postback key.<br>2. Require publisher to send `status="confirmed"` 2-step pings.<br>3. Adjust `claim_percent_threshold` or `blocked_inbound_percent`. |
| `ping_shield_already_reserved` | Warning | Duplicate reservation attempt for a caller number with active unexpired reservation. | Publisher or CRM fired duplicate pings for the same caller within the TTL window. | Dedup pings upstream at publisher CRM/lead generation engine. |
| `ping_shield_already_processing` | Warning | Concurrent in-flight evaluation already underway for the identical caller number. | Multiple HTTP POST requests dispatched concurrently for the same lead. | Implement lock/semaphore at publisher ingress. |
| `target_disqualified_by_cap` | Warning | Target reached daily, hourly, or monthly cap. | Target volume cap exhausted. | Adjust caps in Target settings or add secondary buyers. |
| `target_simulcapped` | Warning | Target reached maximum simultaneous active calls. | High concurrency or agent queue full. | Increase buyer concurrency limit if buyer PBX permits. |
| `targets_closed` | Warning | Call received outside target's operating hours schedule. | Lead pinged after call center business hours. | Check time zone settings on target business hours. |
| `undialable_expression` | Error | Target response did not contain a valid dialable phone number. | Malformed SIP URI or missing phone number tag in webhook response. | Fix `PingOutputMap` or buyer response parser. |

---

## 2. Webhook & Integration Failure Diagnostics

### 2.1 Execution Engines & Constraints
Retreaver runs two distinct webhook engines:
1. **Real-Time Synchronous Engine** (triggers: `Data-appending ping`, `Pass-through ping`, `Start`, `Post Zip`, `Selected`, `Answered`, `After AI Analysis`, `Recording Available`):
   - Strict **5-second timeout**. If endpoint does not respond within 5s, Retreaver advances or fails the call.
   - Recommended partner SLA is **<1.0 second**.
   - Supports custom HTTP request headers.
2. **Browser Emulated Engine** (triggers: `Timer`, `Conversion`, `Non-Conversion`, `Connect`, `Postback`, `Always`):
   - Fires asynchronously post-call or on duration milestone.
   - **Does NOT support custom HTTP headers**. All authentication and parameters must reside in the URL query string.

### 2.2 Webhook Diagnostic Runbook
When a webhook fails to fire or errors:
1. **Inspect Trigger Type**:
   - If headers are missing on `Timer` or `Conversion`, move headers into URL query parameters or switch to synchronous trigger.
2. **Verify Tag Match Filters**:
   - Inspect `tag_list` / `Matches` field. If configured, webhook only executes when call tags satisfy the exact rule.
   - Check negation operators: `caller_zip!~.+` fires only if zip is empty.
3. **Check Timeout (HTTP 504)**:
   - Check endpoint response latency. Offload heavy processing to background queues (e.g. SQS/Redis) and return 200 OK immediately.
4. **Token Resolution in Headers**:
   - Replacement tokens (`[caller_number]`, `[call_uuid]`) are **only substituted in the URL path/query**, never in custom header values.
5. **Configurator Syntax & Percent Encoding**:
   - In `https://retreaver.com/webhook-configurator/v1/`, query parameters within payloads must be percent-encoded (`%26` for `&`, `%3F` for `?`, `%22` for `"`).

---

## 3. Call Flow Reconstruction & Routing Analysis

Call flow inspection traces every step of a call's lifecycle from inbound carrier handshake to final termination.

### 3.1 Event Color Semantics in Call Logs
- **Blue (Informative)**: State changes, tag assignments, webhook dispatches, timer registrations.
- **Green (Connection)**: Successful call bridge, target answer, positive conversion.
- **Yellow (Warning)**: Target skipped due to caps, closed hours, or weight bypass.
- **Red (Problem / Error)**: Bridge failures, telco reject codes, carrier timeouts, no buyers matched.

### 3.2 Evaluation Order of Buyer Targets
During call evaluation, Retreaver tests buyers in priority order:
1. **Priority Group** (Priority 1 before Priority 2).
2. **Route By Bid Winner** (if enabled, highest dynamic bid wins).
3. **Weight** (weighted round-robin within the same priority tier).
4. **Target Feasibility Verification**:
   - Business Hours check (`Closed`).
   - Concurrency and Volume Cap check (`Capped` / `Simulcapped`).
   - Tag Criteria matching (`Not matching tags` - required tags missing or forbidden tags present).
   - Inbound caller suppression / accepted list check.

---

## 4. ClickHouse Analytical Rollups & Aggregations

Retreaver's reporting architecture stores call events and RTB inbound reservations in ClickHouse.
- Never paginate raw call/reservation logs client-side to compute counts or revenue sums.
- Always use `calls_drill_down_tables.read` and `rtb_inbound_drill_down_tables.read` to compute server-side rollups in a single round-trip.

### 4.1 RTB Rollup Dimensions & Metrics
- **Dimensions (`columns`)**: `campaign_id`, `affiliate_id`, `target_id`, `target_group_id`, `postback_key_id`, `status`, `caller_state`, `duplicate`.
- **Metrics (`metrics`)**:
  - `count_of_target_resolutions`: Total pings evaluated.
  - `percentage_of_total_target_resolutions`: Volume share.
  - `original_count` vs `duplicate_count`: New leads vs repeat pings.
  - `bid_percentage` vs `no_bid_percentage`: Proportion of pings generating valid bids.
  - `average_bid_returned`, `average_winning_bid`: Bid pricing benchmarks.
  - `ping_shield_postback_key_claim_based_limited`: Volume throttled by claim rate protection.
  - `ping_shield_already_reserved`: Duplicate reservation blocks.

### 4.2 Call Log Rollup Dimensions & Metrics
- **Dimensions (`columns`)**: `campaign_id`, `affiliate_id`, `target_id`, `status`, `caller_state`, `disposition_disposition_code`, `intent_primary_topic`.
- **Metrics (`metrics`)**:
  - `total_`: Total calls.
  - `connected_`: Calls successfully answered/bridged.
  - `revenue_`: Inbound revenue generated.
  - `payout_`: Outbound affiliate payout.
  - `profit_`: Net margin (`revenue - payout - telco cost`).
  - `cost_`: Carrier telco transit cost.
  - `epc_total` / `cpc_total`: Earnings/cost per call.
  - `total_duration_`, `dialed_call_duration_`, `hold_duration_`, `ivr_duration_`.

---

## 5. CSV Export Lifecycle & Management

To extract complete historical logs without pagination limits:
1. **Initiate Export (`exports.rtb_inbounds.manage` with `action: create`)**:
   - Provide exact filters (`campaign_id`, `affiliate_id`, `status`, `created_at` or ISO time range).
   - ClickHouse streams results directly to an S3-backed CSV file.
   - Returns `export_id` with `in_progress: true`.
2. **Poll Status (`action: show`, `export_id: <id>`)**:
   - Check `export_progress`, `export_percentage`, and `in_progress`.
   - When `in_progress: false`, response contains the direct downloadable S3 `url`.
