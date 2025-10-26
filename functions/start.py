from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram import Bot
import asyncio
import html
import os
from dotenv import load_dotenv

from keyboards.inline import cities_keyboard
from keyboards.reply import get_admin_keyboard
from functions.statisic import add_or_update_user
from functions.channel import check_user_subscription, get_subscription_keyboard
from functions.group import send_group_info

load_dotenv()
ADMIN1 = os.getenv("ADMIN1")
ADMIN2 = os.getenv("ADMIN2")
ADMIN_IDS = []
if ADMIN1:
    ADMIN_IDS.append(int(ADMIN1))
if ADMIN2:
    ADMIN_IDS.append(int(ADMIN2))


async def greeting(message: Message, force_menu: bool = False, bot: Bot = None):
    user = message.from_user
    user_id = user.id
    user_name = user.first_name or "Foydalanuvchi"
    safe_name = html.escape(user_name)
    mention = f"<a href=\"tg://user?id={user_id}\">{safe_name}</a>"
    greeting_text = f"Assalomu Aleykum {mention}\nO'zingizga kerakli viloyatni tanlang👇"
    
    if user_id in ADMIN_IDS:
        await message.answer(
            text=greeting_text,
            reply_markup=get_admin_keyboard(),
            parse_mode="HTML",
        )
        await message.answer(
            text="Viloyatni tanlang:",
            reply_markup=cities_keyboard,
            parse_mode="HTML",
        )
        await send_group_info(message, bot=message.bot)
    else:
        try:
            await asyncio.to_thread(add_or_update_user, user, False, "start")
        except Exception as e:
            print(f"DB error (add_or_update_user): {e}")
        
        if not bot:
            from aiogram import Bot as BotClass
            bot = message.bot
        
        is_subscribed, not_subscribed = await check_user_subscription(bot, user_id)
        
        if not is_subscribed and not force_menu:
            await message.answer(
                "⚠️ Botdan foydalanish uchun quyidagi kanallarga obuna bo'ling:",
                reply_markup=get_subscription_keyboard(not_subscribed),
                parse_mode="HTML",
            )
        else:
            await message.answer(
                text=greeting_text,
                reply_markup=cities_keyboard,
                parse_mode="HTML",
            )
            await send_group_info(message)

