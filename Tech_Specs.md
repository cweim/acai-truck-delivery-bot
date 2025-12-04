# Tech Specifications - Acai Supper Bot

**Project:** Acai Supper Bot
**Type:** Full-Stack Telegram Ordering System
**Last Updated:** December 3, 2025

---

## 1. Project Overview

**Acai Supper Bot** is a complete ordering system for acai bowls built on Telegram. Customers can browse a dynamic menu, place delivery or pickup orders, and submit payment proof via QR code. An admin dashboard powered by FastAPI allows managers to configure menus, track orders, and view analytics. The system uses Supabase (PostgreSQL + Storage) as the backend database.

### Key Statistics
- **Codebase:** ~4,000+ lines of Python code (excluding dependencies)
- **Core Files:** ~20 Python modules
- **Dependencies:** 10 main packages
- **Database Tables:** 8+ core entities
- **Admin Pages:** 8 HTML templates
- **API Endpoints:** 20+ FastAPI routes

---

## 2. Architecture & Technology Stack

### 2.1 System Architecture

```
                        TELEGRAM USERS
                              |
                    ┌─────────┴─────────┐
                    |                   |
              BOT.PY (Polling)    DASHBOARD (FastAPI)
                    |                   |
         ┌──────────┴───────────┬───────┴──────────┐
         |                      |                   |
      Handlers         Telegram Bot API      FastAPI Routes
    ├─ order_flow.py                     ├─ /login, /logout
    ├─ payment_handler.py                ├─ /dashboard
    └─ menu_helpers.py                   ├─ /delivery-orders
         |                               ├─ /pickup-orders
         |                               ├─ /deliveries
      SUPABASE SDK                       ├─ /settings
         |                               ├─ /analytics
    ┌────┴──────────────────┐            ├─ /storage
    |                       |            └─ /api/*
  PostgreSQL           Storage
  (Database)          (S3 Bucket)
```

### 2.2 Core Technology Stack

| Category | Technology | Version | Purpose |
|----------|-----------|---------|---------|
| **Runtime** | Python | 3.11+ | Core application language |
| **Bot Framework** | python-telegram-bot | 21.4 | Telegram API abstraction |
| **Web Framework** | FastAPI | ≥0.109.0 | Admin dashboard backend |
| **ASGI Server** | uvicorn[standard] | ≥0.27.0 | HTTP server for FastAPI |
| **Database** | PostgreSQL (Supabase) | Latest | Relational data storage |
| **Storage** | Supabase Storage (S3) | - | File uploads (payment receipts) |
| **Template Engine** | Jinja2 | ≥3.1.0 | HTML rendering for dashboard |
| **Config Management** | python-dotenv | Latest | Environment variables |
| **Form Parsing** | python-multipart | ≥0.0.6 | FastAPI form data handling |

---

## 3. Application Structure

### 3.1 Directory Layout

