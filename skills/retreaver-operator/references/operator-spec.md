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
# Retreaver Knowledge Base: Routing, Numbers, and Reporting

A comprehensive operational reference for managing Retreaver Campaigns, Numbers, Dynamic Number Pools, SIP Trunks, Waiting Room queues, Geo Data resolution, Call Flow debugging, AI Analyst inspection, and ClickHouse/CSV analytics.

---

## 1. Campaign Structure and Navigation Menus

A Campaign serves as the parent orchestration unit in Retreaver. Numbers, Endpoints (Buyers), and Affiliates (Publishers) assigned to a Campaign inherit its operational parameters.

### 1.1 Core Navigation Tabs
- **Overview:** Displays high-level routing topology, prompt sequences, default conversion criteria, and recent call tallies. Also displays webhook activity and general campaign descriptors.
- **Toggles:** Operational switchboard controlling runtime call behavior:
  - *Repeat Caller Handling:* Dictates routing logic for return callers on the same promotional number:
    - `Default`: Follows standard routing criteria (Priority, Weight, Caps, Tag matching).
    - `Previous Call Endpoint (Buyer)`: Bypasses IVR prompts and direct-routes the caller to the last Buyer they connected with. *(Caution: When testing IVRs, ensure caller ID is not being auto-routed by this setting).*
    - `New Call Endpoint (Buyer)`: Enforces routing to an uncontacted Buyer to maximize conversion potential.
    - *Tag Carryover Warning:* Repeat caller handling carries over tags from prior calls to return calls. If using ping/post tags (such as dynamic bids or temporary transfer numbers), contact Retreaver support to set the account flag disabling repeat tag inheritance while retaining routing logic.
  - *Geo Data Handling:* Controls automatic geographic inference (Carrier Geo vs. Caller Number Geo).
  - *Call Recording:* Enables inbound call recording. Audio files are accessible in the Call Log and Call Flow inspect views.
  - *Conversion Propagation:* When routing calls to secondary Retreaver accounts, forward duration and conversion status synchronize with the downstream recipient's conversion outcome.
  - *Publisher Management:* Empowers invited Publisher collaborators to self-provision or destroy tracking numbers assigned to their publisher entity.
  - *Click-to-Call:* Authorization gate required for programmatic outbound call initiation.
- **Permissions:** Scopes role-based access control (RBAC) across invited Publisher and Buyer collaborators for the specific campaign.
- **Retreaver.js Settings:** Houses the JavaScript snippet for landing page integration:
  - *Campaign ID & Key:* Cryptographic identifiers that authorize tracking requests.
  - *URL Parameter Mappers:* Defines query parameter key-to-tag transformations (e.g., mapping `utm_source` or `f_n` into call tags).
  - *Dynamic Number Insertion (DNI):* Scans DOM elements to swap hardcoded placeholder telephone numbers with dynamically leased tracking numbers in exact phone formatting.
- **AI Analyst:** Enables automated transcription, call categorization, intent/disposition extraction, custom prompting, and volume capping.
- **Calls / Call Log:** Filterable historical call log scoped specifically to the campaign.

---

## 2. Tracking Numbers & Sourcing

### 2.1 Local vs. Toll-Free Numbers
- **Toll-Free Numbers:** Nationally recognized US prefixes (`800`, `888`, `877`, `866`, `855`, `844`, `833`). Provisioned automatically from carrier wholesale pools; ideal for nationwide broadcast media (TV, Radio, National Search).
- **Local Numbers:** Bound to specific regional area codes (e.g., `312`/`773` Chicago, `201` New Jersey). Selected state-by-state and city/rate-center from live inventories.
- **International Availability Constraints:** Retreaver currently supports United States local and toll-free numbers (callable from US and Canada). International DIDs are unsupported by default and require custom enterprise arrangements with high-volume commitments (100+ calls/day).

### 2.2 Sourcing and Attribution Entities
- **Publisher (Source / Affiliate):** Each number maps to a traffic partner. Retreaver isolates reporting, revenue shares, and access control by Publisher ID (`AFID`).
- **Sub IDs (`sub_id`):** Granular tracking for sub-affiliates or sub-campaigns. Configured on static numbers via the Tag Wizard (`Text` -> key `sub_id` -> value) or ingested via DNI parameters. `sub_id` surfaces natively across Call Logs and exports.
- **Static Context Tags:** Custom key-value pairs (e.g., `channel = tv`, `agent_name = simon`) attached directly to a number. Every call arriving on that DID inherits these tags for downstream routing, webhooks, and reporting.

### 2.3 Inheritance and Surgical Overrides
Every number inherits four major operational blocks from its parent Campaign by default:
1. **Route Settings** (Endpoint distribution, priority, weight, routing criteria)
2. **Prompts** (IVR greetings, whisper messages, hold audio, DTMF gather menus)
3. **Conversion Criteria** (Revenue values, duration thresholds, payout events)
4. **Webhooks** (HTTP triggers fired throughout the call lifecycle)

