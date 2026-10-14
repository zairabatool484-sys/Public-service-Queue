import os
import sqlite3
from datetime import datetime
from functools import wraps

from flask import (
    Flask, request, redirect, url_for, session, flash,
    render_template_string, jsonify
)
from werkzeug.security import generate_password_hash, check_password_hash

# ---------------------------------------------------------
# SC-03 | QueueCare - Public Service Queue and Wait-Time Optimizer
# Run: py main.py
# Open: http://127.0.0.1:5000
# Default staff login: admin / admin123
# ---------------------------------------------------------

app = Flask(__name__)
app.secret_key = os.environ.get("QUEUECARE_SECRET_KEY", "queuecare-local-dev-key-change-for-deployment")
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "queuecare.db")


def get_db():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    return db


def init_db():
    with get_db() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS customers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                token INTEGER UNIQUE NOT NULL,
                name TEXT NOT NULL,
                service TEXT NOT NULL DEFAULT 'General Service',
                priority INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'Waiting',
                created_at TEXT NOT NULL,
                completed_at TEXT
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)
        db.execute("INSERT OR IGNORE INTO settings(key, value) VALUES('next_token', '100')")
        db.execute("""
            CREATE TABLE IF NOT EXISTS staff (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL
            )
        """)
        if not db.execute("SELECT id FROM staff WHERE username = 'admin'").fetchone():
            db.execute(
                "INSERT INTO staff(username, password_hash) VALUES(?, ?)",
                ("admin", generate_password_hash("admin123"))
            )


STYLE = """
:root{--navy:#12345a;--teal:#0f9b8e;--pale:#eef6f8;--ink:#172b4d;--muted:#64748b;--white:#fff;--line:#e2e8f0;--orange:#f59e0b;--red:#dc2626}
*{box-sizing:border-box}
body{margin:0;background:#f4f7fb;color:var(--ink);font-family:Inter,Segoe UI,Arial,sans-serif}
nav{background:var(--navy);color:#fff;padding:16px max(5%,calc((100% - 1120px)/2));display:flex;justify-content:space-between;align-items:center;gap:16px;flex-wrap:wrap}
.brand{font-weight:800;font-size:20px;letter-spacing:.2px}
nav .links{display:flex;gap:8px;flex-wrap:wrap}
nav a{color:#eaf7ff;text-decoration:none;padding:9px 11px;border-radius:8px;font-size:14px}
nav a:hover{background:#ffffff1b}
main{max-width:1120px;margin:28px auto;padding:0 18px;min-height:70vh}
.hero{background:linear-gradient(120deg,#12345a,#137f83);color:white;padding:34px;border-radius:22px;box-shadow:0 14px 30px #12345a18}
.hero h1{font-size:clamp(28px,4vw,42px);margin:0 0 12px}
.hero p{max-width:650px;line-height:1.7;color:#e3f7f7}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:18px;margin:20px 0}
.two{display:grid;grid-template-columns:repeat(auto-fit,minmax(290px,1fr));gap:20px}
.card,.stat{background:#fff;border:1px solid #edf1f6;border-radius:18px;padding:22px;box-shadow:0 6px 22px #14213d08;margin:18px 0}
.stat small{color:var(--muted);font-weight:600}
.stat h2{font-size:32px;margin:10px 0 4px;color:var(--teal)}
h2,h3{margin-top:0}
label{display:block;font-size:14px;font-weight:700;margin:12px 0 6px}
input,select{width:100%;padding:13px 14px;border:1px solid #cbd5e1;border-radius:10px;background:white;font:inherit}
input:focus,select:focus{outline:3px solid #0f9b8e20;border-color:var(--teal)}
button,.btn{display:inline-block;border:0;border-radius:10px;background:var(--teal);color:white;padding:12px 17px;font-weight:700;text-decoration:none;cursor:pointer;font-size:14px}
button:hover,.btn:hover{filter:brightness(.95)}
.secondary{background:var(--navy)}.warning{background:var(--orange);color:#1f2937}.danger{background:var(--red)}
.muted{color:var(--muted)}.small{font-size:13px}
.token{font-size:48px;line-height:1.2;font-weight:900;color:var(--teal);margin:12px 0}
.flash{background:#e7f8ef;border:1px solid #b8ebcc;color:#166534;padding:12px 15px;border-radius:10px;margin:12px 0}
.error{background:#fff1f2;border-color:#fecdd3;color:#9f1239}
.table-wrap{overflow-x:auto}
table{border-collapse:collapse;width:100%;min-width:620px}
th,td{text-align:left;padding:13px 12px;border-bottom:1px solid var(--line);font-size:14px}
th{color:var(--muted);font-size:12px;text-transform:uppercase;letter-spacing:.5px}
.pill{display:inline-block;border-radius:99px;padding:5px 9px;font-size:12px;font-weight:800;background:#e0f2fe;color:#075985}
.pill.done{background:#dcfce7;color:#166534}.pill.priority{background:#ffedd5;color:#9a3412}
.inline{display:inline}.inline button{padding:8px 10px}.actions{display:flex;gap:7px;flex-wrap:wrap}
footer{text-align:center;color:var(--muted);padding:26px 12px;font-size:13px}
.empty{padding:24px;text-align:center;color:var(--muted)}
.bar-bg{height:9px;background:#e2e8f0;border-radius:20px;overflow:hidden}.bar{height:100%;background:var(--teal);border-radius:20px}
@media(max-width:600px){nav{padding:15px}main{margin:18px auto}.hero{padding:25px}.card,.stat{padding:18px}.token{font-size:40px}}
"""


