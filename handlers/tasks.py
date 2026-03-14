import logging
from datetime import datetime, timezone

from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from database import Database
from keyboards.menus import task_action_keyboard, task_menu
from states import TaskStates
from utils.access import can_access_bot

logger = logging.getLogger(__name__)
router = Router()


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _seconds_ago(dt: datetime) -> float:
    """কতো সেকেন্ড আগে ছিল তা হিসাব করুন।"""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return (_now_utc() - dt).total_seconds()


async def _validate_task_access(db: Database, user_id: int, task: dict) -> str | None:
    daily_count = await db.get_daily_task_count(user_id, task["task_key"])
    if daily_count >= task["daily_limit"]:
        return f"⏰ আজকের সীমা ({task['daily_limit']} বার) শেষ। কাল আবার আসুন!"

    last_time = await db.get_last_task_time(user_id, task["task_key"])
    if last_time and task["cooldown_seconds"] > 0:
        elapsed = _seconds_ago(last_time)
        if elapsed < task["cooldown_seconds"]:
            remaining = int(task["cooldown_seconds"] - elapsed)
            mins, secs = divmod(remaining, 60)
            return f"⏳ এই টাস্ক আবার করতে আরও {mins} মিনিট {secs} সেকেন্ড অপেক্ষা করুন।"

    return None


async def _check_callback_access(callback: CallbackQuery) -> bool:
    has_access, _, had_error = await can_access_bot(callback.bot, callback.from_user.id)
    if had_error:
        await callback.answer("Channel verification issue.", show_alert=True)
        return False
    if not has_access:
        await callback.answer("আগে required channel join করুন।", show_alert=True)
        return False
    return True


# ──────────────────────────────────────────────
# টাস্ক মেনু দেখান
# ──────────────────────────────────────────────
@router.message(F.text == "✅ টাস্ক করুন")
async def show_tasks(message: Message, db: Database, state: FSMContext, bot: Bot) -> None:
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

    tasks = await db.get_active_tasks()
    if not tasks:
        await message.answer("⚠️ এই মুহূর্তে কোনো active task নেই।")
        return

    await message.answer(
        "📋 <b>উপলব্ধ টাস্কসমূহ</b>\n\n"
        "যেকোনো টাস্ক বেছে পয়েন্ট অর্জন করুন:",
        reply_markup=task_menu(tasks),
    )


# ──────────────────────────────────────────────
# অ্যাড দেখুন — শুরু
# ──────────────────────────────────────────────
@router.callback_query(F.data.startswith("task:start:"))
async def start_task(callback: CallbackQuery, db: Database, state: FSMContext) -> None:
    if not await _check_callback_access(callback):
        return

    task_key = callback.data.split(":", 2)[2]
    task = await db.get_task_by_key(task_key)
    if not task:
        await callback.answer("❌ টাস্কটি পাওয়া যায়নি।", show_alert=True)
        return

    user_id = callback.from_user.id
    user = await db.get_user(user_id)
    if not user or user.get("is_banned"):
        await callback.answer("🚫 অ্যাকাউন্ট নিষিদ্ধ।", show_alert=True)
        return

    access_error = await _validate_task_access(db, user_id, task)
    if access_error:
        await callback.answer(access_error, show_alert=True)
        return

    if task["task_kind"] == "instant":
        await db.add_points(user_id, task["reward_points"])
        await db.record_task(user_id, task["task_key"], task["reward_points"])
        user = await db.get_user(user_id)
        await callback.message.edit_text(
            f"✅ <b>{task['title']} সম্পন্ন!</b>\n\n"
            f"🎁 আপনি <b>+{task['reward_points']} পয়েন্ট</b> পেয়েছেন!\n"
            f"💰 মোট পয়েন্ট: <b>{user['points'] if user else task['reward_points']}</b>",
        )
        await callback.answer(f"🎉 +{task['reward_points']} পয়েন্ট পেয়েছেন!")
        return

    await state.set_state(TaskStates.active_task)
    await state.update_data(task_key=task_key, started_at=_now_utc().isoformat())

    await callback.message.edit_text(
        f"{task['title']}\n\n"
        f"{task['description']}\n\n"
        f"🎁 রিওয়ার্ড: <b>+{task['reward_points']} পয়েন্ট</b>\n"
        f"⏱️ যাচাই সময়: <b>{task['verify_seconds']} সেকেন্ড</b>",
        reply_markup=task_action_keyboard(task),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("task:claim:"), TaskStates.active_task)
async def claim_task(callback: CallbackQuery, db: Database, state: FSMContext) -> None:
    if not await _check_callback_access(callback):
        return

    data = await state.get_data()
    task_key = callback.data.split(":", 2)[2]
    if data.get("task_key") != task_key:
        await state.clear()
        await callback.answer("❌ এই টাস্ক সেশনটি আর বৈধ নেই। আবার শুরু করুন।", show_alert=True)
        return

    task = await db.get_task_by_key(task_key)
    if not task:
        await state.clear()
        await callback.answer("❌ টাস্কটি আর active নেই।", show_alert=True)
        return

    started_at_str = data.get("started_at")

    if started_at_str:
        started_at = datetime.fromisoformat(started_at_str)
        elapsed = _seconds_ago(started_at)
        if elapsed < task["verify_seconds"]:
            remaining = int(task["verify_seconds"] - elapsed)
            await callback.answer(
                f"⏳ আরও {remaining} সেকেন্ড অপেক্ষা করুন।",
                show_alert=True,
            )
            return

    access_error = await _validate_task_access(db, callback.from_user.id, task)
    if access_error:
        await state.clear()
        await callback.answer(access_error, show_alert=True)
        return

    await state.clear()
    user_id = callback.from_user.id
    points = task["reward_points"]

    await db.add_points(user_id, points)
    await db.record_task(user_id, task["task_key"], points)

    user = await db.get_user(user_id)
    await callback.message.edit_text(
        f"✅ <b>{task['title']} সম্পন্ন!</b>\n\n"
        f"🎁 আপনি <b>+{points} পয়েন্ট</b> পেয়েছেন!\n"
        f"💰 মোট পয়েন্ট: <b>{user['points'] if user else points}</b>",
    )
    await callback.answer(f"🎉 +{points} পয়েন্ট পেয়েছেন!")


# ──────────────────────────────────────────────
# টাস্ক বাতিল
# ──────────────────────────────────────────────
@router.callback_query(F.data == "task:cancel")
async def cancel_task(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text("❌ টাস্ক বাতিল করা হয়েছে।")
    await callback.answer()
