---
name: retreaver:pbm
description: Manage Tag Wizard definitions, Replacement Tokens, Payout Bid Modification (PBM) tables, or credit calls
argument-hint: "<tags|tokens|pbm|credit> [args]"
allowed-tools:
  - Bash
  - Read
  - Write
  - Edit
---

<objective>
Manage Tag Wizard definitions, Replacement Tokens, Payout Bid Modification (PBM) tables, or credit calls
</objective>

<execution_context>
Skill Reference: `~/.agents/skills/retreaver-tags-bidding-ops/SKILL.md`
CLI Helper: `python3 ~/.agents/skills/retreaver-tags-bidding-ops/scripts/tags_bidding_ops.py --help`
</execution_context>

<instructions>
Manage Retreaver Tags, Replacement Tokens, Payout Bid Modification (PBM) tables, or Call Credits (`$ARGUMENTS`):
1. Read `skill://retreaver-tags-bidding-ops`.
2. For tags: ensure Numeric and Date tags are registered in `tags.manage` so comparisons don't fall back to lexicographical sorting.
3. For PBM tables: inspect or upload/activate CSV rule tables on the campaign via `payout_bid_modification_tables.read` / `manage`.
4. For call adjustments: credit or update call revenue/payout/converted state via `calls.manage`.
</instructions>
