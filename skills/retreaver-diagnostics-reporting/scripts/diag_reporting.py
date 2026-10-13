#!/usr/bin/env python3
"""
Retreaver Diagnostics & Reporting CLI

Provides operational diagnostic tools and reporting rollups for Retreaver:
- rtb-summary: Aggregates RTB pings and status breakdowns across campaigns/publishers
- rtb-diagnose: Analyzes ping failures (no-target, expired, ping_shield, capacity codes)
- call-stats: Real-time and historical call performance rollups (volume, revenue, payout, profit)
- call-flow: Detailed routing lifecycle and step inspection for specific calls
- export: Create and poll asynchronous CSV exports for RTB reservations
"""

import argparse
import json
import os
import sys
import time

# Ensure retreaver_client can be imported
sys.path.append("/tmp")
try:
    from retreaver_client import call_tool
except ImportError:
    # Direct fallback if /tmp/retreaver_client.py is referenced relatively
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "tmp")))
    from retreaver_client import call_tool


def format_output(data, as_json=False):
    if as_json:
        print(json.dumps(data, indent=2))
        return

    # Basic structured print
    if isinstance(data, dict):
        print(json.dumps(data, indent=2))
    elif isinstance(data, list):
        print(json.dumps(data, indent=2))
    else:
        print(data)


def cmd_rtb_summary(args):
    """Summarize RTB activity across dimensions."""
    columns = [args.group_by] if args.group_by else ["status"]
    metrics = [
        "count_of_target_resolutions",
        "percentage_of_total_target_resolutions",
        "bid_percentage",
        "no_bid_percentage",
        "average_winning_bid",
    ]
    tool_args = {
        "action": "index",
        "columns": columns,
        "metrics": metrics,
    }
    if args.campaign_id:
        tool_args["campaign_id"] = [int(args.campaign_id)]
    if args.affiliate_id:
        tool_args["affiliate_id"] = [int(args.affiliate_id)]
    if args.target_id:
        tool_args["target_id"] = [int(args.target_id)]
    if args.time_frame:
        tool_args["created_at"] = args.time_frame

    res = call_tool("rtb_inbound_drill_down_tables.read", tool_args)
    format_output(res, args.json)


def cmd_rtb_diagnose(args):
    """Diagnose RTB ping failures and identify bottlenecks."""
    columns = ["status"]
    metrics = [
        "count_of_target_resolutions",
        "percentage_of_total_target_resolutions",
        "original_count",
        "duplicate_count",
        "ping_shield_postback_key_claim_based_limited",
        "ping_shield_already_reserved",
        "ping_shield_already_processing",
        "bid_percentage",
        "no_bid_percentage",
    ]
    tool_args = {
        "action": "index",
        "columns": columns,
        "metrics": metrics,
    }
    if args.campaign_id:
        tool_args["campaign_id"] = [int(args.campaign_id)]
    if args.affiliate_id:
        tool_args["affiliate_id"] = [int(args.affiliate_id)]
    if args.postback_key_id:
        tool_args["postback_key_id"] = [int(args.postback_key_id)]
    if args.time_frame:
        tool_args["created_at"] = args.time_frame

    res = call_tool("rtb_inbound_drill_down_tables.read", tool_args)

    # If raw reservations inspection requested or status specified
    if args.inspect_raw or args.status:
        raw_args = {"action": "index", "per_page": args.limit or 20}
        if args.campaign_id:
            raw_args["campaign_id"] = [int(args.campaign_id)]
        if args.affiliate_id:
            raw_args["affiliate_id"] = [int(args.affiliate_id)]
        if args.status:
            raw_args["status"] = [args.status]
        if args.time_frame:
            raw_args["created_at"] = args.time_frame
        raw_res = call_tool("rtb_inbounds.read", raw_args)
        combined = {
            "diagnostic_rollup": res,
            "sample_reservations": raw_res.get("inbound_records", raw_res.get("rtb_inbounds", raw_res)),
        }
        format_output(combined, args.json)
    else:
        format_output(res, args.json)


def cmd_call_stats(args):
    """Compute call volume, revenue, payout, and profit statistics."""
    columns = [args.group_by] if args.group_by else ["campaign_id"]
    metrics = [
        "total_",
        "connected_",
        "revenue_",
        "payout_",
        "profit_",
        "cost_",
        "epc_total",
        "cpc_total",
    ]
    tool_args = {
        "action": "index",
        "columns": columns,
        "metrics": metrics,
    }
    if args.campaign_id:
        tool_args["campaign_id"] = [int(args.campaign_id)]
    if args.affiliate_id:
        tool_args["affiliate_id"] = [int(args.affiliate_id)]
    if args.target_id:
        tool_args["target_id"] = [int(args.target_id)]
    if args.status:
        tool_args["status"] = [args.status]
    if args.time_frame:
        tool_args["created_at"] = args.time_frame

    res = call_tool("calls_drill_down_tables.read", tool_args)
    format_output(res, args.json)


