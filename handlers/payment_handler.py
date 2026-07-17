"""Payment handler - manages QR code display and payment screenshot intake"""
import os
import sys
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, ConversationHandler, CommandHandler,
    CallbackQueryHandler, MessageHandler, filters
)

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import calculate_price, format_currency
from database.supabase_client import get_db
from keyboards import get_main_keyboard
from constants import RESTART_ORDER_BUTTON_TEXT, CANCEL_ORDER_BUTTON_TEXT
from dotenv import load_dotenv

load_dotenv()
ADMIN_ID = int(os.getenv('ADMIN_ID', '0'))

# Payment conversation states
AWAITING_SCREENSHOT = 1
CONFIRM_SCREENSHOT = 8  # High enough not to conflict with order_flow states (0-7)


async def send_payment_qr(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send the payment QR code to the user"""
    qr_path = 'data/qr.png'

    # Set default retry state for the confirm callback (order_flow overrides this to PAYMENT=7)
    if 'payment_retry_state' not in context.user_data:
        context.user_data['payment_retry_state'] = AWAITING_SCREENSHOT

    # Get order details from cart
    total = context.user_data.get('total_price', 0)
    total_quantity = context.user_data.get('total_quantity', 1)
    subtotal = context.user_data.get('subtotal_price', total)
    discount_amount = context.user_data.get('discount_amount', 0)
    discount_rule = context.user_data.get('order_discount_rule') or {}

    pricing_lines = [f"Total Items: {total_quantity}"]
    if discount_amount:
        pricing_lines.append(f"Subtotal: {format_currency(subtotal)}")
        pricing_lines.append(
            f"Discount ({discount_rule.get('min_bowls', 0)}+ bowls): -{format_currency(discount_amount)}"
        )
    pricing_lines.append(f"Total Amount: **{format_currency(total)}**")

    message = (
        f"💳 **Payment Required**\n\n"
        f"{chr(10).join(pricing_lines)}\n\n"
        f"Please:\n"
        f"1️⃣ Scan the QR code below to make payment\n"
        f"2️⃣ Take a screenshot of your payment confirmation\n"
        f"3️⃣ Upload the screenshot here\n\n"
        f"⚠️ Your order will be confirmed once payment is received."
    )

    # Check if QR code exists
    if os.path.exists(qr_path):
        # Send QR code image
        with open(qr_path, 'rb') as qr_file:
            if update.callback_query:
                await update.callback_query.message.reply_photo(
                    photo=qr_file,
                    caption=message,
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_photo(
                    photo=qr_file,
                    caption=message,
                    parse_mode='Markdown'
                )
    else:
        # QR code not found, send text message only
        if update.callback_query:
            await update.callback_query.message.reply_text(
                f"{message}\n\n⚠️ QR code image not configured. Please contact admin for payment details.",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                f"{message}\n\n⚠️ QR code image not configured. Please contact admin for payment details.",
                parse_mode='Markdown'
            )

    # Prompt for screenshot
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="📸 Please upload your payment screenshot now, or use /cancel to abort."
    )

    return AWAITING_SCREENSHOT


async def receive_payment_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle uploaded payment screenshot - echo back for user confirmation."""
    if not update.message.photo:
        text = (update.message.text or "").strip()
        if text == CANCEL_ORDER_BUTTON_TEXT:
            return await cancel_payment(update, context)
        if text == RESTART_ORDER_BUTTON_TEXT:
            context.user_data.clear()
            await update.message.reply_text(
                "🔄 Order restarted. Tap **Order Now** to begin again!",
                reply_markup=get_main_keyboard(),
                parse_mode='Markdown'
            )
            return ConversationHandler.END

        await update.message.reply_text("⚠️ Please upload an image (photo). Try again or /cancel.")
        return AWAITING_SCREENSHOT

    # Store file_id — actual upload/logging happens only after user confirms
    photo = update.message.photo[-1]
    context.user_data['pending_photo_file_id'] = photo.file_id

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Yes, that's correct", callback_data="yes_receipt"),
            InlineKeyboardButton("🔄 No, re-upload", callback_data="retry_receipt"),
        ]
    ])
    await update.message.reply_photo(
        photo=photo.file_id,
        caption="📸 Is this the correct payment screenshot?",
        reply_markup=keyboard,
    )
    return CONFIRM_SCREENSHOT


