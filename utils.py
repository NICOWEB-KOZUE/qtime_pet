from datetime import datetime, timezone, timedelta, date
from models import Ticket

JST = timezone(timedelta(hours=9))


def today_jst() -> date:
    return datetime.now(JST).date()


def find_or_create_today_ticket_for_patient(patient):
    """同日・未完了があればそれを返し、なければ新規作成"""
    existing = (
        Ticket.select()
        .where((Ticket.patient == patient) & (Ticket.visit_date == today_jst()) & (Ticket.done == False))
        .first()
    )
    if existing:
        return existing, False
    t = Ticket.create(patient=patient, name=patient.name, visit_date=today_jst())
    return t, True