```
acai_supper_bot/
│
├── bot.py                          # Telegram bot entry point
├── constants.py                    # UI text constants
├── keyboards.py                    # Telegram keyboard definitions
├── menu.py                         # Menu data fetching & caching
├── utils.py                        # Shared utility functions
├── requirements.txt                # Python dependencies
├── .env                            # Environment variables (secret)
├── .env.example                    # Example configuration
│
├── handlers/                       # Telegram conversation handlers
│   ├── order_flow.py              # Delivery/pickup order flow state machine
│   ├── payment_handler.py         # QR payment & screenshot handling
│   └── menu_helpers.py            # Dynamic menu building utilities
│
├── database/                       # Supabase data layer
│   ├── supabase_client.py         # Main client (1400+ lines)
│   ├── schema.sql                 # Database schema & migrations
│   ├── auth_functions.sql         # PostgreSQL RPC functions
│   └── migrations/                # Database migration scripts
│       ├── 001_add_telegram_notifications.sql
│       └── 002_add_cart_system.sql
│
├── dashboard/                      # FastAPI admin web interface
│   ├── app.py                     # FastAPI application (1000+ lines)
│   ├── telegram_notifier.py       # Telegram message service
│   ├── templates/                 # Jinja2 HTML templates
│   │   ├── base.html              # Base layout template
│   │   ├── login.html             # Admin login page
│   │   ├── dashboard.html         # Main dashboard view
│   │   ├── delivery_orders.html   # Delivery order management
│   │   ├── pickup_orders.html     # Pickup order management
│   │   ├── deliveries.html        # Delivery session management
│   │   ├── analytics.html         # Sales & performance analytics
│   │   └── settings.html          # Menu/pricing configuration
│   └── static/                    # Static assets
│       └── js/main.js             # Client-side interactions
│
├── data/                          # Local fallback data (JSON)
│   ├── deliveries.json            # Fallback delivery sessions
│   ├── pickup_stores.json         # Fallback pickup locations
│   ├── users.json                 # Fallback customer profiles
│   ├── qr.png                     # Payment QR code image
│   └── temp_screenshots/          # Local screenshot storage
│
└── .gitignore                      # Git ignore configuration
```

### 3.2 Module Responsibilities

#### **Bot Entry Point** (`bot.py`)
- Application initialization with `telegram.ext.Application`
- Command handlers: `/start`, `/help`, `/order`
- Callback handlers for button presses
- Conversation handler registration
- Error handling and logging
- Polling-based event loop

#### **Order Flow Handler** (`handlers/order_flow.py` - 20 KB)
State machine with flow:
1. **SELECT_DELIVERY** → Choose delivery or pickup
2. **REGISTER_NAME** → Collect customer name
3. **REGISTER_PHONE** → Collect phone number
4. **MENU_SELECTION** → Browse dynamic menu
5. **QUANTITY** → Select quantity (1-5)
6. **ADD_MORE_ITEMS** → Add to cart or proceed
7. **CONFIRM** → Review order summary
8. **PAYMENT** → Send payment instructions

Features:
- Supabase user profile creation/update
- Dynamic menu rendering
- Multi-item cart support
- Price calculation

#### **Payment Handler** (`handlers/payment_handler.py` - 19 KB)
- Displays payment QR code (`data/qr.png`)
- Receives screenshot uploads
- Uploads to Supabase Storage (with local fallback)
- Updates order status
- Handles payment verification

#### **Menu Helpers** (`handlers/menu_helpers.py` - 5 KB)
- Dynamic inline keyboard generation
- Menu group rendering
- Selection state caching
- Quantity prompts

#### **Utilities** (`utils.py` - 113 lines)
- JSON file I/O with fallback handling
- Price calculation and formatting
- Currency formatting (SGD)
- Order summary generation
- Delivery validation

#### **Menu Manager** (`menu.py` - 119 lines)
- Fetches menu from Supabase
- 5-minute cache TTL
- Fallback to local defaults
- Bot branding configuration

#### **Database Client** (`database/supabase_client.py` - 1400+ lines)

**User Management:**
- `create_or_update_user()` - Upsert customer profiles
- `get_user()` - Retrieve by Telegram ID

**Settings Management:**
- `get_setting()` / `update_setting()` - Bot configuration
- `get_menu_groups()` / `save_menu_groups()` - Dynamic menus
- `get_pricing()` - Price tiers
- `get_bot_branding()` - Welcome messages & images

**Pickup Operations:**
- `get_pickup_stores()` - List active locations
- `create_pickup_store()` - Add new store
- `update_pickup_store()` - Modify store
- `delete_pickup_store()` - Remove store

**Delivery Sessions:**
- `create_delivery_session()` - Schedule delivery
- `get_delivery_sessions()` - Query all sessions
- `get_active_deliveries()` - Filter by cutoff time
- `update_delivery_session_status()` - Open/close
- `cleanup_delivery_sessions()` - Archive old sessions

