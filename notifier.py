import os
import smtplib
import ssl
from email.message import EmailMessage

SMTP_HOST = os.getenv("SMTP_HOST", "localhost")
SMTP_PORT = int(os.getenv("SMTP_PORT", "25"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")
SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "0") == "1"
MAIL_FROM = os.getenv("MAIL_FROM", SMTP_USER or "no-reply@example.com")


def send_email(to: str, subject: str, body: str) -> None:
    msg = EmailMessage()
    msg["From"] = MAIL_FROM
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)

    # 587: STARTTLS / 465: SSL
    if SMTP_USE_TLS:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=20) as s:
            s.ehlo()
            s.starttls(context=ssl.create_default_context())
            if SMTP_USER and SMTP_PASS:
                s.login(SMTP_USER, SMTP_PASS)
            s.send_message(msg)
    else:
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=ssl.create_default_context(), timeout=20) as s:
            if SMTP_USER and SMTP_PASS:
                s.login(SMTP_USER, SMTP_PASS)
            s.send_message(msg)
