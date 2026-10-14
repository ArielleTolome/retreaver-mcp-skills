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
