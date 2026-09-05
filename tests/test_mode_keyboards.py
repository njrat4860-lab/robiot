from bot.keyboards import gender_menu, mode_menu


def test_mode_menu_keeps_disabled_profile_visible():
    keyboard = mode_menu(True, False)

    buttons = keyboard.inline_keyboard

    assert buttons[0][0].text == "Анфас"
    assert buttons[0][0].callback_data == "mode:frontal"
    assert buttons[1][0].text == "Профиль ✕"
    assert buttons[1][0].callback_data == "mode_disabled:profile"


def test_gender_menu_keeps_disabled_female_visible():
    keyboard = gender_menu(True, False)

    buttons = keyboard.inline_keyboard

    assert buttons[0][0].text == "Мужской"
    assert buttons[0][0].callback_data == "gender:male"
    assert buttons[1][0].text == "Женский ✕"
    assert buttons[1][0].callback_data == "gender_disabled:female"