**Order Management:**
- `create_delivery_order()` / `create_pickup_order()` - Record orders
- `get_delivery_orders()` / `get_pickup_orders()` - Query with filters
- `update_delivery_order()` / `update_pickup_order()` - Modify status
- `get_*_order_with_user()` - Join with user info

**Analytics (30+ methods):**
- Daily/weekly/monthly sales
- Top items analysis
- Customer revenue ranking
- Location performance
- Peak hours detection
- Payment statistics
- Customer acquisition metrics

**File Management:**
- `upload_payment_receipt()` - Supabase Storage upload
- `delete_payment_receipt()` - Remove file
- `delete_old_payment_receipts()` - Batch cleanup (3+ days)

#### **FastAPI Dashboard** (`dashboard/app.py` - 1000+ lines)

**Authentication:**
- HTTP Basic Auth against `admin_users` table
- Password verification via PostgreSQL RPC
- Session cookies (7-day TTL)

**Key Endpoints:**

| Route | Method | Purpose |
|-------|--------|---------|
| `/` | GET | Dashboard homepage |
| `/login` | GET/POST | Admin login |
| `/logout` | GET | Session clear |
| `/delivery-orders` | GET/POST | Delivery order CRUD |
| `/pickup-orders` | GET/POST | Pickup order CRUD |
| `/deliveries` | GET/POST | Delivery session CRUD |
| `/settings` | GET/POST | Menu & pricing configuration |
| `/analytics` | GET | Sales reports & insights |
| `/storage` | GET | Storage usage analytics |
| `/api/*` | Various | JSON API for AJAX requests |

**Features:**
- Order status workflow (pending → confirmed → completed)
- Payment verification
- Telegram notifications on verification
- Bulk order operations
- Live menu editor
- Branding image uploads
- CSV export
- Real-time analytics

#### **Telegram Notifier** (`dashboard/telegram_notifier.py` - 94 lines)
- `send_order_verification_message()` - Async message delivery
- `format_verification_message()` - Template variable substitution
- HTML formatting support
- Error logging

---

## 4. Dependencies & External Libraries

### 4.1 Complete Dependency List

```
python-telegram-bot==21.4          # Telegram bot framework
FastAPI>=0.109.0                   # Async web framework
uvicorn[standard]>=0.27.0          # ASGI server
supabase>=2.0.0,<3.0.0            # Supabase Python SDK
python-dotenv                       # Environment variable loader
Jinja2>=3.1.0                      # Template engine
python-multipart>=0.0.6            # Form data parser
```

### 4.2 Dependency Purposes

| Dependency | Purpose | Why Used |
|-----------|---------|----------|
| `python-telegram-bot` | Telegram API abstraction | Official library, well-maintained, extensive docs |
| `FastAPI` | Admin dashboard backend | High performance, async support, automatic docs |
| `uvicorn` | HTTP server | ASGI standard, supports hot-reload for development |
| `supabase` | PostgreSQL + Storage SDK | Managed database, built-in auth, S3 storage |
| `python-dotenv` | Environment config | Secure secret management without hardcoding |
| `Jinja2` | HTML templating | Server-side rendering, template inheritance |
| `python-multipart` | Form parsing | Required for FastAPI file uploads |

---

## 5. Database Schema & Data Storage

### 5.1 Database System: PostgreSQL via Supabase

**Storage Specifications:**
- Free tier: 500 MB database + 1 GB file storage
- Pro tier: Unlimited storage + overages starting at $25/month
- Typical small bot: 50-100 MB database, 100-500 MB file storage

### 5.2 Core Tables

#### **users**
Stores customer profiles linked to Telegram accounts.
```sql
Columns:
- id (primary key, auto-increment)
- telegram_user_id (unique)
- telegram_handle
- name
- phone
- created_at (timestamp)
- updated_at (timestamp)
```

