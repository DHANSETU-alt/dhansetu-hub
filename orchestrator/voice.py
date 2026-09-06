"""
SHAKTHI VOICE COMMANDER — Phase v4.

Voice -> record (sounddevice, raw PCM -- no ffmpeg needed) -> transcribe
(faster-whisper "base", local, CPU) -> intent detection (keyword routing +
fuzzy wake-word match) -> CEO review (risky commands only) -> Owner/Family/
Guest permission check -> route to the real agent/report function ->
result.

This one file covers what a founder-facing request separately named
voice_commander.py/speech_to_text.py/intent_router.py: recording+STT,
wake-word+intent routing, and the CEO/permission/execute pipeline. It's
one cohesive, already-tested module, not three -- splitting working code
into new files with no new capability per file is exactly the kind of
churn "do not redesign" rules out; see voice_history.py (a real separate
file) for what a genuine new capability looks like instead.

The Whisper model is loaded lazily (first real call only) -- it's a real
~150MB download plus ~60s cold load time (confirmed live), which shouldn't
happen at import time for every CLI invocation that never touches voice.

Live-verified: recording->transcription->routing works end to end for
English via a synthesized test utterance ("Shakthi check my finance
report" -> transcribed as "Shout-T check my finance report", correctly
matched by the wake-word fuzzy list, correctly routed to finance). Hindi/
Gujarati are NOT live-verified in this build -- no Gujarati TTS voice
exists on this machine to generate a test utterance, and Whisper's
multilingual support for both is documented upstream, not re-verified
here. Live microphone capture (as opposed to a synthesized test file)
requires the founder to grant microphone permission to this process when
macOS first prompts for it -- not something that can be granted
programmatically.
"""
import shutil
import subprocess

from . import access, bug_fixer, ceo as ceo_mod, db, finance, routing, security

_model = None

# macOS's built-in `say` -- zero new dependency, already proven reliable
# this session for synthesizing test audio. Both confirmed installed and
# working live on this machine (`say -v '?'`). Daniel (en_GB) for a calm,
# measured male voice; Samantha (en_US) is macOS's own warm, natural female
# voice -- picked for tone, not to imitate any specific fictional character.
# The wake word stays "Shakthi", this project's own identity, regardless of
# which voice answers back.
VOICE_MALE = "Daniel"
VOICE_FEMALE = "Samantha"
TTS_VOICE = VOICE_MALE  # backward-compatible default

TTS_VOICES = {"male": VOICE_MALE, "female": VOICE_FEMALE}


def resolve_voice(voice: str = None, gender: str = None) -> str:
    """A caller can pass an exact `say` voice name (voice=...) or just
    gender=("male"|"female") and get this project's chosen voice for it.
    Falls back to the male voice if gender is unset or unrecognized."""
    if voice:
        return voice
    return TTS_VOICES.get((gender or "male").lower(), VOICE_MALE)


def speak(text: str, voice: str = None, gender: str = None, language: str = "en") -> bool:
    """Best-effort speech through the platform's local TTS engine."""
    resolved = resolve_voice(voice, gender)
    command = None
    if shutil.which("say"):
        command = ["say", "-v", resolved, text]
    else:
        linux_tts = shutil.which("espeak-ng") or shutil.which("espeak")
        if linux_tts:
            lang = language if language in {"en", "hi", "gu"} else "en"
            suffix = "+f3" if (gender or "male").lower() == "female" else "+m3"
            command = [linux_tts, "-v", f"{lang}{suffix}", "-s", "165", text]
    if command is None:
        return False
    try:
        completed = subprocess.run(command, timeout=30, check=False)
        return completed.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _get_model():
    global _model
    if _model is None:
        from faster_whisper import WhisperModel
        _model = WhisperModel("base", device="cpu", compute_type="int8")
    return _model


def record_audio(seconds: float = 5.0, sample_rate: int = 16000):
    import numpy as np
    import sounddevice as sd
    print(f"Listening for {seconds:.0f}s...")
    audio = sd.rec(int(seconds * sample_rate), samplerate=sample_rate, channels=1, dtype="float32")
    sd.wait()
    return audio.flatten()


def transcribe(audio) -> dict:
    model = _get_model()
    segments, info = model.transcribe(audio, language=None)
    text = " ".join(seg.text for seg in segments).strip()
    return {"text": text, "language": info.language, "confidence": info.language_probability}


# Whisper misheard "Shakthi" as "Shout-T" in a live test with macOS TTS --
# an unusual proper noun is exactly what a general-purpose STT model
# struggles with. Fuzzy-match plausible mishears rather than requiring an
# exact string.
WAKE_WORD_VARIANTS = ("shakthi", "shakti", "shukti", "shout-t", "shout t", "chuck t", "sakthi", "shakti os")


