#!/usr/bin/env python3
"""
Retreaver Campaign & Routing Operations CLI
Wraps Retreaver MCP tools:
- campaigns.read
- campaigns.manage
- campaigns.routing_settings.read
- campaigns.routing_settings.manage
- target_groups.read
- target_groups.manage
- target_groups.duplicates.manage
- prompts.read
- prompts.manage
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from retreaver_client import call_tool


def emit(action, data, status="success"):
    if isinstance(data, dict) and data.get("status") == "dry_run":
        status = "dry_run"
    print(json.dumps({"status": status, "action": action, "data": data}, indent=2))


def cmd_list(args):
    params = {"action": "index", "page": args.page, "per_page": args.per_page}
    emit("list", call_tool("campaigns.read", params))


def cmd_show(args):
    params = {"action": "show", "campaign_id": args.campaign_id}
    emit("show", call_tool("campaigns.read", params))


def _campaign_fields(args):
    params = {}
    field_map = {
        "name": "name",
        "client_cid": "client_cid",
        "target_number": "target_number",
        "click_url": "click_url",
        "sale_url": "sale_url",
        "dedupe_seconds": "dedupe_seconds",
        "record_calls": "record_calls",
        "record_seconds": "record_seconds",
        "waiting_room_seconds": "waiting_room_seconds",
        "waiting_room_tries": "waiting_room_tries",
        "repeat_caller_type": "repeat_caller_type",
        "new_target_rolling_reset_days": "new_target_rolling_reset_days",
        "repeat_caller_tag_values_inherit": "repeat_caller_tag_values_inherit",
        "duplicate_caller_type": "duplicate_caller_type",
        "auto_route_repeat_calls": "auto_route_repeat_calls",
        "conversion_propagation": "conversion_propagation",
        "use_global_suppression_list": "use_global_suppression_list",
        "use_carrier_geo_information": "use_carrier_geo_information",
        "use_caller_number_geo_information": "use_caller_number_geo_information",
        "click_to_call": "click_to_call",
        "affiliate_can_pull_number": "affiliate_can_pull_number",
        "paused": "paused",
        "dry_run": "dry_run",
    }
    for attr, key in field_map.items():
        val = getattr(args, attr, None)
        if val is not None:
            params[key] = val
    return params


def cmd_create(args):
    params = {"action": "create"}
    params.update(_campaign_fields(args))
    if getattr(args, "campaign_id", None) is not None:
        params["action"] = "update"
        params["campaign_id"] = args.campaign_id
    emit(params["action"], call_tool("campaigns.manage", params))


def cmd_pause(args):
    params = {"action": "update", "campaign_id": args.campaign_id, "paused": True}
    if args.dry_run:
        params["dry_run"] = True
    emit("pause", call_tool("campaigns.manage", params))


def cmd_resume(args):
    params = {"action": "update", "campaign_id": args.campaign_id, "paused": False}
    if args.dry_run:
        params["dry_run"] = True
    emit("resume", call_tool("campaigns.manage", params))


def cmd_routing(args):
    if args.routing_action == "show":
        res = call_tool("campaigns.routing_settings.read", {
            "action": "show",
            "campaign_id": args.campaign_id,
        })
        emit("routing_show", res)
    elif args.routing_action == "update":
        if args.menu_options_json:
            menu_options = json.loads(args.menu_options_json)
        else:
            row = {}
            if args.row_id is not None:
                row["id"] = args.row_id
            if args.destroy_row:
                row["_destroy"] = True
            if args.target_id is not None:
                row["target_id"] = args.target_id
            if args.target_group_id is not None:
                row["target_group_id"] = args.target_group_id
            if args.priority is not None:
                row["priority"] = args.priority
            if args.weight is not None:
                row["weight"] = args.weight
            if args.locked is not None:
                row["locked"] = args.locked == "true"
            if args.disabled is not None:
                row["disabled"] = args.disabled == "true"
            if args.route_by_bid is not None:
                row["enable_route_by_bid"] = args.route_by_bid == "true"
            if args.route_by_performance is not None:
                row["enable_route_by_performance"] = args.route_by_performance == "true"
            if args.route_by_state_performance is not None:
                row["enable_route_by_state_performance"] = args.route_by_state_performance == "true"
            if args.performance_type is not None:
                row["performance_type"] = args.performance_type
            if args.min_calls_required is not None:
                row["min_calls_required"] = args.min_calls_required
            if args.lookback_days is not None:
                row["performance_lookback_period_value"] = args.lookback_days
            if args.default_performance is not None:
                row["default_performance"] = args.default_performance

            opt = {"action": args.option_action}
            if args.option_id is not None:
                opt["id"] = args.option_id
            if args.options:
                opt["options"] = [x.strip() for x in args.options.split(",") if x.strip()]
            if args.topic is not None:
                opt["topic"] = args.topic
            if args.topic_hint is not None:
                opt["topic_hint"] = args.topic_hint
            if row:
                opt["menu_options_targets_attributes"] = [row]
            menu_options = [opt]

        params = {
            "action": "update",
            "campaign_id": args.campaign_id,
            "menu_options_attributes": menu_options,
        }
        if args.dry_run:
            params["dry_run"] = True
        emit("routing_update", call_tool("campaigns.routing_settings.manage", params))


def cmd_groups(args):
    act = args.group_action
    if act == "list":
        res = call_tool("target_groups.read", {
            "action": "index",
            "page": args.page,
            "per_page": args.per_page,
        })
        emit("groups_list", res)
    elif act == "show":
        res = call_tool("target_groups.read", {
            "action": "show",
            "target_group_id": args.target_group_id,
        })
        emit("groups_show", res)
    elif act == "duplicate":
        res = call_tool("target_groups.duplicates.manage", {
            "action": "create",
            "target_group_id": args.target_group_id,
        })
        emit("groups_duplicate", res)
    elif act in ("create", "update", "delete"):
        params = {"action": act}
        if args.target_group_id is not None:
            params["target_group_id"] = args.target_group_id
        if args.name is not None:
            params["name"] = args.name
        if args.target_ids:
            params["target_ids"] = [int(x.strip()) for x in args.target_ids.split(",") if x.strip()]
        if args.priority is not None:
            params["priority"] = args.priority
        if args.weight is not None:
            params["weight"] = args.weight
        if args.concurrency_cap is not None:
            params["concurrency_cap"] = None if args.concurrency_cap == -1 else args.concurrency_cap
        if args.cap_trigger is not None:
            params["cap_trigger"] = args.cap_trigger
        if args.dedupe_as_company is not None:
            params["dedupe_as_company"] = args.dedupe_as_company == "true"
        if args.paused is not None:
            params["paused"] = args.paused == "true"
        if args.dry_run:
            params["dry_run"] = True
        emit(f"groups_{act}", call_tool("target_groups.manage", params))


def cmd_prompts(args):
    act = args.prompt_op
    base = {
        "promptable_type": args.promptable_type,
        "promptable_id": args.promptable_id,
    }
    if act == "list":
        params = {"action": "index", **base}
        emit("prompts_list", call_tool("prompts.read", params))
    elif act == "show":
        params = {"action": "show", "prompt_id": args.prompt_id, **base}
        emit("prompts_show", call_tool("prompts.read", params))
    elif act in ("create", "update", "delete"):
        params = {"action": act, **base}
        if args.prompt_id is not None:
            params["prompt_id"] = args.prompt_id
        if args.prompt_action is not None:
            params["prompt_action"] = args.prompt_action
        if args.tts is not None:
            params["tts"] = args.tts
        if args.tts_gender is not None:
            params["tts_gender"] = args.tts_gender
        if args.tts_language is not None:
            params["tts_language"] = args.tts_language
        if args.preset is not None:
            params["preset"] = args.preset
        if args.repeat is not None:
            params["repeat"] = args.repeat
        if args.moment is not None:
            params["moment"] = args.moment
        if args.max_attempts is not None:
            params["max_attempts"] = args.max_attempts
        if args.voice_recognition_enabled is not None:
            params["voice_recognition_enabled"] = args.voice_recognition_enabled == "true"
        if args.voice_recognition_transcript is not None:
            params["voice_recognition_transcript"] = args.voice_recognition_transcript
        if args.dry_run:
            params["dry_run"] = True
        emit(f"prompts_{act}", call_tool("prompts.manage", params))


def _add_campaign_args(p):
    p.add_argument("--campaign-id", type=int, help="Campaign ID (triggers update when passed to create)")
    p.add_argument("--name", help="Campaign display name")
    p.add_argument("--client-cid", help="Custom client campaign identifier (CID)")
    p.add_argument("--target-number", help="Default fallback target phone number")
    p.add_argument("--click-url", help="Landing page click URL")
    p.add_argument("--sale-url", help="Post-conversion sale URL")
    p.add_argument("--dedupe-seconds", type=int, help="Deduplication window in seconds")
    p.add_argument("--record-calls", type=lambda x: x.lower() == "true", help="Record inbound calls (true/false)")
    p.add_argument("--record-seconds", type=int, help="Max recording seconds")
    p.add_argument("--waiting-room-seconds", type=int, help="Waiting room max hold duration in seconds")
    p.add_argument("--waiting-room-tries", type=int, help="Waiting room max routing retry attempts")
    p.add_argument("--repeat-caller-type", help="Repeat caller mode (e.g. default, previous, new)")
    p.add_argument("--new-target-rolling-reset-days", type=int, help="Days without calls before buyer is treated as new")
    p.add_argument("--repeat-caller-tag-values-inherit", help="Repeat caller tag inheritance behavior")
    p.add_argument("--duplicate-caller-type", help="Duplicate caller handling mode")
    p.add_argument("--auto-route-repeat-calls", type=lambda x: x.lower() == "true", help="Auto-route repeat callers (true/false)")
    p.add_argument("--conversion-propagation", type=lambda x: x.lower() == "true", help="Propagate conversions downstream (true/false)")
    p.add_argument("--use-global-suppression-list", type=lambda x: x.lower() == "true", help="Enforce company global suppression list (true/false)")
    p.add_argument("--use-carrier-geo-information", type=lambda x: x.lower() == "true", help="Enable telco carrier geo tags (true/false)")
    p.add_argument("--use-caller-number-geo-information", type=lambda x: x.lower() == "true", help="Enable NPA-NXX phone geo tags (true/false)")
    p.add_argument("--click-to-call", type=lambda x: x.lower() == "true", help="Allow programmatic click-to-call (true/false)")
    p.add_argument("--affiliate-can-pull-number", type=lambda x: x.lower() == "true", help="Allow publishers to self-provision DIDs (true/false)")
    p.add_argument("--paused", type=lambda x: x.lower() == "true", help="Initial or updated pause state (true/false)")
    p.add_argument("--dry-run", action="store_true", help="Preview changes without applying")


def main():
    parser = argparse.ArgumentParser(
        description="Retreaver Campaign, Call Routing, Buyer Groups & IVR Prompts CLI"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # list
    p_list = sub.add_parser("list", help="List campaigns")
    p_list.add_argument("--page", type=int, default=1, help="Page number")
    p_list.add_argument("--per-page", type=int, default=25, help="Results per page (max 100)")
    p_list.set_defaults(func=cmd_list)

    # show
    p_show = sub.add_parser("show", help="Show a single campaign in full")
    p_show.add_argument("campaign_id", type=int, help="Campaign integer ID")
    p_show.set_defaults(func=cmd_show)

    # create (also supports --campaign-id for update)
    p_create = sub.add_parser("create", help="Create or update a campaign (including Waiting Room & Geo settings)")
    _add_campaign_args(p_create)
    p_create.set_defaults(func=cmd_create)

    # pause
    p_pause = sub.add_parser("pause", help="Pause a campaign")
    p_pause.add_argument("campaign_id", type=int, help="Campaign integer ID")
    p_pause.add_argument("--dry-run", action="store_true", help="Preview diff only")
    p_pause.set_defaults(func=cmd_pause)

    # resume
    p_resume = sub.add_parser("resume", help="Resume a paused campaign")
    p_resume.add_argument("campaign_id", type=int, help="Campaign integer ID")
    p_resume.add_argument("--dry-run", action="store_true", help="Preview diff only")
    p_resume.set_defaults(func=cmd_resume)

    # routing
    p_routing = sub.add_parser("routing", help="Inspect or update campaign routing settings & menu options")
    p_routing.add_argument("routing_action", choices=["show", "update"], help="Routing operation: show or update")
    p_routing.add_argument("campaign_id", type=int, help="Campaign integer ID")
    p_routing.add_argument("--menu-options-json", help="Raw JSON array for menu_options_attributes")
    p_routing.add_argument("--option-id", type=int, help="Existing menu option ID to update")
    p_routing.add_argument("--option-action", type=int, default=1, choices=[1, 2, 3, 6, 7], help="Menu option action (1=dial, 2=redirect, 3=block, 6=end, 7=cake)")
    p_routing.add_argument("--options", help="Comma-separated DTMF keys (e.g. '-1' for default route, '1,2')")
    p_routing.add_argument("--topic", help="Voice recognition spoken topic phrase")
    p_routing.add_argument("--topic-hint", help="Voice recognition matcher hint")
    p_routing.add_argument("--row-id", type=int, help="Existing routing row ID to update")
    p_routing.add_argument("--destroy-row", action="store_true", help="Remove the specified routing row (_destroy=true)")
    p_routing.add_argument("--target-id", type=int, help="Target (buyer) ID for routing row")
    p_routing.add_argument("--target-group-id", type=int, help="Target Group ID for routing row")
    p_routing.add_argument("--priority", type=int, help="Row priority tier (requires --locked false)")
    p_routing.add_argument("--weight", type=int, help="Row weight within tier (requires --locked false)")
    p_routing.add_argument("--locked", choices=["true", "false"], help="Lock to target's own priority/weight (true/false)")
    p_routing.add_argument("--disabled", choices=["true", "false"], help="Disable row in campaign routing (true/false)")
    p_routing.add_argument("--route-by-bid", choices=["true", "false"], help="Reorder priority tier by highest RTB bid")
    p_routing.add_argument("--route-by-performance", choices=["true", "false"], help="Reorder priority tier by EPC performance")
    p_routing.add_argument("--route-by-state-performance", choices=["true", "false"], help="Use caller-state EPC performance")
    p_routing.add_argument("--performance-type", choices=["strict", "weighted"], help="Performance ordering mode")
    p_routing.add_argument("--min-calls-required", type=int, help="Minimum calls before EPC routing activates")
    p_routing.add_argument("--lookback-days", type=int, help="Days of history for EPC evaluation")
    p_routing.add_argument("--default-performance", type=int, help="Default EPC value while learning")
    p_routing.add_argument("--dry-run", action="store_true", help="Preview diff only")
    p_routing.set_defaults(func=cmd_routing)

    # groups
    p_groups = sub.add_parser("groups", help="Manage handler/buyer groups (target_groups)")
    p_groups.add_argument("group_action", choices=["list", "show", "create", "update", "delete", "duplicate"], help="Group operation")
    p_groups.add_argument("--target-group-id", type=int, help="Target Group ID (required for show/update/delete/duplicate)")
    p_groups.add_argument("--name", help="Target Group name")
    p_groups.add_argument("--target-ids", help="Comma-separated member buyer/target IDs (replaces full membership)")
    p_groups.add_argument("--priority", type=int, help="Group priority")
    p_groups.add_argument("--weight", type=int, help="Group weight")
    p_groups.add_argument("--concurrency-cap", type=int, help="Group concurrency cap (-1 to clear)")
    p_groups.add_argument("--cap-trigger", choices=["connection", "conversion"], help="Group cap trigger")
    p_groups.add_argument("--dedupe-as-company", choices=["true", "false"], help="Dedupe callers across all buyers in group")
    p_groups.add_argument("--paused", choices=["true", "false"], help="Pause or resume group")
    p_groups.add_argument("--page", type=int, default=1, help="Page number for list")
    p_groups.add_argument("--per-page", type=int, default=25, help="Results per page for list")
    p_groups.add_argument("--dry-run", action="store_true", help="Preview diff only")
    p_groups.set_defaults(func=cmd_groups)

    # prompts
    p_prompts = sub.add_parser("prompts", help="Manage IVR prompts and greetings on Campaigns, Targets, or Numbers")
    p_prompts.add_argument("prompt_op", choices=["list", "show", "create", "update", "delete"], help="Prompt operation")
    p_prompts.add_argument("--promptable-type", default="Campaign", choices=["Campaign", "Target", "Number"], help="Owner resource type (default: Campaign)")
    p_prompts.add_argument("--promptable-id", type=int, required=True, help="Owner resource ID")
    p_prompts.add_argument("--prompt-id", type=int, help="Prompt ID (required for show/update/delete)")
    p_prompts.add_argument("--prompt-action", help="Prompt kind (e.g. greeting, whisper, music_on_hold, zip_code_entry_unless_already_present, key_press_1)")
    p_prompts.add_argument("--tts", help="Spoken Text-to-Speech message (supports [tag_key] tokens)")
    p_prompts.add_argument("--tts-gender", choices=["Female", "Male"], help="TTS voice gender")
    p_prompts.add_argument("--tts-language", help="TTS language code (e.g. en-US)")
    p_prompts.add_argument("--preset", help="Music or audio preset name")
    p_prompts.add_argument("--repeat", type=int, help="Number of times to repeat prompt (must be 0 for voice recognition)")
    p_prompts.add_argument("--moment", choices=["before_data_appending", "before_start"], help="Execution timing moment")
    p_prompts.add_argument("--max-attempts", type=int, help="Maximum caller input attempts")
    p_prompts.add_argument("--voice-recognition-enabled", choices=["true", "false"], help="Enable press-or-say speech gather (requires repeat=0 and en-US)")
    p_prompts.add_argument("--voice-recognition-transcript", help="Transcript of spoken choices for uploaded audio (<4000 chars)")
    p_prompts.add_argument("--dry-run", action="store_true", help="Preview diff only")
    p_prompts.set_defaults(func=cmd_prompts)

    args = parser.parse_args()
    try:
        args.func(args)
    except Exception as exc:
        print(json.dumps({
            "status": "error",
            "action": getattr(args, "command", "unknown"),
            "data": {},
            "error_details": str(exc),
        }, indent=2))
        sys.exit(1)


if __name__ == "__main__":
    main()
