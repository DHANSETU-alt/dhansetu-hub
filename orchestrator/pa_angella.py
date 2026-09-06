"""
PA ANGELLA -- sits between the founder and the CEO agent in both the org
tree and the real pipeline. Turns the founder's raw message (often fast,
informal, sometimes broken English) into a clear, professional prompt,
then hands that refined prompt to ceo.decide() -- a real second task, not
a cosmetic relabeling. Two real `tasks` rows per call: one for Angella's
refinement, one for the CEO's actual decision on the refined version.
"""
from . import ceo, routing, voice


def refine_prompt(raw_message: str, business_id: int | None = None) -> dict:
    result = routing.run_task("pa_angella", raw_message, business_id=business_id)
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


def refine_and_send_to_ceo(raw_message: str, business_id: int | None = None) -> dict:
    refined = refine_prompt(raw_message, business_id=business_id)
    decision = ceo.decide(refined["refined_prompt"], business_id=business_id)
    return {
        "raw_message": raw_message,
        "refined_prompt": refined["refined_prompt"],
        "pa_task_id": refined["task_id"],
        "ceo_decision": decision,
    }
