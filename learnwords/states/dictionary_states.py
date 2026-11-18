from aiogram.fsm.state import State, StatesGroup


class DictionaryState(StatesGroup):
    waiting_title = State()
    waiting_search_query = State()
    waiting_word_english = State()
    waiting_word_translation = State()

