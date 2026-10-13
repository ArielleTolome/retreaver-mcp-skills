---
name: retreaver-buyer-ops
description: Configure and manage Retreaver call buyers (targets), priority, weight, timeout, volume/concurrency caps, business hours schedules, tag matching criteria, forward tags, and caller suppression lists.
metadata:
  role: operator
  allowed_tools: ["bash", "read", "edit", "write"]
---

## Role Contract
The `retreaver-buyer-ops` skill manages the lifecycle, traffic arbitration, capacity limits, business hours, and compliance filtering for Retreaver Call Buyers (Targets). It operates either via the Retreaver MCP API directly or through the provided CLI script `scripts/buyer_ops.py`.

Key operational domains:
- **Buyer Lifecycle:** Create, inspect, update, pause/resume, and duplicate buyers.
- **Traffic Arbitration:** Priority precedence (lower numerical value = higher priority, including negative numbers for VIP star performers), weight distribution within priority tiers, connection timeouts, and ring timers.
- **Capacity Management:** 5 distinct cap types (Concurrency, Hourly, Daily, Monthly, Hard), cap increment triggers (`connection` vs `conversion`), and hard cap zeroing.
- **Operating Schedules:** Business hours definition, 7-day multi-block shifts, timezone isolation, and invert windows.
- **Tag Filtering & Forward Tags:** Pre-selection routing tags (`==`, `!=`, `=~`, `!~`, numeric/date ranges) versus post-selection forward tag verification.
- **Caller Filtering & Suppression:** Campaign/Buyer caller lists (`suppressed*` vs `accepted*`), dynamic retention policies, and pipe-delimited regex text tag suppression (`caller_number:!~...`).

## Strict Invariants
1. **Numeric & Date Tag Registration:** Numeric (`<`, `<=`, `>`, `>=`), Date, and DateTime comparison tags MUST be registered via the Retreaver Tag Wizard prior to evaluation. Unregistered numeric tags evaluate as ASCII text, breaking mathematical threshold logic (e.g., string `"1000"` evaluates as less than `"200"`).
2. **Standard vs. Forward Tag Boundary:** Standard tags filter buyers *before* selection. Forward tags evaluate *after* buyer selection but *before* bridging/transferring. Forward tag lists MUST be paired with pre-selection transfer number or bid safeguards (e.g., `buyer_transfer_number:=~.+` or `rtb_bid:>0`) to prevent dead-end routing.
3. **RTB Cap Trigger Coupling:** Period caps (Hourly, Daily, Monthly, Hard) only reserve capacity during Real-Time Bidding if `cap_trigger` is set to `connection`. If set to `conversion`, pre-call RTB reservations will NOT decrement period caps, risking contractual over-delivery. Concurrency caps track reservations regardless of trigger.
4. **Hard Cap Persistence:** Hard caps do not reset on calendar boundaries. To resume traffic to a hard-capped buyer without changing the contract limit, invoke `targets.cap_resets.manage` (`buyer_ops.py reset-cap <target_id>`).
5. **Caller List Name Semantics:** Any list prefixed with `suppressed` (e.g., `suppressed_dnc`, `suppressed_converts`) is enforced as a strict deny list. Lists prefixed with `accepted` act as VIP allow lists. Phone numbers MUST be stored in E.164 format (`+1NXXNXXXXXX`) or 10-digit raw format consistently.
6. **Timezone Integrity in Schedules:** All buyer business hours and midnight daily cap resets evaluate relative to the buyer's explicit `time_zone` / `iana_time_zone`. Overnight shifts spanning midnight MUST be configured as two separate daily blocks (e.g., `20:00–24:00` and `00:00–04:00`).
7. **Dry Run on Destructive Changes:** Bulk cap modifications, schedule shifts, or deletion operations MUST support or test with `dry_run: true` prior to production execution.