def page(title, content):
    return render_template_string("""
    <!doctype html>
    <html lang="en">
    <head>
      <meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
      <title>{{ title }} | QueueCare</title>
      <style>{{ style }}</style>
    </head>
    <body>
      <nav>
        <div class="brand">SC-03 | QueueCare</div>
        <div class="links">
          <a href="/">Home</a><a href="/search">Find Token</a><a href="/staff">Staff</a>
          <a href="/analytics">Analytics</a>{% if logged_in %}<a href="/logout">Logout</a>{% endif %}
        </div>
      </nav>
      <main>
        {% for message in get_flashed_messages() %}
          <div class="flash">{{ message }}</div>
        {% endfor %}
        {{ content|safe }}
      </main>
      <footer>Public Service Queue and Wait-Time Optimizer · SC-03 Project</footer>
    </body>
    </html>
    """, title=title, content=content, style=STYLE, logged_in=("staff_id" in session))


def staff_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if "staff_id" not in session:
            flash("Please log in to access the staff dashboard.")
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper


def next_token_number(db):
    row = db.execute("SELECT value FROM settings WHERE key='next_token'").fetchone()
    token = int(row["value"]) if row else 100
    db.execute("UPDATE settings SET value=? WHERE key='next_token'", (str(token + 1),))
    return token


def queue_rows(db):
    return db.execute("""
        SELECT * FROM customers
        WHERE status='Waiting'
        ORDER BY priority DESC, id ASC
    """).fetchall()


