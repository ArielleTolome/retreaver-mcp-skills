#!/usr/bin/env python3
"""Retreaver Tracking Numbers & Dynamic Number Pools CLI.

Implements:
- list-numbers: List tracking numbers (numbers.read index)
- show-number: Show a single tracking number (numbers.read show)
- update-number: Update a tracking number, tags, pause state, or surgical overrides (numbers.manage update)
- list-pools: List dynamic number pools (number_pools.read index)
- show-pool: Show a single dynamic number pool (number_pools.read show)
- create-pool: Create a dynamic number pool (number_pools.manage create)
- update-pool: Update a dynamic number pool (number_pools.manage update)
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


def parse_bool(val):
    if isinstance(val, bool):
        return val
    v = str(val).strip().lower()
    if v in ("true", "1", "yes", "y", "on"):
        return True
    if v in ("false", "0", "no", "n", "off"):
        return False
    raise argparse.ArgumentTypeError(f"Expected boolean value (true/false), got '{val}'")


def emit(action, raw):
    if isinstance(raw, dict) and "status" in raw:
        out = {
            "status": raw.get("status", "ok"),
            "action": action,
            "data": {k: v for k, v in raw.items() if k not in ("status", "action", "errors")},
        }
        if "errors" in raw:
            out["errors"] = raw["errors"]
    else:
        out = {
            "status": "ok",
            "action": action,
            "data": raw if isinstance(raw, dict) else {"result": raw},
        }
    print(json.dumps(out, indent=2))


def cmd_list_numbers(args):
    params = {"action": "index", "page": args.page, "per_page": args.per_page}
    emit("list-numbers", call_tool("numbers.read", params))


def cmd_show_number(args):
    params = {"action": "show", "number_id": args.number_id}
    emit("show-number", call_tool("numbers.read", params))


def cmd_update_number(args):
    params = {"action": "update", "number_id": args.number_id}
    if args.dry_run:
        params["dry_run"] = True
    optional_fields = [
        "name",
        "number",
        "target_number",
        "campaign_id",
        "affiliate_id",
        "number_pool_id",
        "tag_list",
        "paused",
        "toll_free",
        "country",
        "time_zone",
        "iana_time_zone",
        "extensions_enabled",
        "greeting_use_cs",
        "routing_use_cs",
        "timers_use_cs",
        "conversions_use_cs",
        "locked",
        "pool_buffer",
    ]
    for field in optional_fields:
        val = getattr(args, field, None)
        if val is not None:
            params[field] = val
    emit("update-number", call_tool("numbers.manage", params))


def cmd_list_pools(args):
    params = {"action": "index", "page": args.page, "per_page": args.per_page}
    emit("list-pools", call_tool("number_pools.read", params))


def cmd_show_pool(args):
    params = {"action": "show", "number_pool_id": args.pool_id}
    emit("show-pool", call_tool("number_pools.read", params))


def _collect_pool_fields(args, params):
    if args.dry_run:
        params["dry_run"] = True
    pool_fields = [
        "campaign_id",
        "affiliate_id",
        "max_pool_size",
        "reserve_size",
        "buffer_seconds",
        "max_lease_seconds",
        "toll_free",
        "country",
        "area_code_id",
        "per_visitor",
        "google_analytics",
        "google_analytics_account",
        "hide_embedded_access",
        "sti_type",
    ]
    for field in pool_fields:
        val = getattr(args, field, None)
        if val is not None:
            params[field] = val


def cmd_create_pool(args):
    params = {"action": "create"}
    _collect_pool_fields(args, params)
    emit("create-pool", call_tool("number_pools.manage", params))


def cmd_update_pool(args):
    params = {"action": "update", "number_pool_id": args.pool_id}
    _collect_pool_fields(args, params)
    emit("update-pool", call_tool("number_pools.manage", params))


def _add_pool_opts(p, require_campaign=False):
    p.add_argument("--campaign-id", type=int, required=require_campaign, help="Parent Campaign ID")
    p.add_argument("--affiliate-id", type=int, help="Optional Publisher/Affiliate ID")
    p.add_argument("--max-pool-size", type=int, help="Hard cap on numbers automatically provisioned")
    p.add_argument("--reserve-size", type=int, help="Numbers pre-acquired to avoid carrier acquisition delay")
    p.add_argument("--buffer-seconds", type=int, help="Grace period in seconds after visitor leaves page")
    p.add_argument("--max-lease-seconds", type=int, help="Max lease duration in seconds for lingering visitors")
    p.add_argument("--toll-free", type=parse_bool, help="Provision toll-free numbers (true/false)")
    p.add_argument("--country", help="ISO country code (e.g. US)")
    p.add_argument("--area-code-id", type=int, help="Area code ID for local number pools")
    p.add_argument("--per-visitor", type=parse_bool, help="Track every visitor with a dedicated number (true/false)")
    p.add_argument("--google-analytics", type=parse_bool, help="Enable native Google Analytics integration (true/false)")
    p.add_argument("--google-analytics-account", help="Explicit GA tracker ID override")
    p.add_argument("--hide-embedded-access", type=parse_bool, help="Disallow publisher static number creation (true/false)")
    p.add_argument("--sti-type", help="Single-table inheritance type override")
    p.add_argument("--dry-run", action="store_true", help="Preview changes without applying")


def main():
    parser = argparse.ArgumentParser(
        prog="numbers_pools_ops.py",
        description="Manage Retreaver tracking numbers and dynamic number pools via MCP.",
    )
    sub = parser.add_subparsers(dest="subcommand", required=True)

    # list-numbers
    p_ln = sub.add_parser("list-numbers", help="List tracking numbers")
    p_ln.add_argument("--page", type=int, default=1, help="Page number (default: 1)")
    p_ln.add_argument("--per-page", type=int, default=25, help="Items per page (1-100, default: 25)")
    p_ln.set_defaults(func=cmd_list_numbers)

    # show-number
    p_sn = sub.add_parser("show-number", help="Show details of a tracking number")
    p_sn.add_argument("--number-id", type=int, required=True, help="Tracking number ID")
    p_sn.set_defaults(func=cmd_show_number)

    # update-number
    p_un = sub.add_parser("update-number", help="Update a tracking number")
    p_un.add_argument("--number-id", type=int, required=True, help="Tracking number ID")
    p_un.add_argument("--name", help="Display name for the tracking number")
    p_un.add_argument("--number", help="E.164 phone number string")
    p_un.add_argument("--target-number", help="Direct target forwarding number or SIP URI")
    p_un.add_argument("--campaign-id", type=int, help="Parent Campaign ID")
    p_un.add_argument("--affiliate-id", type=int, help="Assigned Publisher/Affiliate ID")
    p_un.add_argument("--number-pool-id", type=int, help="Associated Number Pool ID")
    p_un.add_argument("--tag-list", help="Comma-separated <<<key:value>>> tags (replaces existing tags)")
    p_un.add_argument("--paused", type=parse_bool, help="Pause or resume number (true/false)")
    p_un.add_argument("--toll-free", type=parse_bool, help="Toll-free flag (true/false)")
    p_un.add_argument("--country", help="Country code (e.g. US)")
    p_un.add_argument("--time-zone", help="Display time zone")
    p_un.add_argument("--iana-time-zone", help="IANA time zone (e.g. America/New_York)")
    p_un.add_argument("--extensions-enabled", type=parse_bool, help="Enable extension dialing (true/false)")
    p_un.add_argument("--greeting-use-cs", type=parse_bool, help="Inherit Campaign greeting prompts (true/false)")
    p_un.add_argument("--routing-use-cs", type=parse_bool, help="Inherit Campaign routing settings (true/false)")
    p_un.add_argument("--timers-use-cs", type=parse_bool, help="Inherit Campaign timer settings (true/false)")
    p_un.add_argument("--conversions-use-cs", type=parse_bool, help="Inherit Campaign conversion settings (true/false)")
    p_un.add_argument("--locked", type=parse_bool, help="Lock number from reassignment (true/false)")
    p_un.add_argument("--pool-buffer", type=parse_bool, help="Pool buffer flag (true/false)")
    p_un.add_argument("--dry-run", action="store_true", help="Preview changes without applying")
    p_un.set_defaults(func=cmd_update_number)

    # list-pools
    p_lp = sub.add_parser("list-pools", help="List dynamic number pools")
    p_lp.add_argument("--page", type=int, default=1, help="Page number (default: 1)")
    p_lp.add_argument("--per-page", type=int, default=25, help="Items per page (1-100, default: 25)")
    p_lp.set_defaults(func=cmd_list_pools)

    # show-pool
    p_sp = sub.add_parser("show-pool", help="Show details of a dynamic number pool")
    p_sp.add_argument("--pool-id", type=int, required=True, help="Number pool ID")
    p_sp.set_defaults(func=cmd_show_pool)

    # create-pool
    p_cp = sub.add_parser("create-pool", help="Create a dynamic number pool")
    _add_pool_opts(p_cp, require_campaign=True)
    p_cp.set_defaults(func=cmd_create_pool)

    # update-pool
    p_up = sub.add_parser("update-pool", help="Update a dynamic number pool")
    p_up.add_argument("--pool-id", type=int, required=True, help="Number pool ID")
    _add_pool_opts(p_up, require_campaign=False)
    p_up.set_defaults(func=cmd_update_pool)

    try:
        parsed = parser.parse_args()
        parsed.func(parsed)
    except Exception as exc:
        sys.stderr.write(f"Error: {exc}\n")
        print(json.dumps({
            "status": "error",
            "action": getattr(parsed, "subcommand", "unknown") if "parsed" in locals() else "unknown",
            "data": {},
            "error_details": str(exc),
        }, indent=2))
        sys.exit(1)


if __name__ == "__main__":
    main()