**Lock/Unlock Mechanism:**
Each of these four settings features an individual toggle. When locked, the number reflects changes made to the parent Campaign. When unlocked, the number uses a standalone configuration, allowing custom IVRs, specific buyer queues, or distinct webhook triggers on high-volume placements without altering the core Campaign.

### 2.4 Lifecycle Management & Decommissioning
- Numbers are not permanently deleted immediately; they are **released**.
- Released numbers enter a cooling-off quarantine period to drain residual caller traffic before returning to carrier pools.
- **Single Release:** Open Number -> Edit -> Click `Delete`.
- **Bulk Release:** Payments view -> `Upcoming Charges` tab -> Select checkboxes -> Click `Release Selected Numbers`.

---

## 3. Dynamic Number Pools & Landing Page DNI

Number Pools eliminate the need to purchase static numbers for every ad variation, affiliate, or keyword. Pools assign temporary numbers dynamically on landing pages via `Retreaver.js`, track concurrent visitors, and recycle numbers when sessions terminate.

### 3.1 Sizing Calculations & Concurrency Math
Number Pool capacity depends entirely on **concurrency within the lease window** and the **granularity of tracking attributes**:
- **Attribute-Level Sharing:**
  - If tracking high-level attributes (e.g., `campaign_id` or `source`), visitors sharing identical values see the same pool number simultaneously.
  - If tracking unique visitor click IDs (`click_id`, `gclid`), every concurrent visitor requires a dedicated number for 100% attribution fidelity.
- **Formula:**
  $$\text{Pool Size} = \text{Peak Concurrent Visitors in Lease Window} \times \text{Unique Attribute Factor}$$
- **Examples:**
  - *Source/Sub-source:* 3 traffic sources $\times$ 10 sub-sources = 30 total combinations. A pool of 30 numbers delivers 100% precision regardless of visitor volume.
  - *ClickID Level:* 10 concurrent page visitors per 5-minute lease = 10 active pool numbers required.

### 3.2 Lease Timing & Recycling Engine
- **Buffer Seconds:** Grace period Retreaver holds a number after the visitor navigates away from the page before returning it to the pool.
- **Max Lease Time:** Maximum duration a visitor can hold a number without placing a call. If exceeded without a call, the number returns to the available pool.
- **Post-Call Immediate Release:** Once a call terminates, if no other active web visitor holds that number, it is instantly recycled into the pool.
- **Visitor Ping Refresh:** Active browsing pings Retreaver periodically, keeping the lease refreshed until `Max Lease Time` is reached.
- **Default Fallback Number:** Static hardcoded number embedded in the page HTML. If the number pool is exhausted (all numbers leased), Retreaver displays the Default Fallback Number. Attribution tags are lost for overflow callers, but the call is captured. Best practice: tag the default number with `sub_id = default number`.

---

## 4. Number Caps & Granular Scheduling

Retreaver supports conversion and connection throttling at the individual tracking number level via Business Hours.

### 4.1 Granule Cap Configuration
1. Open Number -> Click `Edit` -> Navigate to `Business Hours`.
2. Establish time blocks using the green `+` icon (configured down to 1-minute intervals).
3. If a single time block spans the entire day, the cap functions as a daily limit.
4. Define Cap Metric:
   - **Conversions:** Call counts only toward the cap if it meets campaign conversion criteria (e.g., duration or postback).
   - **Connections:** Call counts toward the cap immediately upon establishing a bridge with an endpoint.
5. Save changes via `Update Number`.

### 4.2 Automated Cap Alerts
- Configure thresholds to alert operators when a number approaches or reaches its quota.
- Open bell icon (`Alerts`) -> `Configure Alerts` -> Define percentage/numerical thresholds and clear past notifications.

---

## 5. SIP Trunking: Inbound and Outbound Architecture

Retreaver supports SIP (Session Initiation Protocol) routing, bypassing the PSTN to reduce per-minute transit costs and interface directly with enterprise PBX systems (Asterisk, FreePBX, Twilio, Vicidial).

### 5.1 Outbound SIP Configuration (Buyer Endpoints)
- **Target Addressing:** In the Buyer's `Number` field, enter `sip:endpoint@domain.com`. Dynamic token replacement is supported (e.g., `sip:[buyer_id]@[tag_company].com`).
- **Destination vs. Authentication Credentials:**
  - `Number` field (`sip:username@example.com`): Resolves the destination URI / extension where SIP INVITE packets are dispatched.
  - `SIP Username` / `SIP Password`: Authentication credentials transmitted in the SIP authorization header if the recipient PBX challenges the connection. If left blank, Retreaver dispatches calls unauthenticated.
- **Authentication Modes:**
  1. *Unauthenticated:* Destination accepts open SIP INVITEs.
  2. *Digest Authentication:* Retreaver responds to SIP 401/407 challenges using configured `SIP Username` and `SIP Password`.
  3. *IP Whitelisting:* Buyer firewalls allow signalling traffic originating from Retreaver/Twilio signaling proxy IPs.