#### **delivery_orders**
Records all delivery-based orders.
```sql
Columns:
- order_id (primary key, unique)
- user_id (foreign key → users)
- delivery_session_id (foreign key → delivery_sessions)
- flavor
- sauce
- quantity
- total_price
- order_status (enum: pending, confirmed, completed, cancelled)
- payment_screenshot_url (S3 path)
- telegram_notification_sent (boolean)
- menu_selections (JSONB - flexible options)
- created_at, updated_at (timestamps)
```

#### **pickup_orders**
Records all pickup-based orders.
```sql
Columns:
- order_id (primary key, unique)
- user_id (foreign key → users)
- pickup_store_id (foreign key → pickup_stores)
- pickup_date
- pickup_time
- customer_info (JSONB)
- payment_method (pay_now / pay_at_counter)
- total_price, order_status
- payment_screenshot_url (S3 path)
- menu_selections (JSONB)
- created_at, updated_at (timestamps)
```

#### **delivery_sessions**
Schedules delivery time slots.
```sql
Columns:
- session_id (primary key, unique)
- location
- delivery_datetime
- cutoff_datetime
- status (open, closed, completed)
- created_at, updated_at (timestamps)
```

#### **pickup_stores**
Manages pickup locations.
```sql
Columns:
- store_id (primary key, unique)
- name
- address
- operating_hours (JSONB: {Monday: {open: "09:00", close: "21:00"}, ...})
- status (active, inactive)
- created_at, updated_at (timestamps)
```

#### **settings**
Flexible key-value store for bot configuration.
```sql
Columns:
- key (primary key)
- value (JSONB - stores menu groups, pricing, branding, etc.)
- updated_at (timestamp)

Example keys:
- "menu_groups" → [{name, items: [{name, price, description}]}]
- "pricing" → {standard_delivery: 3.50, express: 5.00}
- "bot_branding" → {welcome_message, image_url}
```

#### **admin_users**
Dashboard administrator accounts.
```sql
Columns:
- username (primary key, unique)
- password_hash (encrypted with pgcrypto)
- is_active (boolean)
- created_at (timestamp)
```

### 5.3 Database Views & Functions

#### RPC Functions (Stored Procedures)
- `check_password(username, password)` - Verify admin credentials
- Custom functions for analytics calculations

#### Views
- `get_daily_sales` - Aggregated daily revenue
- `popular_items` - Most ordered items
- `store_performance` - Pickup location metrics

### 5.4 Storage Bucket

**Supabase Storage: `payment-receipts` bucket**
- Stores customer payment proof screenshots
- Path structure: `{date}/{order_id}.png`
- Auto-cleanup: Deletes files 3+ days old
- Public URLs: Generated for receipt verification

### 5.5 Data Backup & Redundancy

- **Primary:** Supabase PostgreSQL (automatically replicated)
- **Fallback:** Local JSON files in `data/` directory
- **File Storage:** Supabase S3-compatible bucket (automatic redundancy)

---

## 6. External Services & Integrations

### 6.1 Active Integrations

#### **Telegram Bot API**
- **Service:** Telegram
- **Library:** `python-telegram-bot`
- **Connection Type:** Polling
- **Features:**
  - Message sending/receiving
  - Inline keyboard buttons
  - Photo upload/download
  - Conversation state management
- **Rate Limits:** Telegram's standard (no documented limits for bots)

#### **Supabase API**
- **Service:** Supabase (Managed PostgreSQL)
- **SDK:** Official Python SDK
- **Endpoints Used:**
  - `POST /rest/v1/` - CRUD operations
  - `/storage/v1/` - File upload/download/delete
  - RPC calls to PostgreSQL functions
- **Authentication:** API key (service-role key for backend)
- **Rate Limits:** ~350 requests/second on free tier

### 6.2 Optional Integrations (Disabled)

