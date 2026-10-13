# Retreaver Knowledge Base: Buyers, Targets, Caps, Business Hours & Suppression

This document provides a comprehensive operational synthesis of Retreaver's architecture and configuration rules for Call Buyers (Endpoints/Targets), Tag-based Routing, Forward Tag Lists, Buyer Caps, Business Hours, Priority & Weight Distribution, Offer Carousels, and Caller Lists / Suppression Systems.

---

## 1. Tag Engine & Operator Rules

Retreaver uses key-value tags to represent all call attributes. Tags act as filters, preemptive data attachments, or trigger gates depending on the component they attach to:
- **On Endpoints/Buyers:** Filter which calls the buyer can accept.
- **On Numbers:** Preemptively tag every inbound call entering via that tracking number.
- **On Webhooks & Conversion Criteria:** Act as gating conditions; the webhook or conversion event only fires if matching tags exist on the call.

### 1.1 Data Types & Supported Operators

| Data Type | Supported Operators | Operational Behavior / Example |
| :--- | :--- | :--- |
| **Text** | `==` (Default / Exact match)<br>`!=` (Not equal)<br>`=~` (Regex / substring match)<br>`!~` (Regex / substring negative match) | `mortgage_type:==purchase`<br>`mortgage_type:!=refinance`<br>`caller_state:=~california\|new york`<br>`keyword:!~free` |
| **Numeric** | `==` (Default / Equals)<br>`!=` (Not equal)<br>`<` (Less than)<br>`>` (Greater than)<br>`<=` (Less than or equal)<br>`>=` (Greater than or equal) | `loan_amount:>100000`<br>`loan_amount:<=500000`<br>`credit_score:>=720` |
| **Date** | `==`, `!=`, `<`, `>`, `<=`, `>=` | `callback_at:!=2026-12-25`<br>`dob:<1961-01-01` |
| **Date-Time** | `==`, `!=`, `<`, `>`, `<=`, `>=` | Exact timestamp comparisons in UTC or local timezone variants. |

> **Critical Constraint:** Numeric, date, and date-time tags **must be explicitly registered and created** in the Retreaver Tag Wizard (`/tags/wizard/new`). Unregistered tags default to string/text evaluation, which breaks mathematical range checks (e.g., string comparison evaluates `"1000"` as less than `"200"`).

### 1.2 Syntax Equivalences & Conventions
- `sub_id=test` and `sub_id:test` both represent an exact equality (`==`) operator across all data types.
- Multiple range constraints on the same key create bounded intervals:
  - Adding `loan_amount:>100000` and `loan_amount:<600000` requires the call value to fall strictly between 100,000 and 600,000.
- Multiple tag entries with the same key on a buyer act as an **OR** condition:
  - `Product_Interest:Insurance` and `Product_Interest:Healthcare` allow the buyer to accept either Insurance or Healthcare.
  - Adding `Product_Interest!=Phoneplan` explicitly excludes callers with that tag.
- Untagged keys mean "accept all": If a buyer accepts any value for a tag key, omit that tag key entirely from the buyer profile.

### 1.3 Presence vs. Absence Regex Checks
Using the text matching operators with the `.+` regular expression enables presence/absence gating:
- **Tag Presence Check (`=~` with `.+`):** e.g., `leadid:~.+` (or `leadid:=~.+`). Ensures the call carries a non-empty `leadid` tag (critical for TCPA compliance / Jornaya / TrustedForm verification).
- **Tag Absence Check (`!~` with `.+`):** e.g., `fraud_caller_score:!~.+`. Blocks any call where a fraud score tag exists.

### 1.4 Tag Replacement Tokens
Tags can dynamically populate IVR greetings and webhook URLs using bracketed tokens: `[tag_key]`.
- **Webhook substitution:** `https://api.crm.com/lead?phone=[caller_number]&affiliate=[publisher_id]`
- **Dynamic IVR speech:** `"Hello [first_name], please hold while we transfer you."`
- **Missing Token Failure Mode:** If a tag key has an empty value when triggered, Retreaver injects **nothing** (blank string), potentially corrupting webhook endpoints or query parameters.

### 1.5 System Tag Reference Catalog

