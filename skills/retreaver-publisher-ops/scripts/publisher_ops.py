#!/usr/bin/env python3
"""Publisher / Affiliate Operations CLI for Retreaver.

Interacts with Retreaver MCP server to manage affiliates/publishers,
their postback keys (RTB, Data Writing), tracking numbers, and conversion groups.
"""

import argparse
import json
import os
import sys

# Ensure retreaver_client is importable
if "/tmp" not in sys.path:
    sys.path.append("/tmp")

try:
    from retreaver_client import call_tool
except ImportError:
    def call_tool(name, args=None):
        raise RuntimeError("Retreaver client not available at /tmp/retreaver_client.py")


def cmd_list(args):
    """List publishers/affiliates."""
    payload = {
        "action": "index",
        "page": args.page,
        "per_page": args.per_page
    }
    res = call_tool("affiliates.read", payload)
    print(json.dumps(res, indent=2))


def cmd_show(args):
    """Show details of a specific publisher/affiliate."""
    payload = {
        "action": "show",
        "affiliate_id": args.affiliate_id
    }
    res = call_tool("affiliates.read", payload)
    print(json.dumps(res, indent=2))


def cmd_create(args):
    """Create a new publisher/affiliate."""
    payload = {
        "action": "create",
        "dry_run": args.dry_run
    }
    if args.company_name:
        payload["company_name"] = args.company_name
    if args.first_name:
        payload["first_name"] = args.first_name
    if args.last_name:
        payload["last_name"] = args.last_name
    if args.time_zone:
        payload["time_zone"] = args.time_zone
    if args.iana_time_zone:
        payload["iana_time_zone"] = args.iana_time_zone
    if args.client_afid:
        payload["client_afid"] = args.client_afid
    if args.alternative_id:
        payload["alternative_id"] = args.alternative_id
    if args.static_number_cap is not None:
        payload["static_number_cap"] = args.static_number_cap
    if args.business_hours:
        try:
            payload["business_hours"] = json.loads(args.business_hours)
        except Exception as e:
            sys.stderr.write(f"Error parsing --business-hours JSON: {e}\n")
            sys.exit(1)

    res = call_tool("affiliates.manage", payload)
    print(json.dumps(res, indent=2))


def cmd_update(args):
    """Update an existing publisher/affiliate."""
    payload = {
        "action": "update",
        "affiliate_id": args.affiliate_id,
        "dry_run": args.dry_run
    }
    if args.company_name is not None:
        payload["company_name"] = args.company_name
    if args.first_name is not None:
        payload["first_name"] = args.first_name
    if args.last_name is not None:
        payload["last_name"] = args.last_name
    if args.time_zone is not None:
        payload["time_zone"] = args.time_zone
    if args.iana_time_zone is not None:
        payload["iana_time_zone"] = args.iana_time_zone
    if args.client_afid is not None:
        payload["client_afid"] = args.client_afid
    if args.alternative_id is not None:
        payload["alternative_id"] = args.alternative_id
    if args.static_number_cap is not None:
        payload["static_number_cap"] = args.static_number_cap
    if args.paused is not None:
        payload["paused"] = args.paused
    if args.business_hours:
        try:
            payload["business_hours"] = json.loads(args.business_hours)
        except Exception as e:
            sys.stderr.write(f"Error parsing --business-hours JSON: {e}\n")
            sys.exit(1)

    res = call_tool("affiliates.manage", payload)
    print(json.dumps(res, indent=2))


def cmd_create_key(args):
    """Create a postback key for a publisher/affiliate or campaign."""
    payload = {
        "action": "create",
        "postbackable_type": args.postbackable_type,
        "postbackable_id": args.postbackable_id,
        "postback_action": args.postback_action,
        "dry_run": args.dry_run
    }
    if args.name:
        payload["name"] = args.name
    if args.tag_prefix:
        payload["tag_prefix"] = args.tag_prefix
    if args.affiliate_id is not None:
        payload["affiliate_id"] = args.affiliate_id
    if args.ttl_seconds is not None:
        payload["ttl_seconds"] = args.ttl_seconds
    if args.start_seconds is not None:
        payload["start_seconds"] = args.start_seconds
    if args.end_seconds is not None:
        payload["end_seconds"] = args.end_seconds
    if args.timeout is not None:
        payload["timeout"] = args.timeout
    if args.inbound_number:
        payload["inbound_number"] = args.inbound_number
    if args.claim_percent_threshold is not None:
        payload["claim_percent_threshold"] = args.claim_percent_threshold
    if args.blocked_inbound_percent is not None:
        payload["blocked_inbound_percent"] = args.blocked_inbound_percent
    if args.add_to_caps_on_status_reserved is not None:
        payload["add_to_caps_on_status_reserved"] = args.add_to_caps_on_status_reserved
    if args.allow_no_caller_number is not None:
        payload["allow_no_caller_number"] = args.allow_no_caller_number
    if args.sip_auth_method:
        payload["sip_auth_method"] = args.sip_auth_method

    res = call_tool("postback_keys.manage", payload)
    print(json.dumps(res, indent=2))


def cmd_list_keys(args):
    """List postback keys for a publisher/affiliate or campaign."""
    payload = {
        "action": "index",
        "postbackable_type": args.postbackable_type,
        "postbackable_id": args.postbackable_id,
        "page": args.page,
        "per_page": args.per_page
    }
    if args.postback_key_id:
        payload["action"] = "show"
        payload["postback_key_id"] = args.postback_key_id

    res = call_tool("postback_keys.read", payload)
    print(json.dumps(res, indent=2))


