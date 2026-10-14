#!/usr/bin/env python3
"""
Retreaver Operator Unified CLI
Provides direct operational commands for Retreaver MCP API:
- buyers (targets)
- publishers (affiliates)
- webhooks / timers
- RTB diagnostics & ping/post analysis
- call analytics & real-time stats
"""

import argparse
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

TOKEN_FILE = os.path.expanduser("~/.retreaver_oauth_token.json")
# Fallback to /tmp if home is read-only
if not os.path.exists(TOKEN_FILE) and os.path.exists("/tmp/retreaver_token.json"):
    TOKEN_FILE = "/tmp/retreaver_token.json"

CLIENT_ID = "mcp_client_rkFh19Fy7plE74WEACpmcAUqVpg9LMoB"
RESOURCE = "https://ai.retreaver.com/mcp"
TOKEN_URL = "https://retreaver.com/oauth/token"
MCP_URL = "https://ai.retreaver.com/mcp"

def get_valid_token():
    if not os.path.exists(TOKEN_FILE):
        if os.path.exists("/tmp/retreaver_token.json"):
            with open("/tmp/retreaver_token.json") as f:
                data = json.load(f)
        else:
            raise RuntimeError(f"No token file found at {TOKEN_FILE} or /tmp/retreaver_token.json")
    else:
        with open(TOKEN_FILE) as f:
            data = json.load(f)

    if time.time() > data.get("expires_at", 0) - 45:
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
            # Also sync /tmp
            try:
                with open("/tmp/retreaver_token.json", "w") as tfw:
                    json.dump(data, tfw)
            except Exception:
                pass
    return data["access_token"]

def call_mcp(name, args=None):
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
        if "error" in res:
            raise RuntimeError(f"MCP error {res['error'].get('code')}: {res['error'].get('message')}")
        result = res.get("result", {})
        if "structuredContent" in result:
            return result["structuredContent"]
        if "content" in result:
            for item in result["content"]:
                if item.get("type") == "text":
                    try:
                        return json.loads(item["text"])
                    except Exception:
                        return item["text"]
        return result

def cmd_whoami(args):
    data = call_mcp("account.whoami")
    print(json.dumps(data, indent=2))

def cmd_buyer(args):
    if args.action == "list":
        res = call_mcp("targets.read", {"action": "index", "per_page": args.limit})
        print(json.dumps(res, indent=2))
    elif args.action == "show":
        res = call_mcp("targets.read", {"action": "show", "target_id": args.target_id})
        print(json.dumps(res, indent=2))
    elif args.action == "create":
        payload = {
            "action": "create",
            "name": args.name,
            "number": args.number,
            "priority": args.priority,
            "weight": args.weight,
            "timeout_seconds": args.timeout,
            "dry_run": args.dry_run,
        }
        res = call_mcp("targets.manage", payload)
        print(json.dumps(res, indent=2))
    elif args.action == "caps":
        payload = {
            "target_id": args.target_id,
            "hourly": args.hourly,
            "daily": args.daily,
            "monthly": args.monthly,
            "concurrency": args.concurrency,
            "hard": args.hard,
            "dry_run": args.dry_run,
        }
        res = call_mcp("targets.caps.manage", {k: v for k, v in payload.items() if v is not None})
        print(json.dumps(res, indent=2))

def cmd_publisher(args):
    if args.action == "list":
        res = call_mcp("affiliates.read", {"action": "index", "per_page": args.limit})
        print(json.dumps(res, indent=2))
    elif args.action == "show":
        res = call_mcp("affiliates.read", {"action": "show", "affiliate_id": args.affiliate_id})
        print(json.dumps(res, indent=2))
    elif args.action == "create":
        payload = {
            "action": "create",
            "name": args.name,
            "email": args.email,
            "dry_run": args.dry_run,
        }
        res = call_mcp("affiliates.manage", {k: v for k, v in payload.items() if v is not None})
        print(json.dumps(res, indent=2))

def cmd_webhook(args):
    if args.action == "list":
        res = call_mcp("webhooks.read", {
            "action": "index",
            "timerable_type": args.type,
            "timerable_id": args.id,
            "per_page": args.limit,
        })
        print(json.dumps(res, indent=2))
    elif args.action == "templates":
        res = call_mcp("webhooks.templates.read", {"per_page": args.limit})
        print(json.dumps(res, indent=2))
    elif args.action == "test-fire":
        res = call_mcp("webhooks.test_fires.manage", {"action": "create", "webhook_id": args.webhook_id})
        print(json.dumps(res, indent=2))

def cmd_rtb_diag(args):
    minutes = args.minutes
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(minutes=minutes)
    res = call_mcp("rtb_inbounds.read", {"action": "index", "per_page": 100})
    rows = res.get("rtb_inbounds", []) if isinstance(res, dict) else []
    
    recent = []
    for r in rows:
        c_str = r.get("created_at")
        if c_str:
            dt = datetime.fromisoformat(c_str.replace("Z", "+00:00"))
            if dt >= cutoff:
                recent.append(r)
                
    counts = {}
    for r in recent:
        st = r.get("status", "unknown")
        counts[st] = counts.get(st, 0) + 1
        
    print(f"--- RTB DIAGNOSTICS (Last {minutes} Minutes) ---")
    print(f"Total Inbounds: {len(recent)}")
    print(f"Status Breakdown: {json.dumps(counts, indent=2)}")
    
    if recent:
        print("\nTop Inbounds:")
        for r in recent[:10]:
            print(f"- {r.get('uuid')} | {r.get('created_at')} | status={r.get('status')} | target={r.get('target_id')} | rev=${r.get('revenue')} | state={r.get('caller_state')}")

