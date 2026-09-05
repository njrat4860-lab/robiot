import pytest

from bot.handlers import pay
from bot import texts


class Payment:
    invoice_payload = pay.PAYLOAD
    currency = "XTR"
    total_amount = 50


class User:
    id = 1


class Message:
    def __init__(self):
        self.from_user = User()
        self.successful_payment = Payment()
        self.answers = []

    async def answer(self, text, reply_markup=None):
        self.answers.append((text, reply_markup))


class Database:
    def __init__(self):
        self.credits = 0
        self.payments = 0

    async def add_credit(self, user_id):
        self.credits += 1

    async def add_payment(self, user_id, payload, amount, status):
        self.payments += 1


@pytest.mark.asyncio
async def test_successful_payment_returns_to_gender_selection():
    message = Message()
    database = Database()

    await pay.on_successful_payment(message, database)

    assert database.credits == 1
    assert database.payments == 1
    assert message.answers[0][0] == texts.CHOOSE_GENDER
