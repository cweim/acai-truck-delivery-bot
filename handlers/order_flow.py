"""Order flow conversation handler - guides users through ordering process"""
import logging
import os
import re
import sys
from datetime import datetime
from typing import Any, Dict, List
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, ConversationHandler, CommandHandler,
    CallbackQueryHandler, MessageHandler, filters
)

# Set up logging
logger = logging.getLogger(__name__)

# Add parent directory to path to import utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import read_json, write_json, is_delivery_active, format_order_summary, generate_delivery_id, calculate_price
from database.supabase_client import get_db
from handlers.payment_handler import (
    send_payment_qr,
    receive_payment_screenshot,
    cancel_payment,
)
from keyboards import get_order_keyboard, get_main_keyboard
from constants import ORDER_BUTTON_TEXT, RESTART_ORDER_BUTTON_TEXT, CANCEL_ORDER_BUTTON_TEXT
from handlers.menu_helpers import (
    cache_menu_data,
    get_menu_groups,
    accumulate_menu_selections,
    start_menu_selection_from_query,
    start_menu_selection_from_message,
    prompt_menu_option_via_query,
)

# Conversation states
SELECT_DELIVERY, REGISTER_NAME, REGISTER_PHONE, MENU_SELECTION, QUANTITY, ADD_MORE_ITEMS, CONFIRM, PAYMENT = range(8)


def _format_datetime_label(raw_value: str | None) -> str:
    if not raw_value:
        return "Unknown"
    for pattern in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            dt = datetime.strptime(raw_value, pattern)
            break
        except ValueError:
            dt = None
    if not dt:
        try:
            dt = datetime.fromisoformat(raw_value)
        except ValueError:
            return raw_value
    return dt.strftime("%a, %d %b %Y • %I:%M %p")


def _load_active_delivery_sessions() -> List[Dict[str, Any]]:
    """Fetch active delivery sessions from Supabase with JSON fallback."""
    try:
        db = get_db()
        active_deliveries = db.get_active_deliveries()
        logger.info("Loaded %d active deliveries from Supabase", len(active_deliveries))
        return active_deliveries
    except Exception as exc:
        logger.error("Error loading deliveries from Supabase: %s", exc)
        deliveries = read_json('data/deliveries.json')
        fallback = [
            d for d in deliveries
            if d.get('status') == 'open' and is_delivery_active(d.get('cutoff_time'))
        ]
        logger.info("Loaded %d active deliveries from JSON fallback", len(fallback))
        return fallback


