import logging

from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from config import (
    ADMIN_IDS,
    MIN_ACTIVE_REFERRALS,
    MIN_WITHDRAWAL_BDT,
    MIN_WITHDRAWAL_POINTS,
    POINTS_PER_TAKA,
    WITHDRAWAL_ENABLED,
)
from database import Database
from keyboards.menus import (
    withdrawal_methods_keyboard,
    confirm_withdrawal_keyboard,
    admin_withdrawal_keyboard,
)
from states import WithdrawalStates
from utils.access import can_access_bot

logger = logging.getLogger(__name__)
router = Router()

STATUS_LABELS = {
    "pending":  "⏳ অপেক্ষমাণ",
    "approved": "✅ অনুমোদিত",
    "rejected": "❌ প্রত্যাখ্যাত",
}


async def _get_withdrawal_requirements(db: Database, user_id: int, points: int) -> tuple[int, bool, int, int]:
    active_referrals = await db.get_referral_count(user_id)
    missing_points = max(MIN_WITHDRAWAL_POINTS - points, 0)
    missing_referrals = max(MIN_ACTIVE_REFERRALS - active_referrals, 0)
    can_withdraw = (
        WITHDRAWAL_ENABLED
        and points >= MIN_WITHDRAWAL_POINTS
        and active_referrals >= MIN_ACTIVE_REFERRALS
    )
    return active_referrals, can_withdraw, missing_points, missing_referrals


async def send_wallet_overview(message: Message, db: Database, state: FSMContext, bot: Bot) -> None:
    await state.clear()
    has_access, _, had_error = await can_access_bot(bot, message.from_user.id)
    if had_error:
        await message.answer("⚠️ Channel verification issue আছে। পরে আবার চেষ্টা করুন।")
        return
    if not has_access:
        await message.answer("🔒 আগে required channel join করে /start দিন।")
        return

    user = await db.get_user(message.from_user.id)
    if not user or user.get("is_banned"):
        await message.answer("🚫 আপনার অ্যাকাউন্ট নিষিদ্ধ।")
        return

    points = user["points"]
    withdrawable_taka = points / POINTS_PER_TAKA
    active_referrals, can_withdraw, missing_points, missing_referrals = await _get_withdrawal_requirements(
        db, message.from_user.id, points
    )

    history = await db.get_user_withdrawals(message.from_user.id)
    history_text = ""
    if history:
        history_text = "\n\n📜 <b>সর্বশেষ উত্তোলন:</b>\n"
        for w in history[:5]:
            label = STATUS_LABELS.get(w["status"], w["status"])
            history_text += (
                f"  • {w['points']} পয়েন্ট → ৳{w['amount_bdt']:.0f} "
                f"({w['payment_method']}) — {label}\n"
            )

    text = (
        f"💰 <b>আমার ওয়ালেট</b>\n\n"
        f"🔵 বর্তমান পয়েন্ট: <b>{points}</b>\n"
        f"💵 উত্তোলনযোগ্য: <b>৳{withdrawable_taka:.2f}</b>\n"
        f"👥 সক্রিয় রেফারেল: <b>{active_referrals}/{MIN_ACTIVE_REFERRALS}</b>\n"
        f"📊 মোট অর্জন: <b>{user['total_earned']}</b>\n"
        f"🏦 মোট উত্তোলন: <b>{user['total_withdrawn']}</b> পয়েন্ট\n\n"
        f"📌 উত্তোলন শর্ত: <b>কমপক্ষে ৳{MIN_WITHDRAWAL_BDT}</b> এবং <b>{MIN_ACTIVE_REFERRALS}টি সক্রিয় রেফারেল</b>"
        f"{history_text}"
    )

    if WITHDRAWAL_ENABLED and can_withdraw:
        from aiogram.utils.keyboard import InlineKeyboardBuilder
        from aiogram.types import InlineKeyboardButton

        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text="💸 টাকা উত্তোলন করুন", callback_data="wd:start")
        )
        await message.answer(text, reply_markup=builder.as_markup())
    elif not WITHDRAWAL_ENABLED:
        await message.answer(
            text
            + "\n\n🛠️ পেমেন্ট সিস্টেম এখনো চালু হয়নি।\n"
              "পেমেন্ট ইন্টিগ্রেশন শেষ হলে উত্তোলন অপশন চালু হবে।"
        )
    else:
        reasons: list[str] = []
        if missing_points > 0:
            reasons.append(f"আরও <b>{missing_points}</b> পয়েন্ট (৳{missing_points / POINTS_PER_TAKA:.2f}) দরকার")
        if missing_referrals > 0:
            reasons.append(f"আরও <b>{missing_referrals}</b>টি সক্রিয় রেফারেল দরকার")
        await message.answer(
            text + "\n\n⚠️ উত্তোলনের জন্য " + " এবং ".join(reasons) + "."
        )


