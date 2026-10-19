"""
PA ANGELLA -- sits between the founder and the CEO agent in both the org
tree and the real pipeline. Turns the founder's raw message (often fast,
informal, sometimes broken English) into a clear, professional prompt,
then hands that refined prompt to ceo.decide() -- a real second task, not
a cosmetic relabeling. Two real `tasks` rows per call: one for Angella's
refinement, one for the CEO's actual decision on the refined version.
"""
from . import ceo, routing, voice


def refine_prompt(raw_message: str, business_id: int | None = None, agent_id: str = "pa_angella") -> dict:
    """agent_id defaults to 'pa_angella' -- every existing caller keeps
    working unchanged. Same real gap as ceo.decide() (2026-09-09,
    5-Why/KPIV): hardcoded literal made pa_angella_2 (Team 2's mirror)
    unreachable. The real org design is ONE Angella feeding both CEOs
    (see /org-chart), so this parameter exists for completeness/
    consistency with every other agent, not because two independent
    Angellas are the intended architecture."""
    result = routing.run_task(agent_id, raw_message, business_id=business_id)
    return {"task_id": result["task_id"], "raw_message": raw_message, "refined_prompt": result["output"]}


def refine_and_speak(raw_message: str, business_id: int | None = None, gender: str = "female") -> dict:
    """Real voice output: refines the message exactly like refine_prompt(),
    then speaks the refined prompt back through the same TTS pipeline
    Voice Commander already uses (voice.py -> macOS `say`). Default voice
    is female, matching PA Angella's own persona -- override with gender=
    if you want her spoken back in the male voice instead.

    Live microphone input is NOT part of this call -- speaking TO her by
    voice still needs the founder's own mic-permission grant and reuses
    voice.record_audio()/transcribe(), same honest limitation as the rest
    of Voice Commander."""
    refined = refine_prompt(raw_message, business_id=business_id)
    voice.speak(f"Got it. {refined['refined_prompt']}", gender=gender)
    return refined


def refine_and_send_to_ceo(raw_message: str, business_id: int | None = None, ceo_agent_id: str = "ceo") -> dict:
    """ceo_agent_id defaults to 'ceo' (Team 1) -- pass 'ceo_2' to route
    this decision to Team 2 instead. This is the real, load-bearing
    parameter for the two-team org design (one Angella, two CEOs) --
    unlike pa_angella's own agent_id, choosing WHICH CEO a refined prompt
    goes to is the actual decision that matters here."""
    refined = refine_prompt(raw_message, business_id=business_id)
    decision = ceo.decide(refined["refined_prompt"], business_id=business_id, agent_id=ceo_agent_id)
    return {
        "raw_message": raw_message,
        "refined_prompt": refined["refined_prompt"],
        "pa_task_id": refined["task_id"],
        "ceo_decision": decision,
    }


def push_pending_work(snapshot: dict, business_id: int | None = None) -> str:
    """The other direction from refine_prompt(): CEO/system data -> Angella
    -> founder, instead of founder -> Angella -> CEO. agents/pa_angella.yaml
    already defines a full "Operating mode" for exactly this (unfinished
    work, ranked by urgency, each item turned into a concrete next action,
    a FOUNDER ACTION REQUIRED section, push firmly) -- it just never had a
    real caller before 2026-09-06. This is that caller: hands her the real
    compiled dashboard snapshot (founder_review.compile_review_data()).

    Two real local-model calls, not one, found necessary live: asking a
    single call to reason over 20+ initiatives AND switch language AND
    hold a strict output format at once pushed qwen2.5 past its response
    time on this Mac (confirmed live: the same prompt made the Ollama
    runner spin for 24+ minutes before being killed). Splitting the heavy
    reasoning (English, llama3.2 -- proven fast and reliable for this
    prompt size) from the translation (a much smaller text, any capable
    local model handles it quickly) keeps both steps fast AND meets the
    founder's real, established Gujarati preference.

    Never invents progress -- the prompt explicitly forbids it, matching
    her yaml's own "never claim progress that is not in the snapshot" rule.
    """
    initiative_lines = "\n".join(
        f"  Task {i['seq']} — {i['title']}: {i['percent_complete']}% "
        f"({i['milestone_done']}/{i['milestone_total']} milestones), status={i['status']}"
        for i in snapshot["initiatives"]
    )
    prompt = (
        "Dashboard snapshot (real, current, the only evidence you have -- do not invent "
        "anything beyond it):\n\n"
        f"Governor status: {snapshot['governor_status']}\n"
        f"Security posture score: {snapshot['security_score']}\n"
        f"Watchdog: {snapshot['watchdog_critical']} critical, {snapshot['watchdog_warning']} warning event(s)\n"
        f"CEO decisions awaiting founder input: {snapshot['pending_decisions']}\n\n"
        f"Tracked initiatives:\n{initiative_lines}\n\n"
        "Per your own operating mode: identify unfinished work, rank by urgency and "
        "dependency. For EACH pending item, write its solution as a short flow chain of "
        "concrete steps joined by ' -> ' arrows, ending in DONE, e.g.:\n"
        "  Task 15 (67%): verify test-mode checkout -> fix any failure found -> re-test -> DONE\n"
        "Keep a short FOUNDER ACTION REQUIRED section for anything only the founder can "
        "do (credentials, publishing, device permissions, provider setup) -- same "
        "' -> ' flow style. Push firmly. Write in English for now -- it gets translated "
        "separately. No JSON, no markdown headers, just the flow chains."
    )
    result = routing.run_task("pa_angella", prompt, business_id=business_id)
    text = result["output"].strip()
    # routing.py appends a "[Note: ... cloud escalation ...]" line on local
    # fallback -- real and useful for debugging (see log_event
    # "escalation_unavailable"), but it breaks the flow reading as a
    # message actually from Angella. Strip it from what the founder sees;
    # the underlying task_id in `result` still carries the real fallback
    # status for anyone checking task history.
    if "\n\n[Note: this is the local model's own output" in text:
        text = text.split("\n\n[Note: this is the local model's own output")[0].strip()
    return translate_to_gujarati(text)


def translate_to_gujarati(english_text: str) -> str:
    """Deliberately separate from the reasoning call above -- a short,
    already-written text is a much smaller job than reasoning over the
    whole dashboard, so this stays fast even on a bigger/better model.
    Falls back to the English text (logged, not silently swapped for
    something invented) if the local model is unreachable or empty."""
    from . import model_gateway

    try:
        translated, _, _ = model_gateway.call_local(
            "qwen2.5",
            "You translate English text to simple, everyday spoken Gujarati. "
            "Keep all numbers, task names, and the ' -> ' arrow chains exactly "
            "as given -- translate only the surrounding words. Output only the "
            "Gujarati translation, nothing else.",
            english_text,
        )
        return translated.strip() or english_text
    except model_gateway.ModelError:
        return english_text
