from aiogram import Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
import sqlite3
import os
import html as html_lib
from typing import List, Dict, Optional
from states import ChannelStates

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "bot.sqlite3")


def _get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_channels_table():
    conn = _get_db()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS channels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            channel_id TEXT UNIQUE NOT NULL,
            channel_link TEXT NOT NULL,
            channel_name TEXT NOT NULL,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


def add_channel(channel_id: str, channel_link: str, channel_name: str):
    conn = _get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO channels (channel_id, channel_link, channel_name) VALUES (?, ?, ?)",
        (channel_id, channel_link, channel_name)
    )
    conn.commit()
    conn.close()


def delete_channel(channel_id: str):
    conn = _get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM channels WHERE channel_id = ?", (channel_id,))
    conn.commit()
    conn.close()


def get_all_channels() -> List[Dict]:
    conn = _get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM channels ORDER BY added_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


async def check_user_subscription(bot: Bot, user_id: int) -> tuple[bool, List[Dict]]:
    channels = get_all_channels()
    if not channels:
        return True, []
    
    not_subscribed = []
    for channel in channels:
        try:
            member = await bot.get_chat_member(chat_id=channel["channel_id"], user_id=user_id)
            if member.status in ["left", "kicked"]:
                not_subscribed.append(channel)
        except Exception as e:
            print(f"[ERROR] Checking subscription for channel {channel['channel_id']}: {e}")
            not_subscribed.append(channel)
    
    return len(not_subscribed) == 0, not_subscribed