def cmd_call_flow(args):
    """Inspect the step-by-step routing flow and attributes for a call."""
    tool_args = {
        "action": "show",
        "uuid": args.uuid,
    }
    res = call_tool("calls.read", tool_args)
    format_output(res, args.json)


def cmd_export(args):
    """Create or poll RTB CSV exports."""
    if args.poll_id:
        tool_args = {
            "action": "show",
            "export_id": int(args.poll_id),
        }
        res = call_tool("exports.rtb_inbounds.manage", tool_args)
        format_output(res, args.json)
        return

    # Create export
    tool_args = {
        "action": "create",
        "format": "csv",
    }
    if args.campaign_id:
        tool_args["campaign_id"] = [int(args.campaign_id)]
    if args.affiliate_id:
        tool_args["affiliate_id"] = [int(args.affiliate_id)]
    if args.status:
        tool_args["status"] = [args.status]
    if args.time_frame:
        tool_args["created_at"] = args.time_frame

    res = call_tool("exports.rtb_inbounds.manage", tool_args)
    format_output(res, args.json)


def main():
    parser = argparse.ArgumentParser(
        description="Retreaver Diagnostics and Reporting CLI",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--json", action="store_true", help="Output raw JSON response")
    subparsers = parser.add_subparsers(dest="subcommand", help="Diagnostic subcommands")

    # rtb-summary
    p_summary = subparsers.add_parser("rtb-summary", help="Aggregate RTB pings and status breakdowns")
    p_summary.add_argument("--group-by", choices=["campaign_id", "affiliate_id", "target_id", "postback_key_id", "status", "caller_state"], default="status", help="Grouping dimension")
    p_summary.add_argument("--campaign-id", type=int, help="Filter by campaign ID")
    p_summary.add_argument("--affiliate-id", type=int, help="Filter by publisher/affiliate ID")
    p_summary.add_argument("--target-id", type=int, help="Filter by buyer/target ID")
    p_summary.add_argument("--time-frame", default="last_7d", help="Time frame token (e.g., last_24h, last_7d, last_30d)")

    # rtb-diagnose
    p_diag = subparsers.add_parser("rtb-diagnose", help="Diagnose RTB failures, rate limits, and unrouted pings")
    p_diag.add_argument("--campaign-id", type=int, help="Filter by campaign ID")
    p_diag.add_argument("--affiliate-id", type=int, help="Filter by publisher/affiliate ID")
    p_diag.add_argument("--postback-key-id", type=int, help="Filter by postback key ID")
    p_diag.add_argument("--status", help="Filter by specific RTB status (expired, no-target, rejected, ping_shield_...)")
    p_diag.add_argument("--time-frame", default="last_7d", help="Time frame token")
    p_diag.add_argument("--inspect-raw", action="store_true", help="Include sample individual reservation records")
    p_diag.add_argument("--limit", type=int, default=10, help="Limit for sample raw reservation records")

    # call-stats
    p_stats = subparsers.add_parser("call-stats", help="Compute call performance rollups (volume, revenue, payout, profit)")
    p_stats.add_argument("--group-by", choices=["campaign_id", "affiliate_id", "target_id", "status", "caller_state", "disposition_disposition_code", "intent_primary_topic"], default="campaign_id", help="Grouping dimension")
    p_stats.add_argument("--campaign-id", type=int, help="Filter by campaign ID")
    p_stats.add_argument("--affiliate-id", type=int, help="Filter by publisher/affiliate ID")
    p_stats.add_argument("--target-id", type=int, help="Filter by target ID")
    p_stats.add_argument("--status", help="Filter by call status (established, canceled, busy, failed, etc.)")
    p_stats.add_argument("--time-frame", default="last_7d", help="Time frame token")

    # call-flow
    p_flow = subparsers.add_parser("call-flow", help="Inspect call flow and routing lifecycle for a call UUID")
    p_flow.add_argument("uuid", help="Call UUID")

    # export
    p_export = subparsers.add_parser("export", help="Create or poll CSV export of RTB reservations")
    p_export.add_argument("--campaign-id", type=int, help="Filter by campaign ID")
    p_export.add_argument("--affiliate-id", type=int, help="Filter by publisher/affiliate ID")
    p_export.add_argument("--status", help="Filter by status")
    p_export.add_argument("--time-frame", default="last_7d", help="Time frame token")
    p_export.add_argument("--poll-id", type=int, help="Export ID to poll progress for")

    args = parser.parse_args()

    if not args.subcommand:
        parser.print_help()
        sys.exit(0)

    if args.subcommand == "rtb-summary":
        cmd_rtb_summary(args)
    elif args.subcommand == "rtb-diagnose":
        cmd_rtb_diagnose(args)
    elif args.subcommand == "call-stats":
        cmd_call_stats(args)
    elif args.subcommand == "call-flow":
        cmd_call_flow(args)
    elif args.subcommand == "export":
        cmd_export(args)


if __name__ == "__main__":
    main()