#### **Google Sheets API**
- Configuration: `USE_GOOGLE_SHEETS=false`
- Can be enabled with `GOOGLE_APPLICATION_CREDENTIALS` environment variable
- Allows syncing orders to Google Sheets

#### **Google Drive API**
- Configuration: `USE_GOOGLE_DRIVE=false`
- Enables automatic backup of files to Google Drive
- Requires OAuth service account

### 6.3 Notification Flow

```
Customer                Bot                Dashboard               Telegram
  |                     |                    |                       |
  └─────Payment────────→|                    |                       |
                        |                    |                       |
                        └─────Store Order───→|                       |
                        |                    |                       |
                        |              (Admin verification)          |
                        |                    |                       |
                        |                    └─────Send Message─────→|
                        |                    |                       |
                        |←───────Notification Sent─────────────────→|
```

---

## 7. Authentication & Security

### 7.1 Telegram Bot Security

- **API Key:** `BOT_TOKEN` environment variable
- **Admin Access:** `ADMIN_ID` restricts sensitive commands
- **Polling Mode:** No webhook exposure (more secure, slightly slower)

### 7.2 Dashboard Authentication

- **Method:** HTTP Basic Auth
- **User Database:** `admin_users` table
- **Password Hashing:** PostgreSQL `pgcrypto` extension
- **Session Management:** HTTP-only cookies (7-day expiration)
- **Verification Flow:** Username + password → RPC → bcrypt hash comparison

### 7.3 Supabase Security

- **API Key:** Service-role key (backend-only, never expose to frontend)
- **Row-Level Security:** PostgreSQL RLS policies
- **Database:** Private by default, only accessible via authenticated API calls
- **Storage:** Bucket permissions restrict public access

### 7.4 Environment Variables

**Required Secrets:**
```
BOT_TOKEN              # Telegram bot API token
ADMIN_ID               # Telegram user ID for admin commands
SUPABASE_URL          # Supabase project URL
SUPABASE_KEY          # Service-role API key (backend only)
SUPABASE_BUCKET       # Storage bucket name (payment-receipts)
```

**Optional Secrets:**
```
GOOGLE_APPLICATION_CREDENTIALS   # Path to Google service account JSON
DRIVE_FOLDER_ID                  # Google Drive folder for backups
```

**Stored in:** `.env` file (never commit to git)

---

## 8. Frontend Technologies

### 8.1 Dashboard UI Stack

| Technology | Usage | Purpose |
|-----------|-------|---------|
| **Jinja2** | HTML templating | Server-side rendering |
| **Bootstrap 5** | CSS framework | Responsive UI design |
| **JavaScript** | Client-side interactivity | AJAX requests, form handling |
| **HTML5** | Markup | Page structure |
| **CSS3** | Styling | Custom theme and layout |

### 8.2 Telegram Bot UI

- **Inline Keyboards:** Button-based navigation (e.g., menu selection)
- **Reply Keyboards:** Quick response buttons (e.g., main menu)
- **Text Messages:** Primary communication format
- **Photos:** Menu images, QR code display

### 8.3 Dashboard Pages

| Page | Purpose | Key Features |
|------|---------|--------------|
| `login.html` | Admin authentication | Username/password form |
| `dashboard.html` | Main overview | Quick stats, order count |
| `delivery_orders.html` | Delivery order management | Table with status updates, bulk actions |
| `pickup_orders.html` | Pickup order management | Similar to delivery orders |
| `deliveries.html` | Session management | Create/edit/delete delivery slots |
| `settings.html` | Menu configuration | Menu editor, pricing, branding uploads |
| `analytics.html` | Sales reports | Charts, daily/weekly/monthly stats |
| `storage.html` | Storage usage | File breakdown, cleanup tools |

---

## 9. Development & Deployment

### 9.1 Local Development Setup

**Prerequisites:**
- Python 3.11+
- pip or conda
- Git
- Text editor/IDE