### 5.2 Outbound SIP Headers
- Custom SIP headers pass operational context directly into recipient call centers:
  - Custom headers are appended under `Add Header` (e.g., `X-Campaign-ID: [campaign_id]`, `X-Publisher-ID: [affiliate_id]`).
- **Default Automatic SIP Headers:**
  - `X-PH-RetreaverUUID`: Global Unique Identifier of the call record.
  - `X-PH-RetreaverKey`: Campaign postback key.
  - `X-PH-RetreaverAFID`: Publisher / Affiliate ID.
  - `X-PH-RetreaverSID`: Sub-affiliate ID (`sub_id`).

### 5.3 Inbound SIP Setup
- Supported via manual activation through Retreaver network operations (`support@retreaver.com`).
- **Inbound SIP URIs:**
  - Credential Authentication: `sip:+1[E164Number]@retreaver.sip.twilio.com`
  - IP-Whitelisted Signalling: `sip:+1[E164Number]@retreaver-ip.sip.twilio.com`
- Any active Retreaver DID can accept inbound SIP traffic worldwide when formatted with E.164 country codes (`+1...`).

---

## 6. The Waiting Room: Dynamic Queueing & Polling

The Waiting Room places callers on hold when no Buyer endpoint is immediately available, preventing premature drop-offs or fallback routing.

### 6.1 Operational Lifecycle
1. Caller dials in; initial routing sweep matches zero available/open/uncapped buyers.
2. Caller is placed into the Waiting Room and hears hold music.
3. Every **5 seconds**, Retreaver executes a background re-check across routing criteria and active ping webhooks.
4. The instant a Buyer becomes available and accepts, the call bridges immediately.
5. If the queue expires before an endpoint matches, the call cascades to the **No Buyer Matched** routing outcome (voicemail, overflow buyer, or hangup).

### 6.2 Expiration Logic & Attempt Limits
Configured under Campaign -> `Edit` -> `Waiting Room`:
- **Duration (Seconds):** Hold timer limit (e.g., `30` seconds). Blank disables duration-based expiration.
- **Attempts:** Maximum routing cycles evaluated while in the queue (e.g., `3` attempts). An attempt increments each time the call enters the Waiting Room cycle.
- **Dual Termination Rule:** If both duration and attempts are populated, the Waiting Room terminates as soon as **either** threshold is reached.

### 6.3 Re-Fireable Webhooks in Queues
To prevent spamming external systems, Retreaver re-executes only webhooks explicitly marked **Re-fireable** during Waiting Room loops:
- Applicable webhook triggers:
  - *Data-Appending ping*
  - *Passthrough ping*
  - *When a call comes in*
- *Buyer Selection Rule:* Webhooks triggered on *When a buyer is selected* with *Hold caller until completion* enabled are **re-fireable by default**.
- Operators must toggle `Re-fireable: ON` on ping-post availability webhooks to enable real-time capacity polling while callers wait.

### 6.4 Billing & Telemetry
- **Billing Rate:** Billed at **2x standard per-minute call rate** for the exact duration spent in the queue.
- **Billing Rounding:** Time in the Waiting Room rounds up to the next whole minute (e.g., 20 seconds = 1 billed minute).
- **Audit Entries in Call Debug Log:**
  - `"Holding caller until a buyer becomes available"`
  - `"Waiting room expired"`

---

## 7. Geo Data Handling & Location Precedence

Retreaver normalizes location attributes (Country, State, City, Zip) into structured `geo` tags (`us`, `us-ca`, `us-90210`, `310`) to drive geographic routing matrices.

### 7.1 Geo Resolution Hierarchy (Precedence Order)
Location data is resolved according to strict priority:
1. **RTB Inbound Request:** Pre-call reservation ping sending `caller_zip` or `geo`. Takes absolute precedence over automated lookups.
2. **Data Writing API:** Pre-call or mid-call data injection keyed by caller number or UUID. Overrides phone and carrier inference.
3. **Webhook Response Overwrite:** Mid-call JSON responses from Start or Data Append webhooks (e.g., Retreaver IQ / Audience Acuity).
4. **ZIP Prompt IVR:** Direct caller DTMF entry.
5. **Carrier-Supplied Geo:** Telco signaling metadata captured at inbound connection.
6. **Caller Number Geo:** NPA-NXX phone number parsing lookup.

### 7.2 Campaign Geo Toggles
Located under Campaign -> `Toggles` -> `Geo Data Handling`:
- **Use Caller Number geo information (Default: ON):** Derives city, state, zip from the caller's phone number NPA-NXX. If disabled, phone-derived zip tags are not generated.
- **Use carrier geo information (Default: ON):** Extracts location parameters delivered in the carrier's inbound webhook. If disabled, carrier signaling location is discarded.