def cmd_stats(args):
    res = call_mcp("calls_drill_down_tables.read", {
        "action": "index",
        "created_at": args.window,
        "columns": ["campaign_id", "status"],
    })
    print(json.dumps(res, indent=2))

def cmd_audit(args):
    who = call_mcp("account.whoami")
    campaigns = call_mcp("campaigns.read", {"action": "index", "per_page": 100}).get("campaigns", [])
    targets = call_mcp("targets.read", {"action": "index", "per_page": 100}).get("targets", [])
    numbers = call_mcp("numbers.read", {"action": "index", "per_page": 100}).get("numbers", [])
    pools = call_mcp("number_pools.read", {"action": "index", "per_page": 100}).get("number_pools", [])
    
    uncapped_targets = []
    token_targets = []
    for t in targets:
        if not t.get("paused") and str(t.get("number", "")).startswith("["):
            token_targets.append({"id": t.get("id"), "name": t.get("name"), "number": t.get("number")})
        t_detail = call_mcp("targets.read", {"action": "show", "target_id": t["id"]}).get("target", {})
        caps = t_detail.get("caps", [])
        if not t.get("paused") and all(c.get("cap") is None for c in caps) and t_detail.get("concurrency_cap") is None:
            uncapped_targets.append({"id": t.get("id"), "name": t.get("name")})
            
    paused_cids = {c.get("cid"): c.get("name") for c in campaigns if c.get("paused")}
    orphaned_numbers = [
        {"id": n.get("id"), "number": n.get("number"), "campaign": paused_cids[n.get("cid")]}
        for n in numbers if n.get("cid") in paused_cids
    ]
    
    report = {
        "status": "success",
        "command": "audit",
        "company": who.get("company"),
        "counts": {
            "campaigns": len(campaigns),
            "targets": len(targets),
            "numbers": len(numbers),
            "number_pools": len(pools),
        },
        "findings": {
            "active_targets_without_caps": uncapped_targets,
            "dynamic_token_targets": token_targets,
            "numbers_on_paused_campaigns": orphaned_numbers,
        },
    }
    print(json.dumps(report, indent=2))

def main():
    parser = argparse.ArgumentParser(description="Retreaver Operator CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # whoami
    subparsers.add_parser("whoami", help="Check Retreaver current user and company")

    # buyer
    p_buyer = subparsers.add_parser("buyer", help="Manage buyers / targets")
    p_buyer.add_argument("action", choices=["list", "show", "create", "caps"])
    p_buyer.add_argument("--target-id", type=int, help="Target ID for show/caps")
    p_buyer.add_argument("--name", type=str, help="Target Name")
    p_buyer.add_argument("--number", type=str, help="Destination phone number")
    p_buyer.add_argument("--priority", type=int, default=1, help="Priority tier (1 is highest)")
    p_buyer.add_argument("--weight", type=int, default=1, help="Weight allocation")
    p_buyer.add_argument("--timeout", type=int, default=30, help="Dial timeout seconds")
    p_buyer.add_argument("--concurrency", type=int, help="Concurrency cap")
    p_buyer.add_argument("--hourly", type=int, help="Hourly cap")
    p_buyer.add_argument("--daily", type=int, help="Daily cap")
    p_buyer.add_argument("--monthly", type=int, help="Monthly cap")
    p_buyer.add_argument("--hard", type=int, help="Hard cap")
    p_buyer.add_argument("--dry-run", action="store_true", help="Preview only")
    p_buyer.add_argument("--limit", type=int, default=25, help="Results limit")
    p_buyer.set_defaults(func=cmd_buyer)

    # publisher
    p_pub = subparsers.add_parser("publisher", help="Manage publishers / affiliates")
    p_pub.add_argument("action", choices=["list", "show", "create"])
    p_pub.add_argument("--affiliate-id", type=int, help="Affiliate ID for show")
    p_pub.add_argument("--name", type=str, help="Affiliate Name")
    p_pub.add_argument("--email", type=str, help="Affiliate Email")
    p_pub.add_argument("--dry-run", action="store_true", help="Preview only")
    p_pub.add_argument("--limit", type=int, default=25, help="Results limit")
    p_pub.set_defaults(func=cmd_publisher)

    # webhook
    p_wh = subparsers.add_parser("webhook", help="Manage webhooks / timers")
    p_wh.add_argument("action", choices=["list", "templates", "test-fire"])
    p_wh.add_argument("--type", type=str, default="Campaign", choices=["Campaign", "Target", "Company"], help="Timerable type")
    p_wh.add_argument("--id", type=int, help="Timerable resource ID")
    p_wh.add_argument("--webhook-id", type=int, help="Webhook ID for test-fire")
    p_wh.add_argument("--limit", type=int, default=25, help="Results limit")
    p_wh.set_defaults(func=cmd_webhook)

    # rtb-diag
    p_rtb = subparsers.add_parser("rtb-diag", help="Diagnose RTB pings and reservation failures")
    p_rtb.add_argument("--minutes", type=int, default=15, help="Window minutes to analyze (default: 15)")
    p_rtb.set_defaults(func=cmd_rtb_diag)

    # stats
    p_stats = subparsers.add_parser("stats", help="Get call and revenue statistics")
    p_stats.add_argument("--window", type=str, default="today", help="Window token (e.g. today, yesterday, last_7d)")
    p_stats.set_defaults(func=cmd_stats)

    # audit
    p_audit = subparsers.add_parser("audit", help="Run full operational housekeeping audit")
    p_audit.set_defaults(func=cmd_audit)

    args = parser.parse_args()
    if args.command == "whoami":
        cmd_whoami(args)
    else:
        args.func(args)

if __name__ == "__main__":
    main()
