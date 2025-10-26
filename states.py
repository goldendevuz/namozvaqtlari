from aiogram.fsm.state import StatesGroup, State

class PostStates(StatesGroup):
    waiting_for_post = State()

class ChannelStates(StatesGroup):
    waiting_for_channel_id = State()
    waiting_for_channel_link = State()
    waiting_for_channel_name = State()
    waiting_for_bot_admin_confirmation = State()
