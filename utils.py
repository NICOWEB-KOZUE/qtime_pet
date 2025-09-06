from datetime import datetime, timezone, timedelta, date
from models import Ticket
from peewee import fn

JST = timezone(timedelta(hours=9))


def today_jst() -> date:
    return datetime.now(JST).date()


def current_session():
    h = datetime.now(JST).hour
    return "AM" if h < 12 else "PM"


def _next_seq_no_for_day(vdate: date) -> int:
    """その日の最後の seq_no の次を返す（なければ1）"""
    last = (
        Ticket.select(fn.MAX(Ticket.seq_no))
        .where(Ticket.visit_date == vdate)
        .scalar()
    )
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

    db = Ticket._meta.database
    with db.atomic():  # ← 競合対策
        seq = _next_seq_no_for_day(vdate)
        t = Ticket.create(
            patient=patient,
            name=patient.name,
            visit_date=vdate,
            session=current_session(),  # 表示用に保持
            seq_no=seq,  # ★ 日別連番
        )
    return t, True
