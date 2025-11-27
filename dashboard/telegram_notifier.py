"""
Telegram notification utilities for admin dashboard
Handles sending verification messages to customers
"""
import os
from typing import Optional, Tuple
from telegram import Bot
from telegram.error import TelegramError
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN not found in .env file!")


async def send_order_verification_message(
    telegram_user_id: int,
    message: str
) -> Tuple[bool, Optional[str]]:
    """
    Send order verification message to customer via Telegram

    Args:
        telegram_user_id: Customer's Telegram user ID
        message: Message template (can contain variables like {customer_name})

    Returns:
        Tuple of (success: bool, error_message: Optional[str])
        - (True, None) if successful
        - (False, error_msg) if failed
    """
    try:
        bot = Bot(token=BOT_TOKEN)
        await bot.send_message(
            chat_id=telegram_user_id,
            text=message,
            parse_mode='HTML'  # Allow HTML formatting in messages
        )
        return True, None
    except TelegramError as e:
        error_msg = f"Telegram error: {str(e)}"
        print(f"❌ {error_msg}")
        return False, error_msg
    except Exception as e:
        error_msg = f"Error sending message: {str(e)}"
        print(f"❌ {error_msg}")
        return False, error_msg


def format_verification_message(
    template: str,
    customer_name: str,
    order_id: str,
    total_price: float,
    delivery_location: Optional[str] = None,
    delivery_time: Optional[str] = None,
    pickup_store: Optional[str] = None,
    pickup_time: Optional[str] = None
) -> str:
    """
    Format message template with order details

    Args:
        template: Message template with variables like {customer_name}, {order_id}, etc.
        customer_name: Customer's name
        order_id: Order ID
        total_price: Total price of order
        delivery_location: Location for delivery (optional)
        delivery_time: Delivery time (optional)
        pickup_store: Store name for pickup (optional)
        pickup_time: Pickup time (optional)

    Returns:
        Formatted message with variables replaced
    """
    message = template
    message = message.replace('{customer_name}', customer_name)
    message = message.replace('{order_id}', order_id)
    message = message.replace('{total_price}', f"${total_price:.2f}")

    if delivery_location:
        message = message.replace('{delivery_location}', delivery_location)
    if delivery_time:
        message = message.replace('{delivery_time}', delivery_time)
    if pickup_store:
        message = message.replace('{pickup_store}', pickup_store)
    if pickup_time:
        message = message.replace('{pickup_time}', pickup_time)

    return message