#### Text System Tags
- `campaign_id` / `campaign_name`: Internal campaign identifier and display name.
- `publisher_id`, `source_id`, `affiliate_id`: Interchangeable source identifiers across UI editions (Performance, Marketer, API).
- `affiliate_first_name`, `affiliate_last_name`, `affiliate_company`: Publisher profile attributes.
- `buyer_id`, `handler_id`, `target_id`: Interchangeable buyer identifiers.
- `target_name`, `system_target_group_id`: Target display name and buyer group ID.
- `called_number`: The inbound tracking DID dialed by the lead.
- `target_number`, `call_forwarded_to`: The destination phone or SIP URI dialed.
- `call_uuid`, `retreaver_url`, `call_key`: Unique call tracking identifier, deep-link URL, and postback authentication key.
- `caller_number`: Caller ID in standard format.
- `caller_number_digits`: Caller ID digits without the leading `+`.
- `nanp_caller_number`: Caller ID without North American `+1`.
- `nanp_caller_number_area_code`, `nanp_caller_number_prefix`, `nanp_caller_number_suffix`: 3-digit NPA, 3-digit NXX, 4-digit line number.
- `caller_city`, `caller_state`, `caller_zip`, `caller_country`: Geographic location inferred or collected via IVR.
- `call_recording_url`: URL of the recorded call MP3.
- `call_status`: Final call disposition status.
- `click_to_call`: Boolean indicating programmatic call origin.
- `keys_pressed`: String sequence of DTMF tones pressed during IVR routing.
- `fired_pixels_count`: Total number of webhooks dispatched for the call.
- `hung_up_by`: Identifies disconnect initiator (`caller` vs `buyer`).
- `converted`, `duplicate`, `repeat`: Boolean indicators for revenue qualification, duplicate conversion status within conversion group, and repeat campaign caller status.
- `conversion_name`: Name of the conversion criteria applied.
- `google_analytics_client_id`, `google_analytics_tracking_id`, `visitor_url`: Web session attribution attributes.

#### Date-Time System Tags
Timezone variants available: `_utc`, `_at`, `_ct`, `_mt`, `_pt`, and `_et`.
- `call_start_time`, `call_forwarded_time`, `call_finish_time`
- `call_start_time_day_of_week_et`: Numerical day (1 = Monday, 7 = Sunday).
- `call_start_time_year_et`, `call_start_time_month`, `call_start_time_day`, `call_start_time_hour`, `call_start_time_minute`, `call_start_time_second`

#### Numeric System Tags
- `system_buyer_id`: Internal database ID of the matched endpoint.
- `call_duration`: Total call length from carrier connect to carrier disconnect (seconds).
- `call_forwarded_duration` / `call_connected_duration`: Total talk time with buyer endpoint (seconds).
- `call_ivr_duration`: Time spent inside IVR prompts (seconds).
- `call_hold_duration`: Time spent in waiting room or on hold (seconds).
- `billable_minutes`, `charge_per_minute_in`, `charge_per_minute_out`, `charge_total`: Retreaver billing metrics.
- `conversion_seconds`: Target conversion threshold duration.
- `revenue`, `receivable`, `receivable_converted_duration`, `receivable_duplicate`: Incoming revenue financials and duplicate flags.
- `payout`, `payable`, `payable_converted_duration`, `payable_duplicate`: Outgoing publisher payout financials and duplicate flags.

---

## 2. Standard Tag Lists vs. Forward Tag Lists

Retreaver divides tag evaluation on buyers into two distinct lifecycle phases.

### 2.1 Standard Tag Lists (Pre-Selection)
- **Evaluation Timing:** Evaluated **BEFORE** a buyer is selected for routing.
- **Use Cases (95% of rules):**
  - Demographic filters (`age:>=65`)
  - Geographic constraints (`caller_state:=~CA|TX|FL`)
  - Minimum bid requirements (`bid_amount:>=15.00`)
  - Concurrency and operating criteria
- **Behavior:** If standard tags do not match incoming call tags, the buyer is eliminated from the candidate pool immediately.

### 2.2 Forward Tag Lists (Post-Selection, Pre-Routing)
- **Evaluation Timing:** Evaluated **AFTER** the buyer is selected as the top candidate, but **IMMEDIATELY PRIOR** to connecting or bridging the call.
- **Primary Operational Purpose:** Defer expensive or external validation webhooks (e.g., Litigator List / DNC scrubs, Jornaya LeadID verification, TrustedForm claim checks, carrier lookup API calls).
- **Architecture Benefits:** In RTB environments with high ping volume, running third-party validation on every inbound ping is cost-prohibitive. Forward tags ensure verification webhooks fire **only** for the single winning buyer that is actually about to receive the live caller.

