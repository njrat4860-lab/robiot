from bot.config import _clean_token


def test_clean_token_removes_spaces_and_hidden_chars():
    token = " 123:abc\n\u200bdef\ufeff "

    assert _clean_token(token) == "123:abcdef"
