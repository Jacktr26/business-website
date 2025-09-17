from datetime import date, datetime
import os, json, csv, smtplib, ssl
from email.message import EmailMessage

from flask import Flask, render_template, request, url_for, jsonify
from dotenv import load_dotenv
import stripe

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "dev-secret")

# Stripe config
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY", "")
YOUR_DOMAIN = os.getenv("YOUR_DOMAIN", "http://localhost:5000")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")

BOOKINGS_FILE = "bookings.json"
CONTACT_CSV = "contacts.csv"

# ---------- Helpers ----------
def get_booked_dates():
    if os.path.exists(BOOKINGS_FILE):
        with open(BOOKINGS_FILE, "r") as f:
            try:
                return json.load(f).get("booked_dates", [])
            except Exception:
                return []
    return []

def save_booked_dates(dates):
    with open(BOOKINGS_FILE, "w") as f:
        json.dump({"booked_dates": dates}, f, indent=2)

def reserve_date(iso):
    dates = set(get_booked_dates())
    dates.add(iso)
    save_booked_dates(sorted(list(dates)))
    return True

def send_email(subject, body):
    host = os.getenv("SMTP_HOST")
    port = int(os.getenv("SMTP_PORT", "587"))
    username = os.getenv("SMTP_USERNAME")
    password = os.getenv("SMTP_PASSWORD")
    to_addr = os.getenv("NOTIFY_EMAIL")
    if not (host and port and username and password and to_addr):
        return False
    try:
        msg = EmailMessage()
        msg["From"] = username
        msg["To"] = to_addr
        msg["Subject"] = subject
        msg.set_content(body)
        context = ssl.create_default_context()
        with smtplib.SMTP(host, port) as server:
            server.starttls(context=context)
            server.login(username, password)
            server.send_message(msg)
        return True
    except Exception as e:
        print("Email error:", e)
        return False

# ---------- Demo data ----------
PROJECTS = [
    {
        "name": "Arnold Brothers Guitar",
        "tagline": "Band site with gigs calendar",
        "image": "img/arnold-brothers.jpg",  # points to static/img/arnold-brothers.jpg
        "url": "https://arnoldbrothersguitar.co.uk/",
    },
    {"name": "Cafe Bloom", "tagline": "Local cafe with online ordering"},
    {"name": "Chester Fitness", "tagline": "Trainer bookings + Stripe checkout"},
]

PACKAGES = [
    {
        "slug": "essential",
        "name": "Essential",
        "desc": "Perfect for a simple, clean landing page.",
        "image": "img/packages/essential.jpg",
    },
    {
        "slug": "professional",
        "name": "Professional",
        "desc": "Best for businesses needing bookings & payments.",
        "image": "img/packages/professional.jpg",
    },
    {
        "slug": "elite",
        "name": "Elite",
        "desc": "Premium builds with custom features and integrations.",
        "image": "img/packages/elite.jpg",
    },
]

STARTERS = [
    {"name": "Edge", "desc": "Futuristic startup landing page with gradient hero & CTAs"},
    {"name": "Local Hero", "desc": "Small business site with sections for services & testimonials"},
    {"name": "Showcase Pro", "desc": "Creative portfolio with gallery and case studies"},
]

PLANS = [
    {"name":"Starter", "price": 199, "features":[
        "1–3 pages, mobile-first", "Template customisation", "Contact form", "Basic SEO"
    ]},
    {"name":"Business", "price": 499, "features":[
        "Up to 6 pages", "Booking calendar", "Stripe deposits", "SEO + Analytics"
    ]},
    {"name":"Pro", "price": 899, "features":[
        "Custom design & components", "Blog/CMS option", "Performance budget", "Priority support"
    ]},
]

# ---------- Routes ----------
@app.route("/")
def index():
    return render_template("index.html", projects=PROJECTS)

@app.route("/portfolio")
def portfolio():
    return render_template("portfolio.html")

@app.route("/templates")
def templates_page():
    return render_template("templates.html", templates=PACKAGES)

@app.route("/templates/<slug>")
def template_detail(slug):
    t = next((x for x in PACKAGES if x["slug"] == slug), None)
    if not t:
        return "Not found", 404
    return render_template("template_detail.html", t=t)

@app.route("/pricing")
def pricing():
    return render_template("pricing.html", plans=PLANS)

@app.route("/book")
def book():
    return render_template("book.html")

@app.route("/contact", methods=["GET","POST"])
def contact():
    if request.method == "POST":
        name = request.form.get("name","").strip()
        email = request.form.get("email","").strip()
        message = request.form.get("message","").strip()
        first_write = not os.path.exists(CONTACT_CSV)
        with open(CONTACT_CSV, "a", newline="") as f:
            writer = csv.writer(f)
            if first_write: writer.writerow(["timestamp","name","email","message"])
            writer.writerow([datetime.utcnow().isoformat(), name, email, message])
        send_email("New lead: " + name, f"From: {name} <{email}>\n\n{message}")
        return render_template("contact.html", success=True)
    return render_template("contact.html", success=False)

@app.route("/privacy")
def privacy():
    return render_template("privacy.html")

# ---- Booking API ----
@app.route("/api/booked-dates")
def api_booked():
    return jsonify({"booked_dates": get_booked_dates()})

# ---- Stripe Checkout ----
from flask import jsonify

@app.route("/create-checkout-session", methods=["POST"])
def create_checkout_session():
    data = request.get_json(silent=True) or {}
    chosen_date = data.get("date")
    if not stripe.api_key:
        return jsonify({"error":"Stripe not configured"}), 500
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            mode="payment",
            line_items=[{
                "price_data": {
                    "currency": "gbp",
                    "product_data": { "name": f"Build Slot Deposit ({chosen_date or 'TBD'})" },
                    "unit_amount": 10000  # £100
                },
                "quantity": 1,
            }],
            success_url=f"{YOUR_DOMAIN}{url_for('checkout_success')}?date={chosen_date or ''}",
            cancel_url=f"{YOUR_DOMAIN}{url_for('checkout_cancel')}",
            metadata={"date": chosen_date or ""},
        )
        if chosen_date:
            send_email("Checkout started", f"Someone is checking out for {chosen_date}.")
        return jsonify({"checkout_url": session.url})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/checkout/success")
def checkout_success():
    iso = request.args.get("date")
    return render_template("checkout_success.html", date=iso)

@app.route("/checkout/cancel")
def checkout_cancel():
    return render_template("checkout_cancel.html")

# ---- Stripe Webhook ----
@app.route("/webhook", methods=["POST"])
def stripe_webhook():
    payload = request.data
    sig_header = request.headers.get("Stripe-Signature", "")
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
    except Exception as e:
        return str(e), 400

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        chosen_date = (session.get("metadata") or {}).get("date")
        if chosen_date:
            reserve_date(chosen_date)
            send_email(f"Booked slot confirmed: {chosen_date}",
                       f"A client successfully paid the deposit for {chosen_date}.")
    return "", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
