#!/bin/bash
# homelab-security — Claude Code cloud-session setup script.
#
# Point your project's setup script at this (or paste its body). It:
#   1. builds the flattened skills + generated agents from the manifest
#   2. installs them into ~/.claude so every session in this environment
#      discovers them regardless of working directory
#
# Assumes this repo is already present (the cloud environment clones your
# configured source repo before running setup). If you instead want setup to
# clone it, uncomment the git clone block below.
set -euo pipefail

# --- locate the repo -------------------------------------------------------
# If the environment already cloned this repo, set REPO to its path.
REPO="${REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}"

# To have setup clone it instead, uncomment and set the URL:
# REPO="${HOME}/red-team"
# [ -d "$REPO" ] || git clone --depth 1 https://github.com/NoahIles/red-team "$REPO"

# --- build -----------------------------------------------------------------
pip install --quiet pyyaml >/dev/null 2>&1 || true
python3 "$REPO/build_skills.py" --all --target "$REPO/.claude"

# --- install into ~/.claude (user scope, loads in every session) -----------
mkdir -p "$HOME/.claude/skills" "$HOME/.claude/agents"
# skills: copy each flattened skill up to the user skills root
cp -r "$REPO/.claude/skills/." "$HOME/.claude/skills/"
# agents: copy generated agent definitions
cp -r "$REPO/.claude/agents/." "$HOME/.claude/agents/"

echo "homelab-security installed:"
echo "  skills: $(find "$HOME/.claude/skills" -name SKILL.md | wc -l | tr -d ' ')"
echo "  agents: $(find "$HOME/.claude/agents" -maxdepth 1 -name '*.md' | wc -l | tr -d ' ')"
