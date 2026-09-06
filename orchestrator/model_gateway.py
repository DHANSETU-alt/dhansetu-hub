"""
Model Gateway — the one place that knows how to reach a model.

Agents never call Ollama or Claude directly; they go through call_local() or
call_cloud() here. That's what keeps the cost/routing policy centralized
(Phase 8 of the architecture doc) instead of copy-pasted into 100 agent
prompts.
"""
import json
import urllib.request
import urllib.error

from . import config


class ModelError(RuntimeError):
    pass


def call_local(model: str, system_prompt: str, user_prompt: str) -> tuple[str, int, int]:
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
