"""Jarvis-style founder-language mediator for SHAKTHI_OS.

This module does not execute tools. It converts conversational input into a
small, inspectable prompt contract; the existing Voice Commander retains
identity, risk, approval, execution and audit responsibility.
"""
from __future__ import annotations

import re

LANGUAGE_NAMES = {"en": "English", "hi": "Hindi", "gu": "Gujarati"}


def detect_language(text: str, stt_language: str | None = None) -> str:
    if re.search(r"[\u0a80-\u0aff]", text):
        return "gu"
    if re.search(r"[\u0900-\u097f]", text):
        return "hi"
    return stt_language if stt_language in LANGUAGE_NAMES else "en"


def normalize_request(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", text).strip(" ,.-")
    return cleaned or "status report"


def build_prompt(transcript: str, intent: dict, stt_language: str | None = None) -> dict:
    language = detect_language(transcript, stt_language)
    objective = normalize_request(intent.get("args") or transcript)
    prompt = (
        "You are Jarvis, the Prompt Master mediator inside SHAKTHI_OS. "
        "Preserve the founder's intent; never invent missing facts or authority.\n"
        f"Founder language: {LANGUAGE_NAMES[language]}\n"
        f"Original request: {transcript.strip()}\n"
        f"Normalized objective: {objective}\n"
        f"Route: {intent.get('category', 'unknown')}/{intent.get('action', 'unknown')}\n"
        "Return the real result in the founder's language. If execution requires "
        "credentials, payment, destructive action, or external publication, stop at the approval gate."
    )
    return {"language": language, "objective": objective, "prompt": prompt}
