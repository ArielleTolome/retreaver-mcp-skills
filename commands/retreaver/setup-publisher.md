---
name: retreaver:setup-publisher
description: Onboard a Publisher (Affiliate), generate RTB or Data Writing postback keys, and assign tracking numbers
argument-hint: "<publisher_name> [campaign_id] [payout]"
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
---

<objective>
Onboard a Publisher (Affiliate), generate RTB or Data Writing postback keys, and assign tracking numbers
</objective>

<execution_context>
Skill Reference: `~/.agents/skills/retreaver-publisher-ops/SKILL.md`
CLI Helper: `python3 ~/.agents/skills/retreaver-publisher-ops/scripts/publisher_ops.py create --help`
</execution_context>

<instructions>
Onboard and configure a Retreaver Publisher / Affiliate (`$ARGUMENTS`):
1. Read `skill://retreaver-publisher-ops`.
2. Create or look up the publisher via `affiliates.manage` / `affiliates.read`.
3. If an RTB or postback integration is needed, create a scoped Postback Key (`postback_keys.manage`) bound to the campaign and publisher (`action: "rtb"`, `ttl_seconds: 60`), and return the full posting URL (`https://rtb.retreaver.com/rtbs.json?key=...`).
4. If dedicated tracking numbers are requested, assign or configure numbers via `numbers.manage`.
</instructions>
