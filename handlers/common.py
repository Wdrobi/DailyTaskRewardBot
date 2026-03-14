from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, ReplyKeyboardRemove

from utils.access import can_access_bot

router = Router()


@router.message(Command("cancel"))
async def cancel_any_state(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        "✅ চলমান কাজ বাতিল করা হয়েছে। আবার শুরু করতে /start দিন।",
        reply_markup=ReplyKeyboardRemove(),
    )


@router.message(Command("menu"))
async def show_main_menu(message: Message, state: FSMContext, bot: Bot) -> None:
    await state.clear()
    has_access, _, had_error = await can_access_bot(bot, message.from_user.id)
    if had_error:
        await message.answer("⚠️ Channel verification issue আছে। পরে আবার চেষ্টা করুন।")
        return
    if not has_access:
        await message.answer("🔒 আগে required channel join করে /start দিন।")
        return

    await message.answer(
        "এই বট-এ quick menu রাখা হয়নি। Mini App খুলতে /start দিন।",
        reply_markup=ReplyKeyboardRemove(),
    )


@router.message(F.text)
async def fallback_text(message: Message, bot: Bot) -> None:
    has_access, _, had_error = await can_access_bot(bot, message.from_user.id)
    if had_error:
        await message.answer("⚠️ Channel verification issue আছে। পরে আবার চেষ্টা করুন।")
        return
    if not has_access:
        await message.answer("🔒 আগে required channel join করে /start দিন।")
        return

    await message.answer(
        "❓ কমান্ডটি বুঝতে পারিনি।\n"
        "Mini App খুলতে /start দিন।",
        reply_markup=ReplyKeyboardRemove(),
    )
