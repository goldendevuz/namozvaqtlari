from aiogram import Bot
from aiogram.types import Message, ChatMemberUpdated, InlineKeyboardMarkup, InlineKeyboardButton
import sqlite3
import os
from datetime import datetime, time as dt_time
import asyncio
from typing import List, Dict

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "bot.sqlite3")


def _get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_groups_table():
    conn = _get_db()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS groups (
            chat_id INTEGER PRIMARY KEY,
            chat_title TEXT,
            region TEXT DEFAULT 'toshkent',
            is_active INTEGER DEFAULT 1,
            joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


def add_group(chat_id: int, chat_title: str, region: str = 'toshkent'):
    conn = _get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO groups (chat_id, chat_title, region, is_active) VALUES (?, ?, ?, 1)",
        (chat_id, chat_title, region)
    )
    conn.commit()
    conn.close()


def remove_group(chat_id: int):
    conn = _get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM groups WHERE chat_id = ?", (chat_id,))
    conn.commit()
    conn.close()


def get_all_active_groups() -> List[Dict]:
    conn = _get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM groups WHERE is_active = 1")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_group_info_keyboard(bot_username: str = None) -> InlineKeyboardMarkup:
    if not bot_username:
        bot_username = "your_bot"
    add_url = f"https://t.me/{bot_username}?startgroup=true"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Guruhga qo'shish", url=add_url)]
        ]
    )


async def send_group_info(message: Message, bot: Bot = None):
    if not bot:
        bot = message.bot
    
    bot_info = await bot.get_me()
    bot_username = bot_info.username
    
    info_text = (
        "🕌 <b>Bu bot guruhlarda ham ishlaydi!</b>\n\n"
        "Har kuni 🕐 <b>20:00</b> dan boshlab ertangi Namoz vaqtlarini eslatib turadi.\n\n"
        "⭐️ Agar botimizni <b>admin</b> qilib qo'ysangiz, 20:00 da Namoz vaqtlari "
        "kelib tushganida o'zi avtomatik tarzda <b>📌 PIN</b> qilib beradi!\n\n"
        "👇 Pastdagi tugma orqali guruhingizga qo'shing:"
    )
    await message.answer(
        text=info_text,
        reply_markup=get_group_info_keyboard(bot_username),
        parse_mode="HTML"
    )


async def handle_bot_added_to_group(update: ChatMemberUpdated, bot: Bot):
    chat = update.chat
    new_status = update.new_chat_member.status
    
    if new_status in ["member", "administrator"]:
        add_group(chat.id, chat.title or "Unknown Group")
        
        welcome_text = (
            "🕌 <b>Assalomu Aleykum!</b>\n\n"
            "Men Namoz vaqtlari botiman. Har kuni 🕐 20:00 da ertangi kun "
            "uchun Namoz vaqtlarini eslatib turaman.\n\n"
            "⭐️ Agar meni <b>admin</b> qilib qo'ysangiz, xabarlarni avtomatik "
            "tarzda PIN qilib beraman!"
        )
        
        try:
            await bot.send_message(
                chat_id=chat.id,
                text=welcome_text,
                parse_mode="HTML"
            )
        except Exception as e:
            print(f"[ERROR] Sending welcome to group {chat.id}: {e}")


async def handle_bot_removed_from_group(update: ChatMemberUpdated):
    chat = update.chat
    new_status = update.new_chat_member.status
    
    if new_status in ["left", "kicked"]:
        remove_group(chat.id)
        print(f"[INFO] Bot removed from group: {chat.title} ({chat.id})")


async def send_daily_prayer_times(bot: Bot):
    from functions.praytime import fetch_prayer_times, _format_prayer_text, REGION_MAP
    
    groups = get_all_active_groups()
    
    for group in groups:
        try:
            region_key = group.get("region", "toshkent")
            region_name = REGION_MAP.get(region_key, "Toshkent")
            
            data = await fetch_prayer_times(region_key)
            text = _format_prayer_text(region_name, data)
            
            tomorrow_text = (
                "🌙 <b>Ertangi kun Namoz vaqtlari:</b>\n\n"
                f"{text}"
            )
            
            sent_message = await bot.send_message(
                chat_id=group["chat_id"],
                text=tomorrow_text,
                parse_mode="HTML"
            )
            
            try:
                member = await bot.get_chat_member(
                    chat_id=group["chat_id"],
                    user_id=bot.id
                )
                
                if member.status == "administrator" and member.can_pin_messages:
                    await bot.pin_chat_message(
                        chat_id=group["chat_id"],
                        message_id=sent_message.message_id,
                        disable_notification=True
                    )
                    print(f"[INFO] Pinned message in group {group['chat_title']}")
            except Exception as e:
                print(f"[ERROR] Pinning message in {group['chat_title']}: {e}")
                
        except Exception as e:
            print(f"[ERROR] Sending prayer times to group {group.get('chat_title')}: {e}")


async def schedule_daily_prayers(bot: Bot):
    while True:
        now = datetime.now()
        target_time = now.replace(hour=20, minute=0, second=0, microsecond=0)
        
        if now >= target_time:
            target_time = target_time.replace(day=target_time.day + 1)
        
        wait_seconds = (target_time - now).total_seconds()
        print(f"[INFO] Waiting {wait_seconds/3600:.2f} hours until 20:00 for daily prayer times")
        
        await asyncio.sleep(wait_seconds)
        
        print("[INFO] Sending daily prayer times to all groups...")
        await send_daily_prayer_times(bot)
        
        await asyncio.sleep(60)


__all__ = [
    "init_groups_table",
    "add_group",
    "remove_group",
    "get_all_active_groups",
    "get_group_info_keyboard",
    "send_group_info",
    "handle_bot_added_to_group",
    "handle_bot_removed_from_group",
    "send_daily_prayer_times",
    "schedule_daily_prayers",
]
