#!/usr/bin/env python3
"""
Retreaver Buyer Operations CLI
Implements:
- list: List or search buyers/targets
- show: Inspect a single buyer in detail
- create: Create a new buyer/target
- update: Update buyer attributes (pause, priority, weight, timeout, tags, etc.)
- set-caps: Update caps (hard, hourly, daily, monthly, concurrency, cap_trigger)
- reset-cap: Reset hard cap counter for a buyer
- duplicate: Clone an existing buyer with deep copy of settings
"""

import argparse
import json
import os
import sys

# Import retreaver_client from /tmp
sys.path.append("/tmp")
try:
    from retreaver_client import call_tool
except ImportError:
    # Inline fallback if not present in /tmp
    import time
    import urllib.parse
    import urllib.request

    TOKEN_FILE = "/tmp/retreaver_token.json"
    CLIENT_ID = "mcp_client_rkFh19Fy7plE74WEACpmcAUqVpg9LMoB"
    RESOURCE = "https://ai.retreaver.com/mcp"
    TOKEN_URL = "https://retreaver.com/oauth/token"
    MCP_URL = "https://ai.retreaver.com/mcp"

    def get_valid_token():
        with open(TOKEN_FILE, "r") as f:
            data = json.load(f)
        if time.time() > data.get("expires_at", 0) - 30:
            params = {
                "grant_type": "refresh_token",
                "client_id": CLIENT_ID,
                "refresh_token": data["refresh_token"],
                "resource": RESOURCE,
            }
            req = urllib.request.Request(
                TOKEN_URL,
                data=urllib.parse.urlencode(params).encode(),
                method="POST",
            )
            req.add_header("Content-Type", "application/x-www-form-urlencoded")
            with urllib.request.urlopen(req) as resp:
                new_data = json.loads(resp.read().decode())
                data["access_token"] = new_data["access_token"]
                data["refresh_token"] = new_data["refresh_token"]
                data["expires_at"] = time.time() + new_data.get("expires_in", 899)
                with open(TOKEN_FILE, "w") as fw:
                    json.dump(data, fw)
        return data["access_token"]

    def call_tool(name, args=None):
        if args is None:
            args = {}
        token = get_valid_token()
        req = urllib.request.Request(MCP_URL, method="POST")
        req.add_header("Authorization", f"Bearer {token}")
        req.add_header("Content-Type", "application/json")
        req.add_header("Accept", "application/json, text/event-stream")
        body = {
            "jsonrpc": "2.0",
            "id": int(time.time() * 1000) % 1000000,
            "method": "tools/call",
            "params": {"name": name, "arguments": args},
        }
        req.data = json.dumps(body).encode("utf-8")
        with urllib.request.urlopen(req) as resp:
            res = json.loads(resp.read().decode("utf-8"))
            if "result" in res and "structuredContent" in res["result"]:
                return res["result"]["structuredContent"]
            elif "result" in res and "content" in res["result"]:
                for item in res["result"]["content"]:
                    if item.get("type") == "text":
                        try:
                            return json.loads(item["text"])
                        except Exception:
                            return item["text"]
            return res


def print_json(data):
    print(json.dumps(data, indent=2))


def cmd_list(args):
    params = {"action": "index", "page": args.page, "per_page": args.per_page}
    if args.query:
        params["query"] = args.query
    res = call_tool("targets.read", params)
    print_json(res)


def cmd_show(args):
    params = {"action": "show", "target_id": args.target_id}
    res = call_tool("targets.read", params)
    print_json(res)


