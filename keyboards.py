"""Factory functions for Telegram reply keyboards."""
from telegram import ReplyKeyboardMarkup, KeyboardButton
from constants import (
    ORDER_BUTTON_TEXT,
    HELP_BUTTON_TEXT,
    START_OVER_BUTTON_TEXT,
    SHOW_MENU_BUTTON_TEXT,
    SHOW_DELIVERIES_BUTTON_TEXT,
    RESTART_ORDER_BUTTON_TEXT,
    CANCEL_ORDER_BUTTON_TEXT,
)


def get_main_keyboard() -> ReplyKeyboardMarkup:
    """Main menu keyboard presented outside of order flow."""
    keyboard = [
        [KeyboardButton(ORDER_BUTTON_TEXT), KeyboardButton(SHOW_MENU_BUTTON_TEXT)],
        [KeyboardButton(SHOW_DELIVERIES_BUTTON_TEXT), KeyboardButton(HELP_BUTTON_TEXT)],
        [KeyboardButton(START_OVER_BUTTON_TEXT)],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def get_order_keyboard() -> ReplyKeyboardMarkup:
    """Keyboard displayed while a user is in the ordering flow."""
    keyboard = [
        [KeyboardButton(RESTART_ORDER_BUTTON_TEXT), KeyboardButton(CANCEL_ORDER_BUTTON_TEXT)]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
