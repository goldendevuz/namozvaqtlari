from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

ADMIN_BUTTONS = {
    "stats": "📊 Statistika",
    "post": "📣 Post jo'natish",
    "add_channel": "➕ Kanal qo'shish",
    "del_channel": "➖ Kanal o'chirish",
}

def get_admin_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=ADMIN_BUTTONS["stats"]),
                KeyboardButton(text=ADMIN_BUTTONS["post"]),
            ],
            [
                KeyboardButton(text=ADMIN_BUTTONS["add_channel"]),
                KeyboardButton(text=ADMIN_BUTTONS["del_channel"]),
            ],
        ],
        resize_keyboard=True,
        input_field_placeholder="Admin menyu",
    )

admin_keyboard = get_admin_keyboard()

__all__ = ["get_admin_keyboard", "admin_keyboard", "ADMIN_BUTTONS"]