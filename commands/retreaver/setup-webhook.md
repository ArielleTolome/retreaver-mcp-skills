---
name: retreaver:setup-webhook
description: Add, configure, or test-fire a Campaign/Buyer Webhook (Timer) or Configurator Template
argument-hint: "<target_or_campaign_id> <template_or_url>"
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
---

<objective>
Add, configure, or test-fire a Campaign/Buyer Webhook (Timer) or Configurator Template
</objective>

<execution_context>
Skill Reference: `~/.agents/skills/retreaver-webhook-ops/SKILL.md`
CLI Helper: `python3 ~/.agents/skills/retreaver-webhook-ops/scripts/webhook_ops.py --help`
</execution_context>

<instructions>
Configure and verify a Retreaver Webhook / Timer (`$ARGUMENTS`):
1. Read `skill://retreaver-webhook-ops`.
2. Check if a pre-built integration matches in `webhooks.templates.read` (e.g. CallGrid, TrackDrive, Anura, Leadspedia, 33MileRadius).
3. Create the webhook via `webhooks.configurations.manage` (template) or `webhooks.manage` (custom `PassthroughTimer`, `HTTPTimer`, `PingTimer`, `PostbackTimer`).
4. Immediately run `webhooks.test_fires.manage` on the webhook ID and report the exact outbound request URL, HTTP status, response payload, and parsed tags.
</instructions>
