from flask import Flask, render_template, request, redirect, url_for
from models import db, Ticket
import datetime

app = Flask(__name__)
db.connect()
db.create_tables([Ticket])


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/checkin", methods=["POST"])
def checkin():
    name = request.form["name"]
    ticket = Ticket.create(name=name)
    return redirect(url_for("done", ticket_id=ticket.id))


@app.route("/done/<int:ticket_id>")
def done(ticket_id):
    ticket = Ticket.get_by_id(ticket_id)
    return render_template("done.html", ticket=ticket)


@app.route("/status")
def status():
    tickets = Ticket.select().where(Ticket.done == False)
    return render_template("status.html", tickets=tickets)


@app.route("/admin/next")
def admin_next():
    ticket = Ticket.select().where(Ticket.done == False).first()
    if ticket:
        ticket.done = True
        ticket.save()
    return redirect(url_for("status"))


if __name__ == "__main__":
    app.run(port=8000, debug=True)
