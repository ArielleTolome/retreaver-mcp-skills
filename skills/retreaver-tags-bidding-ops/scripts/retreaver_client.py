import json
import os
import sys
import time
import urllib.parse
import urllib.request

MCP_URL = os.environ.get("RETREAVER_MCP_URL", "https://ai.retreaver.com/mcp")
TOKEN_URL = os.environ.get("RETREAVER_TOKEN_URL", "https://retreaver.com/oauth/token")
CLIENT_ID = os.environ.get("RETREAVER_CLIENT_ID", "mcp_client_rkFh19Fy7plE74WEACpmcAUqVpg9LMoB")
RESOURCE = "https://ai.retreaver.com/mcp"

# Candidate token files
TOKEN_FILES = [
    os.environ.get("RETREAVER_TOKEN_FILE", ""),
    os.path.expanduser("~/.retreaver_oauth_token.json"),
    "/tmp/retreaver_token.json",
]

def get_valid_token():
    # 1. Environment variable
    env_token = os.environ.get("RETREAVER_TOKEN") or os.environ.get("RETREAVER_MCP_TOKEN")
    if env_token:
        return env_token

    # 2. Token file
    token_file = None
    for tf in TOKEN_FILES:
        if tf and os.path.exists(tf):
            token_file = tf
            break

    if not token_file:
        raise RuntimeError("No Retreaver OAuth token found. Set RETREAVER_TOKEN or authenticate via Retreaver MCP.")

    with open(token_file, "r") as f:
        data = json.load(f)

    # Auto-refresh if approaching expiration
    if time.time() > data.get("expires_at", 0) - 45 and data.get("refresh_token"):
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
        try:
            with urllib.request.urlopen(req) as resp:
                new_data = json.loads(resp.read().decode())
                data["access_token"] = new_data["access_token"]
                data["refresh_token"] = new_data.get("refresh_token", data["refresh_token"])
                data["expires_at"] = time.time() + new_data.get("expires_in", 899)
                with open(token_file, "w") as fw:
                    json.dump(data, fw)
        except Exception:
            # Fall back to using existing token
            pass

    return data.get("access_token")

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
        "params": {
            "name": name,
            "arguments": args,
        },
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
