from peewee import Model, SqliteDatabase, CharField, BooleanField, DateTimeField
import datetime

db = SqliteDatabase("qtime_pet.sqlite")


class Ticket(Model):
    name = CharField()
    created_at = DateTimeField(default=datetime.datetime.now)
    done = BooleanField(default=False)

    class Meta:
        database = db