def cmd_create(args):
    params = {
        "action": "create",
        "name": args.name,
        "number": args.number,
    }
    if args.dry_run:
        params["dry_run"] = True
    if args.priority is not None:
        params["priority"] = args.priority
    if args.weight is not None:
        params["weight"] = args.weight
    if args.timeout is not None:
        params["timeout_seconds"] = args.timeout
    if args.time_zone:
        params["time_zone"] = args.time_zone
    if args.concurrency_cap is not None:
        params["concurrency_cap"] = args.concurrency_cap
    if args.cap_trigger:
        params["cap_trigger"] = args.cap_trigger
    if args.tag_list:
        params["tag_list"] = args.tag_list
    if args.forward_tag_list:
        params["forward_tag_list"] = args.forward_tag_list
    if args.client_tid:
        params["client_tid"] = args.client_tid

    res = call_tool("targets.manage", params)
    print_json(res)


def cmd_update(args):
    params = {
        "action": "update",
        "target_id": args.target_id,
    }
    if args.dry_run:
        params["dry_run"] = True
    if args.name is not None:
        params["name"] = args.name
    if args.number is not None:
        params["number"] = args.number
    if args.paused is not None:
        params["paused"] = args.paused
    if args.priority is not None:
        params["priority"] = args.priority
    if args.weight is not None:
        params["weight"] = args.weight
    if args.timeout is not None:
        params["timeout_seconds"] = args.timeout
    if args.time_zone is not None:
        params["time_zone"] = args.time_zone
    if args.tag_list is not None:
        params["tag_list"] = args.tag_list
    if args.forward_tag_list is not None:
        params["forward_tag_list"] = args.forward_tag_list
    if args.concurrency_cap is not None:
        params["concurrency_cap"] = args.concurrency_cap
    if args.cap_trigger is not None:
        params["cap_trigger"] = args.cap_trigger
    if args.client_tid is not None:
        params["client_tid"] = args.client_tid

    res = call_tool("targets.manage", params)
    print_json(res)


def cmd_set_caps(args):
    params = {
        "action": "update",
        "target_id": args.target_id,
    }
    if args.dry_run:
        params["dry_run"] = True
    if args.hard_cap is not None:
        params["hard_cap"] = None if args.hard_cap == -1 else args.hard_cap
    if args.hourly_cap is not None:
        params["hourly_cap"] = None if args.hourly_cap == -1 else args.hourly_cap
    if args.daily_cap is not None:
        params["daily_cap"] = None if args.daily_cap == -1 else args.daily_cap
    if args.monthly_cap is not None:
        params["monthly_cap"] = None if args.monthly_cap == -1 else args.monthly_cap
    if args.concurrency_cap is not None:
        params["concurrency_cap"] = None if args.concurrency_cap == -1 else args.concurrency_cap
    if args.cap_trigger is not None:
        params["cap_trigger"] = args.cap_trigger

    res = call_tool("targets.caps.manage", params)
    print_json(res)


def cmd_reset_cap(args):
    params = {
        "action": "create",
        "target_id": args.target_id,
    }
    res = call_tool("targets.cap_resets.manage", params)
    print_json(res)


def cmd_duplicate(args):
    params = {
        "action": "create",
        "target_id": args.target_id,
    }
    res = call_tool("targets.duplicates.manage", params)
    print_json(res)


