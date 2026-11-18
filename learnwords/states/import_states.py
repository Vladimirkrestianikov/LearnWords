from aiogram.fsm.state import State, StatesGroup


class ImportState(StatesGroup):
    waiting_text = State()
    waiting_file = State()
    reviewing_staged = State()