def main():
    parser = argparse.ArgumentParser(
        description="Retreaver Publisher/Affiliate Operations CLI tool",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # list
    p_list = subparsers.add_parser("list", help="List publishers/affiliates")
    p_list.add_argument("--page", type=int, default=1, help="Page number")
    p_list.add_argument("--per-page", type=int, default=25, help="Items per page (max 100)")
    p_list.set_defaults(func=cmd_list)

    # show
    p_show = subparsers.add_parser("show", help="Show publisher details")
    p_show.add_argument("--affiliate-id", type=int, required=True, help="Publisher/Affiliate ID")
    p_show.set_defaults(func=cmd_show)

    # create
    p_create = subparsers.add_parser("create", help="Create a new publisher/affiliate")
    p_create.add_argument("--company-name", type=str, help="Company name")
    p_create.add_argument("--first-name", type=str, help="Contact first name")
    p_create.add_argument("--last-name", type=str, help="Contact last name")
    p_create.add_argument("--time-zone", type=str, default="Eastern Time (US & Canada)", help="Display time zone")
    p_create.add_argument("--iana-time-zone", type=str, help="IANA time zone (e.g., America/New_York)")
    p_create.add_argument("--client-afid", type=str, help="Client custom affiliate ID / slug")
    p_create.add_argument("--alternative-id", type=str, help="External ID / partner reference")
    p_create.add_argument("--static-number-cap", type=int, help="Limit on static numbers allocated")
    p_create.add_argument("--business-hours", type=str, help="JSON string of weekly business hours array")
    p_create.add_argument("--dry-run", action="store_true", help="Preview only without making changes")
    p_create.set_defaults(func=cmd_create)

    # update
    p_update = subparsers.add_parser("update", help="Update an existing publisher/affiliate")
    p_update.add_argument("--affiliate-id", type=int, required=True, help="Publisher/Affiliate ID")
    p_update.add_argument("--company-name", type=str, help="Company name")
    p_update.add_argument("--first-name", type=str, help="Contact first name")
    p_update.add_argument("--last-name", type=str, help="Contact last name")
    p_update.add_argument("--time-zone", type=str, help="Display time zone")
    p_update.add_argument("--iana-time-zone", type=str, help="IANA time zone")
    p_update.add_argument("--client-afid", type=str, help="Client custom affiliate ID")
    p_update.add_argument("--alternative-id", type=str, help="External ID / partner reference")
    p_update.add_argument("--static-number-cap", type=int, help="Limit on static numbers allocated")
    p_update.add_argument("--paused", dest="paused", action="store_true", default=None, help="Pause traffic from publisher")
    p_update.add_argument("--resume", dest="paused", action="store_false", help="Resume traffic from publisher")
    p_update.add_argument("--business-hours", type=str, help="JSON string of weekly business hours array")
    p_update.add_argument("--dry-run", action="store_true", help="Preview only without making changes")
    p_update.set_defaults(func=cmd_update)

    # create-key
    p_ckey = subparsers.add_parser("create-key", help="Create a postback key (RTB or data_writing)")
    p_ckey.add_argument("--postbackable-type", type=str, default="Affiliate",
                        choices=["Affiliate", "Campaign", "Company"], help="Owner entity type")
    p_ckey.add_argument("--postbackable-id", type=int, required=True, help="Owner entity ID")
    p_ckey.add_argument("--postback-action", type=str, required=True,
                        choices=["rtb", "data_writing"], help="Kind of key")
    p_ckey.add_argument("--name", type=str, help="Descriptive name for the postback key")
    p_ckey.add_argument("--tag-prefix", type=str, help="Tag namespace prefix ending in underscore (e.g. pub1_)")
    p_ckey.add_argument("--affiliate-id", type=int, help="Publisher ID to bind if creating on Campaign")
    p_ckey.add_argument("--ttl-seconds", type=int, default=15, help="RTB reservation TTL seconds (10-999)")
    p_ckey.add_argument("--start-seconds", type=int, help="Data writing allowed post-call window in seconds")
    p_ckey.add_argument("--end-seconds", type=int, help="Data writing pre-call tag storage window in seconds")
    p_ckey.add_argument("--timeout", type=float, default=5.0, help="RTB evaluation timeout in seconds")
    p_ckey.add_argument("--inbound-number", type=str, help="Fixed inbound number override for RTB")
    p_ckey.add_argument("--claim-percent-threshold", type=float, help="Ping shield claim ratio threshold")
    p_ckey.add_argument("--blocked-inbound-percent", type=float, help="Ping shield throttle block percentage")
    p_ckey.add_argument("--add-to-caps-on-status-reserved", action="store_true", default=None, help="Hold caps on initial reservation")
    p_ckey.add_argument("--allow-no-caller-number", action="store_true", default=None, help="Allow SIP transfer without caller number")
    p_ckey.add_argument("--sip-auth-method", type=str, choices=["ip_whitelist", "credentials"], help="SIP authentication method")
    p_ckey.add_argument("--dry-run", action="store_true", help="Preview only without making changes")
    p_ckey.set_defaults(func=cmd_create_key)

    # list-keys
    p_lkeys = subparsers.add_parser("list-keys", help="List postback keys for an affiliate or campaign")
    p_lkeys.add_argument("--postbackable-type", type=str, default="Affiliate",
                         choices=["Affiliate", "Campaign", "Company"], help="Owner entity type")
    p_lkeys.add_argument("--postbackable-id", type=int, required=True, help="Owner entity ID")
    p_lkeys.add_argument("--postback-key-id", type=int, help="Optional specific key ID to show")
    p_lkeys.add_argument("--page", type=int, default=1, help="Page number")
    p_lkeys.add_argument("--per-page", type=int, default=25, help="Items per page (max 100)")
    p_lkeys.set_defaults(func=cmd_list_keys)

    parsed = parser.parse_args()
    parsed.func(parsed)


if __name__ == "__main__":
    main()
