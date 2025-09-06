import os
import time
from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, jsonify, session, flash
from models import db, Ticket, Patient
from utils import find_or_create_today_ticket_for_patient, today_jst
from utils import _next_seq_no_for_day
from email.utils import parseaddr
from emails import compose_two_ahead_email

from notifier import send_email
from notify import NOTIFY_ENABLED

# .env を読み込む
load_dotenv()

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-unsafe-key")

# 環境変数で ON/OFF（"1" で有効）
NOTIFY_ENABLED = os.getenv("NOTIFY_ENABLED") == "1"


# 起動時にDBを用意
if db.is_closed():
    db.connect()
db.create_tables([Patient, Ticket], safe=True)

# ---- ユーティリティ ----
def issue_card_number() -> str:
    # 簡易：タイムスタンプ由来の6桁
    return f"C{int(time.time()) % 1000000:06d}"


def last4_from_birth(birth: str) -> str:
    # birth = "YYYY-MM-DD"
    try:
        _, m, d = birth.split("-")
        return (m + d)[-4:]
    except Exception:
        return ""


def looks_like_email(value: str) -> bool:
    """最低限の形式チェック"""
    _, addr = parseaddr(value or "")
    if "@" not in addr:
        return False
    local, _, domain = addr.rpartition("@")
    return bool(local) and "." in domain


# ---- 画面ルート ----
@app.route("/")
def index():
    return render_template("index.html")


# 初回登録フォーム
@app.route("/register", methods=["GET"])
def register_get():
    return render_template("register.html")


@app.route("/register", methods=["POST"])
def register_post():
    name = request.form.get("name", "").strip()
    kana = request.form.get("kana", "").strip() or None
    pet_name = request.form.get("pet_name", "").strip()
    phone = request.form.get("phone", "").strip()
    birth = request.form.get("birth", "").strip()  # YYYY-MM-DD
    email = request.form.get("email", "").strip() or None

    # email は任意項目：空ならバリデーション不要
    if email and not looks_like_email(email):
        return render_template("register.html", error="メールアドレスの形式が正しくありません", form=request.form)

    if not (name and pet_name and phone and birth):
        return render_template("register.html", error="必須項目を入力してください", form=request.form)

    card = issue_card_number()
    pwd = last4_from_birth(birth)
    if not pwd:
        return render_template(
            "register.html", error="生年月日を YYYY-MM-DD で入力してください", form=request.form
        )

    p = Patient.create(
        name=name,
        kana=kana,
        pet_name=pet_name,
        phone=phone,
        birth=birth,
        email=email,
        card_number=card,
        password=pwd,
    )

    # 受付（番号発行）＝ Ticket作成
    t, created = find_or_create_today_ticket_for_patient(p)
    return redirect(url_for("done", ticket_id=t.id))


# 再診ログイン
@app.route("/login", methods=["GET"])
def login_get():
    return render_template("login.html")


@app.route("/login", methods=["POST"])
def login_post():
    card = request.form.get("card", "").strip()
    pwd = request.form.get("pwd", "").strip()
    p = Patient.get_or_none(Patient.card_number == card, Patient.password == pwd)
    if not p:
        return render_template("login.html", error="診察券番号またはパスワードが違います", form=request.form)

    # 受付（番号発行）
    t, created = find_or_create_today_ticket_for_patient(p)
    return redirect(url_for("done", ticket_id=t.id))


# 受付完了
@app.route("/done/<int:ticket_id>")
def done(ticket_id):
    ticket = Ticket.get_by_id(ticket_id)
    return render_template("done.html", ticket=ticket)


# 診察状況（未処理チケット）
@app.route("/status")
def status():
    tickets = Ticket.select().where(Ticket.done == False)
    return render_template("status.html", tickets=tickets)


# 診察状況
@app.route("/status.json")
def status_json():
    # 今日の未処理（待ち行列）
    queue = (
        Ticket.select()
        .where((Ticket.visit_date == today_jst()) & (Ticket.done == False))
        .order_by(Ticket.seq_no)
    )
    # 今日の直近処理済み＝「ただいまの診察番号」なければ　None)
    now_serving = (
        Ticket.select()
        .where((Ticket.visit_date == today_jst()) & (Ticket.done == True))
        .order_by(Ticket.seq_no.desc())
        .first()
    )

    return jsonify(
        {
            "now_serving": (
                {"id": now_serving.id, "seq_no": now_serving.seq_no}
                if now_serving else None
            ),
            "queue": [{"id": t.id, "seq_no": t.seq_no} for t in queue]
        }
    )

