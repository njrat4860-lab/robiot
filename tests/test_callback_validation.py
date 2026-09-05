import pytest

from bot.handlers import admin, feedback, profile


class User:
    id = 1


class Message:
    async def delete(self):
        return None

    async def edit_text(self, text, reply_markup=None):
        return None


class Callback:
    def __init__(self, data):
        self.data = data
        self.from_user = User()
        self.message = Message()
        self.answered = False

    async def answer(self, text=None):
        self.answered = True


class Database:
    def __init__(self):
        self.called = False

    async def delete_rating(self, user_id, rating_id):
        self.called = True

    async def remove_sponsor(self, sponsor_id):
        self.called = True

    async def get_ticket(self, ticket_id):
        self.called = True

    async def close_ticket(self, ticket_id):
        self.called = True


@pytest.mark.asyncio
async def test_invalid_rating_delete_callback_is_rejected():
    callback = Callback("rating_del:bad")
    database = Database()

    await profile.on_rating_delete(callback, database, None)

    assert callback.answered is True
    assert database.called is False


@pytest.mark.asyncio
async def test_invalid_sponsor_delete_callback_is_rejected():
    callback = Callback("admin:sponsor_del:bad")
    database = Database()

    await admin.on_sponsor_del(callback, database, {1})

    assert callback.answered is True
    assert database.called is False


@pytest.mark.asyncio
async def test_invalid_ticket_open_callback_is_rejected():
    callback = Callback("admin:ticket:bad")
    database = Database()

    await feedback.on_admin_ticket(callback, database, {1})

    assert callback.answered is True
    assert database.called is False


@pytest.mark.asyncio
async def test_invalid_ticket_close_callback_is_rejected():
    callback = Callback("admin:ticket_close:bad")
    database = Database()

    await feedback.on_admin_ticket_close(callback, database, {1})

    assert callback.answered is True
    assert database.called is False
