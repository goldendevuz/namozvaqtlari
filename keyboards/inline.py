from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

cities = [
    ("Farg'ona", "fargona"),
    ("Xiva", "xiva"),
    ("Toshkent", "toshkent"),
    ("Namangan", "namangan"),
    ("Buxoro", "buxoro"),
    ("Guliston", "guliston"),
    ("Jizzax", "jizzax"),
    ("Zarafshon", "zarafshon"),
    ("Qarshi", "qarshi"),
    ("Navoiy", "navoiy"),
    ("Nukus", "nukus"),
    ("Samarqand", "samarqand"),
    ("Termiz", "termiz"),
    ("Urganch", "urganch"),
]

buttons = [
    InlineKeyboardButton(text=f"🕌 {city[0]}", callback_data=city[1])
    for city in cities
]

rows = [buttons[i:i+2] for i in range(0, len(buttons), 2)]

rows.append([InlineKeyboardButton(text="🕌 Andijon", callback_data="andijon")])

BACK_TO_MENU = "back_to_menu"
REFRESH_PREFIX = "refresh_"

cities_keyboard = InlineKeyboardMarkup(inline_keyboard=rows)


def prayer_controls_keyboard(region_key: str | None = None) -> InlineKeyboardMarkup:
    buttons = [
        InlineKeyboardButton(text="🔄 Yangilash", callback_data=f"{REFRESH_PREFIX}{region_key}"),
        InlineKeyboardButton(text="◀️ Orqaga", callback_data=BACK_TO_MENU)
    ]
    return InlineKeyboardMarkup(inline_keyboard=[buttons])

__all__ = [
    "cities",
    "cities_keyboard",
    "prayer_controls_keyboard",
    "BACK_TO_MENU",
    "REFRESH_PREFIX",
]