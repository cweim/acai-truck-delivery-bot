"""Utility functions for the Acai Supper Bot"""
import json
import os
from datetime import datetime
from typing import Dict, List, Any, Optional


def read_json(filepath: str) -> Any:
    """Read and parse a JSON file. Returns empty dict/list if file doesn't exist."""
    if not os.path.exists(filepath):
        return {} if not filepath.endswith('deliveries.json') else []

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {} if not filepath.endswith('deliveries.json') else []


def write_json(filepath: str, data: Any) -> bool:
    """Write data to a JSON file. Returns True on success."""
    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except IOError as e:
        print(f"Error writing to {filepath}: {e}")
        return False


def calculate_price(quantity: int, unit_price: float = 8.0) -> float:
    """Calculate total price for acai bowls."""
    return quantity * unit_price


def get_default_order_discount_rule() -> Dict[str, Any]:
    """Return the default fixed discount configuration."""
    return {
        "enabled": False,
        "min_bowls": 2,
        "amount_off": 0.0,
    }


def normalize_order_discount_rule(raw_value: Any) -> Dict[str, Any]:
    """Normalize discount settings from storage into a predictable shape."""
    rule = get_default_order_discount_rule()
    if not isinstance(raw_value, dict):
        return rule

    try:
        min_bowls = int(raw_value.get("min_bowls", rule["min_bowls"]) or rule["min_bowls"])
    except (TypeError, ValueError):
        min_bowls = rule["min_bowls"]

    try:
        amount_off = float(raw_value.get("amount_off", rule["amount_off"]) or 0)
    except (TypeError, ValueError):
        amount_off = rule["amount_off"]

    rule["enabled"] = bool(raw_value.get("enabled", False))
    rule["min_bowls"] = max(1, min_bowls)
    rule["amount_off"] = max(0.0, amount_off)
    return rule


def calculate_order_totals(subtotal: float, total_bowls: int, discount_rule: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Calculate final order totals after applying a fixed discount rule."""
    normalized_rule = normalize_order_discount_rule(discount_rule)
    safe_subtotal = max(0.0, float(subtotal or 0))
    safe_total_bowls = max(0, int(total_bowls or 0))

    discount_applied = (
        normalized_rule["enabled"]
        and normalized_rule["amount_off"] > 0
        and safe_total_bowls >= normalized_rule["min_bowls"]
        and safe_subtotal > 0
    )
    discount_amount = min(safe_subtotal, normalized_rule["amount_off"]) if discount_applied else 0.0
    total_price = max(0.0, safe_subtotal - discount_amount)

    return {
        "subtotal": round(safe_subtotal, 2),
        "discount_amount": round(discount_amount, 2),
        "total_price": round(total_price, 2),
        "total_bowls": safe_total_bowls,
        "discount_applied": discount_applied,
        "bowls_until_discount": max(normalized_rule["min_bowls"] - safe_total_bowls, 0),
        "discount_rule": normalized_rule,
    }


def format_currency(amount: float) -> str:
    """Format amount as Singapore dollars."""
    return f"${amount:.2f}"


def parse_datetime(dt_string: str) -> Optional[datetime]:
    """Parse datetime string in ISO or 'YYYY-MM-DD HH:MM' formats."""
    if not dt_string:
        return None
    try:
        return datetime.fromisoformat(dt_string.replace('Z', '+00:00'))
    except ValueError:
        try:
            return datetime.strptime(dt_string, '%Y-%m-%d %H:%M')
        except ValueError:
            return None


def is_delivery_active(cutoff_time: str) -> bool:
    """Check if a delivery session is still accepting orders based on cutoff time."""
    cutoff_dt = parse_datetime(cutoff_time)
    if not cutoff_dt:
        return False
    try:
        from zoneinfo import ZoneInfo
    except ImportError:
        ZoneInfo = None
    now = datetime.now(ZoneInfo("Asia/Singapore")) if ZoneInfo else datetime.now()
    if cutoff_dt.tzinfo is None:
        return now.replace(tzinfo=None) < cutoff_dt
    if not now.tzinfo:
        now = now.replace(tzinfo=cutoff_dt.tzinfo)
    return now < cutoff_dt


def format_order_summary(order_data: Dict[str, Any]) -> str:
    """Format order data into a readable summary."""
    quantity = order_data.get('quantity', 0)
    unit_price = order_data.get('unit_price')
    price = calculate_price(quantity, unit_price or 8.0)
    delivery = order_data.get('delivery', {})
    delivery_label = delivery.get('display_label') or delivery.get('location', 'N/A')
    delivery_time = delivery.get('display_time') or delivery.get('delivery_datetime') or delivery.get('datetime', 'N/A')

    menu_selections: List[Dict[str, Any]] = order_data.get('menu_selections') or []

    price_lines = [f"💰 Total: {format_currency(price)}"]
    if unit_price is not None:
        price_lines.append(f"(Price per bowl: {format_currency(unit_price)})")

    selection_lines: List[str] = []
    if menu_selections:
        selection_lines.append("🍧 **Selections:**")
        for selection in menu_selections:
            selection_lines.append(f"• {selection.get('title', 'Option')}: {selection.get('value', 'N/A')}")
    else:
        flavor = order_data.get('flavor', 'N/A')
        sauce = order_data.get('sauce', 'N/A')
        selection_lines.append(f"🍧 Flavor: {flavor}")
        selection_lines.append(f"🍯 Sauce: {sauce}")

    summary_parts = [
        "📋 **Order Summary**",
        "",
        *selection_lines,
        f"📦 Quantity: {quantity}",
        "\n".join(price_lines),
        "",
        f"📍 Delivery: {delivery_label}",
        f"🕐 Time: {delivery_time}",
    ]

    return "\n".join(summary_parts).strip()


def generate_delivery_id() -> str:
    """Generate a unique delivery ID based on timestamp."""
    return datetime.now().strftime('%Y%m%d%H%M%S')


def load_users() -> Dict[str, Dict]:
    """Load users from JSON file (legacy function for backward compatibility)."""
    users_file = 'data/users.json'
    return read_json(users_file)


def save_users(users: Dict[str, Dict]) -> bool:
    """Save users to JSON file (legacy function for backward compatibility)."""
    users_file = 'data/users.json'
    return write_json(users_file, users)
