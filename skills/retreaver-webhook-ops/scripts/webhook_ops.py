#!/usr/bin/env python3
"""Retreaver Webhook & Integration Operations CLI.

Supports managing webhooks/timers across Campaign, Target, Number, and Company scopes,
instantiating configurator templates, and executing synthetic test-fires.
"""

import argparse
import json
import os
import sys

# Ensure retreaver_client can be imported from /tmp
if "/tmp" not in sys.path:
    sys.path.insert(0, "/tmp")

try:
    import retreaver_client
except ImportError:
    print(json.dumps({
        "status": "error",
        "error": "Missing /tmp/retreaver_client.py"
    }))
    sys.exit(1)


def cmd_list(args):
    """List webhooks for an owner (Campaign, Target, Number, Company)."""
    tool_args = {
        "action": "index",
        "timerable_type": args.owner_type,
        "timerable_id": args.owner_id,
        "page": args.page,
        "per_page": args.per_page
    }
    res = retreaver_client.call_tool("webhooks.read", tool_args)
    print(json.dumps(res, indent=2))


def cmd_show(args):
    """Show details of a specific webhook."""
    tool_args = {
        "action": "show",
        "timerable_type": args.owner_type,
        "timerable_id": args.owner_id,
        "webhook_id": args.webhook_id
    }
    res = retreaver_client.call_tool("webhooks.read", tool_args)
    print(json.dumps(res, indent=2))


def cmd_create(args):
    """Create a new webhook with pixels."""
    pixels = []
    if args.url:
        pixel = {
            "url": args.url,
            "request_method": args.method.lower(),
            "fire_order": args.fire_order or 0
        }
        if args.headers:
            try:
                hdrs = json.loads(args.headers)
                if isinstance(hdrs, dict):
                    pixel["headers"] = [{"key": k, "value": str(v)} for k, v in hdrs.items()]
                elif isinstance(hdrs, list):
                    pixel["headers"] = hdrs
            except Exception as e:
                print(json.dumps({"status": "error", "error": f"Invalid headers JSON: {e}"}))
                sys.exit(1)
        pixels.append(pixel)
    elif args.pixels_json:
        try:
            pixels = json.loads(args.pixels_json)
        except Exception as e:
            print(json.dumps({"status": "error", "error": f"Invalid pixels JSON: {e}"}))
            sys.exit(1)

    tool_args = {
        "action": "create",
        "timerable_type": args.owner_type,
        "timerable_id": args.owner_id,
        "name": args.name,
        "trigger_type": args.trigger_type,
        "pixels": pixels
    }
    if args.seconds is not None:
        tool_args["seconds"] = args.seconds
    if args.tag_list:
        tool_args["tag_list"] = args.tag_list
    if args.dedupe_seconds is not None:
        tool_args["dedupe_seconds"] = args.dedupe_seconds
    if args.re_fireable is not None:
        tool_args["re_fireable"] = args.re_fireable

    res = retreaver_client.call_tool("webhooks.manage", tool_args)
    print(json.dumps(res, indent=2))


def cmd_from_template(args):
    """Instantiate a webhook from a pre-built configurator template."""
    params = {}
    if args.params:
        try:
            params = json.loads(args.params)
        except Exception as e:
            print(json.dumps({"status": "error", "error": f"Invalid params JSON: {e}"}))
            sys.exit(1)

    tool_args = {
        "action": "create",
        "timerable_type": args.owner_type,
        "timerable_id": args.owner_id,
        "template_id": args.template_id,
        "parameters": params
    }
    if args.name:
        tool_args["name"] = args.name

    res = retreaver_client.call_tool("webhooks.configurations.manage", tool_args)
    print(json.dumps(res, indent=2))


def cmd_test_fire(args):
    """Simulate and test-fire an existing webhook."""
    tool_args = {
        "action": "create",
        "webhook_id": args.webhook_id
    }
    if args.number_id:
        tool_args["number_id"] = args.number_id
    if args.target_id:
        tool_args["target_id"] = args.target_id
    if args.affiliate_id:
        tool_args["affiliate_id"] = args.affiliate_id
    if args.tag_list:
        tool_args["tag_list"] = args.tag_list

    res = retreaver_client.call_tool("webhooks.test_fires.manage", tool_args)
    print(json.dumps(res, indent=2))