### 7.3 Webhook Geo Updates & Guardrail Tags
- When a webhook returns `caller_zip` or `geo:us-xxxxx`, Retreaver clears and replaces prior clearable geo tags.
- **Conditional Enrichment Guard:** To execute enrichment webhooks only when location is absent upstream (preventing unnecessary API costs):
  $$\text{Tag Filter Rule: } \mathtt{caller\_zip!\sim.+ }$$
  *(Matches only when `caller_zip` does not contain any characters).*

### 7.4 IVR ZIP Gathering Logic
- **`ZIP code entry — unless already present`:** Plays DTMF collection prompt only if the caller is US-based and lacks a `geo:us-xxxxx` tag. Skips if RTB, Data Writing, Carrier, or Number inference already populated a zip.
- **`ZIP code entry — always`:** Plays for all US callers regardless of existing tags. Overwrites previous zip and geo tags upon valid 5-digit entry. Requires explicit activation by Retreaver support. If both prompts exist, `always` takes precedence.

---

## 8. Call Flow Execution & Debugging

The Call Flow interface reconstructs the step-by-step routing sequence for every call.

### 8.1 Accessing Call Flow
Navigate to `Calls` (Call Log) -> Click on the target call's **UUID** link -> Scroll to the bottom of the Call Overview screen.

### 8.2 Event Color Matrix
Events appear in reverse-chronological order:
- **Blue (Informative):** State changes, tag assignments, webhook dispatches, timer starts.
- **Green (Connection):** Successful call bridging, buyer connection, positive answer state.
- **Yellow (Warning):** Non-fatal routing conditions (endpoint capped, business hours closed, weight bypass).
- **Red (Problem / Error):** Failed bridges, webhook timeouts, carrier reject codes, no buyers matched.

### 8.3 Buyer Routing Inspection
During each routing phase, the log details every Buyer evaluated in priority order. If a buyer was skipped, the log records the exact reason:
- `Closed` (Outside business hours or holiday schedule)
- `Capped` (Hit concurrency, hourly, daily, or monthly limits)
- `Not matching tags` (Tag evaluation failure: required tag missing, forbidden tag present, or value mismatch)

---

## 9. AI Analyst Engine

Retreaver AI Analyst utilizes automated speech-to-text and language modeling to evaluate call recordings without manual listening.

### 9.1 Scoping and Hierarchy
- Accessible to **Superuser** accounts.
- Execution levels:
  - *Call Log Sampling (Ad-hoc):* Run on filtered historical calls directly within Call Log 2.0.
  - *Automated Pipeline:* Configurable at the **Campaign**, **Publisher**, **Buyer**, or **Buyer Group** level.

### 9.2 Configuration Controls
- **Transcription Window:** Options for Full Call, First $X$ Minutes, or Last $X$ Minutes (recommended: $\ge$15 minutes for accurate outcome capture).
- **Volume Sampling Caps:** Throttles cost by restricting runs to $N$ calls per hour, day, or month.
- **Automated Filters:** Analyzes only calls meeting specific criteria (e.g., `Receivable calls only`, `Completed calls only`, or specific tag matches).
- **Custom Prompts:** Injects custom QA inquiries (e.g., *"Did the agent read the compliance disclaimer?"*, *"Did the caller confirm Medicare Part A and B?"*).

### 9.3 Structured Output Tags & Webhook Tokens
AI Analyst writes structured tags to the call record upon completion:
- **Intent Analysis:** Primary topic, caller motivation, supporting evidence from transcript.
- **Disposition Analysis:** Call outcome (e.g., `Appointment Set`, `Qualified Lead`, `Sale Completed`, `Hangup`, `Transfer Failed`), loss reason, termination reason.
- **Webhook Integration (`After AI Analysis`):**
  - Triggers immediately after AI Analyst completes processing.
  - Supported tokens:
    - `[disposition_positive_outcome]`
    - `[disposition_stage_reached]`
    - `[disposition_disposition_code]`
    - `[disposition_primary_loss_reason]`
    - `[disposition_termination_reason]`
    - `[disposition_transfer_outcome]`
    - `[disposition_summary]`
    - `[intent_primary_topic]`
    - `[intent_summary]`
    - Custom prompt tags (e.g., `[ai_compliance_pass]`)
- **Pricing:** Billed usage-based at \$0.05 per transcribed minute (\$3.00/hour).

---

## 10. Analytics, Reporting & Data Extraction

### 10.1 ClickHouse Analytical Architecture
Retreaver stores call events, attributes, and tags in an underlying analytical datastore (ClickHouse-backed storage architecture).
- **Tag Rollups & Dimensions:** Every attribute written via RTB, Data Writing, Retreaver.js, Webhooks, or AI Analyst functions as an indexed reporting dimension. Operators can aggregate, filter, and pivot metrics across:
  - Core financial metrics: Revenue, Payout, Margin, RPC (Revenue Per Call).
  - Time series: Real-time, hourly, daily, weekly, monthly cohorts.
  - Attribution keys: Campaign, Publisher (`AFID`), Sub-Publisher (`sub_id`), Buyer Endpoint, Inbound DID.
  - Custom tag keys: UTM parameters, geo tags, intent codes, disposition codes.

