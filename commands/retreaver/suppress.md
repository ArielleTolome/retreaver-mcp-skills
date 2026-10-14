---
name: retreaver:suppress
description: Manage Caller Lists, add/remove suppressed or accepted numbers, check a number, or upload bulk CSVs
argument-hint: "<check|add|remove|upload> <number_or_file> [campaign_or_target_id]"
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
---

<objective>
Manage Caller Lists, add/remove suppressed or accepted numbers, check a number, or upload bulk CSVs
</objective>

<execution_context>
Skill Reference: `~/.agents/skills/retreaver-caller-lists-suppression/SKILL.md`
CLI Helper: `python3 ~/.agents/skills/retreaver-caller-lists-suppression/scripts/caller_lists_ops.py --help`
</execution_context>

<instructions>
Execute Caller List suppression or acceptance operations (`$ARGUMENTS`):
1. Read `skill://retreaver-caller-lists-suppression`.
2. Inspect caller lists on the target Campaign or Buyer via `caller_lists.read` (remembering `suppressed*` = blocklist, `accepted*` = allowlist).
3. Execute number lookup (`caller_list_checks.manage`), single add/remove (`caller_list_numbers.manage`), or bulk upload (`caller_list_uploads.manage`) and report verification status.
</instructions>