async def confirm_screenshot_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline confirmation of the payment screenshot."""
    query = update.callback_query
    await query.answer()

    if query.data == "retry_receipt":
        context.user_data.pop('pending_photo_file_id', None)
        await query.edit_message_caption("🔄 No problem! Please send your payment screenshot again.")
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="📸 Please upload your payment screenshot now, or use /cancel to abort."
        )
        # Return to whichever state was active before the confirmation step
        return context.user_data.get('payment_retry_state', AWAITING_SCREENSHOT)

    # "yes_receipt" — proceed to process
    await query.edit_message_caption("✅ Got it! Processing your payment...")
    await _process_confirmed_screenshot(update, context)
    return ConversationHandler.END


async def _process_confirmed_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Download, upload to storage, and log the confirmed payment screenshot."""
    file_id = context.user_data.get('pending_photo_file_id')
    order_id = context.user_data.get('order_id', 'unknown')
    screenshot_url = None

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="⏳ Processing your order..."
    )

    try:
        file = await context.bot.get_file(file_id)

        # Download to temporary location
        temp_dir = 'data/temp_screenshots'
        os.makedirs(temp_dir, exist_ok=True)
        temp_path = f"{temp_dir}/{order_id}.jpg"

        await file.download_to_drive(temp_path)

        # Upload to Supabase Storage
        db = get_db()
        screenshot_url = db.upload_payment_receipt(order_id, temp_path)

        if screenshot_url:
            print(f"✅ Screenshot uploaded to Supabase Storage: {screenshot_url}")
        else:
            print(f"⚠️ Supabase upload failed, using local storage as fallback")
            screenshot_dir = 'data/payment_screenshots'
            os.makedirs(screenshot_dir, exist_ok=True)
            screenshot_url = f"{screenshot_dir}/{order_id}.jpg"
            import shutil
            shutil.move(temp_path, screenshot_url)

        # Clean up temp file if it still exists
        if os.path.exists(temp_path):
            os.remove(temp_path)

    except Exception as e:
        print(f"❌ Error uploading to Supabase Storage: {e}")
        # Fallback to local storage
        try:
            file = await context.bot.get_file(file_id)
            screenshot_dir = 'data/payment_screenshots'
            os.makedirs(screenshot_dir, exist_ok=True)
            screenshot_url = f"{screenshot_dir}/{order_id}.jpg"
            await file.download_to_drive(screenshot_url)
        except Exception as e2:
            print(f"❌ Local fallback also failed: {e2}")
            screenshot_url = "upload_failed"

    # Log to Supabase
    try:
        user_id = update.effective_user.id
        user_info = context.user_data.get('user_info', {})
        order_type = context.user_data.get('order_type', 'delivery')
        quantity = context.user_data.get('quantity', 1)
        unit_price = context.user_data.get('unit_price')
        if unit_price is None:
            pricing = context.user_data.get('menu_pricing', {})
            unit_price = pricing.get('price_per_bowl', 8.0)
        total_price = calculate_price(quantity, unit_price)

        db = get_db()

        # Create or update user in database
        db.create_or_update_user(
            telegram_user_id=user_id,
            name=user_info.get('name', 'Unknown'),
            telegram_handle=user_info.get('handle', ''),
            phone=user_info.get('phone', 'Unknown')
        )

        if order_type == 'pickup':
            success = await log_pickup_order(update, context, payment_screenshot=screenshot_url)

            if success:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=(
                        f"🎉 **Pickup Order Complete!**\n\n"
                        f"Your order has been logged successfully.\n"
                        f"Order ID: `{order_id}`\n\n"
                        f"**Pickup Details:**\n"
                        f"🏪 Store: {context.user_data['pickup_store']['name']}\n"
                        f"📅 Date: {context.user_data['pickup_date_display']}\n"
                        f"🕐 Time: {context.user_data['pickup_time_display']}\n\n"
                        f"We'll verify your payment and prepare your order.\n"
                        f"Thank you! 🍧"
                    ),
                    reply_markup=get_main_keyboard(),
                    parse_mode='Markdown'
                )
            else:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=(
                        "⚠️ There was an issue logging your order to the system. "
                        "Your payment screenshot has been saved. Please contact the admin."
                    ),
                    reply_markup=get_main_keyboard()
                )

        else:
            delivery = context.user_data.get('delivery', {})
            delivery_session_id = delivery.get('id')
            if isinstance(delivery_session_id, str):
                try:
                    delivery_session_id = int(delivery_session_id)
                except ValueError:
                    delivery_session_id = None

            cart = context.user_data.get('cart', [])
            total_price = context.user_data.get('total_price', 0)
            total_quantity = context.user_data.get('total_quantity', 0)

            order_data = {
                'order_id': order_id,
                'user_id': user_id,
                'delivery_session_id': delivery_session_id,
                'customer_name': user_info.get('name', 'Unknown'),
                'customer_phone': user_info.get('phone', 'Unknown'),
                'customer_handle': user_info.get('handle', ''),
                'items': cart if cart else None,
                'total_quantity': total_quantity if cart else None,
                'total_price': total_price,
                'payment_screenshot_url': screenshot_url,
                'payment_status': 'submitted',
                'order_status': 'confirmed'
            }

            if cart:
                order_data['flavor'] = cart[0].get('flavor', 'Unknown')
                order_data['sauce'] = cart[0].get('sauce', 'Unknown')
                order_data['quantity'] = total_quantity
            else:
                order_data['flavor'] = context.user_data.get('flavor', 'Unknown')
                order_data['sauce'] = context.user_data.get('sauce', 'Unknown')
                order_data['quantity'] = quantity

            success = db.create_delivery_order(**order_data)

            if success:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=(
                        f"🎉 **Order Complete!**\n\n"
                        f"Your order has been logged successfully.\n"
                        f"Order ID: `{order_id}`\n\n"
                        f"We'll verify your payment and confirm your order soon.\n"
                        f"Thank you for ordering! 🍧\n\n"
                        f"Use the buttons below to place another order or get help!"
                    ),
                    reply_markup=get_main_keyboard(),
                    parse_mode='Markdown'
                )
            else:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=(
                        "⚠️ There was an issue logging your order to the system. "
                        "Your payment screenshot has been saved. Please contact the admin."
                    ),
                    reply_markup=get_main_keyboard()
                )

    except Exception as e:
        print(f"Error logging order: {e}")
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=(
                "⚠️ Error processing order. Please contact the admin with your order ID: "
                f"`{order_id}`"
            ),
            reply_markup=get_main_keyboard(),
            parse_mode='Markdown'
        )

    # Clear user data
    context.user_data.clear()