# ──────────────────────────────────────────────
# ওয়ালেট দেখুন
# ──────────────────────────────────────────────
@router.message(F.text == "💰 আমার ওয়ালেট")
async def show_wallet(message: Message, db: Database, state: FSMContext, bot: Bot) -> None:
    await send_wallet_overview(message, db, state, bot)


# ──────────────────────────────────────────────
# উইথড্রয়াল শুরু
# ──────────────────────────────────────────────
@router.callback_query(F.data == "wd:start")
async def start_withdrawal(callback: CallbackQuery, db: Database, state: FSMContext) -> None:
    has_access, _, had_error = await can_access_bot(callback.bot, callback.from_user.id)
    if had_error:
        await callback.answer("Channel verification issue.", show_alert=True)
        return
    if not has_access:
        await callback.answer("আগে required channel join করুন।", show_alert=True)
        return

    if not WITHDRAWAL_ENABLED:
        await state.clear()
        await callback.answer(
            "🛠️ পেমেন্ট সিস্টেম এখনো চালু হয়নি। পরে আবার চেষ্টা করুন।",
            show_alert=True,
        )
        return

    user_id = callback.from_user.id
    user = await db.get_user(user_id)

    if not user or user.get("is_banned"):
        await callback.answer("🚫 অ্যাকাউন্ট নিষিদ্ধ।", show_alert=True)
        return

    active_referrals, can_withdraw, missing_points, missing_referrals = await _get_withdrawal_requirements(
        db, user_id, user["points"]
    )
    if not can_withdraw:
        messages: list[str] = []
        if missing_points > 0:
            messages.append(f"ন্যূনতম ৳{MIN_WITHDRAWAL_BDT} ({MIN_WITHDRAWAL_POINTS} পয়েন্ট) লাগবে")
        if missing_referrals > 0:
            messages.append(f"{MIN_ACTIVE_REFERRALS}টি সক্রিয় রেফারেল লাগবে, আপনার আছে {active_referrals}")
        await callback.answer("❌ " + " | ".join(messages), show_alert=True)
        return

    if await db.has_pending_withdrawal(user_id):
        await callback.answer(
            "⏳ আপনার একটি উত্তোলন আবেদন ইতিমধ্যে প্রক্রিয়াধীন আছে।",
            show_alert=True,
        )
        return

    await state.set_state(WithdrawalStates.selecting_method)
    await state.update_data(points=user["points"], active_referrals=active_referrals)

    await callback.message.edit_text(
        f"💸 <b>টাকা উত্তোলন</b>\n\n"
        f"আপনার পয়েন্ট: <b>{user['points']}</b>\n"
        f"উত্তোলনযোগ্য: <b>৳{user['points'] / POINTS_PER_TAKA:.2f}</b>\n\n"
        f"সক্রিয় রেফারেল: <b>{active_referrals}/{MIN_ACTIVE_REFERRALS}</b>\n"
        f"ন্যূনতম শর্ত: <b>৳{MIN_WITHDRAWAL_BDT}</b> + <b>{MIN_ACTIVE_REFERRALS}টি সক্রিয় রেফারেল</b>\n\n"
        f"পেমেন্ট মাধ্যম বেছে নিন:",
        reply_markup=withdrawal_methods_keyboard(),
    )
    await callback.answer()