### 2.3 Operational Safeguards & Edge Cases with Forward Tags
- **Missing Transfer Number Vulnerability:** In legacy routing, buyers without a valid transfer number or bid were invalidated prior to selection. With forward tag lists, buyer selection occurs before transfer number verification. To avoid routing into dead ends, always maintain a standard tag condition verifying the presence of a transfer number or active bid:
  - `buyer_transfer_number: matches .+`
  - `rtb_bid > 0`
- **Validation Webhook Configuration:** Pair forward tags with webhooks triggered on **"When the buyer is selected"** and enable the **"Hold Call"** checkbox. This pauses call routing while the API scrub returns.
- **Rate-Limiting Lockout:** If an external verification endpoint hits a rate limit or fails to respond, Retreaver cannot retrieve the required tag. The buyer will fail forward tag evaluation and remain unroutable.

---

## 3. Buyer Volume Caps & Trigger Architecture

Caps control call allocation to individual buyers based on concurrent capacity or time-windowed totals.

### 3.1 The 5 Cap Types

| Cap Type | Scope / Window | Reset Interval | Operational Intent |
| :--- | :--- | :--- | :--- |
| **Concurrency** | Active live simultaneous calls | Instantaneous (slot frees as soon as an active call disconnects) | Protects call center agent staffing thresholds and PBX trunk capacity. |
| **Hard Cap** | Cumulative lifetime calls | **Never resets automatically**; manual reset required via Buyer UI. | Fixed-volume contract fulfillment (e.g., 500-call test pilot). |
| **Hourly Cap** | Calls within a clock hour | Top of each hour (`:00`) in buyer's timezone. | Smoothes hourly inbound pacing. |
| **Daily Cap** | Calls within a calendar day | Midnight (`00:00:00`) in buyer's timezone. | Enforces daily contractual quotas. |
| **Monthly Cap** | Calls within a calendar month | 1st day of month at `00:00:00` in buyer's timezone. | Monthly contract allocation. |

### 3.2 Cap Triggers: Connection vs. Conversion
The Cap Trigger determines the exact lifecycle event that increments period caps (Hard, Hourly, Daily, Monthly):
- **Conversion Trigger (Default):** A call only increments the cap counter once it satisfies conversion criteria (e.g., reaches duration threshold, postback fires, or revenue is credited). Unqualified short calls do not burn cap allocation.
- **Connection Trigger:** A call increments the cap counter immediately upon bridging/connecting to the buyer, regardless of call duration or conversion outcome.

### 3.3 Real-Time Bidding (RTB) Reservation Caps
When RTB is active, Retreaver reserves capacity before the live call reaches the buyer.

#### Mechanics & Over-Allocation Prevention
- When a buyer submits a winning bid, an **RTB Reservation** is created with a defined TTL (Time-To-Live).
- The reservation increments the buyer's cap counter immediately:
  $$\text{Effective Cap Count} = \text{Connected Calls} + \text{Pending Reservations}$$
- If adding a reservation would cause the buyer to exceed **any** configured cap, the reservation is rejected entirely (all-or-nothing check across all 5 cap types).
- When the live call arrives and connects, the reservation converts into an active call. If the call does not arrive before the TTL expires, the reservation is released and capacity restored.

#### Trigger Dependency for RTB Reservations
- **Connection Trigger Requirement:** Period caps (Hard, Hourly, Daily, Monthly) **only** track reservations if the Cap Trigger is set to **Connection**. If set to Conversion, period caps ignore pre-call reservations (since unconverted pings cannot be assumed to convert).
- **Concurrency Exception:** Concurrency caps **always** track reservations regardless of whether the trigger is Connection or Conversion. Concurrent trunks must never be over-allocated.

---

## 4. Business Hours & Granular Schedule Caps

Business Hours dictate whether a buyer or tracking number can receive calls, preventing calls outside operating hours without manually pausing campaigns.

### 4.1 UI Presets & Multi-Block Schedules
- **Presets:**
  - `Open 24-7`: Continuously open every day.
  - `Open 9-5 Monday - Friday`: 09:00 to 17:00 Monday through Friday; closed Saturday/Sunday.
  - `Noon Lunch`: Monday to Friday split shifts (e.g., 09:00–12:00 and 13:00–17:00).
- **Timezone Isolation:** Configured per buyer profile. All open/close evaluations and daily cap resets execute relative to the specified timezone.
- **Multi-Block Shifts:** Clicking the `(+)` icon allows unlimited discrete operating blocks per calendar day (e.g., 08:00–11:30, 12:30–17:00, 18:00–21:00).
- **Quick-Fill Automation:**
  - Standard natural-language parsing: Entering `"9am"` or `"5pm"` automatically formats to standard 24-hour military time (`09:00`, `17:00`).
  - `Set All`: Copies the active day's time blocks across all remaining active days (does not overwrite days marked as Closed).

