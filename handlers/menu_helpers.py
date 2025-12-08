"""Shared helper functions for dynamic menu selections in bot flows."""
from typing import Any, Dict, List
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from menu import get_menu_data


def cache_menu_data(context: ContextTypes.DEFAULT_TYPE) -> Dict[str, Any]:
    """Load menu data and cache it in the user context."""
    # Force refresh so pricing/menu changes reflect immediately in bot sessions
    menu = get_menu_data(force_refresh=True)
    context.user_data['menu_groups'] = menu.get('groups', [])
    context.user_data['menu_pricing'] = menu.get('pricing', {})
    return menu


def get_menu_groups(context: ContextTypes.DEFAULT_TYPE) -> List[Dict[str, Any]]:
    groups = context.user_data.get('menu_groups')
    if not groups:
        groups = cache_menu_data(context).get('menu_groups', [])
        context.user_data['menu_groups'] = groups
    return groups


def reset_menu_selection(context: ContextTypes.DEFAULT_TYPE):
    context.user_data['menu_index'] = 0
    context.user_data['menu_choices'] = {}
    context.user_data['menu_selections'] = []


def build_menu_keyboard(group: Dict[str, Any], index: int) -> InlineKeyboardMarkup:
    keyboard = []
    for option_index, option in enumerate(group.get('options', [])):
        keyboard.append([InlineKeyboardButton(option, callback_data=f"menu_{index}_{option_index}")])
    keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel")])
    return InlineKeyboardMarkup(keyboard)


def accumulate_menu_selections(context: ContextTypes.DEFAULT_TYPE):
    groups = get_menu_groups(context)
    choices = context.user_data.get('menu_choices', {})
    selections = []
    for idx, group in enumerate(groups):
        value = choices.get(idx)
        if value:
            selections.append({
                "title": group.get('title', f"Option {idx + 1}"),
                "value": value,
                "key": group.get('key') or group.get('id') or f"option_{idx}"
            })
    context.user_data['menu_selections'] = selections

    if selections:
        context.user_data['flavor'] = selections[0]['value']
        extras = [f"{sel['title']}: {sel['value']}" for sel in selections[1:]]
        context.user_data['sauce'] = "; ".join(extras) if extras else selections[0]['value']
    else:
        context.user_data['flavor'] = "Classic Acai"
        context.user_data['sauce'] = ""


async def prompt_menu_option_via_query(query, context: ContextTypes.DEFAULT_TYPE) -> str:
    groups = get_menu_groups(context)
    index = context.user_data.get('menu_index', 0)

    if index >= len(groups):
        accumulate_menu_selections(context)
        await prompt_quantity_via_query(query, context)
        return "quantity"

    group = groups[index]
    keyboard = build_menu_keyboard(group, index)

    await query.edit_message_text(
        f"{group.get('title', 'Please select an option')}:",
        reply_markup=keyboard,
        parse_mode='Markdown'
    )
    return "menu"


async def prompt_menu_option_via_message(message, context: ContextTypes.DEFAULT_TYPE) -> str:
    groups = get_menu_groups(context)
    index = context.user_data.get('menu_index', 0)

    if index >= len(groups):
        accumulate_menu_selections(context)
        await prompt_quantity_via_message(message, context)
        return "quantity"

    group = groups[index]
    keyboard = build_menu_keyboard(group, index)

    await message.reply_text(
        f"{group.get('title', 'Please select an option')}:",
        reply_markup=keyboard,
        parse_mode='Markdown'
    )
    return "menu"


async def start_menu_selection_from_query(query, context: ContextTypes.DEFAULT_TYPE):
    reset_menu_selection(context)
    return await prompt_menu_option_via_query(query, context)


async def start_menu_selection_from_message(message, context: ContextTypes.DEFAULT_TYPE):
    reset_menu_selection(context)
    return await prompt_menu_option_via_message(message, context)


async def prompt_quantity_via_query(query, context: ContextTypes.DEFAULT_TYPE):
    keyboard = []
    for i in range(1, 6):
        keyboard.append([InlineKeyboardButton(f"{i} bowl(s)", callback_data=f"qty_{i}")])
    keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel")])

    await query.edit_message_text(
        "📦 **Select Quantity:**",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )
    return None


async def prompt_quantity_via_message(message, context: ContextTypes.DEFAULT_TYPE):
    keyboard = []
    for i in range(1, 6):
        keyboard.append([InlineKeyboardButton(f"{i} bowl(s)", callback_data=f"qty_{i}")])
    keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel")])

    await message.reply_text(
        "📦 **Select Quantity:**",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )
    return None