# ──────────────────────────────────────────────
# পেমেন্ট মেথড বাছাই
# ──────────────────────────────────────────────
@router.callback_query(F.data.startswith("wd_method:"), WithdrawalStates.selecting_method)
async def select_payment_method(callback: CallbackQuery, state: FSMContext) -> None:
    if not WITHDRAWAL_ENABLED:
        await state.clear()
        await callback.answer("এই ফিচার এখন বন্ধ আছে।", show_alert=True)
        return

    method = callback.data.split(":")[1]
    method_labels = {"bkash": "বিকাশ", "nagad": "নগদ", "rocket": "রকেট"}
    label = method_labels.get(method, method)

    await state.update_data(method=method)
    await state.set_state(WithdrawalStates.entering_number)

    await callback.message.edit_text(
        f"📱 <b>{label} নম্বর লিখুন</b>\n\n"
        f"আপনার {label} অ্যাকাউন্ট নম্বরটি লিখুন:\n"
        f"(উদাহরণ: 01XXXXXXXXX)"
    )
    await callback.answer()


# ──────────────────────────────────────────────
# অ্যাকাউন্ট নম্বর গ্রহণ
# ──────────────────────────────────────────────
@router.message(WithdrawalStates.entering_number)
async def receive_account_number(message: Message, state: FSMContext) -> None:
    if not WITHDRAWAL_ENABLED:
        await state.clear()
        await message.answer("🛠️ পেমেন্ট সিস্টেম এখনো চালু হয়নি।")
        return

    number = message.text.strip() if message.text else ""

    # বেসিক ভ্যালিডেশন: ১১ সংখ্যার বাংলাদেশি নম্বর
    if not (number.isdigit() and len(number) == 11 and number.startswith("01")):
        await message.answer(
            "❌ সঠিক নম্বর দিন।\n"
            "বাংলাদেশি মোবাইল নম্বর হতে হবে (01XXXXXXXXX)।"
        )
        return

    data = await state.get_data()
    points = data["points"]
    method = data["method"]
    amount_taka = points / POINTS_PER_TAKA
    method_labels = {"bkash": "বিকাশ", "nagad": "নগদ", "rocket": "রকেট"}
    label = method_labels.get(method, method)

    await state.update_data(account_number=number)
    await state.set_state(WithdrawalStates.confirming)

    await message.answer(
        f"✅ <b>নিশ্চিত করুন</b>\n\n"
        f"📊 পয়েন্ট: <b>{points}</b>\n"
        f"💵 টাকা: <b>৳{amount_taka:.2f}</b>\n"
        f"📱 মাধ্যম: <b>{label}</b>\n"
        f"📞 নম্বর: <b>{number}</b>\n\n"
        f"⚠️ নিশ্চিত করার পর পয়েন্ট কেটে যাবে।\n"
        f"অ্যাডমিন অনুমোদনের পর আপনার একাউন্টে টাকা পাঠানো হবে।",
        reply_markup=confirm_withdrawal_keyboard(),
    )


