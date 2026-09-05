from bot.sponsors import normalize_sponsor_channel, valid_sponsor_channel


def test_sponsor_channel_rejects_numeric_id():
    assert valid_sponsor_channel("-1001234567890") is False


def test_sponsor_channel_rejects_private_invite_without_checkable_username():
    assert valid_sponsor_channel("https://t.me/+abcdef") is False


def test_sponsor_channel_accepts_public_username():
    assert valid_sponsor_channel("https://t.me/channel_name") is True
    assert normalize_sponsor_channel("@channel_name") == "channel_name"
