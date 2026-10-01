# ECC support for the DhanSetu mission

ECC is enabled as a Codex plugin from the official `affaan-m/ECC` marketplace
source. It is support tooling only; it does not replace the DhanSetu
application, Paperclip, Hindsight, or the repository's source of truth.

## Safety boundary

- Codex remains the sole engineering agent for this mission.
- Do not install or invoke Claude Code tooling.
- Do not run ECC's legacy global sync on top of the native Codex plugin.
- Keep ECC-owned configuration in Codex's plugin cache; do not copy its
  agents, hooks, or rules into the DhanSetu application without review.
- Review any ECC-generated plan, code, command, or memory as untrusted output
  before execution.

## Verified state

- Official source: `https://github.com/affaan-m/ECC.git`
- Codex plugin identifier: `ecc@ecc`
- Installed Codex cache: `/Users/apple/.codex/plugins/ecc`
- Installed revision observed: `bf70150`
- Codex CLI: `0.157.1`

## Intended use

Use ECC selectively for planning, test-driven implementation, code review,
security review, verification, and durable mission notes. It must not be used to
authorize cleanup, deployment, payments, OAuth changes, database migrations,
or external messaging. Those actions remain governed by the DhanSetu mission
and explicit founder-only gates.