### 10.2 Call Log Dashboards (1.0 vs. 2.0)
- **Call Log 1.0 (`/calls`):** Classic interface with bottom-anchored CSV export, column resizing, and browser-stored filter configurations saved per Company.
- **Call Log 2.0 (`/calls_new`):** Modernized real-time analytical table featuring instant multi-tag filtering, inline audio playback, AI Analyst batch initiation, and top-right CSV export.
- Key default columns: `Via` (Call medium & status), `UUID` (Flow link), `Number` (DID dialed), `Call Publisher` (Source), `Call Endpoint` (Buyer), `Duration`, `Revenue`, `Payout`.

### 10.3 CSV Export Workflows
- **Ad-hoc Browser Export:**
  - Apply desired filters (date ranges, tags, campaign, publisher).
  - Click `CSV Export` (top-right in Call Log 2.0; bottom in Call Log 1.0).
  - File is compiled asynchronously and downloaded directly via browser.
- **Scheduled Automated Exports:**
  - Navigate to `Exports` -> `New Call Export` (`https://retreaver.com/reports/calls/new`).
  - Toggle `Scheduled` to active.
  - Set delivery frequency: `Daily`, `Weekly`, `Bi-weekly`, or `Quarterly`.
  - Configure target email recipient list.
  - Customize column schema: Select exactly which metadata, financial fields, and custom tags are exposed to recipients (useful for sanitizing sensitive buyer/publisher data).
  - *Collaborator Alternative:* Rather than emailing recurring CSV files, operators can provision restricted Collaborator logins for Publishers or Buyers, granting them scoped access to their respective Call Logs and real-time reports.
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
# Retreaver Webhooks, Timers, Configurator & Integrations — Operator Manual

This reference provides operational rules, execution mechanics, timing lifecycles, configuration templates, and third-party data appending specifications for Retreaver's webhook and integration subsystems.

---

## 1. Webhook Architecture & Execution Hierarchy

Retreaver webhooks execute HTTP requests to send and receive call data across four distinct platform levels:

1. **Company Level ("Default Webhooks")**: Inherited across all campaigns in the company. Avoids redundant setup for universal logging, master CRMs, or global compliance endpoints.
2. **Campaign Level**: Executes based on campaign-wide routing lifecycle events (Start, Selected, Answered, Connect, Conversion, Non-Conversion, Timer, Always).
3. **Number Level**: Can be "unlocked" (via the lock icon) on an individual tracking number to clone and override campaign webhooks. Used for dedicated media sources (e.g., TV broadcasts) requiring custom payload destinations or tokens.
4. **Buyer Level**: Configured on Call Endpoints (Buyers) primarily for Real-Time Bidding (RTB) pings and dynamic transfer number extraction.
5. **Publisher Postback Level**: Inbound postback keys issued on Publisher profiles allowing publishers to push pre-call or post-call attributes into Retreaver.

### Tag Filtering ("Matches" Field)
Every webhook configuration supports a **Matches** tag filter. If tags are defined under Matches, the webhook will **only fire** if those exact tag criteria evaluate to `true` on the active call.

---

## 2. Webhook Triggers & Lifecycles

Retreaver divides webhook execution into two runtime engines: **Real-Time Synchronous Engine** (pings/calls in-flight) and **Browser Emulated Engine** (post-call / asynchronous events).

| Trigger Name | Execution Engine | Trigger Point | Custom Headers Supported? | Primary Use Case |
|---|---|---|---|---|
| **Data-appending Ping** | Real-Time | Pre-routing, before passthrough pings | Yes | Pre-fetching demographic/location tags (e.g., Retreaver IQ) to inform subsequent pings. |
| **Pass-through Ping** | Real-Time | Start of call / RTB reservation | Yes | RTB buyer pre-pings; affiliate networks pinging to calculate potential bid profitability. |
| **Start** | Real-Time | Instant call enters campaign | Yes | Fetching initial caller profile/tags synchronously or dispatching CRM call notifications. |
| **Post Zip** | Real-Time | Immediately after caller enters IVR ZIP | Yes | Dynamic routing recalculation based on collected postal code. |
| **Selected** | Real-Time | Moment an endpoint/buyer is selected | Yes | Pre-populating agent screen pops before connection. *(Caution: Fires again if first buyer fails).* |
| **Answered** | Real-Time | Moment call is answered by buyer | Yes | Verifying agent connection and logging connected buyer identity without leakage risk. |
| **After AI Analysis** | Real-Time / Event | When AI Analyst completes processing | Yes | Pushing call intent, disposition, and AI summary tags to external data lakes. |
| **Recording Available** | Real-Time / Event | Audio recording rendered | Yes | Syncing MP3/WAV recording URLs with call records in CRM/QA platforms. |
| **Timer** | Browser Emulated | Call reaches specified duration (sec) | **No** | In-call milestones, mid-call analytics, or duration-based conversion triggers. |
| **Conversion** | Browser Emulated | Campaign conversion criteria met | **No** | Payout/revenue attribution to publisher networks (e.g., Ringba, Cake). |
| **Non-Conversion** | Browser Emulated | Call terminates without converting | **No** | Logging unbilled/unconverted calls to lead recovery or remarketing. |
| **Connect** | Browser Emulated | Call successfully connects to buyer | **No** | Post-call reporting on completed connections. |
| **Postback** | Browser Emulated | Inbound postback received on call | **No** | Chained processing when external conversion postbacks land. |
| **Always** | Browser Emulated | Call termination (after all others) | **No** | Final disposition sync to CRM, data warehouses, and reporting tables. |

