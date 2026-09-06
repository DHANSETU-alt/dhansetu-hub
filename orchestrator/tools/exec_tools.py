"""
Command execution sandbox — a real but PARTIAL mitigation, not a container
jail. No Docker on this machine, so this is subprocess.run with:
  - a hardcoded argv allowlist (not env-configurable — changing what's
    runnable is a reviewed code change, not a runtime toggle)
  - shell=False always (argv list only — shell metacharacters are inert)
  - a hard timeout
  - a minimal explicit env (not inherited os.environ)
  - cwd pinned to the workspace root
  - stdout/stderr size caps

This stops shell injection and env/secret leakage into the child process.
It does NOT bound what an allowlisted interpreter does once invoked --
`python3 <script>` is unrestricted code execution regardless of argv shape,
because the interpreter itself is Turing-complete. Real containment
requires a container/VM sandbox (Docker, gVisor, Firecracker) -- out of
scope until this leaves a bare laptop.

No agent is granted `run_command` by default in Phase 0.2 (see agents/*.yaml)
and execution additionally requires SHAKTHI_ALLOW_EXEC=1 (see dispatch.py) --
this module ships built, wired, and audited, not switched on.

macOS `sandbox-exec` was evaluated as an extra defense-in-depth layer and
dropped: it produced noisy, confusing stderr (denying python3's own cache-dir
writes) even on successful runs, and its profile grammar is undocumented and
Apple-deprecated -- not something to depend on being right. Real containment
for this tool is a container/VM sandbox, deferred until this leaves a bare
laptop; until then, the allowlist + no-shell + minimal-env + cwd-pin +
timeout controls below are what's actually load-bearing.
"""
import subprocess

from .. import config
from . import paths

ALLOWED_COMMANDS = frozenset({"python3", "pytest", "node"})


class CommandDeniedError(RuntimeError):
    pass


def run_command(business_id: int, argv: list) -> dict:
    if not argv or not isinstance(argv, list):
        raise CommandDeniedError("argv must be a non-empty list")

    binary = argv[0]
    if binary not in ALLOWED_COMMANDS:
        raise CommandDeniedError(
            f"'{binary}' is not on the allowlist: {sorted(ALLOWED_COMMANDS)}"
        )

    workspace = paths.workspace_root(business_id)
    minimal_env = {"PATH": "/usr/bin:/bin:/usr/local/bin", "HOME": str(workspace)}

    try:
        proc = subprocess.run(
            argv,
            shell=False,
            cwd=str(workspace),
            env=minimal_env,
            timeout=config.COMMAND_TIMEOUT_SECONDS,
            capture_output=True,
            text=True,
        )
    except subprocess.TimeoutExpired as e:
        return {
            "ok": False,
            "stdout": (e.stdout or "")[: config.MAX_OUTPUT_BYTES],
            "stderr": f"timed out after {config.COMMAND_TIMEOUT_SECONDS}s",
            "returncode": None,
        }

    return {
        "ok": proc.returncode == 0,
        "stdout": proc.stdout[: config.MAX_OUTPUT_BYTES],
        "stderr": proc.stderr[: config.MAX_OUTPUT_BYTES],
        "returncode": proc.returncode,
    }
