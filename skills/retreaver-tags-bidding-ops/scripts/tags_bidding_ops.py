#!/usr/bin/env python3
"""
Retreaver Tags, Bidding & Call Crediting Operations CLI
Implements:
- list-tags: Inspect or list tag keys in the company catalog (tags.read)
- create-tag: Create, update, or delete a tag key definition (tags.manage)
- list-tokens: List available replacement tokens (tags.replacement_tokens.read)
- list-pbm: List or show Payout Bid Modification (PBM) CSV rule tables (payout_bid_modification_tables.read)
- activate-pbm: Upload, activate/deactivate, or delete a PBM CSV rule table (payout_bid_modification_tables.manage)
- credit-call: Update/credit a call's revenue, payout, receivable/payable flags, or session notes (calls.manage)
"""

import argparse
import json
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)
if "/tmp" not in sys.path:
    sys.path.append("/tmp")

from retreaver_client import call_tool


TAG_TYPE_MAP = {
    "string": "Tags::Types::String",
    "text": "Tags::Types::String",
    "numeric": "Tags::Types::Numeric",
    "number": "Tags::Types::Numeric",
    "date": "Tags::Types::Date",
    "datetime": "Tags::Types::DateTime",
    "boolean": "Tags::Types::Boolean",
    "bool": "Tags::Types::Boolean",
    "Tags::Types::String": "Tags::Types::String",
    "Tags::Types::Numeric": "Tags::Types::Numeric",
    "Tags::Types::Date": "Tags::Types::Date",
    "Tags::Types::DateTime": "Tags::Types::DateTime",
    "Tags::Types::Boolean": "Tags::Types::Boolean",
}


def print_json(data):
    print(json.dumps(data, indent=2))


def parse_bool(val):
    if isinstance(val, bool):
        return val
    return str(val).lower() in ("true", "1", "yes", "y")


def cmd_list_tags(args):
    if args.tag_id is not None:
        params = {"action": "show", "tag_id": args.tag_id}
    else:
        params = {"action": "index", "page": args.page, "per_page": args.per_page}
    res = call_tool("tags.read", params)
    print_json(res)


def cmd_create_tag(args):
    params = {"action": args.action}
    if args.dry_run:
        params["dry_run"] = True
    if args.tag_id is not None:
        params["tag_id"] = args.tag_id
    if args.key is not None:
        params["key"] = args.key
    if args.type is not None:
        params["type"] = TAG_TYPE_MAP.get(args.type, args.type)
    if args.color is not None:
        params["color"] = args.color
    if args.prompt_enabled is not None:
        params["prompt_enabled"] = args.prompt_enabled
    if args.acceptable_tags_enabled is not None:
        params["acceptable_tags_enabled"] = args.acceptable_tags_enabled
    if args.values_report is not None:
        params["values_report"] = args.values_report
    if args.ai_prompt is not None:
        params["ai_prompt"] = args.ai_prompt

    res = call_tool("tags.manage", params)
    print_json(res)


def cmd_list_tokens(args):
    params = {"action": "index"}
    if args.campaign_id is not None:
        params["campaign_id"] = args.campaign_id
    res = call_tool("tags.replacement_tokens.read", params)
    print_json(res)


def cmd_list_pbm(args):
    params = {
        "action": "show" if args.id is not None else "index",
        "campaign_id": args.campaign_id,
    }
    if args.id is not None:
        params["id"] = args.id
    res = call_tool("payout_bid_modification_tables.read", params)
    print_json(res)


def cmd_activate_pbm(args):
    params = {
        "action": args.action,
        "campaign_id": args.campaign_id,
    }
    if args.dry_run:
        params["dry_run"] = True
    if args.id is not None:
        params["id"] = args.id
    if args.csv_file:
        with open(args.csv_file, "r", encoding="utf-8") as f:
            params["csv_data"] = f.read()
    elif args.csv_data is not None:
        params["csv_data"] = args.csv_data
    if args.salt is not None:
        params["salt"] = args.salt
    if args.table_version is not None:
        params["table_version"] = args.table_version
    if args.active is not None:
        params["active"] = args.active

    res = call_tool("payout_bid_modification_tables.manage", params)
    print_json(res)


def cmd_credit_call(args):
    params = {
        "action": "update",
        "uuid": args.uuid,
    }
    if args.dry_run:
        params["dry_run"] = True
    if args.revenue is not None:
        params["revenue"] = args.revenue
    if args.payout is not None:
        params["payout"] = args.payout
    if args.receivable is not None:
        params["receivable"] = args.receivable
    if args.payable is not None:
        params["payable"] = args.payable
    if args.session_notes is not None:
        params["session_notes"] = args.session_notes

    res = call_tool("calls.manage", params)
    print_json(res)


