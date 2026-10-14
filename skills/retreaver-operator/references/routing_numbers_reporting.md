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
