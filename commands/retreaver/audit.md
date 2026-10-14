---
name: retreaver:audit
description: Run a full operational health and housekeeping audit across campaigns, buyers, caps, webhooks, and numbers
argument-hint: ""
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
---

<objective>
Run a full operational health and housekeeping audit across campaigns, buyers, caps, webhooks, and numbers
</objective>

<execution_context>
Skill Reference: `~/.agents/skills/retreaver-operator/SKILL.md`
CLI Helper: `python3 ~/.agents/skills/retreaver-operator/scripts/retreaver_cli.py whoami`
</execution_context>

<instructions>
Run a comprehensive operational and housekeeping audit of this Retreaver company:
1. Confirm company identity via `account.whoami`.
2. Audit Buyers (`targets.read`): Identify any unpaused buyers with no caps set (`cap: null`), buyers hitting hard/daily caps, or buyers with unresolved `[token]` numbers.
3. Audit Campaigns & Numbers (`campaigns.read`, `numbers.read`, `number_pools.read`): Identify paused campaigns that still have active numbers pointed at them, or active RTB campaigns missing fallback buyers/inbound numbers.
4. Audit Webhooks (`webhooks.read`) & Postback Keys (`postback_keys.read`): Flag any webhooks pointing to `staging`/`test` URLs or failing test fires.
5. Present a prioritized table of findings and recommended fixes.
</instructions>
