#!/bin/bash
# red-team — Claude Code cloud-session setup script.
#
# Paste this into your Claude Code project's environment setup-script field
# (Project settings → environment). It runs before each session and:
#   1. clones (or updates) this repo
#   2. builds the team: flattens the upstream skills + generates the agents
#   3. installs skills AND agents into ~/.claude so every session discovers them
#
# Idempotent — safe to run on every session start.
set -euo pipefail

REPO_DIR="${HOME}/red-team"
REPO_URL="https://github.com/NoahIles/red-team"

# 1. Get (or update) the team repo
if [ -d "$REPO_DIR/.git" ]; then
  git -C "$REPO_DIR" fetch --depth 1 origin main
  git -C "$REPO_DIR" reset --hard origin/main
else
  git clone --depth 1 "$REPO_URL" "$REPO_DIR"
fi

# 2. Build: flatten upstream skills + generate agents from the manifest
pip install --quiet pyyaml >/dev/null 2>&1 || true
python3 "$REPO_DIR/build_skills.py" --all --target "$REPO_DIR/.claude"

# 3. Install into ~/.claude so every session discovers them
rm -rf "${HOME}/.claude/skills/claude-red"   # drop the old non-working nested clone, if present
mkdir -p "${HOME}/.claude/skills" "${HOME}/.claude/agents"
cp -r "$REPO_DIR/.claude/skills/." "${HOME}/.claude/skills/"
cp -r "$REPO_DIR/.claude/agents/." "${HOME}/.claude/agents/"

echo "red-team installed: $(find "${HOME}/.claude/skills" -name SKILL.md | wc -l | tr -d ' ') skills, $(find "${HOME}/.claude/agents" -maxdepth 1 -name '*.md' | wc -l | tr -d ' ') agents"