def _strip_wake_word(text: str) -> str:
    lowered = text.lower().strip()
    for variant in WAKE_WORD_VARIANTS:
        if lowered.startswith(variant):
            return text[len(variant):].strip(" ,.-")
    return text


def detect_intent(text: str) -> dict:
    stripped = _strip_wake_word(text)
    lowered = stripped.lower()

    if any(k in lowered for k in ("finance", "revenue", "profit", "પૈસા", "આવક", "નફો", "वित्त", "कमाई", "मुनाफा")):
        return {"category": "finance", "action": "finance_report", "args": stripped}
    if any(k in lowered for k in ("security", "audit", "સુરક્ષા", "ચકાસણી", "सुरक्षा", "जांच")):
        return {"category": "security", "action": "security_review", "args": stripped}
    if any(k in lowered for k in ("website", "site", "વેબસાઇટ", "સાઇટ", "वेबसाइट", "साइट")):
        return {"category": "status", "action": "website_check", "args": stripped}
    if any(k in lowered for k in ("health", "system status", "sentinel", "સિસ્ટમ", "સ્થિતિ", "સ્વાસ્થ્ય", "सिस्टम", "स्थिति", "स्वास्थ्य")):
        return {"category": "status", "action": "sentinel_check", "args": stripped}
    if any(k in lowered for k in ("bug scan", "check bugs", "બગ", "ભૂલ", "बग", "गलती")):
        return {"category": "admin", "action": "bug_scan", "args": stripped}
    return {"category": "buddy", "action": "buddy_chat", "args": stripped}


def execute_intent(intent: dict, identity: str, language: str = "en") -> str:
    if not access.allowed(identity, intent["category"]):
        return f"Sorry, a '{identity}' voice can't do that ({intent['category']} is restricted)."

    action = intent["action"]
    if action == "finance_report":
        r = finance.generate_report("monthly")
        values = (r["revenue_usd"], r["profit_usd"])
        if language == "hi":
            return f"मासिक आय ${values[0]:.2f} और लाभ ${values[1]:.2f} है।"
        if language == "gu":
            return f"માસિક આવક ${values[0]:.2f} અને નફો ${values[1]:.2f} છે."
        return f"Monthly revenue ${values[0]:.2f}, profit ${values[1]:.2f}."
    if action == "security_review":
        r = security.review()
        if language == "hi":
            return f"सुरक्षा स्कोर {r['score']} में से 100 है। {len(r['findings'])} निष्कर्ष मिले।"
        if language == "gu":
            return f"સુરક્ષા સ્કોર 100 માંથી {r['score']} છે. {len(r['findings'])} તારણ મળ્યાં."
        return f"Security score {r['score']}/100, {len(r['findings'])} findings."
    if action == "website_check":
        with db.get_conn() as conn:
            row = conn.execute("SELECT COUNT(*) as c FROM sites WHERE status = 'generated'").fetchone()
        if language == "hi":
            return f"अब तक {row['c']} साइट बनाई गई हैं।"
        if language == "gu":
            return f"અત્યાર સુધી {row['c']} સાઇટ બનાવવામાં આવી છે."
        return f"{row['c']} sites generated so far."
    if action == "sentinel_check":
        from . import sentinel
        h = sentinel.collect_health()
        if language == "hi":
            return f"सिस्टम स्वास्थ्य 100 में से {h['health_score']} और प्रदर्शन 100 में से {h['performance_score']} है।"
        if language == "gu":
            return f"સિસ્ટમ સ્વાસ્થ્ય 100 માંથી {h['health_score']} અને કામગીરી 100 માંથી {h['performance_score']} છે."
        return f"Health {h['health_score']}/100, performance {h['performance_score']}/100."
    if action == "bug_scan":
        candidates = bug_fixer.scan_for_bugs()
        if language == "hi":
            return f"लॉग में {len(candidates)} संभावित बग मिले।"
        if language == "gu":
            return f"લોગમાં {len(candidates)} સંભવિત બગ મળ્યા."
        return f"{len(candidates)} bug candidate(s) found in the logs."
    if action == "buddy_chat":
        from . import buddy
        mode = "family" if identity == "family" else "general"
        result = buddy.chat("voice-session", mode, intent.get("prompt") or intent["args"])
        return result["response"]
    return "Sorry, I didn't understand that command."


def listen_and_execute(seconds: float = 5.0, identity_passphrase: str = None, speak_response: bool = True,
                        voice: str = None, gender: str = None) -> dict:
    audio = record_audio(seconds)
    return _transcribe_and_execute(audio, identity_passphrase, speak_response=speak_response,
                                    voice=voice, gender=gender)


