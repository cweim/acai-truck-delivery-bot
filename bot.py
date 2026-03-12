"""
Acai Supper Bot - Main Application Entry Point
Telegram bot for managing acai bowl orders with delivery sessions
"""
import os
import sys
import logging
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Enable debug logging for telegram conversation handler
logging.getLogger('telegram.ext.ConversationHandler').setLevel(logging.DEBUG)

# Add handlers to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from handlers.order_flow import get_order_conversation_handler
from handlers.payment_handler import get_payment_conversation_handler
from handlers.profile_handler import get_profile_conversation_handler
from constants import (
    ORDER_BUTTON_TEXT,
    HELP_BUTTON_TEXT,
    START_OVER_BUTTON_TEXT,
    SHOW_MENU_BUTTON_TEXT,
    SHOW_DELIVERIES_BUTTON_TEXT,
    CHANGE_NAME_BUTTON_TEXT,
    RESTART_ORDER_BUTTON_TEXT,
    CANCEL_ORDER_BUTTON_TEXT,
    WELCOME_TITLE,
)
from keyboards import get_main_keyboard, get_order_keyboard
from database.supabase_client import get_db
from utils import read_json, format_currency, is_delivery_active
from menu import get_menu_data, get_bot_branding

# Load environment variables
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise ValueError("BOT_TOKEN not found in .env file!")


def _format_datetime_label(raw_value: str | None) -> str:
    if not raw_value:
        return "Unknown"
    try:
        dt = datetime.fromisoformat(raw_value)
    except ValueError:
        # Attempt to parse legacy "YYYY-MM-DD HH:MM"
        try:
            dt = datetime.strptime(raw_value, "%Y-%m-%d %H:%M")
        except ValueError:
            return raw_value
    return dt.strftime("%a, %d %b %Y • %I:%M %p")


def _get_active_deliveries():
    try:
        db = get_db()
        deliveries = db.get_active_deliveries()
    except Exception as exc:
        logger.warning("Falling back to JSON deliveries: %s", exc)
        deliveries = [
            delivery for delivery in read_json("data/deliveries.json")
            if delivery.get("status") == "open" and is_delivery_active(delivery.get("cutoff_time", ""))
        ]
    def _sort_key(item):
        return item.get("delivery_datetime") or item.get("datetime") or ""

    return sorted(deliveries, key=_sort_key)