@app.route("/")
def home():
    with get_db() as db:
        waiting = db.execute("SELECT COUNT(*) n FROM customers WHERE status='Waiting'").fetchone()["n"]
        serving = db.execute("SELECT COUNT(*) n FROM customers WHERE status='Serving'").fetchone()["n"]
        completed = db.execute("SELECT COUNT(*) n FROM customers WHERE status='Completed'").fetchone()["n"]
        current = db.execute("SELECT token, name, service FROM customers WHERE status='Serving' ORDER BY id LIMIT 1").fetchone()
        recent = db.execute("SELECT token, name, service, status FROM customers ORDER BY id DESC LIMIT 5").fetchall()
    current_html = (
        f"<div class='token'>#{current['token']}</div><p>{current['name']} · {current['service']}</p>"
        if current else "<p class='muted'>No customer is being served right now.</p>"
    )
    recent_rows = "".join(
        f"<tr><td>#{r['token']}</td><td>{r['name']}</td><td>{r['service']}</td><td>{r['status']}</td></tr>"
        for r in recent
    ) or "<tr><td colspan='4' class='empty'>No tokens yet. Create the first token!</td></tr>"
    content = f"""
      <section class="hero">
        <h1>Your time matters.</h1>
        <p>Get a service token, follow your queue status, and spend less time waiting. QueueCare helps public service counters stay organized.</p>
        <div class="actions"><a class="btn" href="#get-token">Get a Token</a><a class="btn secondary" href="/search">Check Existing Token</a></div>
      </section>
      <section class="grid">
        <div class="stat"><small>Waiting</small><h2>{waiting}</h2><span class="muted small">Customers in queue</span></div>
        <div class="stat"><small>Currently Serving</small><h2>{serving}</h2><span class="muted small">At the service counter</span></div>
        <div class="stat"><small>Completed Today / Total</small><h2>{completed}</h2><span class="muted small">Completed tokens</span></div>
      </section>
      <section class="two">
        <div class="card" id="get-token">
          <h2>Get your token</h2><p class="muted">Enter your name and select the service you need.</p>
          <form method="post" action="/token">
            <label for="name">Full name</label><input id="name" name="name" maxlength="80" required placeholder="e.g. Ayesha Khan">
            <label for="service">Service type</label>
            <select id="service" name="service">
              <option>General Service</option><option>Document Verification</option><option>Fee Payment</option><option>Registration</option><option>Information Desk</option>
            </select>
            <button type="submit" style="margin-top:12px">Generate Token</button>
          </form>
        </div>
        <div class="card"><h2>Now serving</h2>{current_html}<p class="muted small">Queue status refreshes automatically every 10 seconds.</p><a class="btn secondary" href="/search">Track your token</a></div>
      </section>
      <section class="card"><h2>Recent tokens</h2><div class="table-wrap"><table><thead><tr><th>Token</th><th>Name</th><th>Service</th><th>Status</th></tr></thead><tbody>{recent_rows}</tbody></table></div></section>
      <script>setTimeout(()=>location.reload(),10000);</script>
    """
    return page("Home", content)


@app.route("/token", methods=["POST"])
def create_token():
    name = request.form.get("name", "").strip()
    service = request.form.get("service", "General Service").strip()
    allowed = {"General Service", "Document Verification", "Fee Payment", "Registration", "Information Desk"}
    if not name:
        flash("Please enter your name.")
        return redirect(url_for("home"))
    if len(name) > 80:
        flash("Name must be 80 characters or less.")
        return redirect(url_for("home"))
    if service not in allowed:
        service = "General Service"
    with get_db() as db:
        token = next_token_number(db)
        db.execute(
            """INSERT INTO customers(token,name,service,priority,status,created_at)
               VALUES(?,?,?,0,'Waiting',?)""",
            (token, name, service, datetime.now().isoformat(timespec="seconds"))
        )
    return redirect(url_for("token_created", token=token))


@app.route("/token/<int:token>")
def token_created(token):
    with get_db() as db:
        customer = db.execute("SELECT * FROM customers WHERE token=?", (token,)).fetchone()
        ahead = db.execute(
            """SELECT COUNT(*) n FROM customers
               WHERE status='Waiting' AND
               (priority > COALESCE((SELECT priority FROM customers WHERE token=?),0)
                OR (priority = COALESCE((SELECT priority FROM customers WHERE token=?),0)
                    AND id < COALESCE((SELECT id FROM customers WHERE token=?),999999)))""",
            (token, token, token)
        ).fetchone()["n"]
    if not customer:
        flash("Token not found.")
        return redirect(url_for("search_token"))
    eta = max(0, ahead * 10)
    status_class = "done" if customer["status"] == "Completed" else ""
    content = f"""
      <section class="card" style="text-align:center;padding:35px">
        <p class="muted">YOUR QUEUECARE TOKEN</p><div class="token">#{customer['token']}</div>
        <h2>Hello, {escape_html(customer['name'])}!</h2>
        <p>{escape_html(customer['service'])}</p>
        <p>Status: <span class="pill {status_class}">{customer['status']}</span></p>
        <p>Estimated wait: <strong>{'Complete' if customer['status']=='Completed' else str(eta)+' minutes (approx.)'}</strong></p>
        <p class="muted small">Please keep your token number for checking status later.</p>
        <div class="actions" style="justify-content:center"><a class="btn" href="/search">Track Token</a><a class="btn secondary" href="/">Home</a></div>
      </section>
      <script>setTimeout(()=>location.reload(),15000);</script>
    """
    return page("Your Token", content)