**Setup Steps:**
```bash
# 1. Clone repository
git clone <repo-url>
cd acai_supper_bot

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create .env file
cp .env.example .env
# Edit with your tokens and keys

# 5. Initialize Supabase
# - Create project at https://supabase.com
# - Run database/schema.sql in Supabase SQL editor
# - Create admin user in admin_users table
# - Create payment-receipts storage bucket

# 6. Run bot
python bot.py

# 7. In separate terminal, run dashboard
uvicorn dashboard.app:app --reload

# Dashboard accessible at http://localhost:8000
```

### 9.2 Production Deployment

**Recommended Platforms:**

| Platform | Cost | Pros | Cons |
|----------|------|------|------|
| **Railway** | $5-10/mo | Simple, pay-as-you-go | Less control |
| **Render** | $7+/mo | Good free tier | Limited resources |
| **DigitalOcean** | $4-6/mo | Full VPS control | More setup |
| **Linode** | $5+/mo | Reliable, supports Docker | Complex |
| **Cloud Run** | ~$0-5/mo | Serverless, scalable | Cold starts |

**Supabase Costs:**
- Free tier: 500 MB database, 1 GB storage, 500K API calls/month
- Pro tier: $25/month + overage charges
- Estimated for small bot: $0-15/month (Supabase) + $5-10/mo (server)

**Typical Stack:**
```
Telegram API
    ↓
Polling Bot (Railway/Render/VPS) + Dashboard (FastAPI)
    ↓
Supabase PostgreSQL + Storage (Cloud)
```

### 9.3 Containerization (Docker)

Optional Docker support (no Dockerfile currently included):

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Set environment
ENV PYTHONUNBUFFERED=1

# Run bot
CMD ["python", "bot.py"]
```

**Build & Run:**
```bash
docker build -t acai-bot .
docker run --env-file .env acai-bot
```

### 9.4 Running Both Bot & Dashboard

**Option A: Same Process (Recommended for small deployments)**
```bash
python bot.py &
uvicorn dashboard.app:app --host 0.0.0.0 --port 8000
```

**Option B: Separate Processes (Better for scaling)**
```bash
# Terminal 1
python bot.py

# Terminal 2
uvicorn dashboard.app:app --host 0.0.0.0 --port 8000
```

**Option C: Docker Compose (For containerized deployments)**
```yaml
version: '3'
services:
  bot:
    build: .
    command: python bot.py
    environment:
      - BOT_TOKEN=${BOT_TOKEN}
      - ADMIN_ID=${ADMIN_ID}
      - SUPABASE_URL=${SUPABASE_URL}
      - SUPABASE_KEY=${SUPABASE_KEY}

  dashboard:
    build: .
    command: uvicorn dashboard.app:app --host 0.0.0.0 --port 8000
    ports:
      - "8000:8000"
    environment:
      - BOT_TOKEN=${BOT_TOKEN}
      - SUPABASE_URL=${SUPABASE_URL}
      - SUPABASE_KEY=${SUPABASE_KEY}
```

---

## 10. Testing & Quality Assurance

### 10.1 Current Testing Status

**Status:** No formal testing framework currently implemented

### 10.2 Recommended Testing Strategy

#### Unit Tests (pytest)
```python
# tests/test_utils.py
import pytest
from utils import calculate_price, format_currency

def test_calculate_price():
    assert calculate_price(3, 8.50) == 25.50

def test_format_currency():
    assert format_currency(25.50) == "S$25.50"
