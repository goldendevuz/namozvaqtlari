import asyncio
import os
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, ChatMemberUpdatedFilter, KICKED, MEMBER, ADMINISTRATOR
from aiogram.types import ChatMemberUpdated
from dotenv import load_dotenv
from functions.start import greeting
from functions.praytime import (
    on_region_selected,
    on_back,
    on_refresh,
    ALL_REGION_KEYS,
    close_praytime_session,
)
from functions.statisic import init_db, handle_stats
from keyboards.reply import ADMIN_BUTTONS
from keyboards.inline import REFRESH_PREFIX
from functions.post import post_start, post_receive
from functions.channel import (
    init_channels_table,
    add_channel_start,
    receive_channel_id,
    receive_channel_link,
    receive_channel_name,
    confirm_bot_admin,
    delete_channel_list,
    delete_channel_callback,
    cancel_channel_action,
    check_subscription_callback,
)
from functions.group import (
    init_groups_table,
    handle_bot_added_to_group,
    handle_bot_removed_from_group,
    schedule_daily_prayers,
)
from states import PostStates, ChannelStates
from aiogram.fsm.storage.memory import MemoryStorage

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN1 = os.getenv("ADMIN1")
ADMIN2 = os.getenv("ADMIN2")

async def start_bot(bot: Bot):
    if ADMIN1:
        try:
            await bot.send_message(int(ADMIN1), "🟢 Bot ishga tushdi")
        except Exception as e:
            pass

async def stop_bot(bot: Bot):
    if ADMIN1:
        try:
            await bot.send_message(int(ADMIN1), "🔴 Bot to'xtadi")
        except Exception as e:
            pass

async def main():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    dp.message.register(greeting, CommandStart())
    dp.message.register(handle_stats, F.text == ADMIN_BUTTONS["stats"])
    dp.message.register(post_start, F.text == ADMIN_BUTTONS["post"])
    dp.message.register(post_receive, PostStates.waiting_for_post)
    
    dp.message.register(add_channel_start, F.text == ADMIN_BUTTONS["add_channel"])
    dp.message.register(receive_channel_id, ChannelStates.waiting_for_channel_id)
    dp.message.register(receive_channel_link, ChannelStates.waiting_for_channel_link)
    dp.message.register(receive_channel_name, ChannelStates.waiting_for_channel_name)
    dp.message.register(delete_channel_list, F.text == ADMIN_BUTTONS["del_channel"])
    
    dp.my_chat_member.register(
        handle_bot_added_to_group,
        ChatMemberUpdatedFilter(member_status_changed=(KICKED | MEMBER) >> (ADMINISTRATOR | MEMBER))
    )
    dp.my_chat_member.register(
        handle_bot_removed_from_group,
        ChatMemberUpdatedFilter(member_status_changed=(ADMINISTRATOR | MEMBER) >> KICKED)
    )
    
    dp.callback_query.register(confirm_bot_admin, ChannelStates.waiting_for_bot_admin_confirmation)
    dp.callback_query.register(delete_channel_callback, F.data.startswith("delete_channel_"))
    dp.callback_query.register(cancel_channel_action, F.data == "cancel_channel")
    dp.callback_query.register(check_subscription_callback, F.data == "check_subscription")
    
    dp.callback_query.register(on_region_selected, F.data.in_(ALL_REGION_KEYS))
    dp.callback_query.register(on_refresh, F.data.startswith(REFRESH_PREFIX))
    dp.callback_query.register(on_back, F.data == "back_to_menu")

    await start_bot(bot)
    
    scheduler_task = asyncio.create_task(schedule_daily_prayers(bot))
    
    try:
        await asyncio.to_thread(init_db)
        await asyncio.to_thread(init_channels_table)
        await asyncio.to_thread(init_groups_table)
        await dp.start_polling(bot)
    finally:
        scheduler_task.cancel()
        await stop_bot(bot)
        try:
            await close_praytime_session()
        except Exception as e:
            print(f"Error closing prayer-time session: {e}")
        try:
            await bot.session.close()
        except Exception as e:
            print(f"Error closing session: {e}")

if __name__ == "__main__":
    asyncio.run(main())
