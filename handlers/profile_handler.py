"""Profile update conversation handlers."""
import logging
import os
import re
import sys

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from constants import (
    CANCEL_ORDER_BUTTON_TEXT,
    CHANGE_NAME_BUTTON_TEXT,
    HELP_BUTTON_TEXT,
    ORDER_BUTTON_TEXT,
    RESTART_ORDER_BUTTON_TEXT,
    SHOW_DELIVERIES_BUTTON_TEXT,
    SHOW_MENU_BUTTON_TEXT,
    START_OVER_BUTTON_TEXT,
)
from database.supabase_client import get_db
from keyboards import get_main_keyboard
from utils import read_json, write_json

logger = logging.getLogger(__name__)

CHOOSE_FIELD, EDIT_NAME, EDIT_PHONE = range(3)

CONTROL_TEXTS = {
    ORDER_BUTTON_TEXT,
    HELP_BUTTON_TEXT,
    START_OVER_BUTTON_TEXT,
    SHOW_MENU_BUTTON_TEXT,
    SHOW_DELIVERIES_BUTTON_TEXT,
    CHANGE_NAME_BUTTON_TEXT,
    RESTART_ORDER_BUTTON_TEXT,
    CANCEL_ORDER_BUTTON_TEXT,
}


def _load_existing_user(user_id: str) -> dict:
    """Load the user's saved profile from Supabase or local fallback."""
    try:
        db = get_db()
        supa_user = db.get_user(int(user_id))
        if supa_user:
            return {
                "name": supa_user.get("name") or "Unknown",
                "handle": supa_user.get("telegram_handle") or "",
                "phone": supa_user.get("phone") or "Unknown",
            }
    except Exception as exc:
        logger.warning("Failed to load user from Supabase: %s", exc)

    users = read_json("data/users.json")
    return users.get(user_id, {})