---

## 3. Retreaver Timer Subsystem Mechanics

Retreaver's routing and webhook engine coordinates four distinct timer patterns across execution lifecycles:

### A. HTTPTimer (Call Duration Webhook Timer)
- **Role**: Triggers a webhook request when the live call reaches a precise duration threshold.
- **Trigger**: `Timer` (Browser Emulated).
- **Execution**: Configured with a duration field (in seconds). When the connected call timer reaches the threshold, the HTTP request fires asynchronously.
- **Constraint**: Operates under the Browser Emulated bot engine; **does not support custom HTTP headers**. All parameters must be in the URL query string.

### B. PassthroughTimer / RTB Dynamic Conversion Timer
- **Role**: Dynamically establishes the billable conversion threshold on a per-call basis via RTB response payloads.
- **Execution**:
  - In an RTB ping/post flow, the buyer's endpoint returns a required hold duration (e.g., `{"retreaver_seconds": 90}`).
  - Retreaver maps this into an internal tag (`final_conversion_timer_tag`) via the `PingOutputMap` or `PostOutputMap`.
  - The campaign sets the conversion hold duration dynamically to this received value rather than a static campaign default.

### C. PingTimer (Webhook Execution & Timeout Window)
- **Role**: Governs the timeout window allowed for synchronous webhook execution before Retreaver advances call routing.
- **Threshold**: Strict **5-second timeout window** across real-time pings (Start, Selected, RTB Ping, Data-Append).
- **Failure Behavior**: If the external endpoint does not respond within 5 seconds, Retreaver treats the ping as failed, logs a timeout error, and falls back to default routing or skips the buyer. Recommended partner SLA is **<1.0 second**.

### D. PostbackTimer (Postback Storage & End-Call Cut-Off Window)
- **Role**: Governs the retention and pairing window for asynchronous call data writing.
- **Pre-Call Storage**: When a publisher sends pre-call data via `caller_number`, Retreaver stores the payload until the inbound call arrives (configured storage duration).
- **Post-Call Cut-Off**: When configuring a Postback Key, operators define an **end call cut-off time**. Data writing requests received after the cut-off are rejected to prevent retroactive alteration of finalized calls.

---

## 4. Retreaver Webhook Configurator Engine

The Retreaver Webhook Configurator (`https://retreaver.com/webhook-configurator/v1/`) translates standard Retreaver GET requests into complex, multi-stage JSON ping-post workflows, buyer tagging, and math transformations.

### Base Endpoint & Required URL Parameters
```text
https://retreaver.com/webhook-configurator/v1/?call_key=[call_key]&call_uuid=[call_uuid]&output_tag_prefix=<prefix>&ping_url=<url>
```

### Full Configurator Parameter Reference
| Parameter | Type | Required? | Description |
|---|---|---|---|
| `call_key` | Token | **Yes** | `[call_key]` — Authenticates and tags the active call. |
| `call_uuid` | Token | **Yes** | `[call_uuid]` — Unique call identifier. |
| `output_tag_prefix` | String | **Yes** | Snake_case prefix prepended to all output tags (e.g., `ping_bid_id` becomes `<prefix>_ping_bid_id`). |
| `ping_url` | URL | **Yes** | Destination endpoint for the initial HTTP ping. |
| `ping_method` | Enum | No | `GET` or `POST` (default: `GET`). |
| `ping_headers` | JSON | No | Stringified headers: `{"Content-Type":"application/json"}`. |
| `ping_data` | JSON | No | Stringified body with replacement tokens: `{"caller_zip":"[caller_zip]"}`. |
| `ping_output_map` | JSON | No | Extracts response properties to tags: `{"PingOutputMap":{"target_tag":"json.path"}}`. |
| `send_post` | Boolean | No | `TRUE` or `FALSE` — Enables 2-step Ping-Post flow. |
| `post_condition_key` | String | No | Tag name evaluated to decide whether to fire post. |
| `post_condition_operator`| Enum | No | `is_greater_than`, `is_less_than`, `is_equal`, `is_unequal`, `exists`. |
| `post_condition_value` | String/Num| No | Comparison threshold (e.g., `0`, `success`). |
| `post_url` | URL | No | Destination endpoint for follow-up post. |
| `post_method` | Enum | No | `GET` or `POST`. |
| `post_headers` | JSON | No | Headers for post request. |
| `post_data` | JSON | No | Payload for post request, supporting `<podd>` tokens. |
| `post_output_map` | JSON | No | Extracts post response properties to tags. |
| `payout_output_tag` | Tag Key | No | Tag storing payout to be multiplied. |
| `payout_modifier_percentage` | Float | No | Multiplier (`0.0` to `1.0`). |
| `revshare_output_tag` | Tag Key | No | Tag storing revenue to be multiplied. |
| `revshare_modifier_percentage`| Float | No | Multiplier (`0.0` to `1.0`). |
| `timer_offset_tag` | Tag Key | No | Tag storing conversion timer duration. |
| `timer_offset_modifier`| Integer | No | Seconds added/subtracted (`-999` to `999`). |
| `ping_decode_url_parameters` | Boolean | No | `TRUE` to decode incoming URL query parameters. |
| `post_decode_url_parameters` | Boolean | No | `TRUE` to decode post parameters. |