def main():
    parser = argparse.ArgumentParser(
        description="Retreaver Buyer Operations CLI (targets, caps, priority, tags, schedules)"
    )
    subparsers = parser.add_subparsers(dest="command", help="Buyer operational command")

    # list
    p_list = subparsers.add_parser("list", help="List or search buyers/targets")
    p_list.add_argument("--query", "-q", help="Search substring (name, number, client id)")
    p_list.add_argument("--page", type=int, default=1, help="Page number (default: 1)")
    p_list.add_argument("--per-page", type=int, default=20, help="Results per page (default: 20)")
    p_list.set_defaults(func=cmd_list)

    # show
    p_show = subparsers.add_parser("show", help="Show full details for a buyer")
    p_show.add_argument("target_id", type=int, help="Target/Buyer ID")
    p_show.set_defaults(func=cmd_show)

    # create
    p_create = subparsers.add_parser("create", help="Create a new buyer")
    p_create.add_argument("--name", "-n", required=True, help="Target/Buyer name")
    p_create.add_argument("--number", required=True, help="Destination phone number (E.164) or token")
    p_create.add_argument("--priority", type=int, default=1, help="Routing priority (lower = evaluated first)")
    p_create.add_argument("--weight", type=int, default=1, help="Weight within priority tier")
    p_create.add_argument("--timeout", type=int, default=30, help="Connection timeout seconds")
    p_create.add_argument("--time-zone", help="Timezone (e.g. 'Eastern Time (US & Canada)')")
    p_create.add_argument("--concurrency-cap", type=int, help="Max simultaneous calls")
    p_create.add_argument("--cap-trigger", choices=["connection", "conversion"], help="Cap increment trigger")
    p_create.add_argument("--tag-list", help="Standard tag filter list (<<<key:value>>> format)")
    p_create.add_argument("--forward-tag-list", help="Forward tag list (evaluated post-selection)")
    p_create.add_argument("--client-tid", help="Internal client tracking ID")
    p_create.add_argument("--dry-run", action="store_true", help="Preview change without applying")
    p_create.set_defaults(func=cmd_create)

    # update
    p_update = subparsers.add_parser("update", help="Update buyer parameters")
    p_update.add_argument("target_id", type=int, help="Target/Buyer ID")
    p_update.add_argument("--name", "-n", help="Target name")
    p_update.add_argument("--number", help="Destination number (E.164)")
    p_update.add_argument("--paused", type=lambda x: x.lower() in ["true", "1", "yes"], help="Set paused state (true/false)")
    p_update.add_argument("--priority", type=int, help="Routing priority")
    p_update.add_argument("--weight", type=int, help="Weight ratio within tier")
    p_update.add_argument("--timeout", type=int, help="Connection timeout in seconds")
    p_update.add_argument("--time-zone", help="Buyer timezone")
    p_update.add_argument("--tag-list", help="Standard tag filter list")
    p_update.add_argument("--forward-tag-list", help="Forward tag list")
    p_update.add_argument("--concurrency-cap", type=int, help="Concurrency limit")
    p_update.add_argument("--cap-trigger", choices=["connection", "conversion"], help="Cap increment trigger")
    p_update.add_argument("--client-tid", help="Internal client tracking ID")
    p_update.add_argument("--dry-run", action="store_true", help="Preview change without applying")
    p_update.set_defaults(func=cmd_update)

    # set-caps
    p_caps = subparsers.add_parser("set-caps", help="Configure volume and concurrency caps")
    p_caps.add_argument("target_id", type=int, help="Target/Buyer ID")
    p_caps.add_argument("--hard-cap", type=int, help="Cumulative lifetime cap (-1 to remove)")
    p_caps.add_argument("--hourly-cap", type=int, help="Hourly clock cap (-1 to remove)")
    p_caps.add_argument("--daily-cap", type=int, help="Daily calendar cap (-1 to remove)")
    p_caps.add_argument("--monthly-cap", type=int, help="Monthly calendar cap (-1 to remove)")
    p_caps.add_argument("--concurrency-cap", type=int, help="Max simultaneous calls (-1 to remove)")
    p_caps.add_argument("--cap-trigger", choices=["connection", "conversion"], help="Cap trigger event")
    p_caps.add_argument("--dry-run", action="store_true", help="Preview change without applying")
    p_caps.set_defaults(func=cmd_set_caps)

    # reset-cap
    p_reset = subparsers.add_parser("reset-cap", help="Reset hard cap counter for a buyer")
    p_reset.add_argument("target_id", type=int, help="Target/Buyer ID")
    p_reset.set_defaults(func=cmd_reset_cap)

    # duplicate
    p_dup = subparsers.add_parser("duplicate", help="Clone an existing buyer")
    p_dup.add_argument("target_id", type=int, help="Target/Buyer ID to clone")
    p_dup.set_defaults(func=cmd_duplicate)

    args = parser.parse_args()
    if not hasattr(args, "func"):
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
