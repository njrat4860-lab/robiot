from aiogram.fsm.state import State, StatesGroup


class RatingFlow(StatesGroup):
    awaiting_photo = State()


class FeedbackFlow(StatesGroup):
    awaiting_message = State()


class AdminFlow(StatesGroup):
    awaiting_price = State()
    awaiting_limit = State()
    awaiting_queue_size = State()
    awaiting_metric_toggle = State()
    awaiting_unlimited = State()
    awaiting_sponsor_channel = State()
    awaiting_sponsor_title = State()
    awaiting_ticket_reply = State()
