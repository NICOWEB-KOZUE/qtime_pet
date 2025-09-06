import os, datetime
from dotenv import load_dotenv
from playhouse.db_url import connect
from peewee import (
    Model,
    CharField,
    IntegerField,
    ForeignKeyField,
    DateTimeField,
    BooleanField,
    DateField,
)

load_dotenv()  # .env を読み込む

# 環境変数 DATABASE_URL がなければ sqlite をデフォルトに
db = connect(os.getenv("DATABASE_URL", "sqlite:///qtime_pet.sqlite"))


class BaseModel(Model):
    class Meta:
        database = db


class Patient(Model):
    name = CharField()              # 氏名
    kana = CharField(null=True)     # フリガナ（任意）
    pet_name = CharField()          # ペット名
    phone = CharField()             # 電話番号
    birth = CharField()             # 生年月日（YYYY-MM-DD 文字列でOK）
    email = CharField(null=True)    # メール（任意）
    card_number = CharField(unique=True)  # 診察券番号（自動発行）
    password = CharField()          # 簡易：誕生日下4桁（学習用）


    class Meta:
        database = db

class Ticket(Model):
    patient = ForeignKeyField(Patient, null=True, backref="tickets")
    name = CharField()                        # 表示用（紙受付や簡単表示で使う）
    created_at = DateTimeField(default=datetime.datetime.now)
    done = BooleanField(default=False)

    visit_date = DateField(null=True)  # 当日の運用を明確化
    notified = BooleanField(default=False)  # 通知済フラグ
    session = CharField(default="AM")  # "AM" or "PM"
    seq_no = IntegerField(null=True, index=True)  #  当日連番

    class Meta:
        database = db