def escape_html(value):
    from markupsafe import escape
    return str(escape(value))


@app.route("/search", methods=["GET", "POST"])
def search_token():
    customer = None
    ahead = 0
    if request.method == "POST":
        raw = request.form.get("token", "").strip().lstrip("#")
        if raw.isdigit():
            with get_db() as db:
                customer = db.execute("SELECT * FROM customers WHERE token=?", (int(raw),)).fetchone()
                if customer and customer["status"] == "Waiting":
                    ahead = db.execute(
                        """SELECT COUNT(*) n FROM customers
                           WHERE status='Waiting' AND
                           (priority > ? OR (priority = ? AND id < ?))""",
                        (customer["priority"], customer["priority"], customer["id"])
                    ).fetchone()["n"]
        if not customer:
            flash("Token not found. Please check the number and try again.")
    result = ""
    if customer:
        eta = max(0, ahead * 10)
        result = f"""
        <div class="card">
          <p class="muted">TOKEN DETAILS</p><div class="token">#{customer['token']}</div>
          <h2>{escape_html(customer['name'])}</h2><p>{escape_html(customer['service'])}</p>
          <p>Status: <span class="pill {'done' if customer['status']=='Completed' else ''}">{customer['status']}</span></p>
          <p>People ahead: <strong>{ahead if customer['status']=='Waiting' else 0}</strong></p>
          <p>Estimated wait: <strong>{'Completed' if customer['status']=='Completed' else ('Being served now' if customer['status']=='Serving' else str(eta)+' minutes (approx.)')}</strong></p>
          <p class="muted small">Estimate is approximate and assumes about 10 minutes per customer.</p>
        </div>"""
    content = f"""
      <section class="hero"><h1>Find your token</h1><p>Enter your token number to check the latest queue status.</p></section>
      <section class="card"><form method="post">
        <label for="token">Token number</label><input id="token" name="token" required placeholder="e.g. 100">
        <button type="submit">Search Token</button>
      </form></section>{result}
    """
    return page("Find Token", content)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        with get_db() as db:
            staff = db.execute("SELECT * FROM staff WHERE username=?", (username,)).fetchone()
        if staff and check_password_hash(staff["password_hash"], password):
            session.clear()
            session["staff_id"] = staff["id"]
            session["username"] = staff["username"]
            flash("Login successful. Welcome to the staff dashboard.")
            return redirect(url_for("staff"))
        flash("Incorrect username or password.")
    content = """
      <section class="hero"><h1>Staff portal</h1><p>Authorized staff can manage the queue and prioritize urgent cases.</p></section>
      <section class="card" style="max-width:500px;margin:22px auto">
        <h2>Staff Login</h2><form method="post">
          <label for="username">Username</label><input id="username" name="username" required autocomplete="username">
          <label for="password">Password</label><input id="password" type="password" name="password" required autocomplete="current-password">
          <button type="submit">Login</button>
        </form><p class="muted small">First run demo login: admin / admin123. Change this before any public deployment.</p>
      </section>
    """
    return page("Staff Login", content)


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.")
    return redirect(url_for("home"))


