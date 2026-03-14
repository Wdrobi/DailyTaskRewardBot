from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from keyboards.menus import main_menu
from utils.access import can_access_bot

router = Router()


@router.message(Command("cancel"))
async def cancel_any_state(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("✅ চলমান কাজ বাতিল করা হয়েছে।", reply_markup=main_menu())


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

    await message.answer("📋 মেইন মেনু", reply_markup=main_menu())


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
        "নিচের মেনু ব্যবহার করুন অথবা /start দিন।",
        reply_markup=main_menu(),
    )
