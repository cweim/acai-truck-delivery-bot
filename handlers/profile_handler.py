"""Profile update conversation handlers."""
import logging
import os
import re
import sys

from telegram import ReplyKeyboardRemove, Update
from telegram.ext import CommandHandler, ContextTypes, ConversationHandler, MessageHandler, filters

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

EDIT_NAME = 1

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


async def start_name_update(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Prompt the user for a new display name."""
    user_id = str(update.effective_user.id)
    existing_user = _load_existing_user(user_id)
    if not existing_user:
        await update.message.reply_text(
            "⚠️ I don't have a saved profile for you yet. Place your first order first, then you can change your name anytime.",
            reply_markup=get_main_keyboard(),
        )
        return ConversationHandler.END

    context.user_data["profile_existing_user"] = existing_user

    current_name = existing_user.get("name")
    if current_name and current_name != "Unknown":
        prompt = (
            f"👤 Your current saved name is **{current_name}**.\n\n"
            "Send me your new name."
        )
    else:
        prompt = "👤 Send me the name you want the bot to use for future orders."

    message = update.message
    await message.reply_text(
        f"{prompt}\n\nUse /cancel to stop.",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove(),
    )
    return EDIT_NAME


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

    updated_user = {
        "name": text,
        "handle": user_handle,
        "phone": phone,
    }

    try:
        db = get_db()
        db.create_or_update_user(
            telegram_user_id=int(user_id),
            name=updated_user["name"],
            telegram_handle=updated_user["handle"],
            phone=updated_user["phone"],
        )
    except Exception as exc:
        logger.warning("Failed to update user in Supabase: %s", exc)

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


async def cancel_name_update(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel the name update flow."""
    context.user_data.pop("profile_existing_user", None)
    await update.message.reply_text(
        "Name update cancelled.",
        reply_markup=get_main_keyboard(),
    )
    return ConversationHandler.END


def get_profile_conversation_handler() -> ConversationHandler:
    """Return the conversation handler for profile updates."""
    return ConversationHandler(
        entry_points=[
            CommandHandler("editname", start_name_update),
            MessageHandler(filters.Regex(rf"^{re.escape(CHANGE_NAME_BUTTON_TEXT)}$"), start_name_update),
        ],
        states={
            EDIT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, submit_name_update)],
        },
        fallbacks=[CommandHandler("cancel", cancel_name_update)],
        allow_reentry=True,
        name="PROFILE_FLOW",
        persistent=False,
        per_chat=True,
        per_user=True,
        per_message=False,
        conversation_timeout=300,
    )
