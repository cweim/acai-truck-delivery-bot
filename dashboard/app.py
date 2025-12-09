"""
FastAPI Admin Dashboard Backend for Acai Supper Bot
"""
import base64
import os
import re
from datetime import datetime, date, timedelta
import uuid
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException, Depends, status, Request, Form, UploadFile, File, Body
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.security import HTTPBasicCredentials
from pydantic import BaseModel
import secrets
import csv
from io import StringIO
import sys

# Add parent directory and current directory to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)
sys.path.insert(0, current_dir)

from database.supabase_client import get_db, SupabaseDB
from menu import invalidate_menu_cache, invalidate_branding_cache
from telegram_notifier import send_order_verification_message, format_verification_message, send_broadcast_message

# Helper function to normalize location names for deduplication
def normalize_location(location: str) -> str:
    """Normalize location name by stripping whitespace and converting to title case for display."""
    return location.strip().title() if location else ''

# Initialize FastAPI app
app = FastAPI(
    title="Acai Supper Bot Admin Dashboard",
    description="Admin dashboard for managing orders, settings, and analytics",
    version="1.0.0"
)

BRANDING_IMAGE_ALLOWED_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.webp'}
BRANDING_IMAGE_MAX_BYTES = 2 * 1024 * 1024

# Security / Sessions
SESSION_COOKIE_NAME = "acai_admin_session"
SESSION_MAX_AGE = 60 * 60 * 24 * 7  # 7 days
active_sessions: Dict[str, Dict[str, Any]] = {}

# Templates
templates = Jinja2Templates(directory="dashboard/templates")

# Static files
app.mount("/static", StaticFiles(directory="dashboard/static"), name="static")

# ==================== AUTHENTICATION ====================

def parse_basic_credentials(request: Request) -> Optional[HTTPBasicCredentials]:
    """Parse HTTP Basic credentials manually so we can redirect instead of 401 when missing."""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Basic "):
        return None
    try:
        decoded = base64.b64decode(auth_header.split(" ", 1)[1]).decode("utf-8")
        username, password = decoded.split(":", 1)
        return HTTPBasicCredentials(username=username, password=password)
    except Exception:
        return None


def authenticate_admin(username: str, password: str) -> Dict[str, Any]:
    """Validate admin username/password against Supabase and return the admin record."""
    db = get_db()

    try:
        print(f"[AUTH] Attempting login for username: {username}")

        response = db.client.table('admin_users').select('*').eq('username', username).eq('is_active', True).execute()

        if not response.data:
            print(f"[AUTH] User '{username}' not found or inactive")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password",
                headers={"WWW-Authenticate": "Basic"},
            )

        print(f"[AUTH] User found: {username}")
        admin_user = response.data[0]

        # Verify password (using pgcrypto crypt comparison)
        print(f"[AUTH] Calling check_password RPC for user: {username}")
        try:
            password_check = db.client.rpc('check_password', {
                'username': username,
                'password': password
            }).execute()

            print(f"[AUTH] RPC response: {password_check}")
            print(f"[AUTH] Password check data: {password_check.data}")

            if not password_check.data:
                print(f"[AUTH] Password verification failed for user: {username}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid username or password",
                    headers={"WWW-Authenticate": "Basic"},
                )
        except Exception as rpc_error:
            print(f"[AUTH] RPC Error: {str(rpc_error)}")
            raise

        print(f"[AUTH] Authentication successful for user: {username}")

        # Update last login
        db.client.table('admin_users').update({
            'last_login': datetime.now().isoformat()
        }).eq('username', username).execute()

        return admin_user

    except HTTPException:
        raise
    except Exception as e:
        print(f"[AUTH] Exception: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication error: {str(e)}",
            headers={"WWW-Authenticate": "Basic"},
        )


def verify_admin_credentials(request: Request):
    """
    Verify admin via session cookie first, then fall back to HTTP Basic credentials.
    Redirects to /login instead of immediately returning 401 when no credentials are present.
    """
    session_token = request.cookies.get(SESSION_COOKIE_NAME)
    if session_token and session_token in active_sessions:
        return active_sessions[session_token]

    credentials = parse_basic_credentials(request)
    if credentials:
        return authenticate_admin(credentials.username, credentials.password)

    # No credentials supplied – send to login page
    raise HTTPException(
        status_code=status.HTTP_307_TEMPORARY_REDIRECT,
        detail="Redirecting to login",
        headers={"Location": "/login"},
    )

# ==================== PYDANTIC MODELS ====================

class DeliverySessionCreate(BaseModel):
    location: str
    delivery_datetime: datetime
    cutoff_time: datetime

class SettingUpdate(BaseModel):
    value: Any


class MenuGroup(BaseModel):
    id: Optional[str] = None
    title: str
    options: List[Any]


class MenuGroupsUpdate(BaseModel):
    groups: List[MenuGroup]


class BrandingUpdate(BaseModel):
    title: str
    subtitle: str
    image_url: Optional[str] = None

class VerificationMessageUpdate(BaseModel):
    message: str