async def start_profile_update(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry point for profile updates. Routes to inline chooser or directly based on command."""
    user_id = str(update.effective_user.id)
    existing_user = _load_existing_user(user_id)
    if not existing_user:
        await update.message.reply_text(
            "⚠️ I don't have a saved profile for you yet. Place your first order first, then you can edit your details anytime.",
            reply_markup=get_main_keyboard(),
        )
        return ConversationHandler.END

    context.user_data["profile_existing_user"] = existing_user
    text = (update.message.text or "").strip()

    # /editname → skip chooser, go straight to name prompt
    if text == "/editname":
        return await _prompt_name(update.message, existing_user)

    # /editphone → skip chooser, go straight to phone prompt
    if text == "/editphone":
        return await _prompt_phone(update.message, existing_user)

    # Button press → show inline chooser with current values
    current_name = existing_user.get("name") or "Unknown"
    current_phone = existing_user.get("phone") or "Unknown"
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📝 Update Name", callback_data="profile_name"),
            InlineKeyboardButton("📱 Update Number", callback_data="profile_phone"),
        ]
    ])
    await update.message.reply_text(
        f"👤 **Edit Profile**\n\n"
        f"Name: {current_name}\n"
        f"Phone: {current_phone}\n\n"
        "What would you like to update?",
        reply_markup=keyboard,
        parse_mode="Markdown",
    )
    return CHOOSE_FIELD


async def choose_field(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle inline keyboard selection of which field to edit."""
    query = update.callback_query
    await query.answer()

    existing_user = context.user_data.get("profile_existing_user") or _load_existing_user(
        str(update.effective_user.id)
    )
    context.user_data["profile_existing_user"] = existing_user

    if query.data == "profile_name":
        current_name = existing_user.get("name")
        if current_name and current_name != "Unknown":
            prompt = f"👤 Current name: **{current_name}**.\n\nSend your new name."
        else:
            prompt = "👤 Send the name you want the bot to use."
        await query.edit_message_text(f"{prompt}\n\nUse /cancel to stop.", parse_mode="Markdown")
        return EDIT_NAME

    # profile_phone
    current_phone = existing_user.get("phone")
    if current_phone and current_phone != "Unknown":
        prompt = f"📱 Current number: **{current_phone}**.\n\nSend your new phone number."
    else:
        prompt = "📱 Send your phone number (for delivery contact)."
    await query.edit_message_text(f"{prompt}\n\nUse /cancel to stop.", parse_mode="Markdown")
    return EDIT_PHONE


async def _prompt_name(message, existing_user: dict) -> int:
    """Send the name input prompt directly (used by /editname shortcut)."""
    current_name = existing_user.get("name")
    if current_name and current_name != "Unknown":
        prompt = f"👤 Current name: **{current_name}**.\n\nSend your new name."
    else:
        prompt = "👤 Send the name you want the bot to use."
    await message.reply_text(
        f"{prompt}\n\nUse /cancel to stop.",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove(),
    )
    return EDIT_NAME


async def _prompt_phone(message, existing_user: dict) -> int:
    """Send the phone input prompt directly (used by /editphone shortcut)."""
    current_phone = existing_user.get("phone")
    if current_phone and current_phone != "Unknown":
        prompt = f"📱 Current number: **{current_phone}**.\n\nSend your new phone number."
    else:
        prompt = "📱 Send your phone number (for delivery contact)."
    await message.reply_text(
        f"{prompt}\n\nUse /cancel to stop.",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove(),
    )
    return EDIT_PHONE


async def submit_name_update(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Persist a new name for the user profile."""
    text = update.message.text.strip()

    if text in CONTROL_TEXTS:
        await update.message.reply_text(
            "Name update cancelled.",
            reply_markup=get_main_keyboard(),
        )
        context.user_data.pop("profile_existing_user", None)
        return ConversationHandler.END

    if len(text) < 2:
        await update.message.reply_text("⚠️ Please enter a valid name (at least 2 characters).")
        return EDIT_NAME

    user_id = str(update.effective_user.id)
    existing_user = context.user_data.get("profile_existing_user") or _load_existing_user(user_id)
    user_handle = update.effective_user.username or existing_user.get("handle") or "N/A"
    phone = existing_user.get("phone") or "Unknown"

    updated_user = {"name": text, "handle": user_handle, "phone": phone}

    try:
        db = get_db()
        db.create_or_update_user(
            telegram_user_id=int(user_id),
            name=text,
            telegram_handle=user_handle,
            phone=phone,
        )
    except Exception as exc:
        logger.warning("Failed to update name in Supabase: %s", exc)

    users = read_json("data/users.json")
    users[user_id] = updated_user
    write_json("data/users.json", users)

    context.user_data["user_info"] = updated_user
    context.user_data.pop("profile_existing_user", None)

    await update.message.reply_text(
        f"✅ Your name has been updated to **{text}**.\nIt will be used for future orders.",
        parse_mode="Markdown",
        reply_markup=get_main_keyboard(),
    )
    return ConversationHandler.END


async def submit_phone_update(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Persist a new phone number for the user profile."""
    text = update.message.text.strip()

    if text in CONTROL_TEXTS:
        await update.message.reply_text(
            "Phone update cancelled.",
            reply_markup=get_main_keyboard(),
        )
        context.user_data.pop("profile_existing_user", None)
        return ConversationHandler.END

    if len(text) < 8:
        await update.message.reply_text("⚠️ Please enter a valid phone number (at least 8 digits).")
        return EDIT_PHONE

    user_id = str(update.effective_user.id)
    existing_user = context.user_data.get("profile_existing_user") or _load_existing_user(user_id)
    user_handle = update.effective_user.username or existing_user.get("handle") or "N/A"
    name = existing_user.get("name") or "Unknown"

    updated_user = {"name": name, "handle": user_handle, "phone": text}

    try:
        db = get_db()
        db.create_or_update_user(
            telegram_user_id=int(user_id),
            name=name,
            telegram_handle=user_handle,
            phone=text,
        )
    except Exception as exc:
        logger.warning("Failed to update phone in Supabase: %s", exc)

    users = read_json("data/users.json")
    users[user_id] = updated_user
    write_json("data/users.json", users)

    context.user_data["user_info"] = updated_user
    context.user_data.pop("profile_existing_user", None)

    await update.message.reply_text(
        f"✅ Your phone number has been updated to **{text}**.\nIt will be used for future orders.",
        parse_mode="Markdown",
        reply_markup=get_main_keyboard(),
    )
    return ConversationHandler.END


async def cancel_profile_update(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel any in-progress profile update."""
    context.user_data.pop("profile_existing_user", None)
    await update.message.reply_text(
        "Update cancelled.",
        reply_markup=get_main_keyboard(),
    )
    return ConversationHandler.END


def get_profile_conversation_handler() -> ConversationHandler:
    """Return the conversation handler for profile updates."""
    return ConversationHandler(
        entry_points=[
            CommandHandler("editname", start_profile_update),
            CommandHandler("editphone", start_profile_update),
            MessageHandler(filters.Regex(rf"^{re.escape(CHANGE_NAME_BUTTON_TEXT)}$"), start_profile_update),
        ],
        states={
            CHOOSE_FIELD: [CallbackQueryHandler(choose_field, pattern="^profile_(name|phone)$")],
            EDIT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, submit_name_update)],
            EDIT_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, submit_phone_update)],
        },
        fallbacks=[CommandHandler("cancel", cancel_profile_update)],
        allow_reentry=True,
        name="PROFILE_FLOW",
        persistent=False,
        per_chat=True,
        per_user=True,
        per_message=False,
        conversation_timeout=300,
    )
