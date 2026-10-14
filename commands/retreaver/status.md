---
name: retreaver:status
description: Verify Retreaver MCP connection, company identity, and live account health
argument-hint: ""
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
---

<objective>
Verify Retreaver MCP connection, company identity, and live account health
</objective>

<execution_context>
Skill Reference: `~/.agents/skills/retreaver-operator/SKILL.md`
CLI Helper: `python3 ~/.agents/skills/retreaver-operator/scripts/retreaver_cli.py whoami`
</execution_context>

<instructions>
Check the current Retreaver MCP connection and live account status:
1. Run `account.whoami` (or `python3 ~/.agents/skills/retreaver-operator/scripts/retreaver_cli.py whoami`) to confirm the bound company, user, role, and scopes.
2. List active campaigns (`campaigns.read`) and active targets (`targets.read`).
3. Report a concise summary of the connected company, total active campaigns/buyers, and whether any RTB reservations or calls occurred in the last 15 minutes.
</instructions>
