"""Menu data helpers shared between bot flows."""
import logging
import time
from typing import Dict, List, Tuple
from database.supabase_client import get_db

logger = logging.getLogger(__name__)

# Cache with timestamp: (data, timestamp)
_MENU_CACHE: Tuple[Dict[str, object], float] | None = None
_BRANDING_CACHE: Tuple[Dict[str, str], float] | None = None

# Cache expiration time in seconds (5 minutes)
CACHE_TTL = 300


def get_menu_data(force_refresh: bool = False) -> Dict[str, object]:
    """Fetch menu groups (first group has per-option pricing) from Supabase with fallback."""

    try:
        db = get_db()
        groups = db.get_menu_groups()
    except Exception as exc:
        logger.warning("Failed to load menu from Supabase, using defaults: %s", exc)
        groups = [
            {
                "id": "flavor",
                "key": "flavor",
                "title": "Menu Flavors",
                "options": [
                    {"name": "Classic Acai", "price": 8.0},
                    {"name": "Protein Acai", "price": 9.0},
                    {"name": "Vegan Acai", "price": 8.5},
                ],
            },
            {
                "id": "sauce",
                "key": "sauce",
                "title": "Sauce Options",
                "options": ["Honey", "Peanut Butter", "Nutella", "No Sauce"],
            },
        ]

    # Sanity check groups
    sanitized_groups = []
    for index, group in enumerate(groups):
        options = group.get("options") or []
        if not options:
            continue
        sanitized_groups.append({
            "id": group.get("id") or f"group_{index}",
            "key": group.get("key") or group.get("id") or f"group_{index}",
            "title": group.get("title") or f"Option Group {index + 1}",
            "options": options
        })

    if not sanitized_groups:
        sanitized_groups = [
            {
                "id": "flavor",
                "key": "flavor",
                "title": "Menu Flavors",
                "options": [
                    {"name": "Classic Acai", "price": 8.0},
                ],
            }
        ]

    menu_data = {
        "groups": sanitized_groups,
    }
    return menu_data


def invalidate_menu_cache():
    """Clear cached menu data."""
    global _MENU_CACHE
    _MENU_CACHE = None


def get_bot_branding(force_refresh: bool = False) -> Dict[str, str]:
    """Fetch branding configuration for bot messaging."""
    global _BRANDING_CACHE

    # Check if cache is valid (exists and not expired)
    if _BRANDING_CACHE and not force_refresh:
        data, timestamp = _BRANDING_CACHE
        if time.time() - timestamp < CACHE_TTL:
            return data
        else:
            logger.info("Branding cache expired, refreshing from database")

    try:
        db = get_db()
        branding = db.get_bot_branding()
    except Exception as exc:
        logger.warning("Failed to load branding from Supabase: %s", exc)
        branding = {
            "title": "🍧 Welcome to Acai Supper Bot!",
            "subtitle": "I help you order delicious acai bowls for delivery or pickup.",
            "image_url": ""
        }

    _BRANDING_CACHE = (branding, time.time())
    return branding


def invalidate_branding_cache():
    """Clear cached branding data."""
    global _BRANDING_CACHE
    _BRANDING_CACHE = None