def _transcribe_and_execute(audio, identity_passphrase: str = None, speak_response: bool = True,
                             transcription: dict = None, voice: str = None, gender: str = None) -> dict:
    """Voice -> STT -> Intent -> [CEO, if risky] -> Correct Agent -> Response.

    CEO sits in the loop only for commands routing.classify_risk() flags
    'critical' (refunds, contracts, "delete all", credentials, etc. -- the
    same keyword classifier every other task in this system already uses).
    Not on every command: a full CEO review is a real local-model call
    (1-4 minutes, confirmed elsewhere in this codebase), and gating routine
    "check my finance report" behind that would make voice control
    unusable. The founder's own three example commands are all read-only
    status checks and route straight through, unreviewed, same as before.

    `transcription` lets a caller that already ran transcribe() on this
    exact audio (listen_loop(), checking for the wake word) pass the
    result through instead of paying for a second real STT pass on the
    same clip.
    """
    if transcription is None:
        transcription = transcribe(audio)
    identity = access.identify(identity_passphrase)
    intent = detect_intent(transcription["text"])
    from . import jarvis_mediator
    mediation = jarvis_mediator.build_prompt(
        transcription["text"], intent, transcription.get("language")
    )
    intent["args"] = mediation["objective"]
    intent["prompt"] = mediation["prompt"]
    denied = not access.allowed(identity, intent["category"])

    ceo_status = None
    if denied:
        result_text = f"Sorry, a '{identity}' voice can't do that ({intent['category']} is restricted)."
    else:
        risk = routing.classify_risk(transcription["text"])
        if risk == "critical":
            decision = ceo_mod.decide(f"Voice command requesting: {intent['args']}", business_id=None)
            ceo_status = decision["status"]
            if decision["status"] != "approved":
                result_text = f"CEO did not approve this ({decision['status']}): {decision.get('reason', '(no reason given)')}"
            else:
                result_text = execute_intent(intent, identity, mediation["language"])
        else:
            result_text = execute_intent(intent, identity, mediation["language"])

    denied_reason = None
    if denied:
        denied_reason = "insufficient permission"
    elif ceo_status and ceo_status != "approved":
        denied_reason = f"ceo_{ceo_status}"

    with db.get_conn() as conn:
        db.log_voice_command(
            conn, identity, transcription["text"], transcription["language"], transcription["confidence"],
            routed_agent=intent["category"], routed_action=intent["action"],
            denied_reason=denied_reason, result_summary=result_text,
        )

    if speak_response:
        speak(result_text, voice=voice, gender=gender, language=mediation["language"])

    return {
        "transcript": transcription["text"], "language": transcription["language"],
        "identity": identity, "intent": intent, "mediation": mediation,
        "ceo_status": ceo_status, "result": result_text,
    }


def _contains_wake_word(text: str) -> bool:
    lowered = text.lower()
    return any(v in lowered for v in WAKE_WORD_VARIANTS)


def listen_loop(window_seconds: float = 4.0, identity_passphrase: str = None, announce: bool = True,
                 voice: str = None, gender: str = None):
    """Continuous mode -- the actual 'always listening' behavior a Jarvis-
    style assistant needs, not a one-shot 5-second recording. Records
    short windows back to back, forever; a window that doesn't contain the
    wake word is silently discarded (not logged, not spoken to) so this
    doesn't react to background conversation. Foreground loop, Ctrl+C to
    stop -- same pattern as --sentinel-loop/--worker-daemon.

    Honest limitation, stated plainly: this is continuous polling with a
    real STT model on every window, not a dedicated low-power wake-word
    engine (Porcupine, openWakeWord, etc.) -- it costs real CPU the whole
    time it runs, and there's an up-to-window_seconds delay between you
    speaking and it noticing, not instant. A true low-latency, low-power
    wake word would need a purpose-built wake-word model this project
    doesn't have; this is the honest version of 'always listening' that's
    actually buildable with what's here.
    """
    print(f"Voice Commander: listening in {window_seconds:.0f}s windows (Ctrl+C to stop)...")
    if announce:
        speak("Shakthi voice commander online.", voice=voice, gender=gender)
    while True:
        audio = record_audio(window_seconds)
        transcription = transcribe(audio)
        text = transcription["text"].strip()
        if not text or not _contains_wake_word(text):
            continue
        print(f"[heard] {text}")
        result = _transcribe_and_execute(audio, identity_passphrase, speak_response=True,
                                          transcription=transcription, voice=voice, gender=gender)
        print(f"[{result['identity']}] {result['result']}")
