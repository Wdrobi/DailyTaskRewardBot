import asyncio
import logging

from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from config import ADMIN_IDS, POINTS_PER_TAKA
from database import Database
from keyboards.menus import admin_panel_keyboard, admin_withdrawal_keyboard
from states import AdminStates

logger = logging.getLogger(__name__)
router = Router()


def _is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


# ──────────────────────────────────────────────
# /admin — প্যানেল
# ──────────────────────────────────────────────
@router.message(Command("admin"))
async def admin_panel(message: Message, state: FSMContext) -> None:
    if not _is_admin(message.from_user.id):
        return
    await state.clear()
    await message.answer("🔐 <b>অ্যাডমিন প্যানেল</b>", reply_markup=admin_panel_keyboard())


# ──────────────────────────────────────────────
# পরিসংখ্যান
# ──────────────────────────────────────────────
@router.callback_query(F.data == "admin:stats")
async def admin_stats(callback: CallbackQuery, db: Database) -> None:
    if not _is_admin(callback.from_user.id):
        return
    stats = await db.get_stats()
    await callback.message.edit_text(
        f"📊 <b>বট পরিসংখ্যান</b>\n\n"
        f"👥 মোট ইউজার: <b>{stats['total_users']}</b>\n"
        f"🆕 আজকের নতুন ইউজার: <b>{stats['today_users']}</b>\n"
        f"✅ আজকের টাস্ক সম্পন্ন: <b>{stats['today_tasks']}</b>\n"
        f"⏳ পেন্ডিং উইথড্রয়াল: <b>{stats['pending_withdrawals']}</b>\n"
        f"🪙 মোট পয়েন্ট বিতরণ: <b>{stats['total_points_distributed']}</b>",
        reply_markup=admin_panel_keyboard(),
    )
    await callback.answer()


# ──────────────────────────────────────────────
# পেন্ডিং উইথড্রয়াল তালিকা
# ──────────────────────────────────────────────
@router.callback_query(F.data == "admin:pending_wd")
async def admin_pending_withdrawals(callback: CallbackQuery, db: Database) -> None:
    if not _is_admin(callback.from_user.id):
        return

    pending = await db.get_pending_withdrawals()
    if not pending:
        await callback.answer("✅ কোনো পেন্ডিং উইথড্রয়াল নেই।", show_alert=True)
        return

    method_labels = {"bkash": "বিকাশ", "nagad": "নগদ", "rocket": "রকেট"}

    for w in pending:
        label = method_labels.get(w["payment_method"], w["payment_method"])
        name = w["full_name"] or w["username"] or "অজানা"
        await callback.message.answer(
            f"💸 <b>উত্তোলন আবেদন #{w['id']}</b>\n\n"
            f"👤 {name} (<code>{w['user_id']}</code>)\n"
            f"💵 ৳{w['amount_bdt']:.2f} ({w['points']} পয়েন্ট)\n"
            f"📱 {label}: <code>{w['payment_number']}</code>\n"
            f"📅 তারিখ: {str(w['requested_at'])[:16]}",
            reply_markup=admin_withdrawal_keyboard(w["id"]),
        )
    await callback.answer()


# ──────────────────────────────────────────────
# উইথড্রয়াল অনুমোদন
# ──────────────────────────────────────────────
@router.callback_query(F.data.startswith("admin_wd:approve:"))
async def approve_withdrawal(callback: CallbackQuery, db: Database, bot: Bot) -> None:
    if not _is_admin(callback.from_user.id):
        return

    withdrawal_id = int(callback.data.split(":")[2])
    wd = await db.get_withdrawal_by_id(withdrawal_id)
    if not wd:
        await callback.answer("❌ আবেদন পাওয়া যায়নি।", show_alert=True)
        return
    if wd["status"] != "pending":
        await callback.answer("⚠️ এই আবেদন ইতিমধ্যে প্রক্রিয়া করা হয়েছে।", show_alert=True)
        return

    await db.update_withdrawal_status(withdrawal_id, "approved", "অ্যাডমিন কর্তৃক অনুমোদিত")
    await callback.message.edit_text(
        callback.message.text + "\n\n✅ <b>অনুমোদিত হয়েছে।</b>"
    )
    await callback.answer("✅ অনুমোদন দেওয়া হয়েছে।")

    # ইউজারকে নোটিফাই করুন
    method_labels = {"bkash": "বিকাশ", "nagad": "নগদ", "rocket": "রকেট"}
    label = method_labels.get(wd["payment_method"], wd["payment_method"])
    try:
        await bot.send_message(
            wd["user_id"],
            f"✅ <b>উত্তোলন অনুমোদিত!</b>\n\n"
            f"📋 আবেদন নং: <code>#{withdrawal_id}</code>\n"
            f"💵 পরিমাণ: ৳{wd['amount_bdt']:.2f} ({wd['points']} পয়েন্ট)\n"
            f"📱 {label}: {wd['payment_number']}\n\n"
            f"শীঘ্রই আপনার একাউন্টে টাকা পাঠানো হবে। ধন্যবাদ! 🙏",
        )
    except Exception as e:
        logger.warning(f"ইউজার {wd['user_id']}-কে নোটিফাই করা যায়নি: {e}")


