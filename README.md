# Launchly Studios — Production-ready Build (Dark Neon)

Includes:
- Booking calendar (date turns red **after** payment via Stripe webhook)
- Email notifications (SMTP via .env)
- Portfolio with real + placeholder items
- Privacy Policy page
- Dark neon aesthetic across pages

## Run locally
```bash
python3 -m venv .venv && source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
# Set keys in .env:
# SECRET_KEY, STRIPE_* (Stripe test), YOUR_DOMAIN=http://localhost:5000
# SMTP_* (Gmail app password), NOTIFY_EMAIL=you@example.com
python main.py
```

## Stripe webhook (local)
```bash
stripe login
stripe listen --forward-to localhost:5000/webhook
# copy the whsec_... into STRIPE_WEBHOOK_SECRET in your .env
```
