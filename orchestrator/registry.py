import json

import yaml

from . import config, db


def load_agent_files() -> list[dict]:
    agents = []
    for path in sorted(config.AGENTS_DIR.glob("*.yaml")):
        data = yaml.safe_load(path.read_text())
        # yaml gives a Python list; sqlite needs text.
        data["allowed_tools"] = json.dumps(data.get("allowed_tools") or [])
        agents.append(data)
    return agents


def sync_registry():
    """Load every agents/*.yaml into the agents table. Adding agent #8, #24,
    or #100 later is: write a new yaml file, run this again. No code changes."""
    agents = load_agent_files()
    with db.get_conn() as conn:
        for agent in agents:
            db.upsert_agent(conn, agent)
    return agents
