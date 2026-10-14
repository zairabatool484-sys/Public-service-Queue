
from flask import Flask, request, jsonify, render_template_string
from markupsafe import escape

app = Flask(__name__)

next_token = 100
completed_tokens = 0
service_counters = 1
customers = []

STYLE = """
* { box-sizing: border-box; }
body {
    margin: 0; font-family: Arial, sans-serif;
    background: #f1f5f9; color: #172554;
}
nav {
    background: #12345a; padding: 18px 5%;
    display: flex; justify-content: space-between;
    align-items: center; flex-wrap: wrap; gap: 12px;
}
nav strong { color: white; font-size: 20px; }
nav a { color: white; text-decoration: none; margin: 8px; }
main { max-width: 1050px; margin: 35px auto; padding: 0 18px; }
.hero {
    background: linear-gradient(120deg,#12345a,#168b8b);
    color: white; padding: 38px; border-radius: 18px;
}
.hero h1 { font-size: 32px; margin-top: 0; }
.card {
    background: white; padding: 24px; border-radius: 16px;
    box-shadow: 0 5px 18px #0f172a0d; margin: 18px 0;
}
.grid {
    display: grid; grid-template-columns: repeat(auto-fit,minmax(190px,1fr));
    gap: 18px; margin-top: 22px;
}
.stat { background: white; border-radius: 14px; padding: 22px; }
.stat h2 { color: #168b8b; font-size: 30px; margin: 8px 0; }
input {
    padding: 13px; border: 1px solid #cbd5e1; border-radius: 8px;
    width: 100%; margin: 10px 0;
}
button, .btn {
    display: inline-block; background: #168b8b; color: white;
    padding: 12px 18px; border: 0; border-radius: 8px;
    cursor: pointer; text-decoration: none; font-size: 15px;
}
.secondary { background: #12345a; }
.muted { color: #64748b; }
.big-token { font-size: 48px; color: #168b8b; font-weight: bold; }
footer { text-align: center; color: #64748b; padding: 25px; }
"""

def page(title, content):
    return render_template_string("""
    <!doctype html>
    <html><head><meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{{ title }} | SC-03</title>
    <style>{{ style }}</style></head>
    <body>
    <nav>
      <strong>SC-03 | QueueCare</strong>
      <div>
        <a href="/">Home</a>
        <a href="/staff">Staff</a>
        <a href="/analytics">Analytics</a>
        <a href="/counters">Counters</a>
      </div>
    </nav>
    <main>{{ content|safe }}</main>
    <footer>Public Service Queue and Wait-Time Optimizer</footer>
    </body></html>
    """, title=title, content=content, style=STYLE)

@app.route("/")
def home():
    content = """
    <section class="hero">
      <h1>Skip the confusion. Know your place.</h1>
      <p>Get a digital token and see your estimated queue wait.</p>
    </section>
    <section class="card">
      <h2>Get Your Digital Token</h2>
      <p class="muted">Enter your name to join the service queue.</p>
      <form action="/token" method="post">
        <input name="customer" placeholder="Enter your full name" required maxlength="80">
        <button type="submit">Get My Token →</button>
      </form>
    </section>
    <section class="grid">
      <div class="stat"><h3>Simple & Digital</h3><p>Receive a token without a paper ticket.</p></div>
      <div class="stat"><h3>Know Your Wait</h3><p>View your queue position and estimated wait.</p></div>
      <div class="stat"><h3>Staff Tools</h3><p>Monitor the queue and manage service counters.</p></div>
    </section>
    <section class="card">
      <h2>Quick Links</h2>
      <p><a class="btn secondary" href="/staff">Staff Dashboard</a>
      <a class="btn secondary" href="/analytics">View Analytics</a>
      <a class="btn secondary" href="/counters">Manage Counters</a></p>
    </section>
    <script>
    if ("Notification" in window && Notification.permission === "default") {
      Notification.requestPermission();
    }
    let previous = 100;
    async function checkTokens() {
      try {
        const r = await fetch("/check-new-token");
        const d = await r.json();
        if (d.token_number > previous) {
          previous = d.token_number;
          if ("Notification" in window && Notification.permission === "granted") {
            new Notification("New queue customer", {
              body: d.customer + " received token #" + d.token_number
            });
          }
        }
      } catch (e) {}
    }
    setInterval(checkTokens, 3000);
    </script>
    """
    return page("Home", content)