def get_subscription_keyboard(channels: List[Dict]) -> InlineKeyboardMarkup:
    buttons = []
    for channel in channels:
        buttons.append([InlineKeyboardButton(text=f"📢 {channel['channel_name']}", url=channel['channel_link'])])
    buttons.append([InlineKeyboardButton(text="✅ Tasdiqlash", callback_data="check_subscription")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_channels_list_keyboard() -> InlineKeyboardMarkup:
    channels = get_all_channels()
    buttons = []
    for channel in channels:
        buttons.append([
            InlineKeyboardButton(text=f"📢 {channel['channel_name']}", callback_data=f"channel_info_{channel['id']}"),
            InlineKeyboardButton(text="🗑 O'chirish", callback_data=f"delete_channel_{channel['id']}")
        ])
    buttons.append([InlineKeyboardButton(text="◀️ Orqaga", callback_data="cancel_channel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


async def add_channel_start(message: Message, state: FSMContext):
    admin_ids = []
    admin1 = os.getenv("ADMIN1")
    admin2 = os.getenv("ADMIN2")
    if admin1:
        admin_ids.append(int(admin1))
    if admin2:
        admin_ids.append(int(admin2))
    
    if message.from_user.id not in admin_ids:
        await message.answer("Bu buyruq faqat adminlar uchun!")
        return
    
    await state.set_state(ChannelStates.waiting_for_channel_id)
    await message.answer(
        "Kanal ID sini yuboring:\n\n"
        "Misol: -1001234567890\n"
        "Yoki @kanalusername"
    )


async def receive_channel_id(message: Message, state: FSMContext):
    channel_id = message.text.strip()
    await state.update_data(channel_id=channel_id)
    await state.set_state(ChannelStates.waiting_for_channel_link)
    await message.answer(
        "Kanal linkini yuboring:\n\n"
        "Misol: https://t.me/kanalname\n"
        "Yoki @kanalusername"
    )


async def receive_channel_link(message: Message, state: FSMContext):
    channel_link = message.text.strip()
    await state.update_data(channel_link=channel_link)
    await state.set_state(ChannelStates.waiting_for_channel_name)
    await message.answer("Kanal nomini yuboring:")


async def receive_channel_name(message: Message, state: FSMContext):
    channel_name = message.text.strip()
    await state.update_data(channel_name=channel_name)
    await state.set_state(ChannelStates.waiting_for_bot_admin_confirmation)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Ha", callback_data="bot_admin_yes"),
            InlineKeyboardButton(text="❌ Yo'q", callback_data="bot_admin_no")
        ]
    ])
    await message.answer(
        "Bot kanalda admin qilinganmi?",
        reply_markup=keyboard
    )


async def confirm_bot_admin(callback: CallbackQuery, state: FSMContext, bot: Bot):
    if callback.data == "bot_admin_no":
        await callback.message.edit_text(
            "❌ Iltimos, avval botni kanalda admin qiling va qaytadan urinib ko'ring."
        )
        await state.clear()
        await callback.answer()
        return
    
    data = await state.get_data()
    channel_id = data.get("channel_id")
    channel_link = data.get("channel_link")
    channel_name = data.get("channel_name")
    
    try:
        chat = await bot.get_chat(channel_id)
        member = await bot.get_chat_member(chat_id=channel_id, user_id=bot.id)
        
        if member.status not in ["administrator", "creator"]:
            await callback.message.edit_text(
                "❌ Bot kanalda admin emas! Iltimos, botni admin qiling va qaytadan urinib ko'ring."
            )
            await callback.answer()
            return
        
        add_channel(channel_id, channel_link, channel_name)
        await callback.message.edit_text(
            f"✅ Kanal muvaffaqiyatli qo'shildi!\n\n"
            f"📢 Nom: {channel_name}\n"
            f"🆔 ID: {channel_id}\n"
            f"🔗 Link: {channel_link}"
        )
        await state.clear()
        await callback.answer("Muvaffaqiyatli!")
        
    except Exception as e:
        print(f"[ERROR] Adding channel: {e}")
        await callback.message.edit_text(
            f"❌ Xatolik yuz berdi!\n\n"
            f"Kanal ID to'g'ri ekanligiga ishonch hosil qiling.\n"
            f"Xato: {str(e)}"
        )
        await callback.answer()


async def delete_channel_list(message: Message):
    admin_ids = []
    admin1 = os.getenv("ADMIN1")
    admin2 = os.getenv("ADMIN2")
    if admin1:
        admin_ids.append(int(admin1))
    if admin2:
        admin_ids.append(int(admin2))
    
    if message.from_user.id not in admin_ids:
        await message.answer("Bu buyruq faqat adminlar uchun!")
        return
    
    channels = get_all_channels()
    if not channels:
        await message.answer("Hozircha hech qanday kanal qo'shilmagan.")
        return
    
    await message.answer(
        "O'chirish uchun kanalni tanlang:",
        reply_markup=get_channels_list_keyboard()
    )


async def delete_channel_callback(callback: CallbackQuery):
    channel_id = callback.data.replace("delete_channel_", "")
    
    conn = _get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM channels WHERE id = ?", (channel_id,))
    channel = cursor.fetchone()
    conn.close()
    
    if channel:
        delete_channel(channel["channel_id"])
        await callback.answer("✅ Kanal o'chirildi!", show_alert=True)
        
        channels = get_all_channels()
        if channels:
            await callback.message.edit_reply_markup(reply_markup=get_channels_list_keyboard())
        else:
            await callback.message.edit_text("Hozircha hech qanday kanal qo'shilmagan.")
    else:
        await callback.answer("❌ Kanal topilmadi!", show_alert=True)


async def cancel_channel_action(callback: CallbackQuery):
    await callback.message.delete()
    await callback.answer()


async def check_subscription_callback(callback: CallbackQuery, bot: Bot):
    is_subscribed, not_subscribed = await check_user_subscription(bot, callback.from_user.id)
    
    if is_subscribed:
        await callback.message.delete()
        user_name = callback.from_user.first_name or "Foydalanuvchi"
        safe_name = html_lib.escape(user_name)
        user_id = callback.from_user.id
        mention = f"<a href=\"tg://user?id={user_id}\">{safe_name}</a>"
        greeting_text = f"Assalomu Aleykum {mention}\nO'zingizga kerakli viloyatni tanlang👇"
        
        from keyboards.inline import cities_keyboard
        await callback.message.answer(
            text=greeting_text,
            reply_markup=cities_keyboard,
            parse_mode="HTML",
        )
        
        from functions.group import send_group_info
        fake_message = type('obj', (object,), {
            'answer': callback.message.answer,
            'from_user': callback.from_user,
            'chat': callback.message.chat,
            'bot': bot
        })()
        await send_group_info(fake_message, bot=bot)
        
        await callback.answer("✅ Tasdiqlandi!")
    else:
        await callback.answer(
            "❌ Iltimos, avval kanallarga obuna bo'ling!",
            show_alert=True
        )


__all__ = [
    "init_channels_table",
    "add_channel",
    "delete_channel",
    "get_all_channels",
    "check_user_subscription",
    "get_subscription_keyboard",
    "get_channels_list_keyboard",
    "add_channel_start",
    "receive_channel_id",
    "receive_channel_link",
    "receive_channel_name",
    "confirm_bot_admin",
    "delete_channel_list",
    "delete_channel_callback",
    "cancel_channel_action",
    "check_subscription_callback",
]
