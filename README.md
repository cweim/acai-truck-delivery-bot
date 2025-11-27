# 🍧 Acai Supper Bot

Acai Supper Bot is a Telegram ordering assistant backed by Supabase with a FastAPI admin dashboard. Customers walk through a guided delivery or pickup flow inside Telegram, while staff review and manage orders from the browser-based dashboard.

---

## ✨ Features
- Conversational order flow for delivery or pickup (flavor, sauce, quantity, payment capture).
- Automatic customer profile creation with Supabase persistence and JSON fallbacks for offline development.
- QR-based payment instructions with screenshot collection and Supabase Storage uploads.
- FastAPI admin dashboard for monitoring orders, editing pickup stores, tweaking menu/pricing, and browsing analytics.
- Shared utility layer for pricing, schedule validation, and Supabase access across bot and dashboard.
- Customer keyboard shortcuts to preview the latest menu, delivery sessions, and pickup locations directly in chat.

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Telegram Bot token from [@BotFather](https://t.me/BotFather)
- Supabase project (URL + service role key) with the schema in `database/schema.sql`

### Installation
1. **Clone & enter the project**
   ```bash
   git clone <repo-url>
   cd acai_supper_bot
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate   # Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables** in `.env`
   ```dotenv
   BOT_TOKEN=telegram-bot-token
   ADMIN_ID=your_telegram_user_id

   SUPABASE_URL=https://<your-project>.supabase.co
   SUPABASE_KEY=<service-role-key>
   SUPABASE_BUCKET=payment-receipts         # optional, defaults to payment-receipts
   ```

5. **Provision Supabase schema**
   - Run the SQL in `database/schema.sql` against your Supabase project.
   - Insert at least one admin user record (credentials are validated via the `check_password` RPC referenced in the schema).

6. **Add your payment QR**
   - Replace `data/qr.png` with your PayNow/PayLah (or equivalent) QR code.

### Running the services
- **Telegram bot**
  ```bash
  python bot.py
  ```

- **Admin dashboard**
  ```bash
  uvicorn dashboard.app:app --reload
  ```
  Access at <http://localhost:8000>. Browser prompts for HTTP Basic Auth credentials (checked against Supabase `admin_users`).

---

## 📱 Telegram Flow
1. `/start` greets the user and presents quick actions.
   - Main keyboard offers **Show Menu**, **Show Deliveries**, and **Pickup Locations** for instant information pulled from Supabase.
2. `/order` opens the conversation:
   - Choose delivery session (Supabase backed, JSON fallback for local testing).
   - Register name/phone once (applies to both delivery and pickup flows).
   - Select flavor, sauce, and quantity using the menu set in the admin dashboard.
   - Confirm summary, receive payment QR, upload screenshot.
3. Payment screenshots are uploaded to Supabase Storage (falls back to `data/payment_screenshots/` if upload fails) while the bot keeps the user updated with concise status messages.
4. Orders and user profiles are written to Supabase tables via `database/supabase_client.py`.

---

## 🖥️ Admin Dashboard Highlights
- **Dashboard overview**: same-day order counts, revenue, and pending payments.
- **Delivery orders & pickup orders**: searchable tables with modal updates for order/payment status.
- **Settings**: edit menu flavors, sauces, pricing, and pickup store metadata.
- **Deliveries**: create/close delivery sessions.
- **Analytics**: last 30 days of sales, popular combinations, and pickup store performance (powered by Supabase views/RPCs).

---

## 📂 Project Structure
```
acai_supper_bot/
├── bot.py                     # Telegram bot entry point
├── handlers/
│   ├── order_flow.py          # Delivery/pickup ordering conversation
│   ├── payment_handler.py     # QR payment & screenshot processing
│   └── pickup_flow.py         # Pickup-specific conversation stages
├── dashboard/
│   ├── app.py                 # FastAPI admin backend
│   ├── templates/             # Jinja templates (Bootstrap-based UI)
│   └── static/                # CSS/JS for dashboard interactions
├── database/
│   ├── schema.sql             # Supabase schema and analytics views
│   └── supabase_client.py     # Shared Supabase helper
├── data/
│   ├── deliveries.json        # Local fallback delivery sessions
│   ├── pickup_stores.json     # Local fallback pickup stores
│   ├── users.json             # Local fallback customer profiles
│   └── qr.png                 # Payment QR (replace with your own)
├── utils.py                   # Shared helpers (pricing, summaries)
├── utils_pickup.py            # Pickup scheduling helpers
├── requirements.txt           # Python dependencies
├── .env                       # Environment variables (not committed)
└── README.md                  # This document
```

---

## ⚙️ Configuration Notes
- Customer and order data are persisted in Supabase; JSON files under `data/` are used only when Supabase access fails (handy for local/offline testing).
- Supabase Storage bucket name defaults to `payment-receipts`; update `SUPABASE_BUCKET` in `.env` if you use something else.
- The dashboard relies on Supabase row-level security policies defined in `schema.sql`; ensure the service role key is used server-side only (never ship it in client code).

---

## 🐛 Troubleshooting
- **Bot not responding**: confirm the bot is running, check `BOT_TOKEN`, and verify there is only one polling instance.
- **Supabase errors**: ensure `SUPABASE_URL/KEY` are correct, schema applied, and your IP can reach Supabase.
- **Payment uploads failing**: verify bucket existence and public access; screenshots fall back to `data/payment_screenshots/` when Supabase upload raises.
- **Dashboard authentication**: insert admin records with hashed passwords using the `check_password` helper (see schema comments) and ensure the HTTP Basic credentials match.

---

## 📦 Deployment Tips
- Run the Telegram bot and dashboard in separate processes or containers.
- Use environment variables for all secrets in production.
- Consider enabling Supabase edge functions or scheduled jobs for advanced workflows (e.g., auto-closing sessions).

---

## 🙏 Credits
- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot)
- [FastAPI](https://fastapi.tiangolo.com/)
- [Supabase Python SDK](https://github.com/supabase-community/supabase-py)