def slugify(value: str, prefix: str) -> str:
    base = re.sub(r'[^a-z0-9]+', '-', value.lower()).strip('-')
    return base or prefix


def unique_slug(value: str, existing: set, prefix: str) -> str:
    base = slugify(value, prefix)
    slug = base
    counter = 2
    while slug in existing:
        slug = f"{base}-{counter}"
        counter += 1
    existing.add(slug)
    return slug

class OrderStatusUpdate(BaseModel):
    status: str

class PaymentStatusUpdate(BaseModel):
    payment_status: str

# ==================== DASHBOARD PAGES ====================

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Render login screen if not already authenticated."""
    session_token = request.cookies.get(SESSION_COOKIE_NAME)
    if session_token and session_token in active_sessions:
        return RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)

    return templates.TemplateResponse(
        "login.html",
        {
            "request": request,
            "error": None,
        },
    )


@app.post("/login", response_class=HTMLResponse)
async def handle_login(request: Request, username: str = Form(...), password: str = Form(...)):
    """Process login form, set session cookie, and redirect to dashboard."""
    try:
        admin_user = authenticate_admin(username, password)
    except HTTPException as exc:
        return templates.TemplateResponse(
            "login.html",
            {
                "request": request,
                "error": "Invalid username or password",
            },
            status_code=status.HTTP_401_UNAUTHORIZED if exc.status_code == status.HTTP_401_UNAUTHORIZED else status.HTTP_400_BAD_REQUEST,
        )

    session_token = secrets.token_urlsafe(32)
    active_sessions[session_token] = admin_user

    response = RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(
        SESSION_COOKIE_NAME,
        session_token,
        max_age=SESSION_MAX_AGE,
        httponly=True,
        samesite="lax",
    )
    return response


@app.get("/logout")
async def logout(request: Request):
    """Clear session cookie and redirect to login."""
    session_token = request.cookies.get(SESSION_COOKIE_NAME)
    response = RedirectResponse("/login", status_code=status.HTTP_303_SEE_OTHER)
    if session_token:
        active_sessions.pop(session_token, None)
        response.delete_cookie(SESSION_COOKIE_NAME)
    return response


@app.get("/", response_class=HTMLResponse)
async def dashboard_home(request: Request, admin: Dict = Depends(verify_admin_credentials)):
    """Analytics dashboard - Landing page"""
    db = get_db()

    # Get last 30 days date range
    end_date = date.today()
    start_date = end_date - timedelta(days=30)

    # Get all available delivery sessions (with location info) - no status filter to show all locations
    all_sessions = db.get_delivery_sessions(status='')  # Empty string to get all sessions
    all_locations = sorted(list(set(s.get('location', '') for s in all_sessions if s.get('location', ''))))

    # Existing analytics
    daily_sales = db.get_daily_sales_summary(start_date, end_date)
    weekly_sales = db.get_weekly_sales_summary(start_date, end_date)
    monthly_sales = db.get_monthly_sales_summary(start_date, end_date)
    popular_items = db.get_popular_items(limit=10)
    store_performance = db.get_store_performance()

    # Calculate summary metrics (filtered to last 30 days)
    delivery_orders_30d = db.get_delivery_orders(limit=5000)

    # Filter to last 30 days
    delivery_orders_filtered = [o for o in delivery_orders_30d
                                if o.get('created_at', '').startswith(tuple(
                                    (start_date + timedelta(days=i)).isoformat() for i in range(31)
                                )) and o['order_status'] != 'cancelled']

    total_revenue = sum([float(o.get('total_price', 0)) for o in delivery_orders_filtered])
    total_orders = len(delivery_orders_filtered)
    avg_order_value = total_revenue / total_orders if total_orders > 0 else 0
    delivery_count = len(delivery_orders_filtered)

    # NEW ANALYTICS
    top_customers = db.get_top_customers(start_date, end_date, limit=10)
    # Global leaderboard (ignore location/date filter for completeness)
    top_delivery_sessions = db.get_top_delivery_sessions(limit=10)
    peak_hours = db.get_peak_hours_analysis(start_date, end_date)
    payment_stats = db.get_payment_method_stats(start_date, end_date)
    customer_acquisition = db.get_customer_acquisition_stats(start_date, end_date)

    context = {
        "request": request,
        "admin": admin,
        "date_range": f"{start_date.strftime('%b %d, %Y')} - {end_date.strftime('%b %d, %Y')}",
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "days_back": 30,
        "selected_location": "",
        "all_locations": all_locations,

        # Summary metrics
        "total_revenue": total_revenue,
        "total_orders": total_orders,
        "avg_order_value": avg_order_value,
        "delivery_orders_count": delivery_count,

        # Existing analytics
        "daily_sales": daily_sales,
        "weekly_sales": weekly_sales,
        "monthly_sales": monthly_sales,
        "popular_items": popular_items,

        # New analytics
        "top_customers": top_customers,
        "top_delivery_sessions": top_delivery_sessions,
        "peak_hours": peak_hours,
        "payment_stats": payment_stats,
        "customer_acquisition": customer_acquisition,
    }

    return templates.TemplateResponse("analytics.html", context)

@app.get("/delivery-orders", response_class=HTMLResponse)
async def delivery_orders_page(request: Request, admin: Dict = Depends(verify_admin_credentials)):
    """Delivery orders page"""
    db = get_db()
    sessions = db.get_delivery_sessions()
    selected_session = None
    for session in sessions:
        if session.get('status') == 'open':
            selected_session = session
            break
    if not selected_session and sessions:
        selected_session = sessions[0]

    context = {
        "request": request,
        "admin": admin,
        "sessions": sessions,
        "selected_session": selected_session
    }

    return templates.TemplateResponse("delivery_orders.html", context)

@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request, admin: Dict = Depends(verify_admin_credentials)):
    """Settings page"""
    db = get_db()

    # Get all settings
    menu_groups = db.get_menu_groups()
    branding = db.get_bot_branding()
    verification_setting = db.get_setting('order_verification_message')
    default_verification = "Hi {customer_name}, your order #{order_id} has been confirmed! Total: {total_price}. Thank you!"
    if isinstance(verification_setting, dict):
        verification_message = verification_setting.get('message', default_verification)
    elif isinstance(verification_setting, str):
        verification_message = verification_setting or default_verification
    else:
        verification_message = default_verification

    context = {
        "request": request,
        "admin": admin,
        "menu_groups": menu_groups,
        "branding": branding,
        "verification_message": verification_message
    }

    return templates.TemplateResponse("settings.html", context)

@app.get("/deliveries", response_class=HTMLResponse)
async def deliveries_page(request: Request, admin: Dict = Depends(verify_admin_credentials)):
    """Delivery sessions management page"""
    db = get_db()

    # Get all delivery sessions
    sessions = db.get_delivery_sessions()

    # Add revenue data to each session
    for session in sessions:
        session['revenue'] = db.get_session_revenue(session['id'])

    context = {
        "request": request,
        "admin": admin,
        "sessions": sessions,
        "now": datetime.now().isoformat()
    }

    return templates.TemplateResponse("deliveries.html", context)

@app.get("/analytics", response_class=HTMLResponse)
async def analytics_page(request: Request, admin: Dict = Depends(verify_admin_credentials)):
    """Analytics page - Last 30 days data with location filtering support"""
    db = get_db()

    # Get date range from query params or use last 30 days
    days_param = request.query_params.get('days', '30')
    try:
        days_back = int(days_param)
    except:
        days_back = 30

    end_date = date.today()
    start_date = end_date - timedelta(days=days_back)

    # Get location filter from query params
    selected_location = request.query_params.get('location', '')

    # Get all available delivery sessions (with location info) - no status filter to show all locations
    all_sessions = db.get_delivery_sessions(status='')  # Empty string to get all sessions
    # Deduplicate locations: normalize (strip whitespace, title case) and extract unique location names
    all_locations = sorted(list(set(normalize_location(s.get('location', '')) for s in all_sessions if s.get('location', ''))))

    # Existing analytics - use location filter if provided
    if selected_location and selected_location in all_locations:
        daily_sales = db.get_location_daily_sales(selected_location, start_date, end_date)
        popular_items = db.get_location_popular_items(selected_location, start_date, end_date, limit=10)
        top_customers = db.get_location_top_customers(selected_location, start_date, end_date, limit=10)
    else:
        daily_sales = db.get_daily_sales_summary(start_date, end_date)
        popular_items = db.get_popular_items(limit=10)
        top_customers = db.get_top_customers(start_date, end_date, limit=10)

    # Get weekly and monthly sales summaries
    weekly_sales = db.get_weekly_sales_summary(start_date, end_date)
    monthly_sales = db.get_monthly_sales_summary(start_date, end_date)

    store_performance = db.get_store_performance()
    # Leaderboard is global (not filtered by location) and not limited by date range
    top_delivery_sessions = db.get_top_delivery_sessions(limit=10)
    peak_hours = db.get_peak_hours_analysis(start_date, end_date)
    payment_stats = db.get_payment_method_stats(start_date, end_date)
    customer_acquisition = db.get_customer_acquisition_stats(start_date, end_date)

    # Calculate summary metrics
    delivery_orders_all = db.get_delivery_orders(limit=5000)

    # Filter to date range
    delivery_orders_filtered = [o for o in delivery_orders_all
                                if o.get('created_at', '').startswith(tuple(
                                    (start_date + timedelta(days=i)).isoformat() for i in range(days_back + 1)
                                )) and o['order_status'] != 'cancelled']

    # If location filter is applied, filter delivery orders by location
    if selected_location and selected_location in all_locations:
        location_sessions = db.get_delivery_sessions()
        # Match sessions by normalized location name
        location_session_ids = {s['id'] for s in location_sessions if normalize_location(s.get('location', '')) == selected_location}
        delivery_orders_filtered = [o for o in delivery_orders_filtered if o.get('delivery_session_id') in location_session_ids]

    total_revenue = sum([float(o.get('total_price', 0)) for o in delivery_orders_filtered])
    total_orders = len(delivery_orders_filtered)
    avg_order_value = total_revenue / total_orders if total_orders > 0 else 0
    delivery_count = len(delivery_orders_filtered)

    context = {
        "request": request,
        "admin": admin,
        "date_range": f"{start_date.strftime('%b %d, %Y')} - {end_date.strftime('%b %d, %Y')}",
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "days_back": days_back,
        "selected_location": selected_location,
        "all_locations": all_locations,

        # Summary metrics
        "total_revenue": total_revenue,
        "total_orders": total_orders,
        "avg_order_value": avg_order_value,
        "delivery_orders_count": delivery_count,

        # Analytics
        "daily_sales": daily_sales,
        "weekly_sales": weekly_sales,
        "monthly_sales": monthly_sales,
        "popular_items": popular_items,
        "store_performance": store_performance,
        "top_customers": top_customers,
        "top_delivery_sessions": top_delivery_sessions,
        "peak_hours": peak_hours,
        "payment_stats": payment_stats,
        "customer_acquisition": customer_acquisition,
    }

    return templates.TemplateResponse("analytics.html", context)

@app.get("/storage", response_class=HTMLResponse)
async def storage_management_page(request: Request, admin: Dict = Depends(verify_admin_credentials)):
    """Storage Management page"""
    db = get_db()

    storage_stats = db.get_storage_stats()
    delivery_sessions_breakdown = db.get_delivery_sessions_storage_breakdown()

    context = {
        "request": request,
        "admin": admin,
        "storage_stats": storage_stats,
        "delivery_sessions": delivery_sessions_breakdown,
    }

    return templates.TemplateResponse("storage.html", context)

# ==================== API ENDPOINTS ====================

# --- Settings API ---

@app.get("/api/settings/verification-message")
async def get_verification_message_setting(admin: Dict = Depends(verify_admin_credentials)):
    """Return the current verification message template"""
    db = get_db()
    default_message = "Hi {customer_name}, your order #{order_id} has been confirmed! Total: {total_price}. Thank you!"
    setting = db.get_setting('order_verification_message')

    if isinstance(setting, dict):
        message = setting.get('message') or default_message
    elif isinstance(setting, str):
        message = setting or default_message
    else:
        message = default_message

    return {"success": True, "data": {"message": message}}


@app.put("/api/settings/verification-message")
async def update_verification_message_setting(
    update: VerificationMessageUpdate,
    admin: Dict = Depends(verify_admin_credentials)
):
    """Update the verification message used when confirming payments"""
    message = (update.message or "").strip()
    if not message:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    db = get_db()
    db.update_setting('order_verification_message', {"message": message})
    return {"success": True, "message": "Verification message updated", "data": {"message": message}}


@app.put("/api/settings/menu-groups")
async def update_menu_groups_setting(
    update: Dict[str, Any] = Body(...),
    admin: Dict = Depends(verify_admin_credentials)
):
    """Persist menu option groups (first group supports option prices)."""
    db = get_db()
    used_ids = set()
    sanitized_groups = []

    raw_groups = update.get("groups") or []
    for index, group in enumerate(raw_groups):
        title = (group.get("title") or "").strip()
        if not title:
            raise HTTPException(status_code=400, detail=f"Group {index + 1} title is required")

        raw_options = group.get("options") or []
        if index == 0:
            options = []
            for opt in raw_options:
                if isinstance(opt, dict):
                    name = (opt.get("name") or opt.get("title") or opt.get("label") or "").strip()
                    try:
                        price = float(opt.get("price", 0) or 0)
                    except Exception:
                        price = 0
                else:
                    name = str(opt).strip()
                    price = 0
                if not name:
                    continue
                options.append({"name": name, "price": price})
        else:
            options = [str(opt).strip() for opt in raw_options if str(opt).strip()]

        if not options:
            raise HTTPException(status_code=400, detail=f"{title} must include at least one option")

        group_id = (group.get("id") or "").strip() or slugify(title, f"group-{index + 1}")
        group_id = unique_slug(group_id, used_ids, f"group-{index + 1}")

        sanitized_groups.append({
            "id": group_id,
            "title": title,
            "options": options
        })

    db.save_menu_groups(sanitized_groups)
    invalidate_menu_cache()
    return {"success": True, "message": "Menu groups updated", "data": sanitized_groups}


@app.put("/api/settings/branding")
async def update_branding_setting(
    update: BrandingUpdate,
    admin: Dict = Depends(verify_admin_credentials)
):
    """Update bot branding used for the welcome message"""
    db = get_db()
    branding_payload = {
        "title": update.title.strip(),
        "subtitle": update.subtitle.strip(),
        "image_url": (update.image_url or "").strip()
    }
    db.update_bot_branding(branding_payload)
    invalidate_branding_cache()
    return {"success": True, "message": "Branding updated", "data": branding_payload}


@app.post("/api/settings/branding/image")
async def upload_branding_image(
    file: UploadFile = File(...),
    admin: Dict = Depends(verify_admin_credentials)
):
    """Upload branding hero image to Supabase storage"""
    extension = os.path.splitext(file.filename or "")[1].lower()
    if extension not in BRANDING_IMAGE_ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Unsupported file type. Use PNG, JPG, JPEG, GIF, or WebP.")

    contents = await file.read()
    if len(contents) > BRANDING_IMAGE_MAX_BYTES:
        raise HTTPException(status_code=400, detail="Image must be 2MB or smaller")

    object_name = f"branding/{uuid.uuid4().hex}{extension}"
    db = get_db()
    url = db.upload_branding_image(object_name, contents, file.content_type)
    if not url:
        raise HTTPException(status_code=500, detail="Failed to upload branding image")

    return {"success": True, "url": url}


# --- Delivery Orders API ---

@app.get("/api/delivery-orders")
async def get_delivery_orders(
    session_id: Optional[int] = None,
    payment_status: Optional[str] = None,
    admin: Dict = Depends(verify_admin_credentials)
):
    """Get delivery orders for a specific session"""
    db = get_db()
    if session_id is None:
        raise HTTPException(status_code=400, detail="session_id is required")

    filters = {"delivery_session_id": session_id}
    if payment_status:
        filters['payment_status'] = payment_status

    orders = db.get_delivery_orders(limit=500, **filters)

    session = db.get_delivery_by_id(session_id)
    session_info = {
        "id": session_id,
        "session_id": session.get('session_id') if session else None,
        "location": session.get('location') if session else None,
        "delivery_datetime": session.get('delivery_datetime') if session else None,
        "cutoff_time": session.get('cutoff_time') if session else None,
        "status": session.get('status') if session else None,
    } if session else None

    return {"success": True, "data": orders, "count": len(orders), "session": session_info}

@app.patch("/api/delivery-orders/{order_id}/status")
async def update_delivery_order_status(
    order_id: str,
    update: OrderStatusUpdate,
    admin: Dict = Depends(verify_admin_credentials)
):
    """Update delivery order status"""
    db = get_db()
    success = db.update_delivery_order(order_id, order_status=update.status)

    if success:
        return {"success": True, "message": f"Order {order_id} status updated to {update.status}"}
    else:
        raise HTTPException(status_code=400, detail="Failed to update order status")

@app.patch("/api/delivery-orders/{order_id}/payment")
async def update_delivery_payment_status(
    order_id: str,
    update: PaymentStatusUpdate,
    admin: Dict = Depends(verify_admin_credentials)
):
    """Update delivery order payment status"""
    db = get_db()
    success = db.update_delivery_order(order_id, payment_status=update.payment_status)

    if success:
        return {"success": True, "message": f"Payment status updated to {update.payment_status}"}
    else:
        raise HTTPException(status_code=400, detail="Failed to update payment status")


@app.post("/api/delivery-orders/{order_id}/verify")
async def verify_delivery_order(
    order_id: str,
    verified: bool,
    admin: Dict = Depends(verify_admin_credentials)
):
    """Mark a delivery order payment as verified/unverified"""
    db = get_db()
    status_value = 'verified' if verified else 'submitted'
    success = db.update_delivery_order(order_id, payment_status=status_value)

    if success:
        return {"success": True, "message": f"Payment status updated to {status_value}"}
    else:
        raise HTTPException(status_code=400, detail="Failed to update payment verification")


@app.post("/api/delivery-orders/{order_id}/verify-and-notify")
async def verify_and_notify_delivery_order(
    order_id: str,
    admin: Dict = Depends(verify_admin_credentials)
):
    """Mark delivery order as verified and send Telegram notification to customer"""
    db = get_db()

    # Get order with user info
    order = db.get_delivery_order_with_user(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Mark order as verified
    success = db.update_delivery_order(order_id, payment_status='verified')
    if not success:
        raise HTTPException(status_code=400, detail="Failed to verify order")

    # Get telegram user ID
    telegram_user_id = order.get('user_id')
    if not telegram_user_id:
        # Update notification status with error
        db.update_delivery_order_notification(order_id, False, "No telegram user ID found")
        return {
            "success": True,
            "message": "Order verified but notification not sent - customer has no telegram ID",
            "notification_sent": False,
            "notification_error": "No telegram user ID found"
        }

    # Get verification message template
    message_template = db.get_setting('order_verification_message')
    if not message_template:
        message_template = "Hi {customer_name}, your order #{order_id} has been confirmed! Total: {total_price}. Thank you!"
    else:
        message_template = message_template.get('message', "Hi {customer_name}, your order #{order_id} has been confirmed! Total: {total_price}. Thank you!")

    # Format message with order details
    delivery_session = order.get('delivery_session_id')
    delivery_location = None
    delivery_time = None

    if delivery_session:
        # Get session info for location and time
        session = db.client.table('delivery_sessions').select('location, delivery_datetime').eq('id', delivery_session).execute()
        if session.data:
            delivery_location = session.data[0].get('location')
            delivery_time = session.data[0].get('delivery_datetime')

    formatted_message = format_verification_message(
        message_template,
        customer_name=order.get('customer_name', 'Customer'),
        order_id=order_id,
        total_price=float(order.get('total_price', 0)),
        delivery_location=delivery_location,
        delivery_time=delivery_time
    )

    # Send telegram message
    sent, error = await send_order_verification_message(telegram_user_id, formatted_message)

    # Update notification status
    db.update_delivery_order_notification(order_id, sent, error)

    if sent:
        return {
            "success": True,
            "message": "Order verified and notification sent",
            "notification_sent": True
        }
    else:
        return {
            "success": True,
            "message": "Order verified but notification failed to send",
            "notification_sent": False,
            "notification_error": error
        }


@app.delete("/api/delivery-orders/{order_id}")
async def delete_delivery_order(
    order_id: str,
    admin: Dict = Depends(verify_admin_credentials)
):
    """Delete a delivery order and its payment receipt"""
    db = get_db()
    success = db.delete_delivery_order(order_id)
    if success:
        return {"success": True, "message": f"Order {order_id} deleted"}
    raise HTTPException(status_code=400, detail="Failed to delete delivery order")


@app.post("/api/delivery-orders/broadcast")
async def broadcast_delivery_message(
    session_id: int,
    message: str = Form(...),
    image: UploadFile = File(None),
    admin: Dict = Depends(verify_admin_credentials)
):
    """Send a message (optionally with an image) to all customers in a delivery session"""
    if not message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    db = get_db()
    users = db.get_delivery_session_users(session_id)
    if not users:
        raise HTTPException(status_code=404, detail="No customers found for this session")

    # If an image file was provided, upload it and use that URL
    image_url_final = ""
    if image:
        extension = os.path.splitext(image.filename or "")[1].lower()
        if extension not in BRANDING_IMAGE_ALLOWED_EXTENSIONS:
            raise HTTPException(status_code=400, detail="Unsupported file type. Use PNG, JPG, JPEG, GIF, or WebP.")
        contents = await image.read()
        if len(contents) > BRANDING_IMAGE_MAX_BYTES:
            raise HTTPException(status_code=400, detail="Image must be 2MB or smaller")

        object_name = f"broadcast/{uuid.uuid4().hex}{extension}"
        uploaded_url = db.upload_branding_image(object_name, contents, image.content_type)
        if not uploaded_url:
            raise HTTPException(status_code=500, detail="Failed to upload image")
        image_url_final = uploaded_url

    results = []
    for user in users:
        telegram_id = user.get('telegram_user_id')
        if not telegram_id:
            results.append({"telegram_user_id": None, "success": False, "error": "Missing telegram user id"})
            continue
        success, error = await send_broadcast_message(telegram_id, message, image_url_final or None)
        results.append({"telegram_user_id": telegram_id, "success": success, "error": error})

    sent = sum(1 for r in results if r["success"])
    failed = [r for r in results if not r["success"]]

    return {
        "success": True,
        "sent": sent,
        "failed": failed,
        "total": len(results)
    }


@app.post("/api/customers/broadcast")
async def broadcast_customers_message(
    message: str = Form(...),
    image: UploadFile = File(None),
    admin: Dict = Depends(verify_admin_credentials)
):
    """Send a message (optional image) to all customers with Telegram IDs"""
    if not message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    db = get_db()
    users = db.get_all_telegram_users()
    if not users:
        raise HTTPException(status_code=404, detail="No customers with Telegram IDs found")

    image_url_final = ""
    if image:
        extension = os.path.splitext(image.filename or "")[1].lower()
        if extension not in BRANDING_IMAGE_ALLOWED_EXTENSIONS:
            raise HTTPException(status_code=400, detail="Unsupported file type. Use PNG, JPG, JPEG, GIF, or WebP.")
        contents = await image.read()
        if len(contents) > BRANDING_IMAGE_MAX_BYTES:
            raise HTTPException(status_code=400, detail="Image must be 2MB or smaller")

        object_name = f"broadcast/{uuid.uuid4().hex}{extension}"
        uploaded_url = db.upload_branding_image(object_name, contents, image.content_type)
        if not uploaded_url:
            raise HTTPException(status_code=500, detail="Failed to upload image")
        image_url_final = uploaded_url

    results = []
    for user in users:
        telegram_id = user.get('telegram_user_id')
        if not telegram_id:
            results.append({"telegram_user_id": None, "success": False, "error": "Missing telegram user id"})
            continue
        success, error = await send_broadcast_message(telegram_id, message, image_url_final or None)
        results.append({"telegram_user_id": telegram_id, "success": success, "error": error})

    sent = sum(1 for r in results if r["success"])
    failed = [r for r in results if not r["success"]]

    return {
        "success": True,
        "sent": sent,
        "failed": failed,
        "total": len(results)
    }

# --- Analytics API ---

@app.get("/api/analytics/daily-sales")
async def get_daily_sales(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    admin: Dict = Depends(verify_admin_credentials)
):
    """Get daily sales summary"""
    db = get_db()

    if not start_date:
        start_date = (date.today() - timedelta(days=30)).isoformat()
    if not end_date:
        end_date = date.today().isoformat()

    sales = db.get_daily_sales_summary(
        datetime.fromisoformat(start_date).date(),
        datetime.fromisoformat(end_date).date()
    )

    return {"success": True, "data": sales}

@app.get("/api/analytics/popular-items")
async def get_popular_items(
    limit: int = 10,
    admin: Dict = Depends(verify_admin_credentials)
):
    """Get popular items"""
    db = get_db()
    items = db.get_popular_items(limit=limit)
    return {"success": True, "data": items}

@app.get("/api/analytics/store-performance")
async def get_store_performance(admin: Dict = Depends(verify_admin_credentials)):
    """Get store performance metrics"""
    db = get_db()
    performance = db.get_store_performance()
    return {"success": True, "data": performance}

# --- Delivery Sessions API ---

@app.get("/api/delivery-sessions")
async def get_delivery_sessions(
    status: Optional[str] = None,
    admin: Dict = Depends(verify_admin_credentials)
):
    """Get delivery sessions"""
    db = get_db()
    sessions = db.get_delivery_sessions(status=status)
    return {"success": True, "data": sessions}


@app.get("/api/delivery-orders/export")
async def export_delivery_orders(
    session_id: int,
    admin: Dict = Depends(verify_admin_credentials)
):
    """Export delivery orders for a session as CSV"""
    from datetime import datetime as dt

    db = get_db()
    orders = db.get_delivery_orders(limit=1000, delivery_session_id=session_id)
    session = db.get_delivery_by_id(session_id)

    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow([
        "Order ID", "Created At", "Customer Name", "Customer Phone",
        "Telegram Handle", "Flavor", "Sauce", "Quantity", "Total Price",
        "Payment Status", "Payment Screenshot", "Session Location", "Delivery Time"
    ])

    location = session.get('location') if session else 'Unknown'
    delivery_time = session.get('delivery_datetime') if session else ''

    # Format delivery time for display
    delivery_time_formatted = ''
    if delivery_time:
        try:
            delivery_dt = dt.fromisoformat(delivery_time.replace('+00:00', ''))
            delivery_time_formatted = delivery_dt.strftime('%d %b %Y, %I:%M %p')
        except:
            delivery_time_formatted = delivery_time

    for order in orders:
        # Format created_at for CSV
        created_at = order.get('created_at', '')
        if created_at:
            try:
                created_dt = dt.fromisoformat(created_at.replace('+00:00', ''))
                created_at = created_dt.strftime('%d %b %Y, %I:%M %p')
            except:
                pass

        items = order.get('items', [])

        # If order has items array, create a row for each item
        if items:
            for item in items:
                writer.writerow([
                    order.get('order_id'),
                    created_at,
                    order.get('customer_name'),
                    order.get('customer_phone'),
                    order.get('customer_handle'),
                    item.get('flavor'),
                    item.get('sauce'),
                    item.get('quantity'),
                    order.get('total_price'),  # Total for whole order
                    order.get('payment_status'),
                    order.get('payment_screenshot_url'),
                    location,
                    delivery_time_formatted,
                ])
        else:
            # Fallback to old single-item format for legacy orders
            writer.writerow([
                order.get('order_id'),
                created_at,
                order.get('customer_name'),
                order.get('customer_phone'),
                order.get('customer_handle'),
                order.get('flavor'),
                order.get('sauce'),
                order.get('quantity'),
                order.get('total_price'),
                order.get('payment_status'),
                order.get('payment_screenshot_url'),
                location,
                delivery_time_formatted,
            ])

    buffer.seek(0)
    # Create better filename: delivery_{location}_{date}_{time}.csv
    if delivery_time:
        try:
            delivery_dt = dt.fromisoformat(delivery_time.replace('+00:00', ''))
            date_str = delivery_dt.strftime('%Y-%m-%d')
            time_str = delivery_dt.strftime('%H%M')
            location_slug = location.lower().replace(' ', '_')[:20]
            filename = f"delivery_{location_slug}_{date_str}_{time_str}.csv"
        except:
            filename = f"delivery_orders_{session_id}.csv"
    else:
        filename = f"delivery_orders_{session_id}.csv"

    return StreamingResponse(buffer, media_type="text/csv", headers={
        "Content-Disposition": f"attachment; filename={filename}"
    })

@app.get("/api/delivery-orders/export-kitchen")
async def export_delivery_orders_kitchen(
    session_id: int,
    admin: Dict = Depends(verify_admin_credentials)
):
    """Export kitchen prep sheet - one row per bowl, grouped by flavor"""
    from datetime import datetime as dt
    from collections import defaultdict

    db = get_db()
    orders = db.get_delivery_orders(limit=1000, delivery_session_id=session_id)
    session = db.get_delivery_by_id(session_id)

    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow([
        "Flavor", "Sauce", "Customer Name", "Customer Phone", "Telegram Handle"
    ])

    # Expand orders into individual bowls and collect by flavor
    bowls_by_flavor = defaultdict(list)

    for order in orders:
        items = order.get('items', [])

        # If order has items array, expand each item
        if items:
            for item in items:
                flavor = item.get('flavor', 'Unknown')
                sauce = item.get('sauce', '')
                qty = item.get('quantity', 1)

                # Add a row for each bowl
                for _ in range(qty):
                    bowls_by_flavor[flavor].append({
                        'flavor': flavor,
                        'sauce': sauce,
                        'customer_name': order.get('customer_name', 'Unknown'),
                        'customer_phone': order.get('customer_phone', ''),
                        'customer_handle': order.get('customer_handle', 'n/a')
                    })
        else:
            # Fallback for legacy single-item format
            flavor = order.get('flavor', 'Unknown')
            sauce = order.get('sauce', '')
            qty = order.get('quantity', 1)

            # Add a row for each bowl
            for _ in range(qty):
                bowls_by_flavor[flavor].append({
                    'flavor': flavor,
                    'sauce': sauce,
                    'customer_name': order.get('customer_name', 'Unknown'),
                    'customer_phone': order.get('customer_phone', ''),
                    'customer_handle': order.get('customer_handle', 'n/a')
                })

    # Write rows sorted by flavor
    for flavor in sorted(bowls_by_flavor.keys()):
        for bowl in bowls_by_flavor[flavor]:
            writer.writerow([
                bowl['flavor'],
                bowl['sauce'],
                bowl['customer_name'],
                bowl['customer_phone'],
                bowl['customer_handle']
            ])

    buffer.seek(0)
    # Create filename with session info
    location = session.get('location') if session else 'Unknown'
    delivery_time = session.get('delivery_datetime') if session else ''

    filename = f"kitchen_prep.csv"
    if delivery_time:
        try:
            delivery_dt = dt.fromisoformat(delivery_time.replace('+00:00', ''))
            date_str = delivery_dt.strftime('%Y-%m-%d')
            location_slug = location.lower().replace(' ', '_')[:20]
            filename = f"kitchen_prep_{location_slug}_{date_str}.csv"
        except:
            pass

    return StreamingResponse(buffer, media_type="text/csv", headers={
        "Content-Disposition": f"attachment; filename={filename}"
    })

@app.post("/api/delivery-sessions")
async def create_delivery_session(
    session: DeliverySessionCreate,
    admin: Dict = Depends(verify_admin_credentials)
):
    """Create a new delivery session"""
    db = get_db()
    generated_session_id = f"session-{uuid.uuid4().hex[:8]}"
    success = db.create_delivery_session(
        session_id=generated_session_id,
        location=session.location,
        delivery_datetime=session.delivery_datetime,
        cutoff_time=session.cutoff_time
    )

    if success:
        return {"success": True, "message": "Delivery session created successfully", "session_id": generated_session_id}
    else:
        raise HTTPException(status_code=400, detail="Failed to create delivery session")

@app.patch("/api/delivery-sessions/{session_id}/status")
async def update_delivery_session_status(
    session_id: str,
    update: OrderStatusUpdate,
    admin: Dict = Depends(verify_admin_credentials)
):
    """Update delivery session status"""
    db = get_db()
    success = db.update_delivery_session_status(session_id, update.status)

    if success:
        return {"success": True, "message": f"Session {session_id} status updated"}
    else:
        raise HTTPException(status_code=400, detail="Failed to update session status")


@app.delete("/api/delivery-sessions/{session_id}/orders")
async def delete_delivery_session_orders(
    session_id: int,
    close_session: bool = True,
    admin: Dict = Depends(verify_admin_credentials)
):
    """Delete all delivery orders for a session and optionally close it"""
    db = get_db()
    success = db.delete_delivery_orders_by_session(session_id)

    if not success:
        raise HTTPException(status_code=400, detail="Failed to delete delivery orders")

    if close_session:
        try:
            db.client.table('delivery_sessions').delete().eq('id', session_id).execute()
        except Exception as e:
            print(f"❌ Error deleting delivery session {session_id}: {e}")

    return {"success": True, "message": "Delivery session and orders removed"}

# --- Storage Management API ---

@app.get("/api/storage/stats")
async def get_storage_stats(admin: Dict = Depends(verify_admin_credentials)):
    """Get storage usage statistics"""
    db = get_db()
    stats = db.get_storage_stats()
    return {"success": True, "data": stats}

@app.get("/api/storage/delivery-sessions")
async def get_delivery_sessions_storage(admin: Dict = Depends(verify_admin_credentials)):
    """Get storage breakdown by delivery session"""
    db = get_db()
    breakdown = db.get_delivery_sessions_storage_breakdown()
    return {"success": True, "data": breakdown, "count": len(breakdown)}

@app.delete("/api/storage/delivery-sessions/{session_id}")
async def delete_delivery_session_for_storage(
    session_id: int,
    admin: Dict = Depends(verify_admin_credentials)
):
    """Delete all delivery orders in a session (for storage management)"""
    db = get_db()
    try:
        success = db.delete_delivery_orders_by_session(session_id)
        if success:
            return {"success": True, "message": f"All orders in session {session_id} deleted"}
        else:
            raise HTTPException(status_code=400, detail="Failed to delete session orders")
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ==================== HEALTH CHECK ====================

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

# ==================== RUN SERVER ====================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