@app.route("/staff")
def staff():
    if "staff_id" not in session:
        return redirect(url_for("login"))
    with get_db() as db:
        waiting = queue_rows(db)
        serving = db.execute("SELECT * FROM customers WHERE status='Serving' ORDER BY id LIMIT 1").fetchone()
        completed_count = db.execute("SELECT COUNT(*) n FROM customers WHERE status='Completed'").fetchone()["n"]
    serving_html = (
        f"<h2>Token #{serving['token']}</h2><p>{escape_html(serving['name'])} · {escape_html(serving['service'])}</p>"
        f"<form method='post' action='/complete/{serving['token']}'><button>Mark Completed</button></form>"
        if serving else "<p class='muted'>No customer is currently being served.</p>"
    )
    rows = ""
    for c in waiting:
        priority_label = "<span class='pill priority'>Priority</span>" if c["priority"] else "<span class='pill'>Normal</span>"
        priority_button = (
            f"<form class='inline' method='post' action='/priority/{c['token']}'><button class='warning' type='submit'>Remove priority</button></form>"
            if c["priority"] else
            f"<form class='inline' method='post' action='/priority/{c['token']}'><button class='secondary' type='submit'>Set priority</button></form>"
        )
        rows += f"""<tr><td>#{c['token']}</td><td>{escape_html(c['name'])}</td><td>{escape_html(c['service'])}</td><td>{priority_label}</td>
        <td><div class="actions">{priority_button}
        <form class="inline" method="post" action="/serve/{c['token']}"><button type="submit">Serve next</button></form></div></td></tr>"""
    if not rows:
        rows = "<tr><td colspan='5' class='empty'>No waiting customers right now.</td></tr>"
    content = f"""
      <section class="hero"><h1>Staff dashboard</h1><p>Welcome, {escape_html(session.get('username','staff'))}. Manage waiting customers and keep the line moving.</p></section>
      <div class="grid"><div class="stat"><small>Waiting</small><h2>{len(waiting)}</h2></div><div class="stat"><small>Completed</small><h2>{completed_count}</h2></div><div class="stat"><small>Signed in as</small><h2 style="font-size:23px">{escape_html(session.get('username','staff'))}</h2></div></div>
      <section class="card"><h2>Currently serving</h2>{serving_html}</section>
      <section class="card"><h2>Waiting queue</h2><p class="muted small">Priority customers appear first; within the same priority, older tokens come first.</p>
      <div class="table-wrap"><table><thead><tr><th>Token</th><th>Name</th><th>Service</th><th>Type</th><th>Actions</th></tr></thead><tbody>{rows}</tbody></table></div></section>
      <script>setTimeout(()=>location.reload(),15000);</script>
    """
    return page("Staff Dashboard", content)


@app.route("/serve/<int:token>", methods=["POST"])
@staff_required
def serve_token(token):
    with get_db() as db:
        already_serving = db.execute("SELECT id FROM customers WHERE status='Serving'").fetchone()
        if already_serving:
            flash("Complete the current customer before serving another.")
        else:
            next_customer = db.execute(
                "SELECT * FROM customers WHERE status='Waiting' ORDER BY priority DESC, id ASC LIMIT 1"
            ).fetchone()
            if not next_customer or next_customer["token"] != token:
                flash("Please serve the next customer in queue.")
            else:
                db.execute("UPDATE customers SET status='Serving' WHERE token=?", (token,))
                flash(f"Token #{token} is now being served.")
    return redirect(url_for("staff"))


@app.route("/complete/<int:token>", methods=["POST"])
@staff_required
def complete_token(token):
    with get_db() as db:
        customer = db.execute("SELECT * FROM customers WHERE token=?", (token,)).fetchone()
        if customer and customer["status"] == "Serving":
            db.execute(
                "UPDATE customers SET status='Completed', completed_at=? WHERE token=?",
                (datetime.now().isoformat(timespec="seconds"), token)
            )
            flash(f"Token #{token} marked as completed.")
        else:
            flash("That token is not currently being served.")
    return redirect(url_for("staff"))


