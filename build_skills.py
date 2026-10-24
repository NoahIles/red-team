#!/usr/bin/env python3
"""Build the homelab-security agent team from manifest.yaml.

Two independent steps:

  skills  -> vendor the upstream offensive-security library and FLATTEN it so
             each skill sits at <skills-dir>/<skill-name>/SKILL.md (the only
             layout Claude Code discovers).
  agents  -> generate one <agents-dir>/<name>.md per enabled lane in the
             manifest (soft scoping: each keeps the Skill tool, no preload).

Usage:
  ./build_skills.py --all                 # skills + agents (default)
  ./build_skills.py --agents              # regenerate agent files only
  ./build_skills.py --skills              # vendor + flatten skills only
  ./build_skills.py --validate            # check manifest <-> upstream coverage
  ./build_skills.py --all --target ~/.claude   # write into a different root

Default target root is ".claude" next to this script. Within it:
  <target>/skills/   and   <target>/agents/
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("PyYAML required: pip install pyyaml")

HERE = Path(__file__).resolve().parent
MANIFEST = HERE / "manifest.yaml"


def load_manifest() -> dict:
    with open(MANIFEST) as f:
        return yaml.safe_load(f)


def run(cmd: list[str], **kw) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, check=True, **kw)


# --------------------------------------------------------------------------- #
# skills: clone upstream (pinned) and flatten into <skills-dir>/<name>/
# --------------------------------------------------------------------------- #
def fetch_and_flatten(m: dict, skills_dir: Path) -> dict[str, Path]:
    up = m["upstream"]
    repo, ref, sub = up["repo"], str(up["ref"]), up.get("skills_subdir", "Skills")
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        # A 40-char hex ref is a commit SHA -> init + fetch that exact object.
        is_sha = len(ref) == 40 and all(c in "0123456789abcdef" for c in ref)
        if is_sha:
            run(["git", "init", "-q", str(tmp)])
            run(["git", "-C", str(tmp), "remote", "add", "origin", repo])
            run(["git", "-C", str(tmp), "fetch", "-q", "--depth", "1", "origin", ref])
            run(["git", "-C", str(tmp), "checkout", "-q", "FETCH_HEAD"])
        else:
            run(["git", "clone", "-q", "--depth", "1", "--branch", ref, repo, str(tmp)])

        src = tmp / sub
        if not src.is_dir():
            sys.exit(f"skills subdir '{sub}' not found in upstream repo")

        skills_dir.mkdir(parents=True, exist_ok=True)
        found: dict[str, Path] = {}
        for skill_md in src.rglob("SKILL.md"):
            name = skill_md.parent.name
            if name in found:
                print(f"  ! collision: '{name}' seen twice, keeping first", file=sys.stderr)
                continue
            dest = skills_dir / name
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(skill_md.parent, dest)
            found[name] = dest
        print(f"  flattened {len(found)} skills into {skills_dir}")
        return found


def list_upstream_skill_names(m: dict) -> set[str]:
    """Flatten into a throwaway dir just to learn the available skill names."""
    with tempfile.TemporaryDirectory() as tmp:
        return set(fetch_and_flatten(m, Path(tmp)).keys())


# --------------------------------------------------------------------------- #
# agents: render one markdown file per enabled lane
# --------------------------------------------------------------------------- #
def _clean(text: str) -> str:
    return " ".join((text or "").split())


def render_agent(agent: dict, m: dict) -> str:
    defaults = m.get("defaults", {})
    model = agent.get("model", defaults.get("model", "sonnet"))
    tools = agent.get("tools", defaults.get("tools", []))
    shared = m.get("shared_skills", [])
    lane = list(agent["skills"]) + [s for s in shared if s not in agent["skills"]]
    desc = _clean(agent["description"])
    authz = _clean(m.get("authorization", ""))

    skill_lines = "\n".join(f"- `{s}`" for s in lane)
    fm_tools = ", ".join(tools)

    return f"""---
name: {agent['name']}
description: {desc}
model: {model}
tools: {fm_tools}
---

You are the **{agent['name']}** specialist on Noah's homelab security team.

{desc}

## Authorization (read first, every engagement)
{authz}

## Your skills
Invoke these on demand with the `Skill` tool — load a skill's full guidance only
when you actually start work on that surface, to keep context lean:

{skill_lines}

## How to work
1. Confirm the target is in scope and authorized before acting.
2. Start from the least intrusive technique; escalate only as needed.
3. When you begin on a surface, invoke the matching skill above for methodology.
4. If a task clearly needs a skill outside your lane, you may invoke it, but say
   so and stay within authorized scope.
5. Capture every finding with `offensive-reporting` so results are consistent
   across the team.
"""


def generate_agents(m: dict, agents_dir: Path) -> list[str]:
    agents_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for agent in m["agents"]:
        if not agent.get("enabled", True):
            print(f"  - skipping disabled agent '{agent['name']}'")
            continue
        out = agents_dir / f"{agent['name']}.md"
        out.write_text(render_agent(agent, m))
        written.append(agent["name"])
    print(f"  wrote {len(written)} agents into {agents_dir}: {', '.join(written)}")
    return written


# --------------------------------------------------------------------------- #
# validate: manifest <-> upstream coverage
# --------------------------------------------------------------------------- #
def validate(m: dict) -> int:
    available = list_upstream_skill_names(m)
    shared = set(m.get("shared_skills", []))
    assigned: set[str] = set(shared)
    problems = 0

    for agent in m["agents"]:
        for s in agent["skills"]:
            assigned.add(s)
            if s not in available:
                print(f"  ✗ agent '{agent['name']}' references unknown skill '{s}'")
                problems += 1
    for s in shared:
        if s not in available:
            print(f"  ✗ shared_skills references unknown skill '{s}'")
            problems += 1

    unassigned = available - assigned
    if unassigned:
        print(f"  ⚠ {len(unassigned)} upstream skills not assigned to any lane:")
        for s in sorted(unassigned):
            print(f"      {s}")

    print(f"\n  upstream skills: {len(available)}  |  assigned: {len(assigned & available)}"
          f"  |  unknown refs: {problems}  |  unassigned: {len(unassigned)}")
    return 1 if problems else 0


# --------------------------------------------------------------------------- #
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--all", action="store_true", help="build skills + agents (default)")
    ap.add_argument("--skills", action="store_true", help="vendor + flatten skills only")
    ap.add_argument("--agents", action="store_true", help="generate agent files only")
    ap.add_argument("--validate", action="store_true", help="check manifest vs upstream")
    ap.add_argument("--target", default=str(HERE / ".claude"),
                    help="root holding skills/ and agents/ (default: ./.claude)")
    ap.add_argument("--skills-dir", help="override skills output dir")
    ap.add_argument("--agents-dir", help="override agents output dir")
    args = ap.parse_args()

    m = load_manifest()
    target = Path(args.target).expanduser()
    skills_dir = Path(args.skills_dir).expanduser() if args.skills_dir else target / "skills"
    agents_dir = Path(args.agents_dir).expanduser() if args.agents_dir else target / "agents"

    if args.validate:
        print("Validating manifest against upstream…")
        return validate(m)

    do_skills = args.skills or args.all or not (args.skills or args.agents)
    do_agents = args.agents or args.all or not (args.skills or args.agents)

    if do_skills:
        print("Vendoring + flattening skills…")
        fetch_and_flatten(m, skills_dir)
    if do_agents:
        print("Generating agents…")
        generate_agents(m, agents_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
