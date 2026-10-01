"""
Model Gateway — the one place that knows how to reach a model.

Agents never call Ollama or Claude directly; they go through call_local() or
call_cloud() here. That's what keeps the cost/routing policy centralized
(Phase 8 of the architecture doc) instead of copy-pasted into 100 agent
prompts.
"""
import json
import subprocess
import tempfile
import urllib.request
import urllib.error
from pathlib import Path

from . import config


class ModelError(RuntimeError):
    pass


def call_local(model: str, system_prompt: str, user_prompt: str) -> tuple[str, int, int]:
    """Dispatches to whichever provider this machine is configured for
    (config.LOCAL_PROVIDER) -- "ollama" (default, genuinely free/local) or
    "codex" (OpenAI Codex CLI, real paid API usage). `model` is ignored for
    codex (Codex CLI picks its own model per ~/.codex/config.toml), kept in
    the signature so every existing call_local(agent["local_model"], ...)
    call site doesn't need to change."""
    if config.LOCAL_PROVIDER == "codex":
        return call_codex(system_prompt, user_prompt)
    return _call_ollama(model, system_prompt, user_prompt)


def call_codex(system_prompt: str, user_prompt: str) -> tuple[str, int, int]:
    """OpenAI Codex CLI, non-interactive (`codex exec`). Real paid OpenAI
    usage under whatever account `codex login` authenticated on this
    machine -- NOT free just because it's reached through call_local().
    Requires `codex` on PATH and a prior `codex login` (this session
    verified both live on the Linux box, 2026-09-16: codex-cli 0.154.0,
    model gpt-5.6-luna, real token usage confirmed via --json).

    --skip-git-repo-check: agent workspaces here aren't necessarily git
    repos. -o <file>: the clean final response text, so callers don't have
    to scrape the human-readable transcript. --json on stdout: real
    token counts from the turn.completed event, same honesty standard as
    Ollama's prompt_eval_count/eval_count -- never fabricated."""
    combined_prompt = f"{system_prompt}\n\n---\n\n{user_prompt}"
    with tempfile.NamedTemporaryFile(mode="r", suffix=".txt", delete=False) as tf:
        output_path = Path(tf.name)
    try:
        proc = subprocess.run(
            ["codex", "exec", "--skip-git-repo-check", "--json", "-o", str(output_path), combined_prompt],
            capture_output=True, text=True, timeout=config.CODEX_TIMEOUT_SECONDS,
        )
        if proc.returncode != 0:
            raise ModelError(f"codex exec failed (exit {proc.returncode}): {proc.stderr.strip()[:500]}")

        content = output_path.read_text().strip() if output_path.exists() else ""

        tokens_in = tokens_out = 0
        for line in proc.stdout.splitlines():
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if event.get("type") == "turn.completed":
                usage = event.get("usage", {})
                tokens_in = usage.get("input_tokens", 0)
                tokens_out = usage.get("output_tokens", 0)

        if not content:
            raise ModelError("codex exec returned no output")
        return content, tokens_in, tokens_out
    except subprocess.TimeoutExpired as e:
        raise ModelError(f"codex exec timed out after {config.CODEX_TIMEOUT_SECONDS}s") from e
    except FileNotFoundError as e:
        raise ModelError("`codex` not found on PATH. Run: npm install -g @openai/codex") from e
    finally:
        output_path.unlink(missing_ok=True)


def _call_ollama(model: str, system_prompt: str, user_prompt: str) -> tuple[str, int, int]:
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "stream": False,
    }
    req = urllib.request.Request(
        f"{config.OLLAMA_HOST}/api/chat",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=config.OLLAMA_TIMEOUT_SECONDS) as resp:
            data = json.loads(resp.read())
    except (urllib.error.URLError, TimeoutError) as e:
        # Found live: a socket read timeout during response streaming
        # (large/slow models like gemma4 have taken 2:24-3:26 in this
        # session) raises a bare TimeoutError that urllib does NOT always
        # wrap as URLError -- catching only URLError let this crash with a
        # raw traceback instead of a clean ModelError. Both are network/
        # timeout failures from the caller's point of view.
        raise ModelError(
            f"Could not reach Ollama at {config.OLLAMA_HOST} ({e}). "
            f"Is `ollama serve` running and is `{model}` pulled?"
        ) from e

    content = data.get("message", {}).get("content", "")
    tokens_in = data.get("prompt_eval_count", 0)
    tokens_out = data.get("eval_count", 0)
    return content, tokens_in, tokens_out


def call_cloud(system_prompt: str, user_prompt: str) -> tuple[str, int, int]:
    if not config.ANTHROPIC_API_KEY:
        raise ModelError(
            "Cloud escalation requested but ANTHROPIC_API_KEY is not set. "
            "This is intentional — the system will not silently spend money."
        )
    try:
        import anthropic
    except ImportError as e:
        raise ModelError(
            "Cloud escalation requested but the `anthropic` package isn't "
            "installed. Run: pip install anthropic"
        ) from e

    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    msg = client.messages.create(
        model=config.CLOUD_MODEL,
        max_tokens=1024,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )
    text = "".join(block.text for block in msg.content if block.type == "text")
    return text, msg.usage.input_tokens, msg.usage.output_tokens


# Rough Claude Sonnet 5 blended pricing for the cost ledger. Update if your
# plan/model differs — this number only affects what gets *logged*, not what
# actually gets billed.
CLAUDE_COST_PER_1K_IN = 0.003
CLAUDE_COST_PER_1K_OUT = 0.015


def estimate_cloud_cost(tokens_in: int, tokens_out: int) -> float:
    return (tokens_in / 1000 * CLAUDE_COST_PER_1K_IN) + (tokens_out / 1000 * CLAUDE_COST_PER_1K_OUT)
