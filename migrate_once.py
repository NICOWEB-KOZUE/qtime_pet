from models import db

db.connect(reuse_if_open=True)
cols = [r[1] for r in db.execute_sql("PRAGMA table_info(ticket)").fetchall()]


def add(table, spec):
    col = spec.split()[0]
    if col not in cols:
        db.execute_sql(f"ALTER TABLE {table} ADD COLUMN {spec}")
        print("added:", f"{table}.{col}")


add("ticket", "session TEXT DEFAULT 'AM'")
add("ticket", "seq_no INTEGER")
add("ticket", "visit_date DATE")
add("ticket", "notified BOOLEAN DEFAULT 0")
db.execute_sql("UPDATE ticket SET visit_date = date(created_at) WHERE visit_date IS NULL")
db.execute_sql(
    "UPDATE ticket SET session = CASE WHEN strftime('%H', created_at) >= '12' THEN 'PM' ELSE 'AM' END WHERE session IS NULL OR session = ''"
)
print("done.")