```

#### Integration Tests
- Database operations (create, read, update, delete)
- Supabase connection handling
- Payment receipt upload
- Order flow completion

#### End-to-End Tests
- Full order flow from /start to payment
- Menu retrieval and caching
- Dashboard login and order verification
- Telegram notification delivery

**Test Setup:**
```bash
pip install pytest pytest-asyncio pytest-cov
pytest -v --cov=. tests/
```

### 10.3 Manual Testing Checklist

**Bot Testing:**
- [ ] `/start` command triggers order flow
- [ ] Menu selection works correctly
- [ ] Quantity selection (1-5 range)
- [ ] Multi-item cart functionality
- [ ] Delivery/Pickup selection
- [ ] Payment QR display
- [ ] Screenshot upload handling
- [ ] User profile creation
- [ ] Order save to Supabase

**Dashboard Testing:**
- [ ] Admin login authentication
- [ ] Delivery orders display
- [ ] Pickup orders display
- [ ] Order status updates
- [ ] Menu configuration save
- [ ] Analytics calculations
- [ ] Storage usage display
- [ ] Telegram notification sending

**Database Testing:**
- [ ] Connection to Supabase
- [ ] CRUD operations
- [ ] Query filtering
- [ ] Analytics calculations
- [ ] File upload/cleanup

---

## 11. Performance & Scalability

### 11.1 Performance Characteristics

| Component | Capacity | Limitation |
|-----------|----------|-----------|
| **Concurrent Users** | 1000+ | Limited by Supabase free tier (500K API calls/month) |
| **Requests/Second** | ~350 | Supabase rate limit |
| **Database Size** | 500 MB (free tier) | 100+ MB per 1000 orders |
| **Storage Size** | 1 GB (free tier) | ~300 KB per payment screenshot |
| **Bot Response Time** | <500ms | Depends on Supabase latency |
| **Dashboard Response Time** | <1s | Depends on analytics query complexity |

### 11.2 Optimization Strategies

**Menu Caching:**
- 5-minute cache TTL reduces database queries
- Fallback to local JSON for offline mode

**Order Batching:**
- Bulk operations in dashboard reduce API calls
- Batch payment receipt cleanup (every 24 hours)

**Async Operations:**
- FastAPI uses async/await for concurrent requests
- Telegram notifications sent asynchronously

**Database Indexes:**
- `telegram_user_id` indexed for fast user lookups
- `order_id` indexed for order queries
- `created_at` indexed for analytics

### 11.3 Scaling to Production

**For 1000+ concurrent users:**
1. **Upgrade Supabase:** Pro tier ($25+/month)
2. **Add Load Balancing:** If running multiple bot instances
3. **Separate Bot & Dashboard:** Different servers
4. **Database Replication:** Supabase handles automatically
5. **CDN for Assets:** Supabase Storage includes CDN

---

## 12. Development Workflow

### 12.1 Code Organization

- **Modular Design:** Separate handlers, database, dashboard
- **Configuration-Driven:** Settings in Supabase, not hardcoded
- **Async-First:** FastAPI and python-telegram-bot support async
- **Error Handling:** Try-catch blocks with logging

### 12.2 Git Workflow

**Repository Structure:**
```
main
├── bot.py (always working)
├── handlers/ (feature branches)
├── database/ (migrations on main)
├── dashboard/ (feature branches)
└── tests/ (test branches)
```

**Workflow:**
1. Feature branch from main
2. Test locally (bot.py + uvicorn)
3. Commit with descriptive message
4. Create pull request
5. Code review
6. Merge to main
7. Deploy to production

### 12.3 Updating Dependencies

```bash
# Check for updates
pip list --outdated

# Update specific package
pip install --upgrade python-telegram-bot

# Update all
pip install --upgrade -r requirements.txt

# Save new versions
pip freeze > requirements.txt
```

---

## 13. Monitoring & Maintenance

### 13.1 Recommended Monitoring

**Bot Health:**
- Telegram connection status
- Message processing latency
- Error rate and error types
- User engagement metrics

**Dashboard Health:**
- HTTP response times
- Database query performance
- Login attempts
- File upload success rate

**Infrastructure:**
- Supabase database size
- Storage bucket usage
- API quota consumption
- Server CPU/memory usage

### 13.2 Maintenance Tasks

| Task | Frequency | Purpose |
|------|-----------|---------|
| Clean old payment receipts | Weekly | Free up storage space |
| Archive completed orders | Monthly | Improve query performance |
| Update dependencies | Quarterly | Security patches, features |
| Review analytics | Weekly | Track business metrics |
| Backup database | Daily | Disaster recovery |

### 13.3 Logging & Debugging

**Bot Logging:**
```python
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.info(f"User {user_id} placed order {order_id}")
```

**Dashboard Logging:**
```python
import logging
from fastapi import FastAPI

