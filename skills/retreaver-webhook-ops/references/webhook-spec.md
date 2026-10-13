# Retreaver Webhooks, Timers, Configurator & Integrations Specification

## 1. Architectural Overview & Entity Ownership

Retreaver Webhooks (represented internally as `timers`) fire HTTP requests (via child `pixels`) across five lifecycle hierarchy levels:
- **Company (`timerable_type: "Company"`)**: Inherited across all campaigns in the company. Ideal for master CRM syncing, data lakes, and global compliance endpoints.
- **Campaign (`timerable_type: "Campaign"`)**: Triggered by campaign-level routing lifecycle events (Start, Selected, Answered, Conversion, Non-Conversion, Timer, Always).
- **Tracking Number (`timerable_type: "Number"`)**: Overrides or clones campaign webhooks for specific DIDs requiring dedicated payload formatting or affiliate attribution.
- **Target / Buyer (`timerable_type: "Target"`)**: Configured on Call Endpoints (Buyers) for Real-Time Bidding (RTB) pings and dynamic transfer number extraction.
- **Publisher Postback Key**: Inbound postback access keys enabling publishers to write attributes into calls pre- or post-call.

---

## 2. Trigger Types & Execution Lifecycles

Retreaver divides webhook execution into two distinct engines:
1. **Real-Time Synchronous Engine**: Executes while the call routing is in progress. Strict 5.0-second timeout window (recommended SLA <1.0s). Supports custom HTTP headers.
2. **Browser Emulated Engine**: Fires asynchronously or post-call. Does **not** support custom HTTP headers; all payload attributes must be query string parameters.

### Trigger Type ID Mapping

| Trigger ID | Enum Name | Execution Engine | Trigger Point | Headers Supported? | Primary Use Case |
|---|---|---|---|---|---|
| `0` | `connect` | Browser Emulated | Buyer answers and connects | No | Completed call connection reporting |
| `1` | `always` | Browser Emulated | Call termination | No | Final disposition & tag sync to CRM |
| `2` | `timer` | Browser Emulated | Duration reaches threshold | No | Mid-call milestone, duration-based ping |
| `3` | `postback` | Browser Emulated | Inbound postback received | No | Chained postback forwarding |
| `4` | `bridged` | Real-Time | Target selected / bridging | Yes | Data posting / screen-pop delivery |
| `5` | `conversion` | Browser Emulated | Conversion criteria met | No | Publisher payout attribution |
| `6` | `non_conversion`| Browser Emulated | Call ends unconverted | No | Lead recovery / remarketing log |
| `7` | `cake_buyer` | Real-Time | CAKE platform integration | Yes | Specialized CAKE buyer post |
| `9` | `start` | Real-Time | Call enters campaign | Yes | Ping-post RTB, caller lookup |
| `10` | `answered` | Real-Time | Call answered by buyer | Yes | Live agent connect confirmation |
| `11` | `post_zip` | Real-Time | Caller enters IVR ZIP code | Yes | Dynamic rerouting based on ZIP |
| `12` | `passthrough` | Real-Time | Pre-routing buyer RTB ping | Yes | RTB buyer reservation & dynamic DID |
| `13` | `data_appending` | Real-Time | Pre-routing data append | Yes | Retreaver IQ / demographic lookup |
| `14` | `composite_analysis_complete` | Real-Time/Event | AI analysis finishes | Yes | Pushing AI transcripts / summaries |
| `15` | `recording_available` | Real-Time/Event | Recording rendered | Yes | Syncing audio recording URLs |

---

## 3. Retreaver Timer Subsystem Mechanics

### A. HTTPTimer (Call Duration Webhook Timer)
- **Role**: Triggers an HTTP request when an active call reaches a defined duration threshold.
- **Trigger**: `trigger_type: 2` (`timer`).
- **Configuration**: `seconds` parameter defines the duration threshold in seconds.
- **Engine**: Browser Emulated. No custom headers supported.

### B. PassthroughTimer / RTB Dynamic Conversion Timer
- **Role**: Establishes dynamic conversion hold duration per call returned by an RTB buyer.
- **Configuration**: Webhook extracts buyer hold time (e.g. `buyers[0].offer_conversion_duration`) to internal tag (`timer_offset_tag` or `final_conversion_timer_tag`).
- **Campaign Setting**: Buyer conversion criteria reads the dynamic seconds tag rather than static campaign hold time.

### C. PingTimer (Execution Timeout Window)
- **Role**: Maximum latency allowed for synchronous webhook execution before Retreaver advances call routing.
- **Window**: Strict **5.0 seconds** ceiling across `start`, `passthrough`, `data_appending`, `post_zip`.
- **Behavior**: If endpoint exceeds 5.0s, request aborts, failure is logged, and routing advances to fallback targets. Partner SLA must be <1.0s.

