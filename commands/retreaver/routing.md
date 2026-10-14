---
name: retreaver:routing
description: Inspect or edit Campaign Call Routing tiers, priorities, weights, Waiting Room, and Buyer Groups
argument-hint: "<campaign_id_or_name> [changes]"
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
---

<objective>
Inspect or edit Campaign Call Routing tiers, priorities, weights, Waiting Room, and Buyer Groups
</objective>

<execution_context>
Skill Reference: `~/.agents/skills/retreaver-campaign-routing-ops/SKILL.md`
CLI Helper: `python3 ~/.agents/skills/retreaver-campaign-routing-ops/scripts/campaign_routing_ops.py --help`
</execution_context>

<instructions>
Inspect or modify Campaign Call Routing settings (`$ARGUMENTS`):
1. Read `skill://retreaver-campaign-routing-ops`.
2. Fetch current routing architecture via `campaigns.routing_settings.read` and `campaigns.read`.
3. Display the priority ladder, weights, locked/disabled states, and route-by-bid settings.
4. For requested routing changes, execute `campaigns.routing_settings.manage` with `dry_run: true` first to verify the exact diff before applying.
</instructions>
