import asyncio
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from states import PostStates
from functions.statisic import _load_admin_ids, ADMIN_IDS
import sqlite3
from .statisic import _db_path


async def post_start(message: Message, state: FSMContext):
    _load_admin_ids()
    user_id = int(getattr(message.from_user, "id", 0) or 0)
    if user_id not in ADMIN_IDS:
        await message.answer("⛔ Ushbu buyruq faqat adminlar uchun.")
        return
    await state.set_state(PostStates.waiting_for_post)
    await message.answer("Yuboriladigan xabarni jo'nating.")


def _fetch_all_user_ids() -> list[int]:
    conn = sqlite3.connect(_db_path())
    try:
        cur = conn.cursor()
        cur.execute("SELECT id FROM users")
        rows = cur.fetchall()
        return [int(r[0]) for r in rows if r and r[0]]
    finally:
        conn.close()


async def post_receive(message: Message, state: FSMContext):
    _load_admin_ids()
    user_id = int(getattr(message.from_user, "id", 0) or 0)
    if user_id not in ADMIN_IDS:
        await message.answer("⛔ Ushbu buyruq faqat adminlar uchun.")
        await state.clear()
        return

    bot = message.bot
    ids = await asyncio.to_thread(_fetch_all_user_ids)
    ok = 0
    fail = 0
    for idx, uid in enumerate(ids, 1):
        try:
            await bot.copy_message(chat_id=uid, from_chat_id=message.chat.id, message_id=message.message_id)
            ok += 1
        except Exception:
            fail += 1
        if idx % 25 == 0:
            await asyncio.sleep(0.3)
    await state.clear()
    await message.answer(f"Yuborildi: {ok}\nYuborilmadi: {fail}")