def cmd_templates(args):
    """List or show webhook configurator templates."""
    tool_args = {"action": "show" if args.template_id else "index"}
    if args.template_id:
        tool_args["template_id"] = args.template_id
    res = retreaver_client.call_tool("webhooks.templates.read", tool_args)
    print(json.dumps(res, indent=2))


def main():
    parser = argparse.ArgumentParser(
        description="Retreaver Webhook & Integration Operations CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # list
    p_list = subparsers.add_parser("list", help="List webhooks for an owner")
    p_list.add_argument("--owner-type", required=True, choices=["Campaign", "Target", "Number", "Company"], help="Owner entity type")
    p_list.add_argument("--owner-id", required=True, type=int, help="Owner entity ID")
    p_list.add_argument("--page", type=int, default=1, help="Page number (default: 1)")
    p_list.add_argument("--per-page", type=int, default=25, help="Items per page (default: 25)")
    p_list.set_defaults(func=cmd_list)

    # show
    p_show = subparsers.add_parser("show", help="Show webhook details")
    p_show.add_argument("--owner-type", required=True, choices=["Campaign", "Target", "Number", "Company"], help="Owner entity type")
    p_show.add_argument("--owner-id", required=True, type=int, help="Owner entity ID")
    p_show.add_argument("--webhook-id", required=True, type=int, help="Webhook ID")
    p_show.set_defaults(func=cmd_show)

    # create
    p_create = subparsers.add_parser("create", help="Create a new webhook")
    p_create.add_argument("--owner-type", required=True, choices=["Campaign", "Target", "Number", "Company"], help="Owner entity type")
    p_create.add_argument("--owner-id", required=True, type=int, help="Owner entity ID")
    p_create.add_argument("--name", required=True, help="Webhook display name")
    p_create.add_argument("--trigger-type", required=True, type=int, help="Trigger type ID (e.g. 9=start, 12=passthrough, 2=timer, 1=always)")
    p_create.add_argument("--url", help="Pixel URL to fire")
    p_create.add_argument("--method", default="get", choices=["get", "post"], help="HTTP method (default: get)")
    p_create.add_argument("--headers", help="JSON dictionary or list of headers")
    p_create.add_argument("--fire-order", type=int, default=0, help="Pixel execution order")
    p_create.add_argument("--seconds", type=int, help="Delay / timer threshold seconds")
    p_create.add_argument("--tag-list", help="Tag filter <<<key:val>>>")
    p_create.add_argument("--dedupe-seconds", type=int, help="Dedupe window seconds")
    p_create.add_argument("--re-fireable", action="store_true", default=None, help="Allow multiple fires per call")
    p_create.add_argument("--pixels-json", help="Full JSON array of pixel objects")
    p_create.set_defaults(func=cmd_create)

    # from-template
    p_tpl_create = subparsers.add_parser("from-template", help="Create webhook from configurator template")
    p_tpl_create.add_argument("--owner-type", required=True, choices=["Campaign", "Target", "Number", "Company"], help="Owner entity type")
    p_tpl_create.add_argument("--owner-id", required=True, type=int, help="Owner entity ID")
    p_tpl_create.add_argument("--template-id", required=True, help="Template ID (e.g. callgrid_bid, track_drive_ping_post)")
    p_tpl_create.add_argument("--params", help="JSON dictionary of template parameters")
    p_tpl_create.add_argument("--name", help="Optional custom name override")
    p_tpl_create.set_defaults(func=cmd_from_template)

    # test-fire
    p_test = subparsers.add_parser("test-fire", help="Test-fire an existing webhook")
    p_test.add_argument("--webhook-id", required=True, type=int, help="Webhook ID to test")
    p_test.add_argument("--number-id", type=int, help="Optional Number ID context")
    p_test.add_argument("--target-id", type=int, help="Optional Target ID context")
    p_test.add_argument("--affiliate-id", type=int, help="Optional Publisher ID context")
    p_test.add_argument("--tag-list", help="Optional tag seeding format (<<<key:val>>>)")
    p_test.set_defaults(func=cmd_test_fire)

    # templates
    p_tpl = subparsers.add_parser("templates", help="List or inspect configurator templates")
    p_tpl.add_argument("--template-id", help="Template ID to inspect; omit to list all")
    p_tpl.set_defaults(func=cmd_templates)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
