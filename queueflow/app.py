"""
app.py
Flask + SocketIO backend for QueueFlow.

Routes:
  /            -> Get Token page (public)
  /queue       -> Live Queue page (public, read-only display)
  /staff       -> Staff login + control panel (password protected)
  /staff/logout -> Clears staff session

Socket events (client -> server):
  "add_token"   { name, category }              -- public
  "serve_next"  {}                               -- staff only (server-side checked)
  "complete"    { counter }                      -- staff only (server-side checked)

Socket events (server -> client), broadcast to everyone:
  "state_update"  full current state (see smartqueue.get_state)
  "token_created" { token_id }   (sent only to the client who requested it)
  "not_authorized" {}            (sent back if a non-staff client tries a staff action)
"""

import os

from flask import Flask, render_template, request, redirect, url_for, session
from flask_socketio import SocketIO, emit

from smartqueue import TokenQueue

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "queueflow-secret-change-me")
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="gevent",
                     manage_session=True)

queue = TokenQueue()

# Staff password: set STAFF_PASSWORD as an env var on Render for real deployments.
STAFF_PASSWORD = os.environ.get("STAFF_PASSWORD", "admin123")


def is_staff():
    return session.get("is_staff", False)


# ---------------- PAGE ROUTES ----------------
@app.route("/")
def get_token_page():
    return render_template("get_token.html")


@app.route("/queue")
def queue_page():
    # Public, read-only view — no controls rendered here
    return render_template("queue.html", is_staff=False)


@app.route("/staff", methods=["GET", "POST"])
def staff_page():
    error = None
    if request.method == "POST":
        password = request.form.get("password", "")
        staff_name = request.form.get("staff_name", "").strip() or "Staff"
        if password == STAFF_PASSWORD:
            session["is_staff"] = True
            session["staff_name"] = staff_name
            session["staff_counter"] = 1  # single-operator dashboard controls Counter 1
            return redirect(url_for("staff_page"))
        error = "Incorrect password"

    if is_staff():
        return render_template(
            "staff_dashboard.html",
            staff_name=session.get("staff_name", "Staff"),
            staff_counter=session.get("staff_counter", 1),
        )

    return render_template("staff_login.html", error=error)


@app.route("/staff/logout")
def staff_logout():
    session.pop("is_staff", None)
    session.pop("staff_name", None)
    session.pop("staff_counter", None)
    return redirect(url_for("staff_page"))


@app.route("/admin")
def admin_page():
    if not is_staff():
        return redirect(url_for("staff_page"))
    return render_template("admin.html", staff_name=session.get("staff_name", "Admin"))


# ---------------- SOCKET EVENTS ----------------
@socketio.on("connect")
def on_connect():
    emit("state_update", queue.get_state())


@socketio.on("add_token")
def on_add_token(data):
    # Public action — anyone visiting "/" can request a token
    name = (data or {}).get("name", "Guest").strip() or "Guest"
    category = (data or {}).get("category", "general")

    token_id = queue.add_token(name, category)

    emit("token_created", {"token_id": token_id, "category": category})
    emit("state_update", queue.get_state(), broadcast=True)


@socketio.on("serve_next")
def on_serve_next():
    if not is_staff():
        emit("not_authorized")
        return

    result = queue.serve_next()
    emit("state_update", queue.get_state(), broadcast=True)
    if result:
        emit("token_called", result, broadcast=True)


@socketio.on("serve_next_counter")
def on_serve_next_counter(data):
    """Used by the single-operator staff dashboard: serves the next token
    directly into the staff member's own counter."""
    if not is_staff():
        emit("not_authorized")
        return

    counter = int((data or {}).get("counter", 1)) - 1
    result = queue.serve_next_to_counter(counter)
    emit("state_update", queue.get_state(), broadcast=True)
    if result:
        emit("token_called", result, broadcast=True)


@socketio.on("complete")
def on_complete(data):
    if not is_staff():
        emit("not_authorized")
        return

    counter = int((data or {}).get("counter", 1)) - 1
    queue.complete_token(counter)
    emit("state_update", queue.get_state(), broadcast=True)


# ---------------- RUN ----------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host="0.0.0.0", port=port, debug=True)
