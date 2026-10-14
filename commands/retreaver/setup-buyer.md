---
name: retreaver:setup-buyer
description: Stand up a new Call Buyer (Target) with E.164 number, priority, weight, caps, business hours, and geo tags
argument-hint: "<name> <number> [campaign_id] [caps/hours]"
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
---

<objective>
Stand up a new Call Buyer (Target) with E.164 number, priority, weight, caps, business hours, and geo tags
</objective>

<execution_context>
Skill Reference: `~/.agents/skills/retreaver-buyer-ops/SKILL.md`
CLI Helper: `python3 ~/.agents/skills/retreaver-buyer-ops/scripts/buyer_ops.py create --help`
</execution_context>

<instructions>
Set up or update a Retreaver Call Buyer / Target (`$ARGUMENTS`):
1. Read `skill://retreaver-buyer-ops`.
2. Confirm the connected company via `account.whoami`.
3. Preview the buyer creation or update using `targets.manage` with `dry_run: true` first (validating E.164 phone number or dynamic `[tag_number]`, priority, weight, timeout_seconds, and timezone).
4. Configure concurrency, hourly, daily, monthly, or hard caps via `targets.caps.manage`.
5. Attach required `tag_values` (such as state `geo` whitelists or bid response codes) and link the target to the campaign's routing settings (`campaigns.routing_settings.manage`) if a campaign was specified.
</instructions>
