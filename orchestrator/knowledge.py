"""
SHAKTHI KNOWLEDGE — Phase v4. Plain-text search (LIKE query), not
embeddings -- same stance as memory_entries since Phase 0.1: real, honest,
and good enough at this document volume; upgrade path is nomic-embed-text
via Ollama if this ever needs semantic recall a keyword match can't find.
"""
from . import bug_fixer, db


def add_document(category: str, title: str, content: str, tags: str = "") -> int:
    with db.get_conn() as conn:
        return db.insert_knowledge_doc(conn, category, title, content, tags)


def ask(question: str, category: str = None) -> dict:
    with db.get_conn() as conn:
        matches = db.search_knowledge(conn, question, category=category, limit=5)
        if not matches:
            return {"answer": "No stored knowledge documents matched this question.", "sources": []}

        context = "\n\n".join(f"[{m['title']}]\n{m['content']}" for m in matches)
        task_id = bug_fixer.new_pipeline_task(conn, f"Knowledge query: {question[:60]}")
        prompt = f"Documents:\n{context}\n\nQuestion: {question}"
        answer = bug_fixer.call_agent(conn, task_id, "knowledge", prompt)
        db.update_task(conn, task_id, "done", answer)

    return {"answer": answer, "sources": [m["title"] for m in matches]}