@app.route("/priority/<int:token>", methods=["POST"])
@staff_required
def toggle_priority(token):
    with get_db() as db:
        customer = db.execute("SELECT * FROM customers WHERE token=?", (token,)).fetchone()
        if customer and customer["status"] == "Waiting":
            db.execute("UPDATE customers SET priority=? WHERE token=?", (0 if customer["priority"] else 1, token))
            flash(f"Priority updated for token #{token}.")
        else:
            flash("Only waiting customers can have priority changed.")
    return redirect(url_for("staff"))


@app.route("/analytics")
def analytics():
    with get_db() as db:
        total = db.execute("SELECT COUNT(*) n FROM customers").fetchone()["n"]
        waiting = db.execute("SELECT COUNT(*) n FROM customers WHERE status='Waiting'").fetchone()["n"]
        serving = db.execute("SELECT COUNT(*) n FROM customers WHERE status='Serving'").fetchone()["n"]
        completed = db.execute("SELECT COUNT(*) n FROM customers WHERE status='Completed'").fetchone()["n"]
        services = db.execute(
            "SELECT service, COUNT(*) n FROM customers GROUP BY service ORDER BY n DESC"
        ).fetchall()
        daily = db.execute("""
            SELECT substr(created_at,1,10) day, COUNT(*) n
            FROM customers GROUP BY substr(created_at,1,10)
            ORDER BY day DESC LIMIT 7
        """).fetchall()
    service_rows = "".join(
        f"<tr><td>{escape_html(r['service'])}</td><td>{r['n']}</td></tr>" for r in services
    ) or "<tr><td colspan='2' class='empty'>No data yet.</td></tr>"
    daily_sorted = list(reversed(daily))
    max_daily = max([r["n"] for r in daily_sorted], default=1)
    daily_bars = "".join(
        f"<div style='margin:15px 0'><div style='display:flex;justify-content:space-between;gap:12px;margin-bottom:6px'><span>{r['day']}</span><strong>{r['n']}</strong></div><div class='bar-bg'><div class='bar' style='width:{max(4, int(r['n']/max_daily*100))}%'></div></div></div>"
        for r in daily_sorted
    ) or "<p class='empty'>Tokens will appear here after customers register.</p>"
    content = f"""
      <section class="hero"><h1>Queue analytics</h1><p>Understand service demand and queue progress at a glance.</p></section>
      <section class="grid">
        <div class="stat"><small>Total tokens</small><h2>{total}</h2></div>
        <div class="stat"><small>Waiting</small><h2>{waiting}</h2></div>
        <div class="stat"><small>Serving</small><h2>{serving}</h2></div>
        <div class="stat"><small>Completed</small><h2>{completed}</h2></div>
      </section>
      <section class="two">
        <div class="card"><h2>Tokens by service</h2><div class="table-wrap"><table><thead><tr><th>Service</th><th>Tokens</th></tr></thead><tbody>{service_rows}</tbody></table></div></div>
        <div class="card"><h2>Recent daily demand</h2>{daily_bars}</div>
      </section>
      <p class="muted small">Analytics use the records saved in your local SQLite database.</p>
    """
    return page("Analytics", content)


@app.route("/api/queue")
def api_queue():
    with get_db() as db:
        rows = db.execute("""
            SELECT token, name, service, priority, status
            FROM customers WHERE status IN ('Waiting','Serving')
            ORDER BY CASE status WHEN 'Serving' THEN 0 ELSE 1 END, priority DESC, id ASC
        """).fetchall()
    return jsonify([dict(row) for row in rows])


@app.errorhandler(404)
def not_found(_error):
    return page("Page Not Found", """
      <section class="card"><h1>Page not found</h1><p>The page you requested does not exist.</p><a class="btn" href="/">Go Home</a></section>
    """), 404


if __name__ == "__main__":
    init_db()
    print("\\nQueueCare is starting...")
    print("Open http://127.0.0.1:5000 in your browser")
    print("Demo staff login: admin / admin123\\n")
    app.run(debug=True)