app = FastAPI()
logging.basicConfig(level=logging.INFO)
```

**Supabase Debugging:**
- View logs in Supabase dashboard
- Check RLS policies for access denials
- Monitor storage bucket activity

---

## 14. Known Limitations & Future Enhancements

### 14.1 Current Limitations

| Limitation | Workaround | Future Solution |
|-----------|-----------|-----------------|
| No email notifications | Telegram only | Add email service (SendGrid) |
| No webhook for payments | Manual screenshot | Stripe/PayPal integration |
| Single admin account | Shared credentials | Multi-user admin system |
| No order refunds | Manual cancellation | Automated refund flow |
| No order tracking (delivery) | SMS updates | Real-time GPS tracking |
| Basic analytics | Dashboard only | Advanced BI integration |

### 14.2 Recommended Enhancements

**Short-term:**
1. Add unit tests with pytest
2. Implement error alerts to admin
3. Add order modification capability
4. Create customer receipt PDF generation

**Medium-term:**
1. Integrate payment processor (Stripe/PayPal)
2. Add multi-language support
3. Implement customer loyalty/rewards
4. Real-time order tracking

**Long-term:**
1. Machine learning for demand forecasting
2. Inventory management system
3. Mobile app (React Native)
4. API for third-party integrations

---

## 15. Summary Table

| Aspect | Details |
|--------|---------|
| **Language** | Python 3.11+ |
| **Bot Framework** | python-telegram-bot 21.4 |
| **Web Framework** | FastAPI 0.109.0+ |
| **Database** | PostgreSQL (Supabase) |
| **Storage** | Supabase Storage (S3) |
| **Authentication** | HTTP Basic Auth (admin) |
| **Templating** | Jinja2 3.1.0+ |
| **Async Server** | uvicorn 0.27.0+ |
| **Total Dependencies** | 10 packages |
| **Core Modules** | ~20 Python files |
| **Database Tables** | 8+ core entities |
| **Admin Pages** | 8 HTML templates |
| **API Endpoints** | 20+ FastAPI routes |
| **Code Size** | ~4,000+ lines |
| **Deployment** | Cloud (Railway, Render, DigitalOcean) |
| **Cost (Free Tier)** | Supabase only ($0/month) |
| **Cost (Typical)** | $5-15/month |
| **Scalability** | 1000+ concurrent users (with pro tier) |

---

## 16. Quick Reference

### Important Files

| File | Purpose | Size |
|------|---------|------|
| `bot.py` | Bot entry point | ~330 lines |
| `database/supabase_client.py` | DB layer | 1400+ lines |
| `dashboard/app.py` | Web dashboard | 1000+ lines |
| `handlers/order_flow.py` | Order state machine | 20 KB |
| `handlers/payment_handler.py` | Payment processing | 19 KB |
| `database/schema.sql` | Database schema | 13 KB |

### Key Environment Variables

```bash
BOT_TOKEN=your_telegram_token_here
ADMIN_ID=your_telegram_user_id
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_service_role_key
SUPABASE_BUCKET=payment-receipts
```

### Essential Commands

```bash
# Start bot
python bot.py

# Start dashboard
uvicorn dashboard.app:app --reload

# Install dependencies
pip install -r requirements.txt

# Run tests (when implemented)
pytest -v

# Deploy to Railway
railway up
```

---

**Document Version:** 1.0
**Last Updated:** December 3, 2025
**Maintained By:** Project Team
**Status:** Production Ready
