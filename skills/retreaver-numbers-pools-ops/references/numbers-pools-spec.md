# Retreaver Tracking Numbers, Dynamic Number Pools, and SIP Routing Specification

## 1. Tracking Numbers (`numbers.read`, `numbers.manage`)

Retreaver tracking numbers (DIDs) serve as the inbound entry point for PSTN and SIP call traffic. Each number belongs to a parent Campaign (`campaign_id`) and optionally maps to a specific Publisher/Affiliate (`affiliate_id`) or Dynamic Number Pool (`number_pool_id`).

### 1.1 Toll-Free vs. Local Inventory
- **Toll-Free Numbers (`toll_free: true`):** US/Canada prefixes (`800`, `888`, `877`, `866`, `855`, `844`, `833`). Provisioned instantaneously from wholesale carrier inventory; suited for national campaigns and high-velocity DNI pools.
- **Local Numbers (`toll_free: false`):** Geographically scoped to specific US/Canada NPA area codes (`area_code_id`) and rate centers.
- **Lifecycle & Quarantine:** Deleting a number (`numbers.manage` with `action: "delete"`) places it into a carrier cooling-off quarantine period to drain residual dial-backs before returning it to wholesale pools.

### 1.2 Tracking Number Attributes
| Field | Type | Description |
| :--- | :--- | :--- |
| `number_id` | Integer | System primary key of the tracking number. |
| `number` | String | E.164 formatted phone number (e.g., `"+18885551212"`). Omit on create to auto-provision. |
| `name` | String / Null | Human-readable label for the placement or ad creative. |
| `campaign_id` | Integer | Parent Campaign ID governing default routing, prompts, conversions, and webhooks. |
| `affiliate_id` | Integer / Null | Assigned Publisher / Affiliate ID (`AFID` attribution owner). |
| `number_pool_id` | Integer / Null | Associated Dynamic Number Pool ID if managed by DNI. |
| `tag_list` | String | Comma-separated `<<<key:value>>>` tokens stamped onto every call arriving on this DID. |
| `paused` | Boolean | Administrative toggle (`true` blocks inbound calls; `false` resumes). |
| `toll_free` | Boolean | Indicates toll-free (`true`) vs. local (`false`) DID type. |
| `country` | String / Null | ISO country code (default `"US"`). |
| `time_zone` / `iana_time_zone` | String / Null | Schedule timezone for number-level business hours and caps. |
| `target_number` | String / Null | Direct forwarding destination override when configured. |
| `extensions_enabled` | Boolean | Enables direct extension dialing on the tracking number. |
| `locked` | Boolean | Prevents automatic pool reassignment or collaborator modification. |

### 1.3 Surgical Inheritance Overrides (`*_use_cs`)
By default, every tracking number inherits four operational blocks from its parent Campaign:
1. `routing_use_cs` (`Boolean`): Inherit Campaign buyer routing table, priorities, weights, and criteria.
2. `greeting_use_cs` (`Boolean`): Inherit Campaign IVR greetings, whisper audio, hold music, and DTMF menus.
3. `timers_use_cs` (`Boolean`): Inherit Campaign timer configurations.
4. `conversions_use_cs` (`Boolean`): Inherit Campaign conversion duration thresholds and payout rules.

Setting any `*_use_cs` flag to `false` unlocks that block on the number, allowing surgical per-number IVR prompts, dedicated buyer queues, or custom conversion rules without mutating the parent Campaign.

---

## 2. Dynamic Number Pools & DNI Sizing (`number_pools.read`, `number_pools.manage`)

Dynamic Number Pools power `Retreaver.js` landing page Dynamic Number Insertion (DNI), dynamically leasing temporary phone numbers to active web visitors and recycling them after session expiration or call completion.

### 2.1 Concurrency & Pool Sizing Formula
Pool capacity is determined by concurrent active visitors within the lease window and the cardinality of tracked attributes:

$$\text{Pool Size} = \text{Peak Concurrent Visitors in Lease Window} \times \text{Unique Attribute Factor}$$

- **Shared Attribute Tracking (`per_visitor: false`):** Visitors sharing identical URL parameter tag values (e.g., same `utm_source` and `sub_id`) see the same leased number simultaneously. Total required numbers equals the number of active tag combinations.
- **Visitor-Level Tracking (`per_visitor: true`):** Every concurrent visitor receives an isolated tracking number. Mandatory when using **Step-in IVR** or **Google Analytics integration** (`google_analytics: true`) or when capturing unique click IDs (`gclid`, `click_id`, `fbclid`).

