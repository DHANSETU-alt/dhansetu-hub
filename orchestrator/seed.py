"""
Seeds 10 businesses and 100 sites (10 each, round-robin across 3 templates)
to demonstrate the v2 scale target concretely against the schema — not as
100 real deployments, just proof the data model holds without change.
"""
from . import db

TEMPLATES = ["template_landing_v1", "template_ecommerce_v1", "template_blog_v1"]


def run():
    with db.get_conn() as conn:
        existing = conn.execute("SELECT COUNT(*) as c FROM businesses").fetchone()["c"]
        if existing:
            print(f"{existing} businesses already seeded, skipping.")
            return

        for i in range(1, 11):
            biz_id = db.insert_business(conn, f"Business {i:02d}")
            for j in range(1, 11):
                template = TEMPLATES[(i + j) % len(TEMPLATES)]
                db.insert_site(
                    conn,
                    biz_id,
                    domain=f"biz{i:02d}-site{j:02d}.example.com",
                    template_id=template,
                    status="planned",
                )
        print("Seeded 10 businesses and 100 sites.")


if __name__ == "__main__":
    run()
