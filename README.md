# red-team

A reproducible Claude Code agent team for assessing and hardening Noah's
homelab, dev environment, and public services. The whole team is generated from
one manifest, so it's versioned, reviewable, and rebuildable from scratch.

## How it works

```
red-team/
├── manifest.yaml        # SINGLE SOURCE OF TRUTH: lanes → skills, upstream pin
├── build_skills.py      # generates the team from the manifest
├── setup.sh             # cloud-session setup: build + install into ~/.claude
├── .gitignore           # skills are vendored at build time, not committed
└── .claude/
    ├── agents/          # GENERATED + committed — the team's real config
    │   ├── recon.md
    │   ├── web-app.md
    │   ├── cloud-infra.md
    │   ├── network-wireless.md
    │   ├── appsec-research.md
    │   └── specialist.md
    └── skills/          # GENERATED at build, gitignored (flattened upstream)
```

- **Skills** come from the upstream [`SnailSploit/claude-red`](https://github.com/SnailSploit/claude-red)
  library (79 offensive-security skills), pinned to a commit in `manifest.yaml`.
  `build_skills.py` flattens them to the one-level layout Claude Code requires
  (`skills/<name>/SKILL.md`) — the upstream repo's own nested layout doesn't load.
- **Agents** are generated from the manifest. Each lane becomes one
  `.claude/agents/<name>.md` whose prompt names its skills and carries the shared
  authorization guardrail.

## Scoping model: soft

Every agent keeps the `Skill` tool and loads skill **bodies on demand** — only
short descriptions sit in context until a skill is actually used, and each agent
runs in its own context window, so heavy content never lands in the main thread.
A lane is guidance (named in the prompt), not an enforced wall; an agent *can*
reach another skill if a task genuinely needs it. (If you ever want a hard wall
for one agent, we'd preload its subset and drop its `Skill` tool — at a context
cost. Not used here.)

## The team

| Agent | Lane | Skills |
|---|---|---|
| `recon` | OSINT / attack-surface mapping | 2 |
| `web-app` | Web + API + auth (primary) | 20 |
| `cloud-infra` | Cloud / container / K8s / CI-CD / supply-chain | 7 |
| `network-wireless` | Network + Wi-Fi/BLE/Zigbee/Z-Wave/LoRaWAN | 15 |
| `appsec-research` | Exploit-dev / fuzzing / crypto-TLS | 12 |
| `specialist` | Mobile / IoT / phishing / AI security | 5 |
| `internal-ad` | AD / privesc / lateral / persistence *(parked)* | 16 |

Every agent also gets the shared `offensive-reporting` and
`offensive-fast-checking` skills. `internal-ad` is defined but `enabled: false`
pending the Windows/AD scoping discussion — flip the flag to turn it on.

Totals: 79 upstream skills, all assigned to a lane (validated); 6 agents active, 1 parked.

## Usage

```bash
# everything (flatten skills + generate agents) into ./.claude
python3 build_skills.py --all

# just regenerate agents after editing the manifest
python3 build_skills.py --agents

# just re-vendor skills (e.g. after bumping the upstream pin)
python3 build_skills.py --skills

# sanity-check the manifest against upstream (no writes)
python3 build_skills.py --validate
```

For a Claude Code cloud environment, point the project's setup script at
`setup.sh` — it builds the team and installs it into `~/.claude` so it loads in
every session.

## Adding / changing agents

Edit `manifest.yaml` only, then rerun `build_skills.py --agents`. To move a skill
between lanes, change which agent lists it. To add a brand-new skill, add it to
upstream (or a second source) and assign it to a lane; `--validate` will flag any
skill that isn't assigned.

## Authorization

These are offensive-security skills. Every generated agent prompt states that it
operates only on assets Noah owns or is authorized to test, defaults to the least
intrusive technique, and avoids destructive/DoS/persistence actions without an
explicit scoped go-ahead. Keep that guardrail intact.

## Roadmap

- Resolve Windows/AD scope → enable `internal-ad`.
- A monitoring/alerting layer (log shipping + dashboard + threat notifications)
  as a separate build once the assessment agents are in use.