async def _send_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send menu details sourced from Supabase settings."""
    # Force refresh so latest menu (with per-option prices) is shown immediately
    menu = get_menu_data(force_refresh=True)
    groups = menu.get("groups", [])
    menu_image = None
    try:
        from database.supabase_client import get_db
        menu_image = get_db().get_menu_image()
    except Exception:
        menu_image = None

    message_lines = ["📋 **Our Menu**", ""]

    # Display each menu group dynamically
    for idx, group in enumerate(groups):
        title = group.get("title", "Options")
        options = group.get("options", [])
        if options:
            if idx == 0:
                message_lines.append(f"🍧 **{title}** (choose one)")
            else:
                message_lines.append(f"✨ **{title}**")
            for option in options:
                if isinstance(option, dict):
                    name = option.get("name") or option.get("title") or option.get("label") or "Option"
                    if idx == 0 and option.get("price") is not None:
                        message_lines.append(f"• {name} — ${float(option.get('price')):.2f}")
                    else:
                        message_lines.append(f"• {name}")
                else:
                    message_lines.append(f"• {option}")
            message_lines.append("")

    message = "\n".join(message_lines).rstrip()

    if menu_image:
        try:
            await update.message.reply_photo(
                photo=menu_image,
                caption=message,
                reply_markup=get_main_keyboard(),
                parse_mode="Markdown"
            )
            return
        except Exception:
            # Fallback to text if photo send fails
            pass

    await update.message.reply_text(
        message,
        reply_markup=get_main_keyboard(),
        parse_mode="Markdown"
    )


async def _send_delivery_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send upcoming delivery sessions."""
    user_id = update.effective_user.id
    deliveries = _get_active_deliveries()

    if not deliveries:
        await update.message.reply_text(
            "🚚 There are no active delivery sessions at the moment. Please check back later!",
            reply_markup=get_main_keyboard()
        )
        return

    lines = []
    for delivery in deliveries:
        label = _format_datetime_label(
            delivery.get("delivery_datetime") or delivery.get("datetime")
        )
        cutoff_label = _format_datetime_label(delivery.get("cutoff_time"))
        lines.append(
            f"• **{delivery.get('location', 'Unknown Location')}**\n"
            f"  🕒 Delivery: {label}\n"
            f"  ⏰ Cutoff: {cutoff_label}"
        )

    message = "🚚 **Upcoming Deliveries**\n\n" + "\n\n".join(lines)
    await update.message.reply_text(
        message,
        reply_markup=get_main_keyboard(),
        parse_mode="Markdown"
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send welcome message when /start is issued"""
    branding = get_bot_branding()
    title = branding.get("title", "🍧 Welcome to Acai Supper Bot!")
    subtitle = branding.get("subtitle", "I help you order delicious acai bowls for delivery.")
    image_url = branding.get("image_url", "")

    welcome_message = f"""
**{title}**

{subtitle}

**What you can do:**
• Tap **Order Now** to start a new delivery order
• Use **Show Menu** to preview flavors, sauces, and prices
• Check **Show Deliveries** for upcoming sessions
• Use **Change Name** if you want to update your saved profile name
• Tap **❓ Help** anytime for guidance

Ready for your treat? Tap **🍧 Order Now** or type `/order`! 🎉
"""

    # Send image if available
    if image_url and image_url.strip():
        try:
            await update.message.reply_photo(
                photo=image_url,
                caption=welcome_message,
                reply_markup=get_main_keyboard(),
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.warning(f"Failed to send branding image: {e}")
            # Fallback to text-only message
            await update.message.reply_text(
                welcome_message,
                reply_markup=get_main_keyboard(),
                parse_mode='Markdown'
            )
    else:
        await update.message.reply_text(
            welcome_message,
            reply_markup=get_main_keyboard(),
            parse_mode='Markdown'
        )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send help message"""
    help_message = """
📖 **How to Order**

1️⃣ Tap **Order Now** or type `/order`  
2️⃣ Choose a **delivery session** that fits your schedule  
3️⃣ Select flavor, sauce, and quantity  
4️⃣ Confirm and pay via the QR code  
5️⃣ Upload your payment screenshot

We'll process your order right after payment is submitted. 🍧

**Need a refresher?**
- Use **Show Menu** to see flavors, sauces, and prices  
- Tap **Show Deliveries** for upcoming sessions and cutoffs
- Use **Change Name** or `/editname` to update your saved name

If anything goes wrong, tap **🔄 Restart Order** or **❌ Cancel Order**, or contact @TheacaitruckXNUS.
"""
    await update.message.reply_text(
        help_message,
        reply_markup=get_main_keyboard(),
        parse_mode='Markdown'
    )


async def debug_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Debug callback queries to see if they're being received"""
    if update.callback_query:
        logger.info(f"🔍 DEBUG: Received callback query: {update.callback_query.data}")
        logger.info(f"🔍 DEBUG: From user: {update.effective_user.id}")
        logger.info(f"🔍 DEBUG: Chat ID: {update.effective_chat.id}")


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Log errors caused by updates"""
    logger.error(f"❌ Update {update} caused error {context.error}")
    print(f"Update {update} caused error {context.error}")

    if update and update.effective_message:
        await update.effective_message.reply_text(
            "⚠️ An error occurred while processing your request. "
            "Please try again or contact the admin."
        )


async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button presses from main menu - only specific button texts"""
    text = update.message.text

    button_texts = {
        ORDER_BUTTON_TEXT,
        HELP_BUTTON_TEXT,
        START_OVER_BUTTON_TEXT,
        SHOW_MENU_BUTTON_TEXT,
        SHOW_DELIVERIES_BUTTON_TEXT,
        CHANGE_NAME_BUTTON_TEXT,
        RESTART_ORDER_BUTTON_TEXT,
        CANCEL_ORDER_BUTTON_TEXT,
    }

    # Only handle if it's a button press, not free text
    if text not in button_texts:
        return  # Let other handlers process it

    if text == ORDER_BUTTON_TEXT:
        logger.debug("Order Now button pressed; conversation handler will take over.")
        return

    if text == HELP_BUTTON_TEXT:
        return await help_command(update, context)

    if text == START_OVER_BUTTON_TEXT:
        # Clear any ongoing conversation and restart
        context.user_data.clear()
        logger.info("User requested start over, clearing context")
        return await start(update, context)

    if text == SHOW_MENU_BUTTON_TEXT:
        return await _send_menu(update, context)

    if text == SHOW_DELIVERIES_BUTTON_TEXT:
        return await _send_delivery_schedule(update, context)

    if text == RESTART_ORDER_BUTTON_TEXT:
        logger.info("User requested to restart order via keyboard.")
        context.user_data.clear()
        # Restart flow by sending welcome again
        return await start(update, context)

    if text == CANCEL_ORDER_BUTTON_TEXT:
        logger.info("User requested to cancel order via keyboard.")
        context.user_data.clear()
        await update.message.reply_text(
            "❌ Order cancelled.",
            parse_mode="Markdown"
        )
        return await start(update, context)


def main():
    """Start the bot"""
    print("🚀 Starting Acai Supper Bot...")
    print(f"📱 Bot Token: {TOKEN[:10]}...")

    # Create application
    application = Application.builder().token(TOKEN).build()

    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))

    # Add conversation handlers
    order_handler = get_order_conversation_handler()
    logger.info(f"Order conversation handler created with {len(order_handler.states)} states")
    application.add_handler(order_handler)

    profile_handler = get_profile_conversation_handler()
    logger.info("Profile conversation handler created")
    application.add_handler(profile_handler)

    # Payment handler integrated into order flow, so we need a separate one for direct /payment command
    payment_handler = get_payment_conversation_handler()
    logger.info(f"Payment conversation handler created")
    application.add_handler(payment_handler)

    # Add debug callback query handler (lower priority, group=1, so it doesn't interfere)
    # from telegram.ext import CallbackQueryHandler
    # application.add_handler(CallbackQueryHandler(debug_callback_query), group=1)

    # Add button handler (must be after conversation handlers)
    from telegram.ext import MessageHandler, filters
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handle_button
    ))

    # Add error handler
    application.add_error_handler(error_handler)

    # Start bot
    print("✅ Bot is running! Press Ctrl+C to stop.")
    logger.info("Bot started and ready to receive updates")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
