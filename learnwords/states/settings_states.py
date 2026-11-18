from aiogram.fsm.state import State, StatesGroup


class SettingsState(StatesGroup):
    waiting_custom_topic = State()
    waiting_custom_goal = State()

