import os


def send_email(to_addr: str, subject: str, body: str):
    # まずは“送らない”安全版（ログだけ）
    print(f"[DRY-RUN EMAIL] to={to_addr} subj={subject} body={body[:40]}")


NOTIFY_ENABLED = os.getenv("NOTIFY_ENABLED", "0") == "1"
