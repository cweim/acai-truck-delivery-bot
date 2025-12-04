"""Supabase database client for Acai Supper Bot"""
import os
from typing import List, Dict, Optional, Any
from datetime import datetime, date, time as time_type
from io import BytesIO
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

class SupabaseDB:
    """Handles all database operations with Supabase"""

    def __init__(self):
        """Initialize Supabase client"""
        self.url = os.getenv('SUPABASE_URL')
        self.key = os.getenv('SUPABASE_KEY')

        if not self.url or not self.key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in .env")

        self.client: Client = create_client(self.url, self.key)
        self.bucket_name = os.getenv('SUPABASE_BUCKET', 'payment-receipts')
        print(f"✅ Connected to Supabase")

    # ==================== USERS ====================

    def create_or_update_user(self, telegram_user_id: int, name: str, telegram_handle: str, phone: str) -> Dict:
        """Create or update a user"""
        try:
            # Check if user exists
            result = self.client.table('users').select('*').eq('telegram_user_id', telegram_user_id).execute()

            user_data = {
                'telegram_user_id': telegram_user_id,
                'name': name,
                'telegram_handle': telegram_handle,
                'phone': phone
            }

            if result.data:
                # Update existing user
                response = self.client.table('users').update(user_data).eq('telegram_user_id', telegram_user_id).execute()
            else:
                # Create new user
                response = self.client.table('users').insert(user_data).execute()

            return response.data[0] if response.data else {}
        except Exception as e:
            print(f"❌ Error creating/updating user: {e}")
            return {}

    def get_user(self, telegram_user_id: int) -> Optional[Dict]:
        """Get user by Telegram ID"""
        try:
            response = self.client.table('users').select('*').eq('telegram_user_id', telegram_user_id).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            print(f"❌ Error getting user: {e}")
            return None

    # ==================== SETTINGS ====================

    def get_setting(self, key: str) -> Any:
        """Get a setting value"""
        try:
            response = self.client.table('settings').select('value').eq('key', key).execute()
            if response.data:
                return response.data[0]['value']
            return None
        except Exception as e:
            print(f"❌ Error getting setting: {e}")
            return None

    def update_setting(self, key: str, value: Any) -> bool:
        """Update a setting"""
        try:
            # Use upsert to insert if not exists, update if exists
            # on_conflict specifies which column to check for conflicts
            self.client.table('settings').upsert({
                'key': key,
                'value': value
            }, on_conflict='key').execute()
            return True
        except Exception as e:
            print(f"❌ Error updating setting: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _default_menu_groups(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": "flavor",
                "key": "flavor",
                "title": "Menu Flavors",
                "options": ["Classic Acai", "Protein Acai", "Vegan Acai"]
            },
            {
                "id": "sauce",
                "key": "sauce",
                "title": "Sauce Options",
                "options": ["Honey", "Peanut Butter", "Nutella", "No Sauce"]
            }
        ]

    def get_menu_groups(self) -> List[Dict[str, Any]]:
        """Get configurable menu option groups"""
        groups = self.get_setting('menu_groups')
        if groups:
            return groups

        # Backwards compatibility with legacy settings
        legacy_flavors = self.get_setting('menu_flavors') or []
        legacy_sauces = self.get_setting('menu_sauces') or []
        if legacy_flavors or legacy_sauces:
            groups = []
            if legacy_flavors:
                groups.append({
                    "id": "flavor",
                    "key": "flavor",
                    "title": "Menu Flavors",
                    "options": legacy_flavors
                })
            if legacy_sauces:
                groups.append({
                    "id": "sauce",
                    "key": "sauce",
                    "title": "Sauce Options",
                    "options": legacy_sauces
                })
            if groups:
                self.update_setting('menu_groups', groups)
                return groups

        default_groups = self._default_menu_groups()
        self.update_setting('menu_groups', default_groups)
        return default_groups

    def save_menu_groups(self, groups: List[Dict[str, Any]]) -> bool:
        """Persist menu groups configuration"""
        return self.update_setting('menu_groups', groups)

    def get_menu_flavors(self) -> List[str]:
        """Legacy helper: returns options from first menu group"""
        groups = self.get_menu_groups()
        if groups:
            return groups[0].get('options', [])
        return ["Classic Acai", "Protein Acai", "Vegan Acai"]

    def get_menu_sauces(self) -> List[str]:
        """Legacy helper: returns options from second menu group, if present"""
        groups = self.get_menu_groups()
        if len(groups) > 1:
            return groups[1].get('options', [])
        return ["Honey", "Peanut Butter", "Nutella", "No Sauce"]

    def get_pricing(self) -> Dict:
        """Get pricing configuration"""
        pricing = self.get_setting('pricing')
        return pricing if pricing else {"price_per_bowl": 8.00, "currency": "SGD"}

    def get_bot_branding(self) -> Dict[str, Any]:
        """Get bot branding configuration"""
        branding = self.get_setting('bot_branding')
        if branding:
            return branding
        default = {
            "title": "🍧 Welcome to Acai Supper Bot!",
            "subtitle": "Order your favourite bowls for delivery or pickup.",
            "image_url": ""
        }
        self.update_setting('bot_branding', default)
        return default

    def update_bot_branding(self, branding: Dict[str, Any]) -> bool:
        """Update bot branding configuration"""
        return self.update_setting('bot_branding', branding)

    # ==================== PICKUP STORES ====================

    def get_pickup_stores(self, active_only: bool = True) -> List[Dict]:
        """Get all pickup stores"""
        try:
            query = self.client.table('pickup_stores').select('*')
            if active_only:
                query = query.eq('status', 'active')
            response = query.execute()
            return response.data
        except Exception as e:
            print(f"❌ Error getting pickup stores: {e}")
            return []

    def get_active_pickup_stores(self) -> List[Dict]:
        """Get active pickup stores (alias for compatibility)"""
        return self.get_pickup_stores(active_only=True)

    def get_pickup_store(self, store_id: str) -> Optional[Dict]:
        """Get a specific pickup store"""
        try:
            response = self.client.table('pickup_stores').select('*').eq('store_id', store_id).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            print(f"❌ Error getting pickup store: {e}")
            return None

    def create_pickup_store(self, store_id: str, name: str, address: str, operating_hours: Dict) -> bool:
        """Create a new pickup store"""
        try:
            data = {
                'store_id': store_id,
                'name': name,
                'address': address,
                'operating_hours': operating_hours,
                'status': 'active'
            }
            self.client.table('pickup_stores').insert(data).execute()
            return True
        except Exception as e:
            print(f"❌ Error creating pickup store: {e}")
            return False

    def update_pickup_store(self, store_id: str, **kwargs) -> bool:
        """Update pickup store"""
        try:
            self.client.table('pickup_stores').update(kwargs).eq('store_id', store_id).execute()
            return True
        except Exception as e:
            print(f"❌ Error updating pickup store: {e}")
            return False

    def delete_pickup_store(self, store_id: str) -> bool:
        """Delete a pickup store"""
        try:
            self.client.table('pickup_stores').delete().eq('store_id', store_id).execute()
            return True
        except Exception as e:
            print(f"❌ Error deleting pickup store: {e}")
            return False

    # ==================== DELIVERY SESSIONS ====================

    def create_delivery_session(self, session_id: str, location: str, delivery_datetime: datetime, cutoff_time: datetime) -> bool:
        """Create a delivery session"""
        try:
            data = {
                'session_id': session_id,
                'location': location,
                'delivery_datetime': delivery_datetime.isoformat(),
                'cutoff_time': cutoff_time.isoformat(),
                'status': 'open'
            }
            self.client.table('delivery_sessions').insert(data).execute()
            return True
        except Exception as e:
            print(f"❌ Error creating delivery session: {e}")
            return False

    def get_delivery_sessions(self, status: str = 'open') -> List[Dict]:
        """Get delivery sessions. Pass empty string to get all sessions regardless of status."""
        try:
            query = self.client.table('delivery_sessions').select('*')
            if status:  # Empty string means fetch all, non-empty means filter by status
                query = query.eq('status', status)
            response = query.order('delivery_datetime').execute()
            return response.data
        except Exception as e:
            print(f"❌ Error getting delivery sessions: {e}")
            return []

    def get_active_deliveries(self) -> List[Dict]:
        """Get active delivery sessions - only those that are open and before cutoff time"""
        from datetime import datetime

        sessions = self.get_delivery_sessions(status='open')
        active = []

        for session in sessions:
            cutoff_time = session.get('cutoff_time')
            if cutoff_time:
                try:
                    cutoff_dt = datetime.fromisoformat(cutoff_time.replace('+00:00', '').replace('Z', ''))
                    if datetime.now() < cutoff_dt:
                        active.append(session)
                except:
                    # If we can't parse, include it as active
                    active.append(session)
            else:
                # If no cutoff time, include it
                active.append(session)

        return active

    def get_delivery_by_id(self, delivery_id) -> Optional[Dict]:
        """Get a specific delivery session by ID"""
        try:
            # Try as integer ID first
            if isinstance(delivery_id, str):
                try:
                    delivery_id = int(delivery_id)
                except ValueError:
                    pass

            response = self.client.table('delivery_sessions').select('*').eq('id', delivery_id).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            print(f"❌ Error getting delivery by ID: {e}")
            return None

    def update_delivery_session_status(self, session_id: str, status: str) -> bool:
        """Update delivery session status"""
        try:
            self.client.table('delivery_sessions').update({'status': status}).eq('session_id', session_id).execute()
            return True
        except Exception as e:
            print(f"❌ Error updating delivery session: {e}")
            return False

    def get_session_revenue(self, session_id: int) -> float:
        """Calculate total revenue for a delivery session"""
        try:
            response = self.client.table('delivery_orders').select('total_price').eq('delivery_session_id', session_id).execute()
            orders = response.data or []
            total = sum(float(order.get('total_price', 0)) for order in orders)
            return total
        except Exception as e:
            print(f"❌ Error calculating session revenue: {e}")
            return 0.0

    # ==================== DELIVERY ORDERS ====================

    def create_delivery_order(self, **kwargs) -> bool:
        """Create a delivery order"""
        try:
            self.client.table('delivery_orders').insert(kwargs).execute()
            print(f"✅ Delivery order {kwargs.get('order_id')} created")
            return True
        except Exception as e:
            print(f"❌ Error creating delivery order: {e}")
            return False

    def get_delivery_orders(self, limit: int = 100, offset: int = 0, order_by: str = 'created_at', descending: bool = True, **filters) -> List[Dict]:
        """Get delivery orders with filters"""
        try:
            query = self.client.table('delivery_orders').select('*')

            for key, value in filters.items():
                query = query.eq(key, value)

            if order_by:
                query = query.order(order_by, desc=descending)

            response = query.limit(limit).offset(offset).execute()
            return response.data
        except Exception as e:
            print(f"❌ Error getting delivery orders: {e}")
            return []

    def update_delivery_order(self, order_id: str, **kwargs) -> bool:
        """Update delivery order"""
        try:
            self.client.table('delivery_orders').update(kwargs).eq('order_id', order_id).execute()
            return True
        except Exception as e:
            print(f"❌ Error updating delivery order: {e}")
            return False

    def get_delivery_order_with_user(self, order_id: str) -> Optional[Dict]:
        """Get delivery order with user/telegram info for sending notifications"""
        try:
            response = self.client.table('delivery_orders').select(
                '*, users(telegram_user_id)'
            ).eq('order_id', order_id).execute()

            if response.data and len(response.data) > 0:
                return response.data[0]
            return None
        except Exception as e:
            print(f"❌ Error getting delivery order with user: {e}")
            return None

    def update_delivery_order_notification(self, order_id: str, sent: bool, error: Optional[str] = None) -> bool:
        """Update notification status for delivery order"""
        try:
            from datetime import datetime
            update_data = {
                'telegram_notification_sent': sent,
                'telegram_notification_error': error,
            }
            if sent:
                update_data['telegram_notification_sent_at'] = datetime.utcnow().isoformat()

            self.client.table('delivery_orders').update(update_data).eq('order_id', order_id).execute()
            return True
        except Exception as e:
            print(f"❌ Error updating delivery order notification: {e}")
            return False

    def delete_delivery_orders_by_session(self, session_id: int) -> bool:
        """Delete all delivery orders associated with a session"""
        try:
            receipts = self.client.table('delivery_orders').select('payment_screenshot_url').eq('delivery_session_id', session_id).execute()
            for row in receipts.data or []:
                self.delete_payment_receipt(row.get('payment_screenshot_url'))

            self.client.table('delivery_orders').delete().eq('delivery_session_id', session_id).execute()
            return True
        except Exception as e:
            print(f"❌ Error deleting delivery orders for session {session_id}: {e}")
            return False

    def cleanup_delivery_sessions(self, cutoff_datetime: datetime) -> int:
        """Delete delivery sessions (and their orders) scheduled before cutoff_datetime."""
        try:
            result = self.client.table('delivery_sessions').select('id').lt('delivery_datetime', cutoff_datetime.isoformat()).execute()
            session_ids = [row['id'] for row in result.data or []]

            for session_id in session_ids:
                self.delete_delivery_orders_by_session(session_id)

            if session_ids:
                self.client.table('delivery_sessions').delete().in_('id', session_ids).execute()
            return len(session_ids)
        except Exception as e:
            print(f"❌ Error cleaning up old delivery sessions: {e}")
            return 0

    # ==================== PICKUP ORDERS ====================

    def create_pickup_order(self, **kwargs) -> bool:
        """Create a pickup order"""
        try:
            print(f"🔍 DEBUG: Attempting to create pickup order with data: {kwargs}")
            response = self.client.table('pickup_orders').insert(kwargs).execute()
            print(f"✅ Pickup order {kwargs.get('order_id')} created")
            return True
        except Exception as e:
            print(f"❌ Error creating pickup order: {e}")
            print(f"🔍 DEBUG: Order data was: {kwargs}")
            import traceback
            traceback.print_exc()
            return False

    def get_pickup_orders(self, limit: int = 100, offset: int = 0, **filters) -> List[Dict]:
        """Get pickup orders with filters"""
        try:
            query = self.client.table('pickup_orders').select('*, pickup_stores(name, address)')

            for key, value in filters.items():
                query = query.eq(key, value)

            response = query.order('created_at', desc=True).limit(limit).offset(offset).execute()
            return response.data
        except Exception as e:
            print(f"❌ Error getting pickup orders: {e}")
            return []

    def get_pickup_orders_by_date(self, pickup_date: date) -> List[Dict]:
        """Get pickup orders for a specific date"""
        try:
            response = self.client.table('pickup_orders').select('*, pickup_stores(name, address)').eq('pickup_date', pickup_date.isoformat()).order('pickup_time').execute()
            return response.data
        except Exception as e:
            print(f"❌ Error getting pickup orders by date: {e}")
            return []

    def update_pickup_order(self, order_id: str, **kwargs) -> bool:
        """Update pickup order"""
        try:
            self.client.table('pickup_orders').update(kwargs).eq('order_id', order_id).execute()
            return True
        except Exception as e:
            print(f"❌ Error updating pickup order: {e}")
            return False

    def get_pickup_order_with_user(self, order_id: str) -> Optional[Dict]:
        """Get pickup order with user/telegram info for sending notifications"""
        try:
            response = self.client.table('pickup_orders').select(
                '*, users(telegram_user_id), pickup_stores(name, address)'
            ).eq('order_id', order_id).execute()

            if response.data and len(response.data) > 0:
                return response.data[0]
            return None
        except Exception as e:
            print(f"❌ Error getting pickup order with user: {e}")
            return None

    def update_pickup_order_notification(self, order_id: str, sent: bool, error: Optional[str] = None) -> bool:
        """Update notification status for pickup order"""
        try:
            from datetime import datetime
            update_data = {
                'telegram_notification_sent': sent,
                'telegram_notification_error': error,
            }
            if sent:
                update_data['telegram_notification_sent_at'] = datetime.utcnow().isoformat()

            self.client.table('pickup_orders').update(update_data).eq('order_id', order_id).execute()
            return True
        except Exception as e:
            print(f"❌ Error updating pickup order notification: {e}")
            return False

    def delete_pickup_orders_before(self, cutoff_date: date) -> int:
        """Delete pickup orders older than cutoff_date"""
        try:
            old_orders = self.client.table('pickup_orders').select('payment_screenshot_url').lt('pickup_date', cutoff_date.isoformat()).execute()
            for row in old_orders.data or []:
                self.delete_payment_receipt(row.get('payment_screenshot_url'))

            response = self.client.table('pickup_orders').delete().lt('pickup_date', cutoff_date.isoformat()).execute()
            return len(response.data) if response.data else 0
        except Exception as e:
            print(f"❌ Error deleting old pickup orders: {e}")
            return 0

    def delete_payment_receipt(self, file_url: Optional[str]) -> None:
        """Delete a payment receipt from Supabase Storage or local fallback."""
        if not file_url:
            return

        try:
            if file_url.startswith('http') and self.bucket_name:
                marker = f"/public/{self.bucket_name}/"
                if marker in file_url:
                    object_path = file_url.split(marker, 1)[1]
                    self.client.storage.from_(self.bucket_name).remove([object_path])
            elif os.path.exists(file_url):
                os.remove(file_url)
        except Exception as e:
            print(f"⚠️ Error deleting receipt {file_url}: {e}")

    def delete_old_payment_receipts(self, table_name: str, cutoff_date: date) -> int:
        """Delete payment receipt images for orders 3 days past their delivery/pickup time.

        Args:
            table_name: Either 'pickup_orders' or 'delivery_orders'
            cutoff_date: For pickup orders, delete receipts where pickup_date < cutoff_date (3 days ago)
                        For delivery orders, this parameter is ignored - we check delivery_datetime instead

        Returns:
            Number of receipts deleted
        """
        try:
            deleted_count = 0
            order_ids_to_update = []

            if table_name == 'pickup_orders':
                # For pickup orders: delete receipts 3 days after pickup_date
                old_orders = self.client.table('pickup_orders').select(
                    'order_id, payment_screenshot_url, pickup_date'
                ).lt('pickup_date', cutoff_date.isoformat()).execute()

                for row in old_orders.data or []:
                    receipt_url = row.get('payment_screenshot_url')
                    if receipt_url:
                        self.delete_payment_receipt(receipt_url)
                        deleted_count += 1
                        order_ids_to_update.append(row.get('order_id'))

                # Update records to remove the URL reference
                if order_ids_to_update:
                    for order_id in order_ids_to_update:
                        self.client.table('pickup_orders').update({
                            'payment_screenshot_url': None
                        }).eq('order_id', order_id).execute()

            elif table_name == 'delivery_orders':
                # For delivery orders: get orders with their delivery session info
                # and delete receipts 3 days after delivery_datetime
                sessions = self.client.table('delivery_sessions').select(
                    'id, delivery_datetime'
                ).lt('delivery_datetime', cutoff_date.isoformat()).execute()

                for session in sessions.data or []:
                    session_id = session.get('id')
                    orders = self.client.table('delivery_orders').select(
                        'order_id, payment_screenshot_url'
                    ).eq('delivery_session_id', session_id).execute()

                    for row in orders.data or []:
                        receipt_url = row.get('payment_screenshot_url')
                        if receipt_url:
                            self.delete_payment_receipt(receipt_url)
                            deleted_count += 1
                            order_ids_to_update.append(row.get('order_id'))

                # Update records to remove the URL reference
                if order_ids_to_update:
                    for order_id in order_ids_to_update:
                        self.client.table('delivery_orders').update({
                            'payment_screenshot_url': None
                        }).eq('order_id', order_id).execute()
            else:
                raise ValueError(f"Invalid table_name: {table_name}")

            print(f"✅ Deleted {deleted_count} old payment receipts from {table_name}")
            return deleted_count
        except Exception as e:
            print(f"❌ Error deleting old payment receipts: {e}")
            import traceback
            traceback.print_exc()
            return 0

    # ==================== STORAGE (Payment Receipts) ====================

    def upload_branding_image(self, object_name: str, file_bytes: bytes, content_type: str) -> Optional[str]:
        """Upload branding image to Supabase Storage and return public URL."""
        try:
            self.client.storage.from_(self.bucket_name).upload(
                object_name,
                file_bytes,
                file_options={"content-type": content_type or "image/png", "upsert": "true"}
            )
            public_url = self.client.storage.from_(self.bucket_name).get_public_url(object_name)
            return public_url
        except Exception as e:
            print(f"❌ Error uploading branding image: {e}")
            import traceback
            traceback.print_exc()
            return None

    def upload_payment_receipt(self, order_id: str, file_path: str) -> Optional[str]:
        """Upload payment receipt to Supabase Storage"""
        try:
            file_name = f"payment_{order_id}.jpg"

            with open(file_path, 'rb') as f:
                response = self.client.storage.from_(self.bucket_name).upload(
                    file_name,
                    f,
                    file_options={"content-type": "image/jpeg"}
                )

            # Get public URL
            public_url = self.client.storage.from_(self.bucket_name).get_public_url(file_name)
            print(f"✅ Uploaded payment receipt: {public_url}")
            return public_url

        except Exception as e:
            print(f"❌ Error uploading payment receipt: {e}")
            return None

    # ==================== ANALYTICS ====================

    def get_daily_sales_summary(self, start_date: date, end_date: date) -> List[Dict]:
        """Get daily sales summary"""
        try:
            response = self.client.rpc('get_daily_sales', {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat()
            }).execute()
            return response.data
        except Exception as e:
            # Fallback if RPC doesn't exist
            return self._manual_daily_sales_summary(start_date, end_date)

    def _manual_daily_sales_summary(self, start_date: date, end_date: date) -> List[Dict]:
        """Manual calculation of daily sales"""
        try:
            from collections import defaultdict

            # Get all orders within date range (excluding cancelled)
            delivery_orders = self.client.table('delivery_orders').select(
                'created_at, total_price, quantity, order_status'
            ).gte('created_at', start_date.isoformat()).lte('created_at', end_date.isoformat()).execute()

            pickup_orders = self.client.table('pickup_orders').select(
                'created_at, total_price, quantity, order_status'
            ).gte('created_at', start_date.isoformat()).lte('created_at', end_date.isoformat()).execute()

            # Aggregate by date
            daily_stats = defaultdict(lambda: {
                'sale_date': None,
                'order_type': 'combined',
                'total_orders': 0,
                'total_revenue': 0.0,
                'total_items': 0
            })

            for order in delivery_orders.data:
                if order.get('order_status') == 'cancelled':
                    continue
                created_at = order.get('created_at', '')
                if created_at:
                    sale_date = created_at.split('T')[0]  # Extract date part
                    daily_stats[sale_date]['sale_date'] = sale_date
                    daily_stats[sale_date]['total_orders'] += 1
                    daily_stats[sale_date]['total_revenue'] += float(order.get('total_price', 0))
                    daily_stats[sale_date]['total_items'] += int(order.get('quantity', 0))

            for order in pickup_orders.data:
                if order.get('order_status') == 'cancelled':
                    continue
                created_at = order.get('created_at', '')
                if created_at:
                    sale_date = created_at.split('T')[0]  # Extract date part
                    daily_stats[sale_date]['sale_date'] = sale_date
                    daily_stats[sale_date]['total_orders'] += 1
                    daily_stats[sale_date]['total_revenue'] += float(order.get('total_price', 0))
                    daily_stats[sale_date]['total_items'] += int(order.get('quantity', 0))

            # Convert to sorted list
            summary = sorted(daily_stats.values(), key=lambda x: x['sale_date'])
            return summary
        except Exception as e:
            print(f"❌ Error calculating sales summary: {e}")
            import traceback
            traceback.print_exc()
            return []

    def get_weekly_sales_summary(self, start_date: date, end_date: date) -> List[Dict]:
        """Get weekly sales summary"""
        try:
            from collections import defaultdict
            from datetime import timedelta

            # Get all orders within date range (excluding cancelled)
            delivery_orders = self.client.table('delivery_orders').select(
                'created_at, total_price, quantity, order_status'
            ).gte('created_at', start_date.isoformat()).lte('created_at', end_date.isoformat()).execute()

            pickup_orders = self.client.table('pickup_orders').select(
                'created_at, total_price, quantity, order_status'
            ).gte('created_at', start_date.isoformat()).lte('created_at', end_date.isoformat()).execute()

            # Aggregate by week (ISO week format)
            weekly_stats = defaultdict(lambda: {
                'week_start': None,
                'week_end': None,
                'week_label': None,
                'order_type': 'combined',
                'total_orders': 0,
                'total_revenue': 0.0,
                'total_items': 0
            })

            def get_week_key(date_str):
                """Get week starting date from ISO date string"""
                from datetime import datetime
                dt = datetime.fromisoformat(date_str.split('T')[0])
                # Get Monday of that week
                week_start = dt - timedelta(days=dt.weekday())
                return week_start.date().isoformat()

            for order in delivery_orders.data + pickup_orders.data:
                if order.get('order_status') == 'cancelled':
                    continue
                created_at = order.get('created_at', '')
                if created_at:
                    week_key = get_week_key(created_at)
                    from datetime import datetime
                    week_start_date = datetime.fromisoformat(week_key).date()
                    week_end_date = week_start_date + timedelta(days=6)

                    if week_key not in weekly_stats:
                        weekly_stats[week_key]['week_start'] = week_start_date.isoformat()
                        weekly_stats[week_key]['week_end'] = week_end_date.isoformat()
                        weekly_stats[week_key]['week_label'] = f"{week_start_date.strftime('%b %d')} - {week_end_date.strftime('%b %d')}"

                    weekly_stats[week_key]['total_orders'] += 1
                    weekly_stats[week_key]['total_revenue'] += float(order.get('total_price', 0))
                    weekly_stats[week_key]['total_items'] += int(order.get('quantity', 0))

            # Convert to sorted list
            summary = sorted(weekly_stats.values(), key=lambda x: x['week_start'])
            return summary
        except Exception as e:
            print(f"❌ Error calculating weekly sales summary: {e}")
            import traceback
            traceback.print_exc()
            return []

    def get_monthly_sales_summary(self, start_date: date, end_date: date) -> List[Dict]:
        """Get monthly sales summary"""
        try:
            from collections import defaultdict
            from datetime import datetime

            # Get all orders within date range (excluding cancelled)
            delivery_orders = self.client.table('delivery_orders').select(
                'created_at, total_price, quantity, order_status'
            ).gte('created_at', start_date.isoformat()).lte('created_at', end_date.isoformat()).execute()

            pickup_orders = self.client.table('pickup_orders').select(
                'created_at, total_price, quantity, order_status'
            ).gte('created_at', start_date.isoformat()).lte('created_at', end_date.isoformat()).execute()

            # Aggregate by month
            monthly_stats = defaultdict(lambda: {
                'month': None,
                'month_label': None,
                'order_type': 'combined',
                'total_orders': 0,
                'total_revenue': 0.0,
                'total_items': 0
            })

            def get_month_key(date_str):
                """Get month key (YYYY-MM) from ISO date string"""
                return date_str.split('T')[0][:7]

            for order in delivery_orders.data + pickup_orders.data:
                if order.get('order_status') == 'cancelled':
                    continue
                created_at = order.get('created_at', '')
                if created_at:
                    month_key = get_month_key(created_at)
                    dt = datetime.fromisoformat(created_at.split('T')[0])
                    month_label = dt.strftime('%B %Y')

                    if month_key not in monthly_stats:
                        monthly_stats[month_key]['month'] = month_key
                        monthly_stats[month_key]['month_label'] = month_label

                    monthly_stats[month_key]['total_orders'] += 1
                    monthly_stats[month_key]['total_revenue'] += float(order.get('total_price', 0))
                    monthly_stats[month_key]['total_items'] += int(order.get('quantity', 0))

            # Convert to sorted list
            summary = sorted(monthly_stats.values(), key=lambda x: x['month'])
            return summary
        except Exception as e:
            print(f"❌ Error calculating monthly sales summary: {e}")
            import traceback
            traceback.print_exc()
            return []

    def get_popular_items(self, limit: int = 10) -> List[Dict]:
        """Get popular items"""
        try:
            response = self.client.table('popular_items').select('*').limit(limit).execute()
            return response.data
        except Exception as e:
            print(f"❌ Error getting popular items: {e}")
            return []

    def get_store_performance(self) -> List[Dict]:
        """Get store performance metrics"""
        try:
            response = self.client.table('store_performance').select('*').execute()
            return response.data
        except Exception as e:
            print(f"❌ Error getting store performance: {e}")
            return []

    def get_top_customers(self, start_date: date, end_date: date, limit: int = 10) -> List[Dict]:
        """Get top customers by order count and revenue for date range"""
        try:
            # Aggregate from both delivery and pickup orders
            from collections import defaultdict

            delivery_orders = self.client.table('delivery_orders').select(
                'customer_name, customer_phone, customer_handle, total_price, quantity'
            ).gte('created_at', start_date.isoformat()).lte('created_at', end_date.isoformat()).neq('order_status', 'cancelled').execute()

            pickup_orders = self.client.table('pickup_orders').select(
                'customer_name, customer_phone, customer_handle, total_price, quantity'
            ).gte('created_at', start_date.isoformat()).lte('created_at', end_date.isoformat()).neq('order_status', 'cancelled').execute()

            customer_stats = defaultdict(lambda: {'order_count': 0, 'total_revenue': 0.0, 'total_items': 0})

            for order in delivery_orders.data + pickup_orders.data:
                key = order.get('customer_phone', 'unknown')
                customer_stats[key]['customer_name'] = order.get('customer_name', 'Unknown')
                customer_stats[key]['customer_phone'] = key
                customer_stats[key]['customer_handle'] = order.get('customer_handle', '')
                customer_stats[key]['order_count'] += 1
                customer_stats[key]['total_revenue'] += float(order.get('total_price', 0))
                customer_stats[key]['total_items'] += int(order.get('quantity', 0))

            # Convert to list and calculate avg order value
            result = []
            for phone, stats in customer_stats.items():
                stats['avg_order_value'] = stats['total_revenue'] / stats['order_count'] if stats['order_count'] > 0 else 0
                result.append(stats)

            # Sort by total revenue desc
            result.sort(key=lambda x: x['total_revenue'], reverse=True)
            return result[:limit]
        except Exception as e:
            print(f"❌ Error getting top customers: {e}")
            import traceback
            traceback.print_exc()
            return []

    def get_top_delivery_sessions(self, start_date: date, end_date: date, limit: int = 10) -> List[Dict]:
        """Get top delivery sessions by order count and revenue"""
        try:
            sessions = self.client.table('delivery_sessions').select(
                'id, session_id, location, delivery_datetime, status'
            ).gte('delivery_datetime', start_date.isoformat()).lte('delivery_datetime', end_date.isoformat()).execute()

            session_stats = []
            for session in sessions.data:
                orders = self.client.table('delivery_orders').select(
                    'total_price, quantity'
                ).eq('delivery_session_id', session['id']).neq('order_status', 'cancelled').execute()

                order_count = len(orders.data)
                total_revenue = sum(float(o.get('total_price', 0)) for o in orders.data)
                total_items = sum(int(o.get('quantity', 0)) for o in orders.data)
                avg_order_value = total_revenue / order_count if order_count > 0 else 0

                session_stats.append({
                    'session_id': session.get('session_id'),
                    'location': session.get('location'),
                    'delivery_datetime': session.get('delivery_datetime'),
                    'status': session.get('status'),
                    'order_count': order_count,
                    'total_revenue': total_revenue,
                    'total_items': total_items,
                    'avg_order_value': avg_order_value
                })

            # Sort by total revenue desc
            session_stats.sort(key=lambda x: x['total_revenue'], reverse=True)
            return session_stats[:limit]
        except Exception as e:
            print(f"❌ Error getting top delivery sessions: {e}")
            import traceback
            traceback.print_exc()
            return []

    def get_peak_hours_analysis(self, start_date: date, end_date: date) -> Dict:
        """Analyze peak ordering hours and days"""
        try:
            from collections import defaultdict
            from datetime import datetime as dt

            pickup_orders = self.client.table('pickup_orders').select(
                'created_at, pickup_date'
            ).gte('created_at', start_date.isoformat()).lte('created_at', end_date.isoformat()).neq('order_status', 'cancelled').execute()

            delivery_orders = self.client.table('delivery_orders').select(
                'created_at'
            ).gte('created_at', start_date.isoformat()).lte('created_at', end_date.isoformat()).neq('order_status', 'cancelled').execute()

            day_counts = defaultdict(int)
            hour_counts = defaultdict(int)

            for order in pickup_orders.data + delivery_orders.data:
                created_at = order.get('created_at')
                if created_at:
                    try:
                        dt_obj = dt.fromisoformat(created_at.replace('Z', '+00:00'))
                        day_name = dt_obj.strftime('%A')
                        hour = dt_obj.hour
                        day_counts[day_name] += 1
                        hour_counts[hour] += 1
                    except:
                        pass

            return {
                'by_day': dict(sorted(day_counts.items(), key=lambda x: x[1], reverse=True)),
                'by_hour': dict(sorted(hour_counts.items(), key=lambda x: x[1], reverse=True))
            }
        except Exception as e:
            print(f"❌ Error getting peak hours analysis: {e}")
            import traceback
            traceback.print_exc()
            return {'by_day': {}, 'by_hour': {}}

    def get_payment_method_stats(self, start_date: date, end_date: date) -> Dict:
        """Get payment method breakdown for pickup orders"""
        try:
            pickup_orders = self.client.table('pickup_orders').select(
                'payment_method, payment_status, total_price'
            ).gte('created_at', start_date.isoformat()).lte('created_at', end_date.isoformat()).neq('order_status', 'cancelled').execute()

            stats = {
                'pay_now': {'count': 0, 'revenue': 0.0},
                'pay_at_counter': {'count': 0, 'revenue': 0.0},
                'by_status': {
                    'pending': 0,
                    'submitted': 0,
                    'verified': 0,
                    'paid': 0
                }
            }

            for order in pickup_orders.data:
                method = order.get('payment_method', 'unknown')
                if method in stats:
                    stats[method]['count'] += 1
                    stats[method]['revenue'] += float(order.get('total_price', 0))

                status = order.get('payment_status', 'pending')
                if status in stats['by_status']:
                    stats['by_status'][status] += 1

            return stats
        except Exception as e:
            print(f"❌ Error getting payment method stats: {e}")
            return {
                'pay_now': {'count': 0, 'revenue': 0.0},
                'pay_at_counter': {'count': 0, 'revenue': 0.0},
                'by_status': {}
            }

    def get_customer_acquisition_stats(self, start_date: date, end_date: date) -> Dict:
        """Get new vs returning customer stats"""
        try:
            all_orders = []

            delivery_orders = self.client.table('delivery_orders').select(
                'customer_phone, created_at'
            ).neq('order_status', 'cancelled').order('created_at').execute()

            pickup_orders = self.client.table('pickup_orders').select(
                'customer_phone, created_at'
            ).neq('order_status', 'cancelled').order('created_at').execute()

            all_orders = delivery_orders.data + pickup_orders.data
            all_orders.sort(key=lambda x: x.get('created_at', ''))

            first_order_date = {}
            new_customers = 0
            returning_customers = 0

            for order in all_orders:
                phone = order.get('customer_phone')
                created_at = order.get('created_at', '')

                if not phone or not created_at:
                    continue

                try:
                    order_date = date.fromisoformat(created_at.split('T')[0])
                except:
                    continue

                if start_date <= order_date <= end_date:
                    if phone not in first_order_date:
                        new_customers += 1
                        first_order_date[phone] = order_date
                    else:
                        returning_customers += 1
                elif phone not in first_order_date:
                    first_order_date[phone] = order_date

            return {
                'new_customers': new_customers,
                'returning_customers': returning_customers,
                'total_customers': new_customers + returning_customers
            }
        except Exception as e:
            print(f"❌ Error getting customer acquisition stats: {e}")
            import traceback
            traceback.print_exc()
            return {'new_customers': 0, 'returning_customers': 0, 'total_customers': 0}

    # ==================== LOCATION-SPECIFIC ANALYTICS ====================

    def get_delivery_locations(self) -> List[str]:
        """Get all unique delivery locations"""
        try:
            response = self.client.table('delivery_sessions').select('location').execute()
            locations = list(set(s.get('location', '') for s in response.data if s.get('location')))
            return sorted(locations)
        except Exception as e:
            print(f"❌ Error getting delivery locations: {e}")
            return []

    def get_sessions_by_normalized_location(self, normalized_location: str) -> List[Dict]:
        """Get all delivery sessions matching a normalized location name.
        Handles variations in whitespace and case."""
        try:
            all_sessions = self.client.table('delivery_sessions').select('id, location').execute()
            # Match by normalized location (strip whitespace, convert to title case)
            def normalize(loc: str) -> str:
                return loc.strip().title() if loc else ''

            matching_sessions = [s for s in (all_sessions.data or [])
                                if normalize(s.get('location', '')) == normalized_location]
            return matching_sessions
        except Exception as e:
            print(f"❌ Error getting sessions by normalized location: {e}")
            return []

    def get_location_daily_sales(self, location: str, start_date: date, end_date: date) -> List[Dict]:
        """Get daily sales summary for a specific delivery location (normalized)"""
        try:
            from datetime import datetime, timedelta

            # Get all sessions for this location using normalized matching
            sessions = self.get_sessions_by_normalized_location(location)
            session_ids = [s['id'] for s in sessions]

            if not session_ids:
                return []

            # Initialize daily stats
            daily_stats = {}
            current_date = start_date
            while current_date <= end_date:
                date_str = current_date.isoformat()
                daily_stats[date_str] = {
                    'sale_date': date_str,
                    'total_revenue': 0.0,
                    'total_orders': 0,
                    'total_items': 0
                }
                current_date += timedelta(days=1)

            # Get orders for these sessions
            for session_id in session_ids:
                orders = self.client.table('delivery_orders').select(
                    'created_at, total_price, quantity, order_status'
                ).eq('delivery_session_id', session_id).neq('order_status', 'cancelled').execute()

                for order in orders.data or []:
                    order_date = order.get('created_at', '').split('T')[0]
                    if order_date in daily_stats:
                        daily_stats[order_date]['total_revenue'] += float(order.get('total_price', 0))
                        daily_stats[order_date]['total_orders'] += 1
                        daily_stats[order_date]['total_items'] += int(order.get('quantity', 0))

            result = sorted(daily_stats.values(), key=lambda x: x['sale_date'])
            return result
        except Exception as e:
            print(f"❌ Error getting location daily sales: {e}")
            return []

    def get_location_popular_items(self, location: str, start_date: date, end_date: date, limit: int = 10) -> List[Dict]:
        """Get popular items for a specific delivery location (normalized)"""
        try:
            # Get all sessions for this location using normalized matching
            sessions = self.get_sessions_by_normalized_location(location)
            session_ids = [s['id'] for s in sessions]

            if not session_ids:
                return []

            items_dict = {}

            # Get orders for these sessions
            for session_id in session_ids:
                orders = self.client.table('delivery_orders').select(
                    'flavor, sauce, quantity, order_status'
                ).eq('delivery_session_id', session_id).neq('order_status', 'cancelled').execute()

                for order in orders.data or []:
                    flavor = order.get('flavor', 'Unknown')
                    sauce = order.get('sauce', '')
                    key = f"{flavor}|{sauce}"

                    if key not in items_dict:
                        items_dict[key] = {
                            'flavor': flavor,
                            'sauce': sauce,
                            'order_count': 0,
                            'total_quantity': 0
                        }

                    items_dict[key]['order_count'] += 1
                    items_dict[key]['total_quantity'] += int(order.get('quantity', 0))

            items = list(items_dict.values())
            items.sort(key=lambda x: x['total_quantity'], reverse=True)
            return items[:limit]
        except Exception as e:
            print(f"❌ Error getting location popular items: {e}")
            return []

    def get_location_top_customers(self, location: str, start_date: date, end_date: date, limit: int = 10) -> List[Dict]:
        """Get top customers for a specific delivery location (normalized)"""
        try:
            # Get all sessions for this location using normalized matching
            sessions = self.get_sessions_by_normalized_location(location)
            session_ids = [s['id'] for s in sessions]

            if not session_ids:
                return []

            customer_stats = {}

            # Get orders for these sessions
            for session_id in session_ids:
                orders = self.client.table('delivery_orders').select(
                    'customer_name, customer_phone, customer_handle, total_price, order_status'
                ).eq('delivery_session_id', session_id).neq('order_status', 'cancelled').execute()

                for order in orders.data or []:
                    phone = order.get('customer_phone', 'Unknown')
                    key = phone

                    if key not in customer_stats:
                        customer_stats[key] = {
                            'customer_name': order.get('customer_name', 'Unknown'),
                            'customer_phone': phone,
                            'customer_handle': order.get('customer_handle', ''),
                            'order_count': 0,
                            'total_revenue': 0.0
                        }

                    customer_stats[key]['order_count'] += 1
                    customer_stats[key]['total_revenue'] += float(order.get('total_price', 0))

            customers = list(customer_stats.values())
            for c in customers:
                c['avg_order_value'] = c['total_revenue'] / c['order_count'] if c['order_count'] > 0 else 0

            customers.sort(key=lambda x: x['total_revenue'], reverse=True)
            return customers[:limit]
        except Exception as e:
            print(f"❌ Error getting location top customers: {e}")
            return []

    # ==================== STORAGE MANAGEMENT ====================

    def get_storage_stats(self) -> Dict:
        """Get storage usage statistics for both database and file storage"""
        try:
            # Get all orders with receipt info
            delivery_orders = self.client.table('delivery_orders').select('id, created_at, payment_screenshot_url').execute()
            pickup_orders = self.client.table('pickup_orders').select('id, created_at, payment_screenshot_url').execute()

            all_orders = (delivery_orders.data if delivery_orders.data else []) + (pickup_orders.data if pickup_orders.data else [])

            # Storage constants
            db_free_tier_limit = 500 * 1024 * 1024  # 500 MB
            storage_free_tier_limit = 1 * 1024 * 1024 * 1024  # 1 GB
            bytes_per_order = 600  # Conservative estimate: ~500-700 bytes per order row

            # Calculate database usage - more realistic
            total_orders = len(all_orders)
            estimated_orders_db_size = total_orders * bytes_per_order

            # Other tables: users, sessions, settings, audit_log, etc.
            # More realistic: ~1-5 MB for metadata tables unless you have 10000+ users
            users = self.client.table('users').select('id', count='exact').execute()
            sessions = self.client.table('delivery_sessions').select('id', count='exact').execute()

            total_users = len(users.data) if users.data else 0
            total_sessions = len(sessions.data) if sessions.data else 0

            # Calculate other tables size more accurately
            other_tables_size = (total_users * 300) + (total_sessions * 400) + (1 * 1024 * 1024)  # 1MB base for settings/audit

            total_db_size = estimated_orders_db_size + other_tables_size

            # Get ACTUAL file storage usage from Supabase bucket
            try:
                files = self.client.storage.from_(self.bucket_name).list()
                total_storage_size = 0
                file_count = 0

                if files:
                    for file in files:
                        # Size is in metadata for Supabase
                        if 'metadata' in file and file['metadata'] and 'size' in file['metadata']:
                            size = file['metadata']['size']
                            if size > 0:  # Only count actual files, not directories
                                total_storage_size += size
                                file_count += 1

                # Get count of orders with receipts for reference
                orders_with_receipts = [o for o in all_orders if o.get('payment_screenshot_url')]
                total_receipts = len(orders_with_receipts)

                # Calculate actual average receipt size
                actual_avg_receipt_kb = (total_storage_size / file_count / 1024) if file_count > 0 else 0

            except Exception as e:
                print(f"⚠️  Could not get actual file storage, falling back to estimates: {e}")
                # Fallback to estimates if bucket access fails
                orders_with_receipts = [o for o in all_orders if o.get('payment_screenshot_url')]
                total_receipts = len(orders_with_receipts)
                bytes_per_receipt = 300 * 1024  # 300 KB estimate
                total_storage_size = total_receipts * bytes_per_receipt
                file_count = total_receipts
                actual_avg_receipt_kb = 300

            return {
                'database': {
                    'limit_bytes': db_free_tier_limit,
                    'limit_mb': db_free_tier_limit / (1024 * 1024),
                    'used_bytes': total_db_size,
                    'used_mb': total_db_size / (1024 * 1024),
                    'remaining_bytes': max(0, db_free_tier_limit - total_db_size),
                    'remaining_mb': max(0, (db_free_tier_limit - total_db_size) / (1024 * 1024)),
                    'percent_used': min(100, (total_db_size / db_free_tier_limit) * 100),
                    'total_orders': total_orders,
                    'estimated_orders_size_bytes': estimated_orders_db_size,
                },
                'file_storage': {
                    'limit_bytes': storage_free_tier_limit,
                    'limit_gb': storage_free_tier_limit / (1024 * 1024 * 1024),
                    'used_bytes': total_storage_size,
                    'used_mb': total_storage_size / (1024 * 1024),
                    'remaining_bytes': max(0, storage_free_tier_limit - total_storage_size),
                    'remaining_mb': max(0, (storage_free_tier_limit - total_storage_size) / (1024 * 1024)),
                    'percent_used': min(100, (total_storage_size / storage_free_tier_limit) * 100),
                    'total_receipts': total_receipts,
                    'actual_file_count': file_count,
                    'actual_avg_receipt_kb': actual_avg_receipt_kb,
                    'is_actual_size': True,  # Flag to indicate this is actual, not estimated
                }
            }
        except Exception as e:
            print(f"❌ Error getting storage stats: {e}")
            import traceback
            traceback.print_exc()
            return {}

    def get_delivery_sessions_storage_breakdown(self) -> List[Dict]:
        """Get storage usage breakdown grouped by delivery session"""
        try:
            # Get all delivery sessions
            sessions = self.client.table('delivery_sessions').select(
                'id, session_id, location, delivery_datetime, status'
            ).order('delivery_datetime', desc=True).execute()

            # Get all delivery orders
            delivery_orders = self.client.table('delivery_orders').select(
                'id, order_id, customer_name, delivery_session_id, total_price, payment_screenshot_url'
            ).execute()

            bytes_per_order = 600
            bytes_per_receipt = 300 * 1024

            breakdown = []
            for session in sessions.data or []:
                session_id = session.get('id')

                # Find all orders for this session
                session_orders = [o for o in (delivery_orders.data or []) if o.get('delivery_session_id') == session_id]

                # Calculate storage
                total_orders = len(session_orders)
                orders_db_size = total_orders * bytes_per_order

                receipts_size = 0
                orders_with_receipts = 0
                for order in session_orders:
                    if order.get('payment_screenshot_url'):
                        receipts_size += bytes_per_receipt
                        orders_with_receipts += 1

                total_size = orders_db_size + receipts_size

                breakdown.append({
                    'session_id': session.get('session_id'),
                    'location': session.get('location'),
                    'delivery_datetime': session.get('delivery_datetime'),
                    'status': session.get('status'),
                    'total_orders': total_orders,
                    'orders_with_receipts': orders_with_receipts,
                    'orders_db_size_bytes': orders_db_size,
                    'receipts_size_bytes': receipts_size,
                    'total_size_bytes': total_size,
                    'total_size_kb': total_size / 1024,
                    'total_size_mb': total_size / (1024 * 1024),
                })

            return breakdown
        except Exception as e:
            print(f"❌ Error getting delivery sessions storage breakdown: {e}")
            return []


# Global instance
_db_instance: Optional[SupabaseDB] = None


def get_db() -> SupabaseDB:
    """Get or create the global database instance"""
    global _db_instance
    if _db_instance is None:
        _db_instance = SupabaseDB()
    return _db_instance


# Test function
if __name__ == "__main__":
    print("🧪 Testing Supabase connection...")

    try:
        db = get_db()

        # Test getting stores
        stores = db.get_pickup_stores()
        print(f"✅ Retrieved {len(stores)} pickup stores")

        # Test getting settings
        flavors = db.get_menu_flavors()
        print(f"✅ Retrieved {len(flavors)} flavors: {flavors}")

        print("\n✅ Connection test successful!")
    except Exception as e:
        print(f"\n❌ Connection test failed: {e}")
        print("\nMake sure:")
        print("1. SUPABASE_URL and SUPABASE_KEY are set in .env")
        print("2. Database schema has been run in Supabase")
        print("3. Internet connection is working")
