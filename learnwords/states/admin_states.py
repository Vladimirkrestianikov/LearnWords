from aiogram.fsm.state import State, StatesGroup


class AdminState(StatesGroup):
    waiting_search_id = State()
    waiting_broadcast_message = State()
    waiting_dict_title = State()