### Ping Output Dependent Data (PODD)
PODD enables values parsed during the `ping` stage to be injected into the `post` request URL or body.
- **Syntax**: `<podd_start>tag_key<podd_end>`
- **Quoted string syntax**: `"<podd_start>tag_key<podd_end>"`
- **Example in `post_url`**: `&post_url=<podd_start>confirmation_url<podd_end>`
- **Example in `post_data`**: `&post_data={"bid_id":"<podd_start>ping_bid_id<podd_end>"}`

### URI Encoding Rules in Configurator Templates
Because the entire configurator definition is passed within a single URL query string, nested special characters **MUST** be percent-encoded:
- `?` → `%3F` (sub-parameter start)
- `&` → `%26` (parameter separator inside payloads)
- `=` → `%3D` (parameter value assignment inside payloads)
- `"` → `%22` (JSON property wrappers)
- ` ` (space) → `%20` or `+`
- `[` → `%5B` and `]` → `%5D` (prevent premature Retreaver token parsing if literal)

---

## 5. Webhook Output Modifiers

Output Modifiers execute mathematical transformations on webhook response values before they are committed as call tags. They are located under **Toggle Optional Output Modifiers** in the webhook setup.

```text
+-----------------------+      +---------------------------+      +---------------------+
| Webhook JSON Response | ---> | Ping/Post Output Map      | ---> | Output Modifiers    | ---> Call Tags
| {"bid": {"pay": 20}}  |      | payout_tag = "bid.pay"    |      | Token: payout_tag   |      (payout = 10)
+-----------------------+      +---------------------------+      | Multiplier: 0.5     |
                                                                  +---------------------+
```

### Modifier Fields & Operations
1. **Payout Token**: Identifies the output tag created in `ping_output_map` / `post_output_map` containing base payout.
2. **Payout Multiplier**: Float between `0.0` and `1.0`. Formula: `Final Payout = Base Payout * Multiplier`.
3. **Revenue Token**: Identifies the output tag containing base revenue.
4. **Revenue Multiplier**: Float between `0.0` and `1.0`. Formula: `Final Revenue = Base Revenue * Multiplier`.
5. **Timer Token**: Identifies the output tag containing base timer seconds.
6. **Timer Modifier**: Integer between `-999` and `999`. Formula: `Final Timer = Base Timer + Modifier` (supports negative offsets to shorten hold requirement).

---

## 6. Real-Time Response Data Writing & Appending

### Synchronous JSON Parsing
When a synchronous ping (Start, Data-Append, Pass-Through) returns `200 OK` with `Content-Type: application/json`:
- All root-level key/value pairs are automatically written as tags on the active call.
- **Array Support**: `{"product_interest": ["mortgage", "insurance"]}` writes multiple tags: `product_interest:mortgage` and `product_interest:insurance`.
- **Geo Override**: Returning `{"geo": "us-90210"}` overrides carrier/area code inference, automatically writing country `us`, state `us-ca`, and zip `90210`.

### Asynchronous Call Data Writing API
Used to record lead information before a call arrives or outcomes/dispositions after a call terminates.
- **Endpoint**: `https://retreaverdata.com/data_writing`
- **Key Scopes**:
  - `Company`: Global access across all company calls.
  - `Buyer Group`: All calls routed to any buyer in the group.
  - `Buyer`: Strictly isolated to calls routed to that specific buyer.
  - `Publisher`: Strictly isolated to calls attributed to that publisher.
- **Addressing**:
  - **Pre-Call**: Use `caller_number=E164_NUMBER`. Stored and applied to the next inbound matching call.
  - **Post-Call**: Use `call_uuid=CALL_UUID`. Pinpoints the exact completed call session (prevents collision on repeat callers).
- **Syntax**:
  ```text
  https://retreaverdata.com/data_writing?key=KEY&caller_number=14155550123&prequalified=true&credit_score=720
  ```