### 2.2 Lease Lifecycle & Recycling Parameters
| Field | Type | Recommended | Description |
| :--- | :--- | :--- | :--- |
| `max_pool_size` | Integer | Sized by concurrency | Hard ceiling on phone numbers automatically provisioned for this pool. |
| `reserve_size` | Integer | `2`–`10` (Local DIDs) | Standby numbers pre-acquired in advance so traffic surges assign numbers with zero carrier provisioning lag. |
| `buffer_seconds` | Integer | `60`–`300` | Grace window a number remains locked after a visitor closes the page before reassignment (protects visitors who write down the number). |
| `max_lease_seconds` | Integer | `300`–`1800` | Maximum duration a lingering page visitor can hold a lease without placing a call. Prevents tab-hoarders from exhausting the pool. |
| `per_visitor` | Boolean | `true` for ClickID/GA | Provisions a dedicated lease per individual browser visitor. |
| `toll_free` | Boolean | `true` | Provisions toll-free numbers (`true`) or local area code numbers (`false` with `area_code_id`). |
| `hide_embedded_access` | Boolean | `false` | When `true`, blocks publishers from provisioning static numbers on the campaign. |
| `google_analytics` | Boolean | `false` | Enables native GA goal completion firing via `[google_analytics_tracking_id]`. |

### 2.3 Lease Recycling Mechanics & Default Fallback Number
1. **Active Ping Refresh:** `Retreaver.js` periodically pings Retreaver while the visitor remains on the page, keeping the lease active up to `max_lease_seconds`.
2. **Post-Call Immediate Release:** When an inbound call terminates and no other active browser session holds that number, it returns to the available pool immediately.
3. **Pool Exhaustion Fallback:** If concurrent visitors exceed `max_pool_size`, `Retreaver.js` leaves the hardcoded HTML **Default Fallback Number** visible on the page. Callers still connect, though visitor-specific DNI tags are lost. Always tag the static fallback number with `<<<sub_id:default_number>>>` to monitor pool exhaustion in Call Logs.

---

## 3. Number-Level Caps & Granular Scheduling

Individual tracking numbers support connection and conversion throttling via their Business Hours schedule:
1. **Granular Time Windows:** Time blocks can be defined down to 1-minute granularity across all 7 days of the week (a single 00:00–24:00 block acts as a daily cap).
2. **Cap Metrics:**
   - **Connections:** Increments immediately when an inbound call bridges to a Buyer endpoint.
   - **Conversions:** Increments only when the call satisfies campaign/number conversion criteria.
3. **Cap Alerts:** Operators can configure percentage and numerical threshold alerts to notify before a placement's DID caps out.

---

## 4. SIP URI Routing Architecture (`sip:...`)

Retreaver supports end-to-end Session Initiation Protocol (SIP) trunking for both inbound DID termination and outbound buyer delivery, bypassing PSTN per-minute carrier transit fees.

### 4.1 Inbound SIP Termination (Sending Calls into Retreaver Numbers)
Any active Retreaver tracking number (E.164 `+1NXXNXXXXXX`) accepts inbound SIP traffic once enabled on the account:
- **Credential / Digest Authentication URI:**
  `sip:+1[E164Number]@retreaver.sip.twilio.com`
- **IP-Whitelisted Signaling URI:**
  `sip:+1[E164Number]@retreaver-ip.sip.twilio.com`

### 4.2 Outbound SIP Delivery (Routing to Buyer PBXs)
When configuring a Buyer (`Target`) or forwarding destination:
- **SIP Destination URI:** Format `number` as `sip:endpoint@domain.com`. Dynamic tag tokens are interpolated at call time (e.g., `sip:[buyer_id]@[tag_company].com`).
- **Authentication Modes:**
  1. *Unauthenticated:* Open SIP INVITEs to `sip:user@host`.
  2. *Digest Challenge (401/407):* Retreaver authenticates using configured `sip_username` and `sip_password`.
  3. *IP Whitelisting:* Recipient PBX allows signaling from Retreaver/Twilio proxy IPs.
- **Automatic Retreaver Context Headers:**
  Every outbound SIP INVITE includes:
  - `X-PH-RetreaverUUID`: Unique Call UUID.
  - `X-PH-RetreaverKey`: Campaign postback key.
  - `X-PH-RetreaverAFID`: Publisher / Affiliate ID (`afid`).
  - `X-PH-RetreaverSID`: Sub-affiliate ID (`sub_id`).
  Custom headers (e.g., `X-Campaign-ID: [campaign_id]`) can also be appended per endpoint.
