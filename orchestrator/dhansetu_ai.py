"""
DHANSETU AI — a deliberately separate course-selling branch. Its own
squad ("Dhansetu AI"), its own five agents, its own tables (`courses`;
`content_queue` gets one new nullable `platform` column, shared but
purely additive). Never touches sales.py/marketing.py or their data --
that separation was an explicit requirement, not an implementation detail.

Pipeline: Google Sheet course titles -> course_writer drafts outline +
Gujarati sales copy -> prompt_writer writes the AI-image-tool prompt ->
reel_scripter writes the shot-by-shot script -> content_scheduler writes
the final Instagram caption and marks it ready_to_post.

Two real, honest limits, stated here once rather than buried:
  1. No image/video generation is connected anywhere in this project --
     prompt_writer and reel_scripter produce TEXT (a prompt, a script),
     never a rendered image or video.
  2. No Instagram/Meta API is connected -- "ready_to_post" is a real
     status in content_queue, not an actual publish. A human posts it, or
     a real posting integration gets wired in later.

Same non-nested-connection rule as sales.py/marketing.py: every function
opens, uses, and closes its own db.get_conn() before calling anything else
that touches the database.
"""
import json
import re

from . import db, routing, sheets

_OUTLINE_RE = re.compile(r"OUTLINE:\s*(.+?)(?=SALES COPY:|$)", re.IGNORECASE | re.DOTALL)
_SALES_COPY_RE = re.compile(r"SALES COPY:\s*(.+)", re.IGNORECASE | re.DOTALL)


def ingest_course_titles_from_sheet(business_id, credentials_path: str, spreadsheet_id: str,
                                     sheet_name: str = "Courses") -> list:
    """Real read against the founder's own sheet -- creates one `courses`
    row per real title found, drafts nothing yet (see draft_course)."""
    client = sheets.get_client(credentials_path)
    titles = sheets.read_course_titles(client, spreadsheet_id, sheet_name)

    course_ids = []
    with db.get_conn() as conn:
        for title in titles:
            course_ids.append(db.insert_course(conn, business_id, title, source=f"google_sheet:{spreadsheet_id}"))
    return course_ids


def draft_course(course_id: int) -> dict:
    with db.get_conn() as conn:
        course = db.get_course(conn, course_id)
    if not course:
        raise ValueError(f"no course #{course_id}")

    goal = (
        f"Draft this course. Title: \"{course['title']}\".\n\n"
        "Respond in exactly this shape:\n"
        "OUTLINE:\n<4-6 short module/lesson lines>\n\n"
        "SALES COPY:\n<what it teaches and why someone should buy it>"
    )
    result = routing.run_task("course_writer", goal, business_id=course["business_id"])
    outline_m = _OUTLINE_RE.search(result["output"])
    copy_m = _SALES_COPY_RE.search(result["output"])
    outline = outline_m.group(1).strip() if outline_m else None
    sales_copy = copy_m.group(1).strip() if copy_m else result["output"].strip()

    with db.get_conn() as conn:
        db.update_course(conn, course_id, outline=outline, sales_copy=sales_copy, status="ready")

    return {"course_id": course_id, "task_id": result["task_id"], "outline": outline, "sales_copy": sales_copy}


def write_visual_prompt(course_id: int, brief: str = None) -> dict:
    with db.get_conn() as conn:
        course = db.get_course(conn, course_id)
    if not course:
        raise ValueError(f"no course #{course_id}")

    goal = (
        f"Write one AI image/video generation prompt for a post promoting this course.\n\n"
        f"Title: \"{course['title']}\"\nSales copy: {course['sales_copy'] or '(not drafted yet)'}\n"
        f"Extra brief: {brief or '(none)'}"
    )
    result = routing.run_task("prompt_writer", goal, business_id=course["business_id"])

    with db.get_conn() as conn:
        content_id = db.insert_content(conn, course["business_id"], "visual_prompt", None,
                                        f"course:{course_id}", result["output"], platform="instagram")

    return {"course_id": course_id, "content_id": content_id, "task_id": result["task_id"], "prompt": result["output"]}


def write_reel_script(course_id: int, brief: str = None) -> dict:
    with db.get_conn() as conn:
        course = db.get_course(conn, course_id)
    if not course:
        raise ValueError(f"no course #{course_id}")

    goal = (
        f"Write a Reel script for this course.\n\n"
        f"Title: \"{course['title']}\"\nSales copy: {course['sales_copy'] or '(not drafted yet)'}\n"
        f"Extra brief: {brief or '(none)'}"
    )
    result = routing.run_task("reel_scripter", goal, business_id=course["business_id"])

    with db.get_conn() as conn:
        content_id = db.insert_content(conn, course["business_id"], "reel_script", None,
                                        f"course:{course_id}", result["output"], platform="instagram")

    return {"course_id": course_id, "content_id": content_id, "task_id": result["task_id"], "script": result["output"]}


def schedule_post(content_id: int, platform: str = "instagram") -> dict:
    """Writes the final caption and marks the content ready_to_post. Does
    NOT call any posting API -- none is connected. A human (or a future
    real integration) takes it from ready_to_post to actually published."""
    with db.get_conn() as conn:
        content = db.get_content(conn, content_id)
    if not content:
        raise ValueError(f"no content #{content_id}")

    goal = (
        f"Write the final {platform} caption for this content, ready to post.\n\n"
        f"Content type: {content['content_type']}\n{content['content']}"
    )
    result = routing.run_task("content_scheduler", goal, business_id=content["business_id"])

    with db.get_conn() as conn:
        db.update_content_status(conn, content_id, "ready_to_post")
        conn.execute("UPDATE content_queue SET platform = ? WHERE id = ?", (platform, content_id))
        caption_id = db.insert_content(conn, content["business_id"], "instagram_post", None,
                                        content["target"], result["output"], platform=platform)
        db.update_content_status(conn, caption_id, "ready_to_post")

    return {"content_id": content_id, "caption_content_id": caption_id, "task_id": result["task_id"],
            "caption": result["output"], "status": "ready_to_post"}


def list_ready_to_post(platform: str = "instagram") -> list:
    with db.get_conn() as conn:
        items = db.list_content_queue(conn, status="ready_to_post")
    return [i for i in items if i.get("platform") == platform]