### 4.2 Granular Number Caps via Business Hours
Beyond buyer-level controls, Retreaver allows granular caps directly on Publisher / Tracking Numbers inside the Number Business Hours interface:
- Time blocks can be carved down to minute-level granularity.
- Each discrete time block supports an individual cap threshold.
- **Cap Metrics:** Configurable based on **Conversions** or **Connections**.
- **Concurrency on Business Hours:** Requires account-level enablement by Retreaver support.

---

## 5. Routing Arbitration: Priority, Weight & Carousels

When multiple buyers match an incoming call's standard tags and business hours, Retreaver arbitrates call delivery using a two-tier hierarchy: **Priority First, then Weight.**

```
Incoming Call
     │
     ▼
Check Availability & Standard Tags on Priority Group N (starts at lowest numerical value)
     │
     ├─► [Available Matches Found?] ──YES──► Distribute via WEIGHT ratio within group
     │                                            │
     │                                            ▼
     │                                      Route to Winning Buyer
     │
     NO
     │
     ▼
Move to Priority Group N+1 (e.g., Priority 2 / Overflow)
```

### 5.1 Priority Hierarchy (Precedence)
- Lower numerical priority values have absolute precedence:
  $$\text{Priority } 1 > \text{Priority } 2 > \text{Priority } 3$$
- **Negative Priority Values (Star Performers):** To introduce a top-tier buyer without re-indexing all existing endpoints, assign negative values:
  $$\dots < -2 < -1 < 1 < 2 \dots$$
  A buyer with Priority `-1` will be evaluated and filled before Priority `1` buyers are considered.
- **Overflow & Fallback Routing:** Grouping primary buyers in Priority `1` and backup call centers or internal queues in Priority `2` guarantees calls only divert to overflow when all primary buyers are capped, closed, or offline.

### 5.2 Weight Distribution (Within Priority Groups)
When two or more endpoints within the **same** priority tier are open and matched, Retreaver distributes volume proportionally based on relative weight:

$$\text{Call Allocation Percentage for Buyer } i = \left( \frac{\text{Weight}_i}{\sum_{k=1}^{n} \text{Weight}_k} \right) \times 100\%$$

*Example:* Priority 1 contains Buyer A (Weight 1) and Buyer B (Weight 3). Sum of weights = 4.
- Buyer A receives $\frac{1}{4}$ ($25\%$) of eligible calls.
- Buyer B receives $\frac{3}{4}$ ($75\%$) of eligible calls.

### 5.3 Offer Carousel Architecture
An offer carousel chains multiple distinct buyer offers or campaigns sequentially for the same caller.
1. **Interactive Prompt Tagging:** Create a prompt tag (e.g., `Product_Interest`) configured to solicit DTMF or voice response.
2. **Buyer Tag Alignment:** Each buyer profile represents a distinct vertical or product with positive and negative matching tags:
   - Auto Insurance Buyer: `Product_Interest:Auto, Product_Interest!=Health`
   - Health Insurance Buyer: `Product_Interest:Health, Product_Interest!=Auto`
3. **Sequential Flow:**
   - The campaign prompts the caller for Offer 1.
   - If accepted, the call matches Buyer 1 and bridges immediately.
   - If declined, the carousel prompts for Offer 2 or redirects the call into an alternate campaign.
4. **Mandatory Exit Key:** Carousel campaigns must supply an opt-out exit digit (e.g., "Press 9 at any time to exit") in the campaign greeting to prevent caller entrapment.

---

## 6. Caller Lists & Suppression Systems

Retreaver provides two architectures for suppressing unwanted callers or prioritizing VIPs: **Global/Campaign/Buyer Caller Lists** and **Regex Text-Tag Buyer Suppression**.

### 6.1 Caller Lists (Native Allow / Deny Lists)
Caller Lists operate at either the **Campaign** or **Call Buyer** level to manage repeat callers, suppress converted leads, or prioritize high-value callers.

