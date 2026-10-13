#!/usr/bin/env bash
set -euo pipefail

DEST_DIR="${1:-$HOME/.agents/skills}"
echo "Installing Retreaver Operator Skills to: $DEST_DIR"

mkdir -p "$DEST_DIR"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

for skill_dir in "$SCRIPT_DIR"/skills/retreaver-*; do
  if [ -d "$skill_dir" ]; then
    skill_name="$(basename "$skill_dir")"
    echo "  → Installing $skill_name..."
    rm -rf "$DEST_DIR/$skill_name"
    cp -r "$skill_dir" "$DEST_DIR/"
  fi
done

# Ensure omp agent skills symlink exists if ~/.omp exists
if [ -d "$HOME/.omp/agent" ] && [ ! -e "$HOME/.omp/agent/skills" ]; then
  echo "Linking to ~/.omp/agent/skills..."
  ln -s "$DEST_DIR" "$HOME/.omp/agent/skills"
fi

echo ""
echo "✔ All Retreaver Operator Skills successfully installed!"
echo ""
echo "Next: Configure the Retreaver MCP server (https://ai.retreaver.com/mcp) in your client:"
echo "  • Claude Code: claude mcp add --transport http retreaver --scope user https://ai.retreaver.com/mcp"
echo "  • Codex:       codex mcp add retreaver --url https://ai.retreaver.com/mcp"
echo "  • Grok:        grok mcp add --transport http retreaver https://ai.retreaver.com/mcp"
echo "  • Hermes:      hermes config set mcp_servers.retreaver.url https://ai.retreaver.com/mcp"
echo "  • OMP / Cursor: Add 'retreaver' URL to ~/.omp/agent/mcp.json or ~/.cursor/mcp.json"