- **Response**:
  ```json
  {"tag_values":{"prequalified":"true","credit_score":"720"},"caller_number":"+14155550123","status":"call not found, tags stored"}
  ```

---

## 7. Third-Party Integrations Reference

### Retreaver IQ (by Audience Acuity)
Enriches inbound callers with TransUnion-backed demographic, geographic, and postal intelligence. Billed at **$0.03 per successful pull**.

#### Workflow Implementations:
1. **Option 1: Ping Request First (RTB Pre-Ping / Postback Key Workflows)**
   - *Requirement*: Campaign Webhook with trigger **Data Append**.
   - *URL*: `https://retreaver.com/webhook-integration/retreaver-iq`
   - *Behavior*: Enriches call before passthrough pings or RTB buyer pings fire, ensuring `caller_zip` is available for buyer bid algorithms.
2. **Option 2: Direct Call Transfer First (No Ping)**
   - *Requirement*: Enable campaign under `Integrations → Retreaver IQ by Audience Acuity`. No Data Append webhook needed.
3. **Option 3: Hybrid Traffic (Both Ping First & Direct Calls)**
   - *Requirement*: **Both** the Integration toggle AND the Data Append webhook must be enabled.

### Anura Anti-Fraud Integration
Blocks fraudulent, bot, and invalid lead traffic prior to campaign routing:
1. Web asset loads Anura script (`https://script.anura.io/request.js`) and callback handler.
2. Anura generates authenticity score, populating hidden inputs: `anuratextresponse` and `anuratextresponsecode`.
3. Retreaver Real-Time Tracking script (`Retreaver.js`) captures form values and attaches them to the caller ID:
   ```javascript
   number.replace_tags({
     anura_response: $('input[name="anuratextresponse"]').val(),
     anura_code: $('input[name="anuratextresponsecode"]').val()
   });
   ```
4. Retreaver Tags created: `anura_code` and `anura_response` (disable prompts, color `#03E6FF`).
5. Buyer Routing Gate: Buyer tag criteria set to `anura_code:good` (or `anura_code!=bad`). Fraudulent traffic is skipped or routed to rejection/IVR.

### Twilio Application Connect
Hands off live calls from Twilio voice applications into Retreaver using an authenticated HMAC-SHA256 signature without transferring DIDs:
- **Canonical String Format**:
  ```text
  canonical = `${OriginalTo}:${OriginalCallSid}:${RetreaverPhoneNumber}:${RetreaverCompanyId}`
  ```
- **Signature Computation**: `HMAC-SHA256(canonical, RETREAVER_SECRET).toHex()`
- **TwiML Hand-Off Payload**:
  ```xml
  <Response>
    <Dial>
      <Application applicationSid="RETREAVER_APPLICATION_SID">
        <Parameter name="OriginalTo" value="+14155550123" />
        <Parameter name="OriginalCallSid" value="CA1234567890abcdef" />
        <Parameter name="RetreaverPhoneNumber" value="+18005551234" />
        <Parameter name="RetreaverCompanyId" value="1234" />
        <Parameter name="RetreaverSignature" value="computed_hmac_hex" />
      </Application>
    </Dial>
  </Response>
  ```

---

## 8. Webhook Testing & Diagnostics

### Test Fire Webhook Tool
Built into the webhook configuration UI to simulate live calls and RTB buyer pings without dialing:
- **Synthetic Test Caller**: Fictional NANP caller `+121255501XX`.
- **Default Location**: New York, NY 10001 (`geo:us-ny`, `geo:us-10001`).
- **Publisher Simulation**: Selectable publisher dropdown automatically populates `[publisher_id]`.
- **Tag Simulation**: Custom `key:value` tags can be injected into the test run (e.g., `state:fl`, `campaign:medicare`).
- **Inspection Metrics**: Returns response status code, latency (ms), request headers, response headers, response body, and raw debug timeline.

### Common Failure Modes & Troubleshooting
| Symptom | Root Cause | Operator Remediation |
|---|---|---|
| **Timeout (504)** | Endpoint latency exceeds 5.0s window | Ensure partner endpoint responds <1.0s; offload post-call processing to background queues. |
| **Invalid JSON** | Malformed response payload or bad headers | Validate JSON syntax; verify `Content-Type: application/json` is returned. |
| **Missing Fields** | Response does not match `PingOutputMap` | Inspect exact response keys; verify case sensitivity in output map mappings. |
| **Headers Not Sent** | Configured on Browser Emulated trigger | Move header requirements to synchronous triggers (Start, Selected, Ping) or pass credentials via URL query parameters. |
| **Tokens Unexpanded** | Tokens placed in HTTP Header values | Tokens (`[caller_number]`, `[call_uuid]`) are **only** substituted in the webhook URL, not in custom header values. |
| **Pings Fire Prematurely**| Data-append missing before RTB pings | Add `Data Append` webhook trigger before passthrough pings to ensure enrichment data is stored first. |
