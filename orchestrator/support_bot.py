"""Customer-facing Support Bot -- distinct from the founder-internal chat
widget (dashboard/app/api/blackboxops/chat/route.ts, which pulls the
founder's own live task/initiative snapshot and answers as his delivery
partner). This module must NEVER see or expose that internal business
data -- a site visitor asking a question has no business seeing the
founder's task list. Built on two things that already existed and were
real, not invented for this: knowledge.ask() (plain-text search over
knowledge_documents, honestly returns "no match" rather than fabricating
an answer) and sales.ingest_lead() (real lead scoring + auto-routing).

Flow: try the knowledge base first. If it has a real answer, give it
straight -- no lead capture needed, the visitor got what they came for.
If nothing matched AND the visitor left an email, capture it as a real
lead through the existing sales pipeline (same scoring/escalation logic
every other lead goes through) rather than just... losing the question.
"""
from . import knowledge, sales

# Real bug found live-testing this against the actual seeded knowledge
# base: db.search_knowledge() does a loose LIKE match, so a question with
# no real answer can still pull back a few loosely-related documents --
# `sources` being non-empty does NOT mean the synthesized answer is
# actually useful. Confirmed live: asking about a Tally integration
# pulled 3 unrelated internal docs, and the model correctly, honestly
# answered "cannot be found in the provided documents" -- but a naive
# `matched = bool(sources)` check would have shown that non-answer to a
# customer as if it were a real one. This can't be told apart from
# `sources` alone; checking the answer text for the model's own honest
# refusal phrasing is a pragmatic (if imperfect) second signal until
# knowledge.ask() itself returns a clean matched/unmatched boolean.
_NO_ANSWER_SIGNALS = (
    "cannot be found", "can't be found", "not mentioned", "no information",
    "doesn't mention", "does not mention", "not found in", "no stored knowledge",
)


def _looks_like_a_real_answer(answer: str, sources: list) -> bool:
    if not sources:
        return False
    lowered = answer.lower()
    return not any(signal in lowered for signal in _NO_ANSWER_SIGNALS)


def handle_message(message: str, business_id: int = None, email: str = None,
                    name: str = None, telegram_token: str = None, telegram_chat_id: str = None) -> dict:
    if not message or not message.strip():
        return {"answer": "Ask me anything about the product, pricing, or how it works.",
                "matched": False, "lead_captured": False, "sources": []}

    result = knowledge.ask(message, category=None)
    matched = _looks_like_a_real_answer(result["answer"], result["sources"])

    if matched:
        return {"answer": result["answer"], "sources": result["sources"], "matched": True, "lead_captured": False}

    # No knowledge-base match. Honest response either way -- never invent
    # an answer knowledge.ask() itself didn't have. If we have contact
    # info, route it as a real lead so a human follows up; if not, say so
    # plainly and ask for an email rather than silently dropping it.
    if email:
        lead = sales.ingest_lead(
            business_id, name or "Website visitor", email, source="support_bot_unanswered",
            notes=f"Asked (no knowledge-base match): {message}",
            telegram_token=telegram_token, telegram_chat_id=telegram_chat_id,
        )
        return {
            "answer": "I don't have a stored answer for that yet -- I've passed your question and email to the team, they'll follow up.",
            "sources": [], "matched": False, "lead_captured": True, "lead_id": lead["lead_id"],
        }

    return {
        "answer": "I don't have a stored answer for that yet. Leave your email and I'll make sure the team follows up.",
        "sources": [], "matched": False, "lead_captured": False,
    }
