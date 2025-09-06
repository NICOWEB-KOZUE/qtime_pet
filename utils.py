import os
from datetime import datetime, timezone, timedelta, date
from models import Ticket
from peewee import fn

# --- JST ---
JST = timezone(timedelta(hours=9))


def today_jst() -> date:
    return datetime.now(JST).date()


def current_session() -> str:
    """午前/午後判定（JST）"""
    h = datetime.now(JST).hour
    return "AM" if h < 12 else "PM"


# ---------- 休診日の設定 ----------
def _parse_csv_env(name: str):
    """環境変数をカンマ区切りで集合に"""
    raw = os.getenv(name, "").strip()
    if not raw:
        return set()
    return {x.strip() for x in raw.split(",") if x.strip()}


def _weekday_name(d: date) -> str:
    # Mon..Sun -> 'Mon'..'Sun'
    return ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][d.weekday()]


# 既定：木曜は終日休診／日曜は午後のみ休診
# .env で上書き可能（下に例あり）
CLOSED_FULL_WEEKDAYS = _parse_csv_env("CLOSED_FULL_WEEKDAYS") or {"Thu"}
CLOSED_PM_WEEKDAYS = _parse_csv_env("CLOSED_PM_WEEKDAYS") or {"Sun"}
HOLIDAY_PM_DATES = _parse_csv_env("HOLIDAY_PM_DATES")  # 例: {'2025-09-15', ...}


def is_closed(vdate: date, session: str) -> tuple[bool, str]:
    """休診かどうか（True/False, 理由メッセージ）"""
    wd = _weekday_name(vdate)

    # 終日休診（木曜など）
    if wd in CLOSED_FULL_WEEKDAYS:
        return True, "本日は休診日です（終日）"

    # 午後のみ休診（日曜・祝日の午後）
    if session == "PM":
        if wd in CLOSED_PM_WEEKDAYS:
            return True, "本日の午後は休診です"
        if vdate.isoformat() in HOLIDAY_PM_DATES:
            return True, "本日の午後は祝日のため休診です"

    return False, ""


# ---------- チケット関連 ----------
def _next_seq_no_for_day(vdate: date) -> int:
    """その日の最後の seq_no の次を返す（なければ1）"""
    last = Ticket.select(fn.MAX(Ticket.seq_no)).where(Ticket.visit_date == vdate).scalar()
    return (last or 0) + 1


def find_or_create_today_ticket_for_patient(patient):
    """同日・未完了があればそれを返し、なければ新規作成"""
    vdate = today_jst()
    exist = (
        Ticket.select()
        .where((Ticket.patient == patient) & (Ticket.visit_date == vdate) & (Ticket.done == False))
        .first()
    )
    if exist:
        return exist, False

    # 競合対策：atomic で連番採番 → 作成
    db = Ticket._meta.database
    with db.atomic():
        seq = _next_seq_no_for_day(vdate)
        t = Ticket.create(
            patient=patient,
            name=patient.name,
            visit_date=vdate,
            session=current_session(),  # AM/PM を保存
            seq_no=seq,  # 当日連番
        )
    return t, True
