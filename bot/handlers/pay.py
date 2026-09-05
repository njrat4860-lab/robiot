from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, PreCheckoutQuery, LabeledPrice

from bot.keyboards import gender_menu
from bot import texts

router = Router()

PAYLOAD = "psl_rating"
MIN_STARS_PRICE = 1


@router.callback_query(F.data == "pay")
async def on_pay(callback: CallbackQuery, db):
    price = max(MIN_STARS_PRICE, int(await db.get_setting("price_stars")))
    await callback.message.answer_invoice(
        title="Оценка внешности",
        description="Платная оценка без лимита",
        payload=PAYLOAD,
        currency="XTR",
        prices=[LabeledPrice(label="Оценка", amount=price)],
    )
    await callback.answer()


@router.pre_checkout_query()
async def on_pre_checkout(query: PreCheckoutQuery):
    await query.answer(ok=query.invoice_payload == PAYLOAD and query.currency == "XTR")


@router.message(F.successful_payment)
async def on_successful_payment(message: Message, db):
    payment = message.successful_payment
    if payment.invoice_payload != PAYLOAD or payment.currency != "XTR":
        return
    await db.add_credit(message.from_user.id)
    await db.add_payment(
        message.from_user.id,
        payment.invoice_payload,
        payment.total_amount,
        "paid",
    )
    await message.answer(texts.CHOOSE_GENDER, reply_markup=gender_menu())