# ──────────────────────────────────────────────
# উইথড্রয়াল প্রত্যাখ্যান
# ──────────────────────────────────────────────
@router.callback_query(F.data.startswith("admin_wd:reject:"))
async def reject_withdrawal(callback: CallbackQuery, db: Database, bot: Bot) -> None:
    if not _is_admin(callback.from_user.id):
        return

    withdrawal_id = int(callback.data.split(":")[2])
    wd = await db.get_withdrawal_by_id(withdrawal_id)
    if not wd:
        await callback.answer("❌ আবেদন পাওয়া যায়নি।", show_alert=True)
        return
    if wd["status"] != "pending":
        await callback.answer("⚠️ এই আবেদন ইতিমধ্যে প্রক্রিয়া করা হয়েছে।", show_alert=True)
        return

    # পয়েন্ট ফেরত দিন
    await db.restore_points_on_rejection(withdrawal_id)
    await db.update_withdrawal_status(withdrawal_id, "rejected", "অ্যাডমিন কর্তৃক প্রত্যাখ্যাত")

    await callback.message.edit_text(
        callback.message.text + "\n\n❌ <b>প্রত্যাখ্যাত হয়েছে। পয়েন্ট ফেরত দেওয়া হয়েছে।</b>"
    )
    await callback.answer("❌ প্রত্যাখ্যান করা হয়েছে।")

    method_labels = {"bkash": "বিকাশ", "nagad": "নগদ", "rocket": "রকেট"}
    label = method_labels.get(wd["payment_method"], wd["payment_method"])
    try:
        await bot.send_message(
            wd["user_id"],
            f"❌ <b>উত্তোলন প্রত্যাখ্যাত!</b>\n\n"
            f"📋 আবেদন নং: <code>#{withdrawal_id}</code>\n"
            f"💵 {wd['points']} পয়েন্ট আপনার অ্যাকাউন্টে ফেরত দেওয়া হয়েছে।\n\n"
            f"কোনো সমস্যায় অ্যাডমিনকে যোগাযোগ করুন।",
        )
    except Exception as e:
        logger.warning(f"ইউজার {wd['user_id']}-কে নোটিফাই করা যায়নি: {e}")


# ──────────────────────────────────────────────
# ব্রডকাস্ট
# ──────────────────────────────────────────────
@router.callback_query(F.data == "admin:broadcast")
async def start_broadcast(callback: CallbackQuery, state: FSMContext) -> None:
    if not _is_admin(callback.from_user.id):
        return
    await state.set_state(AdminStates.broadcasting)
    await callback.message.answer(
        "📢 <b>ব্রডকাস্ট মেসেজ</b>\n\n"
        "যে মেসেজটি সব ইউজারকে পাঠাতে চান তা লিখুন।\n"
        "বাতিল করতে /cancel লিখুন।"
    )
    await callback.answer()


@router.message(AdminStates.broadcasting)
async def send_broadcast(message: Message, db: Database, state: FSMContext, bot: Bot) -> None:
    if not _is_admin(message.from_user.id):
        return
    if message.text and message.text.strip() == "/cancel":
        await state.clear()
        await message.answer("❌ ব্রডকাস্ট বাতিল।")
        return

    await state.clear()
    user_ids = await db.get_all_user_ids()
    sent = 0
    failed = 0

    status_msg = await message.answer(f"📤 ব্রডকাস্ট শুরু হচ্ছে... ({len(user_ids)} ইউজার)")

    for uid in user_ids:
        try:
            await bot.copy_message(uid, message.chat.id, message.message_id)
            sent += 1
        except Exception:
            failed += 1
        # টেলিগ্রামের রেট লিমিট এড়াতে
        if sent % 25 == 0:
            await asyncio.sleep(1)

    await status_msg.edit_text(
        f"✅ <b>ব্রডকাস্ট সম্পন্ন!</b>\n\n"
        f"✅ পাঠানো হয়েছে: {sent}\n"
        f"❌ বাতিল/ব্যর্থ: {failed}"
    )


# ──────────────────────────────────────────────
# ব্যান
# ──────────────────────────────────────────────
@router.callback_query(F.data == "admin:ban")
async def start_ban(callback: CallbackQuery, state: FSMContext) -> None:
    if not _is_admin(callback.from_user.id):
        return
    await state.set_state(AdminStates.banning)
    await callback.message.answer(
        "🚫 <b>ইউজার ব্যান</b>\n\nব্যান করতে ইউজারের টেলিগ্রাম আইডি লিখুন:"
    )
    await callback.answer()


@router.message(AdminStates.banning)
async def do_ban(message: Message, db: Database, state: FSMContext) -> None:
    if not _is_admin(message.from_user.id):
        return
    await state.clear()
    try:
        target_id = int(message.text.strip())
    except (ValueError, AttributeError):
        await message.answer("❌ সঠিক আইডি দিন।")
        return

    if target_id in ADMIN_IDS:
        await message.answer("❌ অ্যাডমিনকে ব্যান করা যাবে না।")
        return

    await db.ban_user(target_id)
    await message.answer(f"✅ ইউজার <code>{target_id}</code> ব্যান করা হয়েছে।")


# ──────────────────────────────────────────────
# আনব্যান
# ──────────────────────────────────────────────
@router.callback_query(F.data == "admin:unban")
async def start_unban(callback: CallbackQuery, state: FSMContext) -> None:
    if not _is_admin(callback.from_user.id):
        return
    await state.set_state(AdminStates.unbanning)
    await callback.message.answer(
        "✅ <b>ইউজার আনব্যান</b>\n\nআনব্যান করতে ইউজারের টেলিগ্রাম আইডি লিখুন:"
    )
    await callback.answer()


@router.message(AdminStates.unbanning)
async def do_unban(message: Message, db: Database, state: FSMContext) -> None:
    if not _is_admin(message.from_user.id):
        return
    await state.clear()
    try:
        target_id = int(message.text.strip())
    except (ValueError, AttributeError):
        await message.answer("❌ সঠিক আইডি দিন।")
        return

    await db.unban_user(target_id)
    await message.answer(f"✅ ইউজার <code>{target_id}</code> আনব্যান করা হয়েছে।")
