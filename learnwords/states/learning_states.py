from aiogram.fsm.state import State, StatesGroup


class LearningState(StatesGroup):
    studying_card = State()
    answering_test = State()
    answering_review = State()