async def _maybe_handle_control_text(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    """Handle restart/cancel buttons pressed during text input."""
    if text == CANCEL_ORDER_BUTTON_TEXT:
        return await cancel_order(update, context)

    if text == RESTART_ORDER_BUTTON_TEXT:
        context.user_data.clear()
        await update.message.reply_text(
            "🔄 Order restarted. Tap **Order Now** to begin again!",
            reply_markup=get_main_keyboard(),
            parse_mode='Markdown'
        )
        return ConversationHandler.END

    return None


async def start_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the order flow and prompt for delivery session selection."""
    logger.info(f"User {update.effective_user.id} started order flow")
    logger.info(f"Update type: message={update.message is not None}, callback_query={update.callback_query is not None}")

    # Reset any previous order context so we start fresh
    context.user_data.clear()
    cache_menu_data(context)
    context.user_data['order_type'] = 'delivery'

    active_deliveries = _load_active_delivery_sessions()
    if not active_deliveries:
        logger.warning("No active deliveries available when user attempted to order")
        await update.message.reply_text(
            "⚠️ Sorry, there are no active delivery sessions at the moment.\n"
            "Please check back later or contact the admin team.",
            reply_markup=get_main_keyboard()
        )
        return ConversationHandler.END

    keyboard = []
    for delivery in active_deliveries:
        delivery_time = delivery.get('delivery_datetime') or delivery.get('datetime')
        label = _format_datetime_label(delivery_time)
        location = delivery.get('location', 'Unknown Location')
        button_text = f"{location} • {label}"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"delivery_{delivery['id']}")])

    keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    prompt_message = await update.message.reply_text(
        "🚚 **Select Delivery Session:**\n\n"
        "Choose when you'd like your order delivered:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

    logger.info("Delivery selection menu sent (message_id=%s)", prompt_message.message_id)
    context.user_data['order_message_id'] = prompt_message.message_id

    if update.message:
        await update.message.reply_text(
            "Need to restart or cancel? Use the buttons below anytime.",
            reply_markup=get_order_keyboard()
        )

    return SELECT_DELIVERY


async def select_delivery(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle delivery selection"""
    query = update.callback_query
    await query.answer()

    logger.info(f"User {update.effective_user.id} selected delivery: {query.data}")

    if query.data == "cancel":
        logger.info("User cancelled order")
        await query.edit_message_text("❌ Order cancelled. Use /order to start again.")
        return ConversationHandler.END

    # Extract delivery ID
    delivery_id = query.data.replace("delivery_", "")
    logger.info(f"Looking for delivery ID: {delivery_id}")

    # Try to get delivery from Supabase, fallback to JSON
    try:
        db = get_db()
        selected_delivery = db.get_delivery_by_id(delivery_id)
        logger.info(f"Got delivery from Supabase: {selected_delivery}")
    except Exception as e:
        logger.error(f"Error getting delivery from Supabase: {e}, falling back to JSON")
        deliveries = read_json('data/deliveries.json')
        selected_delivery = next((d for d in deliveries if d['id'] == delivery_id), None)

    if not selected_delivery:
        logger.error(f"Delivery {delivery_id} not found")
        await query.edit_message_text("⚠️ Delivery not found. Please try again.")
        return ConversationHandler.END

    # Handle both 'datetime' (old JSON) and 'delivery_datetime' (Supabase)
    datetime_str = selected_delivery.get('delivery_datetime') or selected_delivery.get('datetime', 'N/A')
    display_label = _format_datetime_label(datetime_str)
    selected_delivery['display_label'] = selected_delivery.get('location', 'Unknown Location')
    selected_delivery['display_time'] = display_label
    logger.info(f"Selected delivery: {selected_delivery['location']} at {datetime_str}")

    # Store delivery in context
    context.user_data['delivery'] = selected_delivery

    # Check if user is registered (Supabase first, then local cache)
    user_id = str(update.effective_user.id)
    logger.info(f"Checking if user {user_id} is registered")

    db = get_db()
    supa_user = db.get_user(int(user_id))
    if supa_user:
        logger.info(f"User {user_id} found in Supabase")
        context.user_data['user_info'] = {
            'name': supa_user.get('name') or 'Unknown',
            'handle': supa_user.get('telegram_handle') or update.effective_user.username or '',
            'phone': supa_user.get('phone') or 'Unknown'
        }
        result = await start_menu_selection_from_query(query, context)
        return QUANTITY if result == "quantity" else MENU_SELECTION

    users = read_json('data/users.json')
    if user_id in users:
        logger.info(f"User {user_id} found in local cache")
        context.user_data['user_info'] = users[user_id]
        result = await start_menu_selection_from_query(query, context)
        return QUANTITY if result == "quantity" else MENU_SELECTION

    # New user - collect name
    logger.info(f"User {user_id} is new, requesting registration")
    await query.edit_message_text(
        "👤 **User Registration**\n\n"
        "Please enter your full name:",
        parse_mode='Markdown'
    )
    return REGISTER_NAME


async def register_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Collect user's name"""
    text = update.message.text.strip()

    maybe_result = await _maybe_handle_control_text(update, context, text)
    if maybe_result is not None:
        return maybe_result

    name = text

    if len(name) < 2:
        await update.message.reply_text("⚠️ Please enter a valid name (at least 2 characters).")
        return REGISTER_NAME

    context.user_data['name'] = name

    await update.message.reply_text(
        "📱 **Phone Number**\n\n"
        "Please enter your phone number (for delivery contact):",
        parse_mode='Markdown'
    )
    return REGISTER_PHONE


async def register_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Collect user's phone number and save to users.json"""
    text = update.message.text.strip()

    maybe_result = await _maybe_handle_control_text(update, context, text)
    if maybe_result is not None:
        return maybe_result

    phone = text

    if len(phone) < 8:
        await update.message.reply_text("⚠️ Please enter a valid phone number.")
        return REGISTER_PHONE

    # Save user info
    user_id = str(update.effective_user.id)
    user_handle = update.effective_user.username or "N/A"

    user_info = {
        'name': context.user_data['name'],
        'handle': user_handle,
        'phone': phone
    }

    # Persist to Supabase
    try:
        db = get_db()
        db.create_or_update_user(
            telegram_user_id=int(user_id),
            name=user_info['name'],
            telegram_handle=user_handle,
            phone=phone
        )
    except Exception as exc:
        logger.warning(f"Failed to save user to Supabase: {exc}")

    # Fallback local cache
    users = read_json('data/users.json')
    users[user_id] = user_info
    write_json('data/users.json', users)

    context.user_data['user_info'] = user_info

    await update.message.reply_text("✅ Registration complete!\n")

    # Show flavor options
    result = await start_menu_selection_from_message(update.message, context)
    return QUANTITY if result == "quantity" else MENU_SELECTION


async def handle_menu_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle dynamic menu option selections."""
    query = update.callback_query
    await query.answer()

    if query.data == "cancel":
        await query.edit_message_text("❌ Order cancelled. Use /order to start again.")
        return ConversationHandler.END

    match = re.match(r"menu_(\d+)_(\d+)", query.data)
    if not match:
        await query.answer("Invalid selection", show_alert=True)
        return MENU_SELECTION

    group_index = int(match.group(1))
    option_index = int(match.group(2))
    groups = get_menu_groups(context)

    if group_index >= len(groups):
        await query.answer("Option expired", show_alert=True)
        return MENU_SELECTION

    options = groups[group_index].get('options', [])
    if option_index >= len(options):
        await query.answer("Option unavailable", show_alert=True)
        return MENU_SELECTION

    selected_option = options[option_index]
    context.user_data.setdefault('menu_choices', {})[group_index] = selected_option
    if group_index == 0:
        # If option is dict with price, capture it
        if isinstance(selected_option, dict):
            context.user_data['main_option_price'] = selected_option.get('price', 0)
            context.user_data['flavor'] = selected_option.get('name', '')
        else:
            context.user_data['main_option_price'] = 0
            context.user_data['flavor'] = str(selected_option)
    context.user_data['menu_index'] = group_index + 1

    result = await prompt_menu_option_via_query(query, context)
    return QUANTITY if result == "quantity" else MENU_SELECTION


async def select_quantity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle quantity selection and add item to cart"""
    query = update.callback_query
    await query.answer()

    if query.data == "cancel":
        await query.edit_message_text("❌ Order cancelled. Use /order to start again.")
        return ConversationHandler.END

    quantity = int(query.data.replace("qty_", ""))

    main_price = context.user_data.get('main_option_price')
    if main_price is None:
        # Fallback: reload menu and try to derive from first group selection
        cache_menu_data(context)
        main_price = context.user_data.get('main_option_price', 8.0)
    unit_price = float(main_price or 0)

    # Ensure selections are captured
    accumulate_menu_selections(context)
    selections = context.user_data.get('menu_selections', [])

    flavor = context.user_data.get('flavor', selections[0]['value'] if selections else 'Classic Acai')
    sauce_text = context.user_data.get('sauce', '')

    # Add item to cart
    await add_item_to_cart(context, flavor, sauce_text, quantity, unit_price)

    # Show prompt to add more items or proceed
    return await prompt_add_more_items(query, context)


async def add_item_to_cart(context: ContextTypes.DEFAULT_TYPE, flavor: str, sauce: str, quantity: int, unit_price: float):
    """Add a selected item to the shopping cart"""
    # Initialize cart if it doesn't exist
    if 'cart' not in context.user_data:
        context.user_data['cart'] = []

    item = {
        'flavor': flavor,
        'sauce': sauce,
        'quantity': quantity,
        'unit_price': unit_price,
        'item_total': quantity * unit_price
    }

    context.user_data['cart'].append(item)

    # Update total price and quantity
    total_price = sum(item['item_total'] for item in context.user_data['cart'])
    total_quantity = sum(item['quantity'] for item in context.user_data['cart'])

    context.user_data['total_price'] = total_price
    context.user_data['total_quantity'] = total_quantity

    logger.info(f"Added item to cart: {flavor} x{quantity}. Cart now has {len(context.user_data['cart'])} items")


async def prompt_add_more_items(query, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Show current cart and ask if user wants to add more items"""
    cart = context.user_data.get('cart', [])
    total_price = context.user_data.get('total_price', 0)

    # Build cart summary
    cart_summary = "🛒 **Your Cart:**\n\n"
    for idx, item in enumerate(cart, 1):
        cart_summary += f"{idx}. {item['flavor']}"
        if item['sauce']:
            cart_summary += f" + {item['sauce']}"
        cart_summary += f" × {item['quantity']}"
        cart_summary += f" = ${item['item_total']:.2f}\n"

    cart_summary += f"\n**Total: ${total_price:.2f}**"

    keyboard = [
        [InlineKeyboardButton("➕ Add More Items", callback_data="add_more")],
        [InlineKeyboardButton("✅ Proceed to Payment", callback_data="proceed_payment")],
        [InlineKeyboardButton("❌ Cancel", callback_data="cancel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        cart_summary,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    return ADD_MORE_ITEMS


async def handle_add_more_items(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle user's choice to add more items or proceed to payment"""
    query = update.callback_query
    await query.answer()

    if query.data == "cancel":
        await query.edit_message_text("❌ Order cancelled. Use /order to start again.")
        return ConversationHandler.END

    if query.data == "add_more":
        # Reset menu selections for next item and go back to menu
        context.user_data['menu_choices'] = {}
        context.user_data['menu_index'] = 0
        result = await start_menu_selection_from_query(query, context)
        return QUANTITY if result == "quantity" else MENU_SELECTION

    elif query.data == "proceed_payment":
        # Show order confirmation with full cart
        return await show_order_confirmation(query, context)

    return ADD_MORE_ITEMS


async def show_order_confirmation(query, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Display full cart and confirm order before payment"""
    cart = context.user_data.get('cart', [])
    total_price = context.user_data.get('total_price', 0)
    delivery = context.user_data.get('delivery', {})

    # Build detailed cart summary
    summary = "✅ **Order Summary:**\n\n"
    summary += f"📍 **Delivery:** {delivery.get('location', 'Unknown')}\n"
    summary += f"🕐 **Time:** {delivery.get('display_time', 'N/A')}\n\n"
    summary += "**Items:**\n"

    for idx, item in enumerate(cart, 1):
        summary += f"{idx}. {item['flavor']}"
        if item['sauce']:
            summary += f" + {item['sauce']}"
        summary += f" × {item['quantity']}"
        summary += f" = ${item['item_total']:.2f}\n"

    summary += f"\n**Total Items:** {context.user_data.get('total_quantity', 0)}\n"
    summary += f"**Total Price:** ${total_price:.2f}\n\n"
    summary += "**Please confirm to proceed to payment:**"

    keyboard = [
        [InlineKeyboardButton("✅ Confirm Order", callback_data="confirm")],
        [InlineKeyboardButton("❌ Cancel", callback_data="cancel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        summary,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    return CONFIRM


async def confirm_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Confirm order and proceed to payment"""
    query = update.callback_query
    await query.answer()

    if query.data == "cancel":
        await query.edit_message_text("❌ Order cancelled. Use /order to start again.")
        return ConversationHandler.END

    # Generate order ID
    order_id = generate_delivery_id()
    context.user_data['order_id'] = order_id

    await query.edit_message_text(
        f"✅ **Order Confirmed!**\n\n"
        f"Order ID: `{order_id}`\n\n"
        f"Proceeding to payment...",
        parse_mode='Markdown'
    )

    # Trigger payment handler
    await send_payment_qr(update, context)

    logger.info(f"Transitioning to PAYMENT state for order {order_id}")
    return PAYMENT


async def request_payment_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Prompt user to send a payment screenshot when they send non-photo content"""
    text = (update.message.text or "").strip()
    if text:
        maybe_result = await _maybe_handle_control_text(update, context, text)
        if maybe_result is not None:
            return maybe_result

    await update.message.reply_text(
        "⚠️ Please upload your payment screenshot as a photo so we can verify it.\n"
        "You can also use /cancel to abort this order."
    )
    return PAYMENT


async def cancel_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel the order flow"""
    if context.user_data.get('order_id'):
        logger.info(f"User {update.effective_user.id} cancelled during payment stage")
        return await cancel_payment(update, context)

    logger.info(f"User {update.effective_user.id} cancelled order before completion")
    context.user_data.clear()
    await update.message.reply_text(
        "❌ Order cancelled. Tap **Order Now** whenever you're ready to try again!",
        reply_markup=get_main_keyboard(),
        parse_mode='Markdown'
    )
    return ConversationHandler.END


# Create the conversation handler
def get_order_conversation_handler():
    """Returns the configured ConversationHandler for orders"""
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler('order', start_order),
            MessageHandler(filters.Regex(rf"^{re.escape(ORDER_BUTTON_TEXT)}$"), start_order),
        ],
        states={
            SELECT_DELIVERY: [CallbackQueryHandler(select_delivery)],
            REGISTER_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, register_name)],
            REGISTER_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, register_phone)],
            MENU_SELECTION: [CallbackQueryHandler(handle_menu_selection)],
            QUANTITY: [CallbackQueryHandler(select_quantity)],
            ADD_MORE_ITEMS: [CallbackQueryHandler(handle_add_more_items)],
            CONFIRM: [CallbackQueryHandler(confirm_order)],
            PAYMENT: [
                MessageHandler(filters.PHOTO, receive_payment_screenshot),
                MessageHandler(filters.TEXT & ~filters.COMMAND, request_payment_screenshot),
            ],
        },
        fallbacks=[CommandHandler('cancel', cancel_order)],
        allow_reentry=True,
        name="ORDER_FLOW",  # Unique name for debugging
        persistent=False,
        per_chat=True,
        per_user=True,
        per_message=False,  # Must be False when mixing MessageHandlers and CallbackQueryHandlers
        conversation_timeout=600,  # 10 minute timeout
    )
    logger.info(f"Created ORDER_FLOW conversation handler with {len(conv_handler.states)} states")
    logger.info(f"Handler config: per_chat={conv_handler.per_chat}, per_user={conv_handler.per_user}, per_message={conv_handler.per_message}")
    return conv_handler