# --- 管理ログイン ---
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        if request.form.get("pin") == os.getenv("ADMIN_PIN"):
            session["admin"] = True
            return redirect(url_for("admin_dashboard"))
        flash("PINが違います")
    return render_template("admin_login.html")


@app.route("/admin/logout", methods=["POST"])
def admin_logout():
    session.pop("admin", None)
    flash("ログアウトしました")
    return redirect(url_for("admin_login"))


# 管理保護（/admin配下を守る）
@app.before_request
def _protect_admin():
    p = request.path
    if p.startswith("/admin") and p != "/admin/login":
        if not session.get("admin"):
            return redirect(url_for("admin_login"))


@app.route("/admin")
def admin_dashboard():
    # 未処理と直近処理済み少数を表示
    pending = (
        Ticket.select()
        .where((Ticket.visit_date == today_jst()) & (Ticket.done == False))
        .order_by(Ticket.seq_no)
    )
    done_recent = (
        Ticket.select()
        .where((Ticket.visit_date == today_jst()) & (Ticket.done == True))
        .order_by(Ticket.seq_no.desc())
        .limit(5)
    )
    return render_template("admin.html", pending=pending, done_recent=done_recent)

# 次を呼ぶ
@app.route("/admin/next", methods=["POST"])
def admin_next():
    t = (
        Ticket.select()
        .where((Ticket.visit_date == today_jst()) & (Ticket.done == False))
        .order_by(Ticket.seq_no)
        .first()
    )
    if t:
        t.done = True
        t.save()

        notify_if_two_ahead()
    return redirect(url_for("admin_dashboard"))

# 戻す（最後に呼んだ番号）
@app.route("/admin/undo", methods=["POST"])
def admin_undo():
    last = (
        Ticket.select()
        .where((Ticket.visit_date == today_jst()) & (Ticket.done == True))
        .order_by(Ticket.seq_no.desc())
        .first()
    )
    if last:
        last.done = False
        last.save()
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/manual_add", methods=["POST"])
def admin_manual_add():
    name = request.form.get("name", "").strip()
    if name:
        vdate = today_jst()
        seq = _next_seq_no_for_day(vdate)
        Ticket.create(
            name=name,
            visit_date=vdate,
            seq_no=seq
        )
    return redirect(url_for("admin_dashboard"))

@app.route("/display")
def display():
    now_serving = (
        Ticket.select()
        .where((Ticket.visit_date == today_jst()) & (Ticket.done == True))
        .order_by(Ticket.seq_no.desc())
        .first()
    )
    queue = (
        Ticket.select()
        .where((Ticket.visit_date == today_jst()) & (Ticket.done == False))
        .order_by(Ticket.seq_no)
        .limit(6)
    )
    return render_template("display.html", now_serving=now_serving, queue=queue)

# 「あと2人で通知」
def notify_if_two_ahead():
    if not NOTIFY_ENABLED:
        return

    queue = (
        Ticket.select()
        .where((Ticket.visit_date == today_jst()) & (Ticket.done == False))
        .order_by(Ticket.seq_no)
    )

    # 0=診察直前, 1=あと1人, 2=あと2人
    target = queue.offset(2).first()  # 先頭の“次の次”＝あと2人
    if not target:
        print("[NOTIFY SKIP] あと2人目の患者がいません")
        return
    if target.notified:
        print(f"[NOTIFY SKIP] 既に通知済み ticket_id={target.id}")
        return

    # 患者が紐づかない（手入力） or メールなし はスキップ
    patient = getattr(target, "patient", None)
    email = getattr(patient, "email", None) if patient else None
    if not email:
        print(f"[EMAIL SKIP] no email for ticket_id={target.id}")
        return

    subject, body = compose_two_ahead_email(target)
    try:
        send_email(email, subject, body)
        print(f"[EMAIL SENT] to={email} ticket_id={target.id}")
        target.notified = True
        target.save()
    except Exception as e:
        # 送れなかったらフラグは立てない（次回リトライできるように）
        print(f"[EMAIL ERROR] to={email} err={e}")


if __name__ == "__main__":
    app.run(port=8000, debug=True)
