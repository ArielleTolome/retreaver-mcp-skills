---
name: retreaver:stats
description: Get call volume, conversion rate, revenue, payout, profit, and EPC statistics
argument-hint: "[today|yesterday|last_7d|this_month]"
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
---

<objective>
Get call volume, conversion rate, revenue, payout, profit, and EPC statistics
</objective>

<execution_context>
Skill Reference: `~/.agents/skills/retreaver-diagnostics-reporting/SKILL.md`
CLI Helper: `python3 ~/.agents/skills/retreaver-diagnostics-reporting/scripts/diag_reporting.py call-stats --window today`
</execution_context>

<instructions>
Generate a comprehensive performance report for Retreaver calls and RTB reservations (`$ARGUMENTS`, default: `today`):
1. Read `skill://retreaver-diagnostics-reporting`.
2. Query `calls_drill_down_tables.read` grouped by `campaign_id`, `affiliate_id`, and `target_id`.
3. Query `rtb_inbound_drill_down_tables.read` for RTB ping volume, bid rate, winning bid average, and duplicate rate.
4. Output a clean markdown comparison table with Calls, Connected, Converted, Revenue, Payout, Profit, and EPC.
</instructions>
