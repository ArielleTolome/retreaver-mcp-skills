#!/usr/bin/env python3
"""
Retreaver Caller Lists & Suppression Operations CLI
Implements:
- list: List all caller lists on a Campaign or Target
- show: Show a single caller list or list numbers on it
- create: Create, update, or delete a caller list (suppressed* deny or accepted* allow)
- add-number: Add a single E.164 number or bulk upload numbers to a caller list
- remove-number: Remove a single E.164 number or bulk remove numbers from a caller list
- check-number: Live check whether a caller number is present on a caller list
- upload-status: Poll asynchronous bulk caller list upload jobs
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from retreaver_client import call_tool


def print_json(data):
    print(json.dumps(data, indent=2))


def normalize_type(val):
    v = val.strip().lower()
    if v in ("campaign", "campaigns"):
        return "Campaign"
    if v in ("target", "targets", "buyer", "buyers"):
        return "Target"
    raise ValueError(f"Invalid caller_listable_type '{val}'. Must be Campaign or Target.")


def cmd_list(args):
    params = {
        "action": "index",
        "caller_listable_type": normalize_type(args.owner_type),
        "caller_listable_id": args.owner_id,
    }
    res = call_tool("caller_lists.read", params)
    print_json(res)


def cmd_show(args):
    owner_type = normalize_type(args.owner_type)
    if args.numbers:
        params = {
            "action": "show" if args.number else "index",
            "caller_listable_type": owner_type,
            "caller_listable_id": args.owner_id,
            "caller_list_name": args.name,
            "page": args.page,
            "per_page": args.per_page,
        }
        if args.number:
            params["number"] = args.number
            params.pop("page", None)
            params.pop("per_page", None)
        if args.search:
            params["search"] = args.search
        res = call_tool("caller_list_numbers.read", params)
    else:
        params = {
            "action": "show",
            "caller_listable_type": owner_type,
            "caller_listable_id": args.owner_id,
            "name": args.name,
        }
        res = call_tool("caller_lists.read", params)
    print_json(res)


def cmd_create(args):
    params = {
        "action": args.action,
        "caller_listable_type": normalize_type(args.owner_type),
        "caller_listable_id": args.owner_id,
        "name": args.name,
    }
    if args.dry_run:
        params["dry_run"] = True
    if args.tag_list is not None:
        params["tag_list"] = args.tag_list
    if args.remove_after_seconds is not None:
        params["remove_number_after_seconds"] = (
            None if args.remove_after_seconds < 0 else args.remove_after_seconds
        )
    if args.add_on_receivable is not None:
        params["add_call_on_receivable"] = args.add_on_receivable
    if args.add_on_payable is not None:
        params["add_call_on_payable"] = args.add_on_payable

    res = call_tool("caller_lists.manage", params)
    print_json(res)


def _read_numbers_input(number_arg, file_arg):
    if file_arg:
        with open(file_arg, "r", encoding="utf-8") as f:
            return f.read().strip()
    return number_arg


def cmd_add_number(args):
    owner_type = normalize_type(args.owner_type)
    raw = _read_numbers_input(args.number, args.file)
    if not raw:
        raise SystemExit("Provide --number or --file containing E.164 phone number(s).")

    is_bulk = args.bulk or args.file or ("\n" in raw) or ("," in raw)
    if is_bulk:
        params = {
            "action": "create",
            "caller_listable_type": owner_type,
            "caller_listable_id": args.owner_id,
            "caller_list_name": args.name,
            "numbers": raw,
            "upload_action": "create",
        }
        if args.clear_before_upload:
            params["clear_before_upload"] = True
        res = call_tool("caller_list_uploads.manage", params)
    else:
        params = {
            "action": "create",
            "caller_listable_type": owner_type,
            "caller_listable_id": args.owner_id,
            "caller_list_name": args.name,
            "number": raw.strip(),
        }
        if args.dry_run:
            params["dry_run"] = True
        res = call_tool("caller_list_numbers.manage", params)
    print_json(res)


def cmd_remove_number(args):
    owner_type = normalize_type(args.owner_type)
    raw = _read_numbers_input(args.number, args.file)
    if not raw:
        raise SystemExit("Provide --number or --file containing E.164 phone number(s).")

    is_bulk = args.bulk or args.file or ("\n" in raw) or ("," in raw)
    if is_bulk:
        params = {
            "action": "create",
            "caller_listable_type": owner_type,
            "caller_listable_id": args.owner_id,
            "caller_list_name": args.name,
            "numbers": raw,
            "upload_action": "delete",
        }
        res = call_tool("caller_list_uploads.manage", params)
    else:
        params = {
            "action": "delete",
            "caller_listable_type": owner_type,
            "caller_listable_id": args.owner_id,
            "caller_list_name": args.name,
            "number": raw.strip(),
        }
        if args.dry_run:
            params["dry_run"] = True
        res = call_tool("caller_list_numbers.manage", params)
    print_json(res)


def cmd_check_number(args):
    params = {
        "action": "create",
        "caller_listable_type": normalize_type(args.owner_type),
        "caller_listable_id": args.owner_id,
        "caller_list_name": args.name,
        "number": args.number.strip(),
    }
    res = call_tool("caller_list_checks.manage", params)
    print_json(res)


def cmd_upload_status(args):
    params = {
        "action": "show" if args.upload_id is not None else "index",
        "caller_listable_type": normalize_type(args.owner_type),
        "caller_listable_id": args.owner_id,
        "caller_list_name": args.name,
    }
    if args.upload_id is not None:
        params["upload_id"] = args.upload_id
    else:
        params["page"] = args.page
        params["per_page"] = args.per_page
    res = call_tool("caller_list_uploads.read", params)
    print_json(res)


def parse_bool(val):
    return str(val).lower() in ("true", "1", "yes", "y")


def main():
    parser = argparse.ArgumentParser(
        description="Retreaver Caller Lists & Suppression CLI (caller_lists, numbers, bulk uploads, membership checks)"
    )
    subparsers = parser.add_subparsers(dest="command", help="Caller list operation")

    # list
    p_list = subparsers.add_parser("list", help="List all caller lists on a Campaign or Target")
    p_list.add_argument("--owner-type", "-t", required=True, help="Campaign or Target")
    p_list.add_argument("--owner-id", "-i", type=int, required=True, help="Campaign or Target integer ID")
    p_list.set_defaults(func=cmd_list)

    # show
    p_show = subparsers.add_parser("show", help="Show a caller list configuration or enumerate its numbers")
    p_show.add_argument("--owner-type", "-t", required=True, help="Campaign or Target")
    p_show.add_argument("--owner-id", "-i", type=int, required=True, help="Campaign or Target integer ID")
    p_show.add_argument("--name", "-n", required=True, help="Caller list name (e.g. suppressed_dnc)")
    p_show.add_argument("--numbers", action="store_true", help="List numbers on the caller list via caller_list_numbers.read")
    p_show.add_argument("--number", help="Specific E.164 number to inspect when --numbers is set")
    p_show.add_argument("--search", "-s", help="Filter numbers by substring when --numbers is set")
    p_show.add_argument("--page", type=int, default=1, help="Page number for --numbers (default: 1)")
    p_show.add_argument("--per-page", type=int, default=50, help="Results per page for --numbers (default: 50)")
    p_show.set_defaults(func=cmd_show)

    # create (also supports update / delete via --action)
    p_create = subparsers.add_parser("create", help="Create, update, or delete a caller list on a Campaign or Target")
    p_create.add_argument("--owner-type", "-t", required=True, help="Campaign or Target")
    p_create.add_argument("--owner-id", "-i", type=int, required=True, help="Campaign or Target integer ID")
    p_create.add_argument("--name", "-n", required=True, help="Unique list name (suppressed* for deny, accepted* for allow)")
    p_create.add_argument("--action", choices=["create", "update", "delete"], default="create", help="Operation (default: create)")
    p_create.add_argument("--tag-list", help="Auto-add tag rule in <<<key:value>>> format")
    p_create.add_argument("--remove-after-seconds", type=int, help="TTL in seconds before auto-removal (-1 for never)")
    p_create.add_argument("--add-on-receivable", type=parse_bool, help="Auto-add caller when call becomes receivable (true/false)")
    p_create.add_argument("--add-on-payable", type=parse_bool, help="Auto-add caller when call becomes payable (true/false)")
    p_create.add_argument("--dry-run", action="store_true", help="Preview diff without applying")
    p_create.set_defaults(func=cmd_create)

    # add-number
    p_add = subparsers.add_parser("add-number", help="Add single number or bulk upload numbers to a caller list")
    p_add.add_argument("--owner-type", "-t", required=True, help="Campaign or Target")
    p_add.add_argument("--owner-id", "-i", type=int, required=True, help="Campaign or Target integer ID")
    p_add.add_argument("--name", "-n", required=True, help="Caller list name")
    p_add.add_argument("--number", help="Single E.164 number (+18885551234) or comma/newline separated batch")
    p_add.add_argument("--file", "-f", help="Path to CSV/text file of E.164 numbers (one per line or comma-separated)")
    p_add.add_argument("--bulk", action="store_true", help="Force async bulk upload endpoint (caller_list_uploads.manage)")
    p_add.add_argument("--clear-before-upload", action="store_true", help="Replace existing list numbers with uploaded batch")
    p_add.add_argument("--dry-run", action="store_true", help="Preview single-number addition without applying")
    p_add.set_defaults(func=cmd_add_number)

    # remove-number
    p_rem = subparsers.add_parser("remove-number", help="Remove single number or bulk delete numbers from a caller list")
    p_rem.add_argument("--owner-type", "-t", required=True, help="Campaign or Target")
    p_rem.add_argument("--owner-id", "-i", type=int, required=True, help="Campaign or Target integer ID")
    p_rem.add_argument("--name", "-n", required=True, help="Caller list name")
    p_rem.add_argument("--number", help="Single E.164 number (+18885551234) or comma/newline separated batch")
    p_rem.add_argument("--file", "-f", help="Path to CSV/text file of E.164 numbers to remove")
    p_rem.add_argument("--bulk", action="store_true", help="Force async bulk upload endpoint with upload_action=delete")
    p_rem.add_argument("--dry-run", action="store_true", help="Preview single-number deletion without applying")
    p_rem.set_defaults(func=cmd_remove_number)

    # check-number
    p_chk = subparsers.add_parser("check-number", help="Live check if a caller number is present on a caller list")
    p_chk.add_argument("--owner-type", "-t", required=True, help="Campaign or Target")
    p_chk.add_argument("--owner-id", "-i", type=int, required=True, help="Campaign or Target integer ID")
    p_chk.add_argument("--name", "-n", required=True, help="Caller list name")
    p_chk.add_argument("--number", required=True, help="Caller number in E.164 format (e.g. +18885551234)")
    p_chk.set_defaults(func=cmd_check_number)

    # upload-status
    p_up = subparsers.add_parser("upload-status", help="Poll status of asynchronous bulk caller list uploads")
    p_up.add_argument("--owner-type", "-t", required=True, help="Campaign or Target")
    p_up.add_argument("--owner-id", "-i", type=int, required=True, help="Campaign or Target integer ID")
    p_up.add_argument("--name", "-n", required=True, help="Caller list name")
    p_up.add_argument("--upload-id", "-u", type=int, help="Specific upload_id to inspect; omit to list recent uploads")
    p_up.add_argument("--page", type=int, default=1, help="Page number (default: 1)")
    p_up.add_argument("--per-page", type=int, default=20, help="Results per page (default: 20)")
    p_up.set_defaults(func=cmd_upload_status)

    args = parser.parse_args()
    if not hasattr(args, "func"):
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