### D. PostbackTimer (Storage & Cut-Off Retention)
- **Role**: Retention and pairing window for asynchronous call data writing.
- **Pre-Call Storage**: Attributes posted to `caller_number` are retained until matching call lands (configured storage duration).
- **Post-Call Cut-Off**: Postback keys define an end-call cut-off time. Writes received after cut-off are rejected.

---

## 4. Retreaver Webhook Configurator Engine

Base Configurator URL:
```text
https://retreaver.com/webhook-configurator/v1/?call_key=[call_key]&call_uuid=[call_uuid]&output_tag_prefix=<prefix>&ping_url=<url>
```

### Configurator Parameters

| Parameter | Type | Required? | Description |
|---|---|---|---|
| `call_key` | Token | Yes | `[call_key]` — Tags the active call session |
| `call_uuid` | Token | Yes | `[call_uuid]` — Unique call session UUID |
| `output_tag_prefix` | String | Yes | Prefix for extracted tags (e.g., `callgrid_148422`) |
| `ping_url` | URL | Yes | Destination endpoint for HTTP ping |
| `ping_method` | Enum | No | `GET` or `POST` (default: `GET`) |
| `ping_headers` | JSON | No | Encoded stringified headers: `{"Content-Type":"application/json"}` |
| `ping_data` | JSON | No | Encoded body with replacement tokens |
| `ping_output_map` | JSON | No | Extracted response tags: `{"PingOutputMap":{"target_tag":"json.path"}}` |
| `send_post` | Boolean | No | `TRUE` / `FALSE` — Enables 2-step Ping-Post flow |
| `post_condition_key` | String | No | Tag name evaluated to decide post execution |
| `post_condition_operator` | Enum | No | `is_greater_than`, `is_less_than`, `is_equal`, `is_unequal`, `exists` |
| `post_condition_value` | String | No | Threshold value (e.g. `accepted`, `0`) |
| `post_url` | URL | No | Destination endpoint for post (supports `<podd>` tokens) |
| `post_method` | Enum | No | `GET` or `POST` |
| `post_headers` | JSON | No | Encoded headers for post request |
| `post_data` | JSON | No | Encoded payload for post request |
| `post_output_map` | JSON | No | Extracted post response tags |
| `payout_output_tag` | Tag Key | No | Tag storing payout to be multiplied |
| `payout_modifier_percentage` | Float | No | Multiplier (`0.0` to `1.0`) |
| `revshare_output_tag` | Tag Key | No | Tag storing revshare to be multiplied |
| `revshare_modifier_percentage` | Float | No | Multiplier (`0.0` to `1.0`) |
| `timer_offset_tag` | Tag Key | No | Tag storing conversion timer duration |
| `timer_offset_modifier` | Integer | No | Seconds added/subtracted (`-999` to `999`) |

### Ping Output Dependent Data (PODD)
Values extracted during `ping` stage are injected into `post_url` or `post_data` using:
- Syntax: `<podd_start>tag_key<podd_end>`
- Example: `&post_url=https://api.leadspedia.com/post?lead_id=<podd_start>lead_id<podd_end>`

---

## 5. Webhook Output Modifiers

Math transformations applied to webhook responses before writing tags:
- **Payout Modifier**: `Final Payout = Base Payout * payout_modifier_percentage`
- **Revshare Modifier**: `Final Revenue = Base Revenue * revshare_modifier_percentage`
- **Timer Modifier**: `Final Timer = Base Timer + timer_offset_modifier` (supports negative offsets)

---

## 6. Pre-Built Configurator Templates

- **CallGrid Bid (`callgrid_bid`)**: Ping to `bid.callgrid.com` returning `dynamicBid`, `dynamicDuration`, `dynamicPhoneNumber`. Maps to prefix tags: `bid`, `timer`, `number`.
- **TrackDrive Ping-Post (`track_drive_ping_post`)**: 2-step flow. Ping checks `status == accepted`, extracts `ping_id`, posts via `<podd_start>ping_id<podd_end>` to obtain `forwarding_number`.
- **Leadspedia Ping-Post (`leadspedia_ping_post`)**: 2-step flow. Ping extracts `request_number_url`, posts directly to the returned URL to receive `number`, `duration`, `payout`.
- **Anura Anti-Fraud**: Pre-routing evaluation capturing `anura_code` (`good`/`bad`) and `anura_response` via web form scripts or API, gating buyer routing.
