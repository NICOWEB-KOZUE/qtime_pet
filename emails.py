import os
from flask import url_for


def _n(t):  # 表示番号（seq_no優先、なければid）
    return getattr(t, "seq_no", None) or t.id


def _patient_name(ticket):
    p = getattr(ticket, "patient", None)
    return getattr(p, "name", None) or "お客様"


def _tel():
    return os.getenv("CLINIC_TEL", "0191-00-0000")


def compose_two_ahead_email(ticket):
    """
    「あと2人です」通知の件名・本文を返す
    """
    subject = f"【平泉どうぶつ病院】まもなく診察です（あと2名／受付No.{_n(ticket)}）"
    body = (
        f"{_patient_name(ticket)} 様\n\n"
        "平泉どうぶつ病院です。\n"
        "本日の診察が **あと2名** でご案内となります。\n\n"
        f"- 受付番号：{_n(ticket)}（{ticket.session}）\n"
        f"- 日付：{ticket.visit_date}\n"
        f"- 現在の進行状況：{url_for('status', _external=True)}\n\n"
        "お早めに当院へお越しください。\n"
        "来院が難しい場合は、お手数ですがお電話にてご連絡ください。\n\n"
        f"――\n平泉どうぶつ病院\nTEL：{_tel()}\nこのメールは送信専用です。返信には対応しておりません。"
    )
    return subject, body


def compose_now_call_email(ticket):
    """
    「ただいまご案内中」通知（必要になったら使う）
    """
    subject = f"【平泉どうぶつ病院】ただいまご案内中です（受付No.{_n(ticket)}）"
    body = (
        f"{_patient_name(ticket)} 様\n\n"
        "平泉どうぶつ病院です。\n"
        f"**受付No.{_n(ticket)}** の方の診察をご案内中です。\n"
        "お早めに当院へお越しください。**\n\n"
        f"- 日付：{ticket.visit_date}（{ticket.session}）\n"
        f"- 進行状況：{url_for('display', _external=True)}\n\n"
        "来院が遅れる場合は、お電話でご連絡ください。\n\n"
        f"――\n平泉どうぶつ病院\nTEL：{_tel()}\n（送信専用）"
    )
    return subject, body