# ──────────────────────────────────────────────
# উইথড্রয়াল নিশ্চিত করুন
# ──────────────────────────────────────────────
@router.callback_query(F.data == "wd:confirm", WithdrawalStates.confirming)
async def confirm_withdrawal(
    callback: CallbackQuery, db: Database, state: FSMContext, bot: Bot
) -> None:
    if not WITHDRAWAL_ENABLED:
        await state.clear()
        await callback.answer("🛠️ পেমেন্ট সিস্টেম এখনো চালু হয়নি।", show_alert=True)
        return

    data = await state.get_data()
    user_id = callback.from_user.id
    points = data["points"]
    method = data["method"]
    number = data["account_number"]

    user = await db.get_user(user_id)
    if not user or user.get("is_banned"):
        await state.clear()
        await callback.answer("🚫 অ্যাকাউন্ট নিষিদ্ধ বা পাওয়া যায়নি।", show_alert=True)
        return

    active_referrals, can_withdraw, _, _ = await _get_withdrawal_requirements(
        db, user_id, user["points"]
    )
    if not can_withdraw:
        await state.clear()
        await callback.answer(
            f"❌ উত্তোলনের শর্ত পূরণ হয়নি। ৳{MIN_WITHDRAWAL_BDT} এবং {MIN_ACTIVE_REFERRALS}টি সক্রিয় রেফারেল লাগবে।",
            show_alert=True,
        )
        return

    if await db.has_pending_withdrawal(user_id):
        await state.clear()
        await callback.answer("⏳ আপনার একটি উত্তোলন আবেদন ইতিমধ্যে প্রক্রিয়াধীন আছে।", show_alert=True)
        return

    points = user["points"]

    # পয়েন্ট কাটুন (এখনই কাটা হয়; প্রত্যাখ্যাত হলে ফেরত দেওয়া হবে)
    success = await db.deduct_points(user_id, points)
    if not success:
        await state.clear()
        await callback.answer("❌ পর্যাপ্ত পয়েন্ট নেই বা অ্যাকাউন্ট সমস্যা।", show_alert=True)
        return

    withdrawal_id = await db.create_withdrawal(user_id, points, method, number)
    await state.clear()

    if not withdrawal_id:
        # পয়েন্ট ফেরত দিন (DB ত্রুটি)
        await db.add_points(user_id, points)
        await callback.answer("❌ সিস্টেম ত্রুটি। পরে চেষ্টা করুন।", show_alert=True)
        return

    method_labels = {"bkash": "বিকাশ", "nagad": "নগদ", "rocket": "রকেট"}
    label = method_labels.get(method, method)
    amount_taka = points / POINTS_PER_TAKA

    await callback.message.edit_text(
        f"✅ <b>উত্তোলন আবেদন জমা হয়েছে!</b>\n\n"
        f"📋 আবেদন নম্বর: <code>#{withdrawal_id}</code>\n"
        f"💵 পরিমাণ: <b>৳{amount_taka:.2f}</b> ({points} পয়েন্ট)\n"
        f"📱 {label}: <b>{number}</b>\n\n"
        f"⏳ অ্যাডমিন অনুমোদনের পর আপনার নম্বরে টাকা পাঠানো হবে।\n"
        f"সাধারণত ২৪ ঘণ্টার মধ্যে প্রক্রিয়া হয়।"
    )
    await callback.answer("✅ আবেদন সফলভাবে জমা হয়েছে!")

    # অ্যাডমিনকে নোটিফিকেশন পাঠান
    name = user["full_name"] if user else "অজানা"
    username = f"@{user['username']}" if user and user.get("username") else "নেই"

    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(
                admin_id,
                f"💸 <b>নতুন উত্তোলন আবেদন!</b>\n\n"
                f"👤 নাম: {name} ({username})\n"
                f"🆔 আইডি: <code>{user_id}</code>\n"
                f"📋 আবেদন নং: <code>#{withdrawal_id}</code>\n"
                f"💵 পরিমাণ: ৳{amount_taka:.2f} ({points} পয়েন্ট)\n"
                f"📱 {label}: {number}\n"
                f"👥 সক্রিয় রেফারেল: {active_referrals}",
                reply_markup=admin_withdrawal_keyboard(withdrawal_id),
            )
        except Exception as e:
            logger.warning(f"অ্যাডমিন {admin_id}-কে নোটিফাই করা যায়নি: {e}")


# ──────────────────────────────────────────────
# উইথড্রয়াল বাতিল
# ──────────────────────────────────────────────
@router.callback_query(F.data == "wd:cancel")
async def cancel_withdrawal(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text("❌ উত্তোলন বাতিল করা হয়েছে।")
    await callback.answer()
