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


def format_currency(amount: float) -> str:
    """Format amount as Singapore dollars."""
    return f"${amount:.2f}"


def parse_datetime(dt_string: str) -> Optional[datetime]:
    """Parse datetime string in format 'YYYY-MM-DD HH:MM'."""
    try:
        return datetime.strptime(dt_string, '%Y-%m-%d %H:%M')
    except ValueError:
        return None


def is_delivery_active(cutoff_time: str) -> bool:
    """Check if a delivery session is still accepting orders based on cutoff time."""
    cutoff_dt = parse_datetime(cutoff_time)
    if not cutoff_dt:
        return False
    return datetime.now() < cutoff_dt


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
