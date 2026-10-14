#!/usr/bin/env bash
set -euo pipefail

DEST_DIR="${1:-$HOME/.agents/skills}"
echo "Installing 9 Retreaver Operator Skills to: $DEST_DIR"

mkdir -p "$DEST_DIR"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

for skill_dir in "$SCRIPT_DIR"/skills/retreaver-*; do
  if [ -d "$skill_dir" ]; then
    skill_name="$(basename "$skill_dir")"
    echo "  → Installing skill: $skill_name"
    rm -rf "$DEST_DIR/$skill_name"
    cp -r "$skill_dir" "$DEST_DIR/"
    
    # Link into Claude, Codex, Grok, and Hermes skill directories if present
    for h_dir in "$HOME/.claude/skills" "$HOME/.codex/skills" "$HOME/.grok/skills" "$HOME/.hermes/skills"; do
      if [ -d "$h_dir" ]; then
        rm -rf "$h_dir/$skill_name"
        ln -s "$DEST_DIR/$skill_name" "$h_dir/$skill_name"
      fi
    done
  fi
done

# Ensure omp agent skills symlink exists if ~/.omp exists
if [ -d "$HOME/.omp/agent" ] && [ ! -e "$HOME/.omp/agent/skills" ]; then
  echo "Linking to ~/.omp/agent/skills..."
  ln -s "$DEST_DIR" "$HOME/.omp/agent/skills"
fi

# Install Slash Command Prompt Shortcuts (/retreaver:*)
if [ -d "$SCRIPT_DIR/commands/retreaver" ]; then
  echo ""
  echo "Installing 10 Slash Command Prompt Shortcuts (/retreaver:*):"
  mkdir -p "$HOME/.claude/commands/retreaver" "$HOME/.omp/agent/commands/retreaver" "$HOME/.cursor/commands"
  for cmd_file in "$SCRIPT_DIR"/commands/retreaver/*.md; do
    if [ -f "$cmd_file" ]; then
      cmd_base="$(basename "$cmd_file" .md)"
      echo "  → /retreaver:$cmd_base"
      cp "$cmd_file" "$HOME/.claude/commands/retreaver/$cmd_base.md"
      cp "$cmd_file" "$HOME/.omp/agent/commands/retreaver/$cmd_base.md"
      cp "$cmd_file" "$HOME/.cursor/commands/retreaver-$cmd_base.md"
    fi
  done
fi

echo ""
echo "✔ All 9 Retreaver Operator Skills & 10 Prompt Shortcuts successfully installed!"