def main():
    parser = argparse.ArgumentParser(
        description="Retreaver Tags, Replacement Tokens, Payout Bid Modification (PBM) & Call Crediting CLI"
    )
    subparsers = parser.add_subparsers(dest="command", help="Operational subcommands")

    # list-tags
    p_lt = subparsers.add_parser("list-tags", help="List tag catalog or inspect a single tag by ID")
    p_lt.add_argument("--tag-id", type=int, help="Show a specific tag ID (omit to list all)")
    p_lt.add_argument("--page", type=int, default=1, help="Page number (default: 1)")
    p_lt.add_argument("--per-page", type=int, default=50, help="Items per page (1-100, default: 50)")
    p_lt.set_defaults(func=cmd_list_tags)

    # create-tag
    p_ct = subparsers.add_parser("create-tag", help="Create, update, or delete a tag key in the company catalog")
    p_ct.add_argument("--action", choices=["create", "update", "delete"], default="create", help="Tag operation (default: create)")
    p_ct.add_argument("--tag-id", type=int, help="Tag ID (required for update/delete)")
    p_ct.add_argument("--key", "-k", help="Tag identifier key (lowercase letters, digits, underscores)")
    p_ct.add_argument(
        "--type",
        "-t",
        choices=[
            "string", "text", "numeric", "number", "date", "datetime", "boolean", "bool",
            "Tags::Types::String", "Tags::Types::Numeric", "Tags::Types::Date", "Tags::Types::DateTime", "Tags::Types::Boolean",
        ],
        help="Tag value type (String, Numeric, Date, DateTime, Boolean)",
    )
    p_ct.add_argument("--color", help="Tag UI badge color")
    p_ct.add_argument("--prompt-enabled", type=parse_bool, help="Enable IVR prompt collection (true/false)")
    p_ct.add_argument("--acceptable-tags-enabled", type=parse_bool, help="Restrict to acceptable values list (true/false)")
    p_ct.add_argument("--values-report", type=parse_bool, help="Include in tag values report (true/false)")
    p_ct.add_argument("--ai-prompt", help="AI Analyst extraction prompt for this tag")
    p_ct.add_argument("--dry-run", action="store_true", help="Preview change without applying")
    p_ct.set_defaults(func=cmd_create_tag)

    # list-tokens
    p_tok = subparsers.add_parser("list-tokens", help="List replacement tokens available to company and campaign")
    p_tok.add_argument("--campaign-id", "-c", type=int, help="Include integration and static custom tokens for this campaign ID")
    p_tok.set_defaults(func=cmd_list_tokens)

    # list-pbm
    p_lpbm = subparsers.add_parser("list-pbm", help="List or inspect Payout Bid Modification (PBM) CSV rule tables")
    p_lpbm.add_argument("--campaign-id", "-c", type=int, required=True, help="Campaign ID")
    p_lpbm.add_argument("--id", type=int, help="Specific PBM table ID to inspect (includes csv_data)")
    p_lpbm.set_defaults(func=cmd_list_pbm)

    # activate-pbm
    p_apbm = subparsers.add_parser("activate-pbm", help="Upload, activate/deactivate, or delete a PBM rule table")
    p_apbm.add_argument("--action", choices=["create", "update", "delete"], default="update", help="Operation: create (upload CSV), update (toggle active), delete (default: update)")
    p_apbm.add_argument("--campaign-id", "-c", type=int, required=True, help="Campaign ID")
    p_apbm.add_argument("--id", type=int, help="PBM table ID (required for update/delete)")
    p_apbm.add_argument("--active", type=parse_bool, default=True, help="Set active status (true/false, default: true)")
    p_apbm.add_argument("--csv-data", help="Raw CSV rule string (required when --action create unless --csv-file used)")
    p_apbm.add_argument("--csv-file", help="Path to CSV rule file to upload on create")
    p_apbm.add_argument("--salt", help="Deterministic hash bucket salt on create (defaults to company+date if blank)")
    p_apbm.add_argument("--table-version", type=int, help="Optional unique revision integer within campaign on create")
    p_apbm.add_argument("--dry-run", action="store_true", help="Preview change without applying")
    p_apbm.set_defaults(func=cmd_activate_pbm)

    # credit-call
    p_cc = subparsers.add_parser("credit-call", help="Update/credit call revenue, payout, receivable/payable flags, or notes")
    p_cc.add_argument("--uuid", "-u", required=True, help="Call UUID to update/credit")
    p_cc.add_argument("--revenue", type=float, help="Call revenue amount (0 clears; >0 sets receivable=true; affects Buyer caps)")
    p_cc.add_argument("--payout", type=float, help="Call publisher payout amount (0 clears; >0 sets payable=true)")
    p_cc.add_argument("--receivable", type=parse_bool, help="Mark call receivable (true fires previously unfired conversion webhooks)")
    p_cc.add_argument("--payable", type=parse_bool, help="Mark call payable (true/false)")
    p_cc.add_argument("--session-notes", help="Operator session notes attached to the call record")
    p_cc.add_argument("--dry-run", action="store_true", help="Preview diff without applying")
    p_cc.set_defaults(func=cmd_credit_call)

    args = parser.parse_args()
    if not hasattr(args, "func"):
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