## Output Specification
All programmatic operations and script commands output raw JSON conforming to this schema:
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["status", "action", "data"],
  "properties": {
    "status": {
      "type": "string",
      "enum": ["success", "error", "dry_run", "partial", "needs_clarification"]
    },
    "action": {
      "type": "string",
      "description": "Operation executed: list, show, create, update, set_caps, reset_cap, duplicate"
    },
    "data": {
      "type": "object",
      "description": "Payload containing target attributes, caps, business hours, or mutation response"
    },
    "error_details": {
      "type": "string",
      "description": "Error diagnostic message when status is error"
    }
  },
  "additionalProperties": false
}
```

## Operational Procedures & MCP Tool Mapping

### 1. Buyer Listing & Inspection
- **MCP Tool:** `targets.read`
  - `action`: `index` (list summary) or `show` (detailed profile)
  - `target_id`: Required for `show`
  - `query`: Substring search across name, DID, or `client_tid`
- **CLI Commands:**
  ```bash
  python3 scripts/buyer_ops.py list --query "Medicare" --per-page 20
  python3 scripts/buyer_ops.py show 139020
  ```

### 2. Buyer Creation & Profile Updates
- **MCP Tool:** `targets.manage`
  - `action`: `create` or `update`
  - `target_id`: Required for `update`
  - Key Parameters:
    - `name`: Buyer display name
    - `number`: Transfer phone number (E.164) or SIP URI
    - `priority`: Evaluation order (integer, lower is evaluated first; e.g. `-1` for top-tier, `1` for standard, `2` for overflow)
    - `weight`: Traffic ratio within the same priority tier (e.g., 3:1 ratio)
    - `timeout_seconds`: Max seconds spent attempting connect before failover (default 30)
    - `time_zone`: Timezone string (e.g., `"Eastern Time (US & Canada)"`)
    - `paused`: Boolean flag (`true` to pause routing, `false` to resume)
    - `tag_list`: Standard criteria tags (format: `<<<key:value>>>` tokens)
    - `forward_tag_list`: Forward verification tags (post-selection validation)
    - `dry_run`: `true` to preview diff without committing
- **CLI Commands:**
  ```bash
  # Create a buyer
  python3 scripts/buyer_ops.py create --name "HealthCare Direct" --number "+18005550199" --priority 1 --weight 2 --timeout 45

  # Update routing weights & pause state
  python3 scripts/buyer_ops.py update 139020 --weight 5 --priority 1 --paused false
  ```

### 3. Volume & Concurrency Cap Management
- **MCP Tool:** `targets.caps.manage`
  - `action`: `update`
  - `target_id`: Target integer ID
  - `hard_cap`: Total cumulative call ceiling (lifetime)
  - `hourly_cap`: Calls per clock hour (resets top of hour)
  - `daily_cap`: Calls per calendar day (resets midnight in buyer timezone)
  - `monthly_cap`: Calls per calendar month (resets 1st of month)
  - `concurrency_cap`: Max simultaneous live calls (instant release on disconnect)
  - `cap_trigger`: `connection` (increments on bridge) or `conversion` (increments on qualified conversion)
  - Note: Pass `null` (or `-1` in CLI) to clear an existing cap limit.
- **MCP Tool:** `targets.cap_resets.manage`
  - `action`: `create`
  - Resets the *hard cap counter* back to 0. Does not alter the cap limit.
- **CLI Commands:**
  ```bash
  # Set daily cap to 100 calls, concurrency to 5, trigger on connection
  python3 scripts/buyer_ops.py set-caps 139020 --daily-cap 100 --concurrency-cap 5 --cap-trigger connection

  # Reset an exhausted hard cap counter
  python3 scripts/buyer_ops.py reset-cap 139020
  ```

### 4. Buyer Duplication & Clones
- **MCP Tool:** `targets.duplicates.manage`
  - `action`: `create`
  - `target_id`: Buyer ID to clone
  - Deep-copies settings, conversion rules, business hours, standard tags, forward tags, and SIP headers into a new endpoint named `"<name> copy"`.
- **CLI Command:**
  ```bash
  python3 scripts/buyer_ops.py duplicate 139020
  ```

### 5. Tag Matching & Suppression Setup
- **Tag Operators:**
  - `==`: Exact match (default)
  - `!=`: Inequality filter
  - `=~`: Regular expression match (e.g. `caller_state:=~CA|FL|TX`)
  - `!~`: Negative regular expression match
  - `>`, `>=`, `<`, `<=`: Registered numeric and date comparisons
- **Presence & Absence Patterns:**
  - Presence: `<<<leadid:=~.+>>>` (ensures token is non-empty)
  - Absence: `<<<fraud_score:!~.+>>>` (blocks if tag is present)
- **Caller Lists & Suppression Lists:**
  - `caller_lists.manage`: Manage allow/deny lists attached to a buyer (`caller_listable_type: "Target"`).
  - Prefix with `suppressed_` for deny list behavior (e.g. `suppressed_unqualified`).
  - `caller_list_numbers.manage`: Add or delete specific E.164 phone numbers.
  - Buyer-Level Regex Text Suppression: Set buyer tag `caller_number:!~^(2125550100|2125550101)$`.

For comprehensive routing arbitration diagrams, carousel architectures, and troubleshooting matrices, refer to `references/buyer-spec.md`.