#### Naming Conventions (Mandatory Behavior Drivers)
The list name's prefix determines routing behavior:
- **Suppression Lists (`suppressed*`):** Any list whose name begins with `suppressed` (e.g., `suppressed_converted_leads`, `suppressed_repeat_callers`) acts as an automated **Deny List**. Callers on the list are blocked from routing to that campaign or buyer.
- **Acceptance Lists (`accepted*`):** Any list whose name begins with `accepted` (e.g., `accepted_vip_callers`) acts as an **Allow List**. Matching callers bypass standard restrictions or receive priority routing.
- **Custom Names:** Custom prefixes do not enforce default block/allow routing and rely on custom tag rules.

#### Retention Policies (`Remove number after`)
- **Never remove:** Number remains on the list permanently.
- **Time-based expiration:** Automatically removes caller phone numbers after a defined interval (e.g., 30 days, 90 days) to allow re-qualification.

#### Automated Population Triggers
Caller lists can dynamically capture numbers post-call:
1. **Add caller on receivable:** Captures the caller if the call earned revenue (qualified conversion).
2. **Add caller on payable:** Captures the caller if the call triggered a publisher payout.
3. **Add on converted calls:** Checking **both** receivable and payable captures only fully converted calls.
4. **Add caller when tags match (Tag Wizard):** Captures numbers dynamically based on custom rules:
   - `caller_state == FL`
   - `call_duration > 60`
   - `fraud_score >= 80`

### 6.2 Buyer-Level Text Tag Suppression (Regex Piping)
When an external client supplies a static suppression list (DNC / past converts) that must be enforced strictly on a single buyer without affecting other buyers on the campaign:

#### Operational Procedure
1. **Clean Phone Numbers:** Strip all punctuation, formatting, and country codes (`+1`). Ensure all numbers are raw 10-digit strings (`NXXNXXXXXX`).
2. **Pipe-Delimited Formatting:** Transpose the list into a single bar-separated regular expression string:
   ```text
   2125550100|2125550101|3125550199|4155550144
   ```
3. **Buyer Tag Wizard Setup:**
   - **Data Type:** Text
   - **Key:** `caller_number`
   - **Operator:** `Does not Match` (`!~`)
   - **Value:** Paste the pipe-delimited regex string.
4. **Execution:** Retreaver evaluates incoming `caller_number` against the exclusion regex. If the caller's number matches any value in the string, the buyer is skipped during evaluation.

---

## 7. Failure Modes, Edge Cases & Verification Guide

### 7.1 Diagnostic Checklist

| Issue | Root Cause | Remediation Step |
| :--- | :--- | :--- |
| Numeric range filter ignored (`loan_amount:>50000`) | Tag was not created in Tag Wizard (`/tags/wizard/new`) and defaults to string comparison. | Register tag key as Numeric in Tag Wizard; re-save campaign. |
| Buyer receives calls during lunch or outside hours | Buyer timezone misconfigured or overnight hours split incorrectly. | Verify buyer's explicit timezone. Spanning midnight requires two distinct blocks (e.g., 20:00–23:59 and 00:00–04:00). |
| RTB calls over-allocating daily buyer cap | Cap Trigger is set to **Conversion** instead of **Connection**. | Change Cap Trigger to **Connection**. Reservations only decrement period caps when triggered on connection. |
| Buyer selected but call fails or dead-ends on RTB | Forward Tag List deferred transfer number validation without a safeguard tag. | Add standard pre-selection tag: `buyer_transfer_number: matches .+` or `rtb_bid > 0`. |
| Webhook URL outputs literal `[first_name]` or broken query param | Caller had no `first_name` tag; Retreaver injected an empty string. | Use tag presence check (`first_name:~.+`) before routing to endpoints dependent on token substitution. |
| Blocked caller still reaching buyer | Suppression list phone numbers contained `+1` prefix or list name did not begin with `suppressed`. | Format list numbers as exact 10 digits (`nanp_caller_number`); verify list prefix is lowercase `suppressed_`. |
| Rate-limited verification webhook leaves buyer unroutable | When an external validation API fails, Retreaver cannot retrieve forward verification tags. | Ensure webhook timeout handlers and fallback buyers exist with lower priority to catch dropped checks. |

### 7.2 Call Flow Verification Matrix
When diagnosing call behavior in **Call Overview -> Call Flow** (reverse-chronological trace):
- **Blue Entries:** Informative status checks (tag matches, priority evaluation).
- **Green Entries:** Successful buyer connection, transfer, or conversion.
- **Yellow Entries:** Non-fatal warnings (buyer cap reached, buyer outside business hours, tag mismatch skipping buyer).
- **Red Entries:** Critical routing failures (no buyer matched, carrier connection failure, webhook timeout).