async def prompt_for_payment_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Remind the user that a payment screenshot photo is required"""
    text = (update.message.text or "").strip()
    if text == CANCEL_ORDER_BUTTON_TEXT:
        return await cancel_payment(update, context)
    if text == RESTART_ORDER_BUTTON_TEXT:
        context.user_data.clear()
        await update.message.reply_text(
            "🔄 Order restarted. Tap **Order Now** to begin again!",
            reply_markup=get_main_keyboard(),
            parse_mode='Markdown'
        )
        return ConversationHandler.END

    await update.message.reply_text(
        "⚠️ Please send your payment screenshot as a **photo attachment**.\n"
        "You can tap ❌ Cancel Order or use /cancel if you need to stop.",
        parse_mode='Markdown'
    )
    return AWAITING_SCREENSHOT


async def handle_payment_method_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle payment method selection for pickup orders"""
    query = update.callback_query
    await query.answer()

    if query.data == "cancel":
        await query.edit_message_text(
            "❌ Order cancelled. Use /order to start again.",
            reply_markup=get_main_keyboard()
        )
        context.user_data.clear()
        return ConversationHandler.END

    if query.data == "payment_now":
        # User chose to pay now - proceed with QR code and screenshot upload
        context.user_data['payment_method'] = 'pay_now'
        await query.edit_message_text(
            "💳 **Payment Method:** Pay Now\n\n"
            "Proceeding to payment...",
            parse_mode='Markdown'
        )
        # Trigger QR payment flow (retry_state defaults to AWAITING_SCREENSHOT)
        await send_payment_qr(update, context)
        from handlers.order_flow import PAYMENT
        return PAYMENT

    elif query.data == "payment_counter":
        # User chose to pay at counter - skip screenshot, log order directly
        context.user_data['payment_method'] = 'pay_at_counter'

        await query.edit_message_text(
            "💵 **Payment Method:** Pay at Counter\n\n"
            "Processing your order...",
            parse_mode='Markdown'
        )

        # Log pickup order without payment screenshot
        success = await log_pickup_order(update, context, payment_screenshot="Pay at Counter")

        if success:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=(
                    f"🎉 **Pickup Order Confirmed!**\n\n"
                    f"Order ID: `{context.user_data.get('order_id')}`\n\n"
                    f"**Pickup Details:**\n"
                    f"🏪 Store: {context.user_data['pickup_store']['name']}\n"
                    f"📅 Date: {context.user_data['pickup_date_display']}\n"
                    f"🕐 Time: {context.user_data['pickup_time_display']}\n\n"
                    f"💵 **Payment:** At Counter\n\n"
                    f"Please pay when you pick up your order.\n"
                    f"Thank you! 🍧"
                ),
                reply_markup=get_main_keyboard(),
                parse_mode='Markdown'
            )
        else:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text="⚠️ There was an issue logging your order. Please contact the admin.",
                reply_markup=get_main_keyboard()
            )

        context.user_data.clear()
        return ConversationHandler.END

    return ConversationHandler.END


