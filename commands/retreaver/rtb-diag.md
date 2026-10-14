---
name: retreaver:rtb-diag
description: Diagnose RTB inbound pings, no-target rejections, expired reservations, and buyer API errors
argument-hint: "[minutes_or_campaign_id]"
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
---

<objective>
Diagnose RTB inbound pings, no-target rejections, expired reservations, and buyer API errors
</objective>

<execution_context>
Skill Reference: `~/.agents/skills/retreaver-diagnostics-reporting/SKILL.md`
CLI Helper: `python3 ~/.agents/skills/retreaver-operator/scripts/retreaver_cli.py rtb-diag --minutes 15`
</execution_context>

<instructions>
Diagnose Retreaver Real-Time Bidding (RTB) inbound reservations and ping failures (`$ARGUMENTS`):
1. Read `skill://retreaver-diagnostics-reporting`.
2. Query `rtb_inbounds.read` and `rtb_inbound_drill_down_tables.read` for the specified time window (default: last 10–15 minutes).
3. Break down reservation statuses (`claimed`, `expired`, `no-target`, `rejected`, `ping_shield_*`).
4. For `no-target`, inspect target `geo` tag whitelists and test/check buyer PassthroughTimer endpoints (e.g. CallGrid `code: 4004` capacity full vs `1000`).
5. For `expired`, check reservation `ttl_seconds`, whether dynamic phone numbers vs SIP addresses were returned, and whether `calls.read` shows any inbound voice calls arriving.
6. Provide a clear table of metrics and exact root-cause remediation.
</instructions>