@app.route("/token", methods=["POST"])
def get_token():
    global next_token
    name = request.form.get("customer", "").strip()
    if not name:
        return "Please enter a name.", 400

    token = next_token
    next_token += 1
    customers.append({"token": token, "name": name, "completed": False})

    position = sum(1 for c in customers if not c["completed"])
    wait = max(0, ((position - 1) * 5 + service_counters - 1) // service_counters)

    content = f"""
    <section class="card" style="text-align:center">
      <p>YOUR TOKEN IS READY</p>
      <div class="big-token">#{token}</div>
      <h2>Welcome, {escape(name)}!</h2>
      <p>Queue position: <strong>{position}</strong></p>
      <p>Estimated wait: <strong>{wait} minutes</strong></p>
      <a class="btn" href="/">Back to Home</a>
    </section>"""
    return page("Your Token", content)

@app.route("/staff")
def staff_dashboard():
    issued = len(customers)
    waiting = sum(not c["completed"] for c in customers)
    completed = sum(c["completed"] for c in customers)
    rows = "".join(
        f"""<tr><td>#{c['token']}</td><td>{escape(c['name'])}</td>
        <td>{'Completed' if c['completed'] else 'Waiting'}</td></tr>"""
        for c in customers
    ) or "<tr><td colspan='3'>No customers yet.</td></tr>"

    content = f"""
    <h1>Staff Dashboard</h1>
    <p class="muted">Monitor customers and serve the next waiting token.</p>
    <section class="grid">
      <div class="stat"><p>Total tokens</p><h2>{issued}</h2></div>
      <div class="stat"><p>Waiting</p><h2>{waiting}</h2></div>
      <div class="stat"><p>Completed</p><h2>{completed}</h2></div>
    </section>
    <section class="card">
      <h2>Queue Register</h2>
      <table width="100%" cellpadding="10" style="text-align:left">
      <tr><th>Token</th><th>Customer</th><th>Status</th></tr>{rows}</table>
      <form action="/complete" method="post">
        <button type="submit">Complete Next Token</button>
      </form>
      <p class="muted">Demo only: this dashboard has no staff login yet.</p>
    </section>"""
    return page("Staff Dashboard", content)

@app.route("/complete", methods=["POST"])
def complete_token():
    for customer in customers:
        if not customer["completed"]:
            customer["completed"] = True
            break
    return __import__("flask").redirect("/staff")

@app.route("/analytics")
def analytics():
    issued = len(customers)
    completed = sum(c["completed"] for c in customers)
    waiting = issued - completed
    content = f"""
    <h1>Queue Analytics</h1>
    <p class="muted">A live summary of this demo session.</p>
    <section class="grid">
      <div class="stat"><p>Tokens Issued</p><h2>{issued}</h2></div>
      <div class="stat"><p>Customers Served</p><h2>{completed}</h2></div>
      <div class="stat"><p>Waiting</p><h2>{waiting}</h2></div>
      <div class="stat"><p>Estimated queue wait</p><h2>{(waiting * 5) // max(1, service_counters)} min</h2></div>
    </section>
    <section class="card"><p>Wait estimates are simplified for demonstration.</p></section>"""
    return page("Analytics", content)

@app.route("/notification")
def notification():
    waiting = sum(not c["completed"] for c in customers)
    content = f"""
    <section class="card"><h1>Queue Notifications</h1>
    <h2>{waiting} customers currently waiting</h2>
    <p>Browser pop-ups are enabled only when permission is granted and the Home page is open.</p>
    <a class="btn" href="/">Back to Home</a></section>"""
    return page("Notifications", content)

@app.route("/check-new-token")
def check_new_token():
    latest = customers[-1] if customers else None
    return jsonify({
        "token_number": latest["token"] if latest else 100,
        "customer": latest["name"] if latest else ""
    })

@app.route("/counters", methods=["GET", "POST"])
def counters():
    global service_counters
    if request.method == "POST":
        action = request.form.get("action")
        if action == "open":
            service_counters += 1
        elif action == "close" and service_counters > 1:
            service_counters -= 1

    waiting = sum(not c["completed"] for c in customers)
    wait = (waiting * 5) // service_counters
    content = f"""
    <h1>Service Counter Management</h1>
    <section class="grid">
      <div class="stat"><p>Active counters</p><h2>{service_counters}</h2></div>
      <div class="stat"><p>Customers waiting</p><h2>{waiting}</h2></div>
      <div class="stat"><p>Estimated wait</p><h2>{wait} min</h2></div>
    </section>
    <section class="card">
      <form method="post">
        <button name="action" value="open">+ Open Extra Counter</button>
        <button class="secondary" name="action" value="close">Close Counter</button>
      </form>
    </section>"""
    return page("Service Counters", content)

if __name__ == "__main__":
    app.run(debug=True)