async def log_pickup_order(update: Update, context: ContextTypes.DEFAULT_TYPE, payment_screenshot: str = "N/A"):
    """Log pickup order to Supabase"""
    try:
        user_id = update.effective_user.id
        user_info = context.user_data.get('user_info', {})
        store = context.user_data.get('pickup_store', {})
        order_id = context.user_data.get('order_id', 'unknown')

        db = get_db()

        # Create or update user in database
        db.create_or_update_user(
            telegram_user_id=user_id,
            name=user_info.get('name', 'Unknown'),
            telegram_handle=user_info.get('handle', ''),
            phone=user_info.get('phone', 'Unknown')
        )

        # Create pickup order
        cart = context.user_data.get('cart', [])
        total_price = context.user_data.get('total_price', 0)
        total_quantity = context.user_data.get('total_quantity', 0)

        if not cart:
            quantity = context.user_data.get('quantity', 1)
            unit_price = context.user_data.get('unit_price')
            if unit_price is None:
                pricing = context.user_data.get('menu_pricing', {})
                unit_price = pricing.get('price_per_bowl', 8.0)
            total_price = calculate_price(quantity, unit_price)
            total_quantity = quantity

        order_data = {
            'order_id': order_id,
            'user_id': user_id,
            'customer_name': user_info.get('name', 'Unknown'),
            'customer_phone': user_info.get('phone', 'Unknown'),
            'customer_handle': user_info.get('handle', ''),
            'store_id': store.get('id'),
            'pickup_date': context.user_data.get('pickup_date', 'Unknown'),
            'pickup_time': context.user_data.get('pickup_time', 'Unknown'),
            'items': cart if cart else None,
            'total_quantity': total_quantity if cart else None,
            'total_price': total_price,
            'payment_method': context.user_data.get('payment_method', 'pay_now'),
            'payment_screenshot_url': payment_screenshot,
            'payment_status': 'pending' if payment_screenshot == "Pay at Counter" else 'submitted',
            'order_status': 'confirmed'
        }

        if cart:
            order_data['flavor'] = cart[0].get('flavor', 'Unknown')
            order_data['sauce'] = cart[0].get('sauce', 'Unknown')
            order_data['quantity'] = total_quantity
        else:
            order_data['flavor'] = context.user_data.get('flavor', 'Unknown')
            order_data['sauce'] = context.user_data.get('sauce', 'Unknown')
            order_data['quantity'] = total_quantity

        success = db.create_pickup_order(**order_data)
        return success

    except Exception as e:
        print(f"❌ Error logging pickup order: {e}")
        return False


async def cancel_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel the payment process"""
    await update.message.reply_text(
        "❌ Payment cancelled. Your order was not submitted.\n"
        "Use the buttons below to start over!",
        reply_markup=get_main_keyboard()
    )
    context.user_data.clear()
    return ConversationHandler.END


def get_payment_conversation_handler():
    """Returns the configured ConversationHandler for payment"""
    return ConversationHandler(
        entry_points=[CommandHandler('payment', send_payment_qr)],
        states={
            AWAITING_SCREENSHOT: [
                MessageHandler(filters.PHOTO, receive_payment_screenshot),
                MessageHandler(filters.TEXT & ~filters.COMMAND, prompt_for_payment_photo)
            ],
            CONFIRM_SCREENSHOT: [
                CallbackQueryHandler(confirm_screenshot_callback, pattern="^(yes_receipt|retry_receipt)$"),
            ],
        },
        fallbacks=[CommandHandler('cancel', cancel_payment)],
        name="PAYMENT_FLOW",
        per_chat=True,
        per_user=False,
        per_message=False,
    )
