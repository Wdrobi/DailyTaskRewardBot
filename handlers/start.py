import logging
import json
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from aiogram import Router, Bot, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from config import (
    FORCE_JOIN_CHANNELS,
    REFERRAL_REWARD,
    BOT_USERNAME,
    MINI_APP_URL,
    MIN_WITHDRAWAL_POINTS,
    POINTS_PER_TAKA,
    TUTORIAL_VIDEO_URL,
    WITHDRAWAL_ENABLED,
)
from database import Database
from keyboards.menus import dashboard_action_keyboard, force_join_keyboard, task_menu
from utils.access import can_access_bot, channel_button_url, channel_label, format_channel_lines

logger = logging.getLogger(__name__)
router = Router()


async def _process_referral_bonus(bot: Bot, db: Database, user_id: int, full_name: str) -> None:
    user = await db.get_user(user_id)
    if not user:
        return

    referrer_id = user.get("referred_by")
    if not referrer_id or referrer_id == user_id:
        return

    referrer = await db.get_user(referrer_id)
    if not referrer or referrer.get("is_banned"):
        return

    inserted = await db.add_referral(referrer_id, user_id, REFERRAL_REWARD)
    if not inserted:
        return

    await db.add_points(referrer_id, REFERRAL_REWARD)
    try:
        await bot.send_message(
            referrer_id,
            f"🎉 <b>রেফারেল বোনাস পেয়েছেন!</b>\n\n"
            f"<b>{full_name}</b> আপনার লিংক দিয়ে যোগ দিয়েছেন।\n"
            f"আপনি <b>+{REFERRAL_REWARD} পয়েন্ট</b> পেয়েছেন! 🎁",
        )
    except Exception:
        pass


async def _send_force_join_prompt(target: Message | CallbackQuery) -> None:
    if not FORCE_JOIN_CHANNELS:
        return

    channels = [
        (channel_label(channel), channel_button_url(channel))
        for channel in FORCE_JOIN_CHANNELS
    ]
    text = (
        "🔒 <b>বট ব্যবহার করতে আগে চ্যানেলগুলো join করতে হবে</b>\n\n"
        f"{format_channel_lines(FORCE_JOIN_CHANNELS)}\n\n"
        "সবগুলো join করার পর নিচের <b>Join Done</b> বাটনে চাপুন।"
    )

    if isinstance(target, CallbackQuery):
        await target.message.edit_text(text, reply_markup=force_join_keyboard(channels))
        await target.answer()
        return

    await target.answer(text, reply_markup=force_join_keyboard(channels))


def _build_url_with_query(base_url: str, params: dict[str, str]) -> str:
    if not base_url:
        return ""

    parsed = urlparse(base_url)
    current_query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    current_query.update({key: value for key, value in params.items() if value != ""})
    return urlunparse(parsed._replace(query=urlencode(current_query)))


async def _build_mini_app_url(db: Database, user_id: int) -> str:
    if not MINI_APP_URL:
        return ""

    user = await db.get_user(user_id)
    if not user:
        return MINI_APP_URL

    active_tasks = await db.get_active_tasks()
    referrals = await db.get_user_referrals(user_id)
    withdrawals = await db.get_user_withdrawals(user_id)
    ref_count = await db.get_referral_count(user_id)

    task_payload: list[dict] = []
    total_limit = 0
    total_completed = 0
    watch_ad_done = 0
    watch_ad_limit = 0

    for task in active_tasks:
        completed_today = await db.get_daily_task_count(user_id, task["task_key"])
        total_limit += task["daily_limit"]
        total_completed += min(completed_today, task["daily_limit"])

        if task["task_key"] == "watch_ad":
            watch_ad_done = completed_today
            watch_ad_limit = task["daily_limit"]

        task_payload.append(
            {
                "taskKey": task["task_key"],
                "title": task["title"],
                "description": task["description"],
                "kind": task["task_kind"],
                "reward": round(task["reward_points"] / POINTS_PER_TAKA, 2),
                "buttonText": task["button_text"],
                "remaining": max(task["daily_limit"] - completed_today, 0),
                "dailyLimit": task["daily_limit"],
                "verifySeconds": task["verify_seconds"],
                "completed": completed_today >= task["daily_limit"],
                "url": task["target_url"],
            }
        )

    referral_payload = [
        {
            "name": item["full_name"] or item["username"] or f"User {item['referred_id']}",
            "joinedAt": str(item["created_at"])[:10],
            "earned": round(item["points_awarded"] / POINTS_PER_TAKA, 2),
        }
        for item in referrals
    ]

    withdrawal_payload = [
        {
            "amount": round(item["amount_bdt"], 2),
            "status": item["status"],
            "method": item["payment_method"],
            "date": str(item["requested_at"])[:10],
        }
        for item in withdrawals[:20]
    ]

    progress = int((total_completed / total_limit) * 100) if total_limit else 0
    query = {
        "botUsername": BOT_USERNAME,
        "name": user["full_name"],
        "balance": f"{user['points'] / POINTS_PER_TAKA:.2f}",
        "adsToday": str(watch_ad_done),
        "adsLimit": str(watch_ad_limit),
        "referrals": str(ref_count),
        "progress": str(progress),
        "tasksCompleted": str(total_completed),
        "referralReward": f"{REFERRAL_REWARD / POINTS_PER_TAKA:.2f}",
        "tutorialUrl": TUTORIAL_VIDEO_URL,
        "supportUrl": f"https://t.me/{BOT_USERNAME}",
        "ref": f"start=ref_{user_id}",
        "tasks": json.dumps(task_payload, ensure_ascii=False, separators=(",", ":")),
        "referralUsers": json.dumps(referral_payload, ensure_ascii=False, separators=(",", ":")),
        "withdrawals": json.dumps(withdrawal_payload, ensure_ascii=False, separators=(",", ":")),
        "withdrawEnabled": "1" if WITHDRAWAL_ENABLED else "0",
    }
    return _build_url_with_query(MINI_APP_URL, query)


def _dashboard_text(full_name: str) -> str:
    return (
        f"✅ <b>স্বাগতম {full_name}</b> 🌟\n\n"
        "নিচের <b>ইনকাম শুরু করুন</b> বাটনে চাপুন। Mini App খুলে টাস্ক করুন এবং আয় শুরু করুন।\n\n"
        "👉 <b>ইনকাম শুরু করুন</b> বাটনে চাপুন।\n\n"
        "বোঝার সুবিধার জন্য 🎥 টিউটোরিয়াল ভিডিও-ও দেখে নিন।"
    )


async def _send_dashboard(message: Message, db: Database) -> None:
    user = await db.get_user(message.from_user.id)
    if not user:
        await message.answer("❌ ইউজার ডেটা পাওয়া যায়নি। আবার /start দিন।")
        return

    mini_app_url = await _build_mini_app_url(db, message.from_user.id)

    await message.answer(
        _dashboard_text(user["full_name"]),
        reply_markup=dashboard_action_keyboard(mini_app_url, TUTORIAL_VIDEO_URL),
    )


async def _send_dashboard_to_chat(bot: Bot, db: Database, chat_id: int, user_id: int) -> None:
    user = await db.get_user(user_id)
    if not user:
        await bot.send_message(chat_id, "❌ ইউজার ডেটা পাওয়া যায়নি। আবার /start দিন।")
        return

    mini_app_url = await _build_mini_app_url(db, user_id)

    await bot.send_message(
        chat_id,
        _dashboard_text(user["full_name"]),
        reply_markup=dashboard_action_keyboard(mini_app_url, TUTORIAL_VIDEO_URL),
    )


async def _ensure_message_access(message: Message, bot: Bot) -> bool:
    has_access, _, had_error = await can_access_bot(bot, message.from_user.id)
    if had_error:
        await message.answer("⚠️ Channel verification issue আছে। পরে আবার চেষ্টা করুন।")
        return False
    if not has_access:
        await _send_force_join_prompt(message)
        return False
    return True


# ──────────────────────────────────────────────
# /start
# ──────────────────────────────────────────────
@router.message(CommandStart())
async def cmd_start(message: Message, db: Database, state: FSMContext, bot: Bot) -> None:
    await state.clear()
    from_user = message.from_user

    # রেফারেল আর্গুমেন্ট পার্স করুন  e.g. /start ref_123456
    referred_by: int | None = None
    args = message.text.split(maxsplit=1)
    if len(args) > 1 and args[1].startswith("ref_"):
        try:
            ref_id = int(args[1][4:])
            if ref_id != from_user.id:
                referred_by = ref_id
        except ValueError:
            pass

    is_new = await db.register_user(
        user_id=from_user.id,
        username=from_user.username or "",
        full_name=from_user.full_name,
        referred_by=referred_by,
    )

    if not is_new:
        await db.update_user_info(from_user.id, from_user.username or "", from_user.full_name)

    user = await db.get_user(from_user.id)
    if user and user.get("is_banned"):
        await message.answer("🚫 আপনার অ্যাকাউন্ট নিষিদ্ধ করা হয়েছে।")
        return

    has_access, _, had_error = await can_access_bot(bot, from_user.id)
    if had_error:
        await message.answer(
            "⚠️ Channel verification এখন কাজ করছে না।\n"
            "Bot-কে required channel-এ admin/member করে আবার চেষ্টা করুন।"
        )
        return

    if not has_access:
        await _send_force_join_prompt(message)
        return

    await _process_referral_bonus(bot, db, from_user.id, from_user.full_name)
    await _send_dashboard(message, db)


@router.callback_query(F.data == "force_join:check")
async def force_join_check(callback: CallbackQuery, db: Database, bot: Bot) -> None:
    has_access, _, had_error = await can_access_bot(bot, callback.from_user.id)
    if had_error:
        await callback.answer(
            "Channel check failed. Bot-কে channel-এ add/admin করা আছে কিনা দেখুন।",
            show_alert=True,
        )
        return

    if not has_access:
        await callback.answer("সব required channel এখনো join করা হয়নি।", show_alert=True)
        return

    await _process_referral_bonus(bot, db, callback.from_user.id, callback.from_user.full_name)
    await callback.message.delete()
    await _send_dashboard_to_chat(bot, db, callback.message.chat.id, callback.from_user.id)
    await callback.answer()


@router.message(lambda m: m.text == "🏠 ড্যাশবোর্ড")
async def dashboard(message: Message, db: Database, bot: Bot) -> None:
    if not await _ensure_message_access(message, bot):
        return

    await _send_dashboard(message, db)


# ──────────────────────────────────────────────
# প্রোফাইল
# ──────────────────────────────────────────────
@router.message(lambda m: m.text == "📊 আমার প্রোফাইল")
async def my_profile(message: Message, db: Database, bot: Bot) -> None:
    if not await _ensure_message_access(message, bot):
        return

    user = await db.get_user(message.from_user.id)
    if not user or user.get("is_banned"):
        await message.answer("🚫 আপনার অ্যাকাউন্ট নিষিদ্ধ।")
        return

    ref_count = await db.get_referral_count(message.from_user.id)
    withdrawable = user["points"] // POINTS_PER_TAKA

    await message.answer(
        f"📊 <b>আমার প্রোফাইল</b>\n\n"
        f"👤 নাম: <b>{user['full_name']}</b>\n"
        f"🆔 আইডি: <code>{user['user_id']}</code>\n\n"
        f"💰 বর্তমান পয়েন্ট: <b>{user['points']}</b>\n"
        f"📈 মোট অর্জন: <b>{user['total_earned']}</b>\n"
        f"🏦 মোট উত্তোলন: <b>{user['total_withdrawn']}</b> পয়েন্ট\n"
        f"👥 সফল রেফারেল: <b>{ref_count}</b> জন\n\n"
        f"💵 উত্তোলনযোগ্য: <b>৳{withdrawable:.0f}</b>\n"
        f"📅 যোগদান: {user['joined_at'][:10]}",
    )


# ──────────────────────────────────────────────
# লিডারবোর্ড
# ──────────────────────────────────────────────
@router.message(lambda m: m.text == "🏆 লিডারবোর্ড")
async def leaderboard(message: Message, db: Database, bot: Bot) -> None:
    if not await _ensure_message_access(message, bot):
        return

    top = await db.get_top_users(10)
    if not top:
        await message.answer("এখনো কোনো তথ্য নেই।")
        return

    lines = ["🏆 <b>শীর্ষ ১০ আর্নার</b>\n"]
    medals = ["🥇", "🥈", "🥉"]
    for i, u in enumerate(top):
        medal = medals[i] if i < 3 else f"{i + 1}."
        name = u["full_name"] or u["username"] or "অজানা"
        lines.append(f"{medal} {name} — <b>{u['total_earned']}</b> পয়েন্ট")

    await message.answer("\n".join(lines))


# ──────────────────────────────────────────────
# রেফার লিংক
# ──────────────────────────────────────────────
@router.message(lambda m: m.text == "👥 রেফার করুন")
async def refer(message: Message, db: Database, bot: Bot) -> None:
    if not await _ensure_message_access(message, bot):
        return

    user = await db.get_user(message.from_user.id)
    if not user or user.get("is_banned"):
        return

    ref_count = await db.get_referral_count(message.from_user.id)
    ref_link = f"https://t.me/{BOT_USERNAME}?start=ref_{message.from_user.id}"

    await message.answer(
        f"👥 <b>রেফার করুন, আয় করুন!</b>\n\n"
        f"প্রতিটি সফল রেফারেলে আপনি <b>+{REFERRAL_REWARD} পয়েন্ট</b> পাবেন।\n\n"
        f"🔗 <b>আপনার রেফারেল লিংক:</b>\n"
        f"<code>{ref_link}</code>\n\n"
        f"👥 এখন পর্যন্ত রেফার করেছেন: <b>{ref_count}</b> জন",
    )


# ──────────────────────────────────────────────
# সাহায্য
# ──────────────────────────────────────────────
@router.message(lambda m: m.text == "ℹ️ সাহায্য")
async def help_cmd(message: Message, bot: Bot) -> None:
    if not await _ensure_message_access(message, bot):
        return

    withdrawal_help = (
        f"  ন্যূনতম {MIN_WITHDRAWAL_POINTS} পয়েন্ট হলে বিকাশ/নগদে টাকা পাবেন\n"
        f"  ১০০ পয়েন্ট = ১ টাকা\n\n"
        if WITHDRAWAL_ENABLED
        else "  পেমেন্ট/উত্তোলন ফিচার এখনো চালু হয়নি\n"
             "  পরে আপডেট দিয়ে চালু করা হবে\n\n"
    )

    await message.answer(
        "ℹ️ <b>সাহায্য ও নির্দেশিকা</b>\n\n"
        "<b>টাস্ক করুন:</b>\n"
        "  📺 অ্যাড দেখুন → ৫ পয়েন্ট (দিনে সর্বোচ্চ ৫ বার)\n"
        "  🌐 সাইট ভিজিট → ৩ পয়েন্ট (দিনে সর্বোচ্চ ৩ বার)\n"
        "  📅 দৈনিক চেক-ইন → ২ পয়েন্ট (দিনে ১ বার)\n\n"
        "<b>রেফারেল:</b>\n"
        "  বন্ধুকে রেফার করুন → +২০ পয়েন্ট\n\n"
        "<b>উত্তোলন:</b>\n"
        f"{withdrawal_help}"
        "❓ সমস্যা হলে অ্যাডমিনকে মেসেজ করুন।",
    )


@router.callback_query(F.data == "nav:tasks")
async def nav_tasks(callback: CallbackQuery, db: Database, bot: Bot) -> None:
    has_access, _, had_error = await can_access_bot(bot, callback.from_user.id)
    if had_error:
        await callback.answer("Channel verification issue.", show_alert=True)
        return
    if not has_access:
        await callback.answer("আগে required channel join করুন।", show_alert=True)
        return

    tasks = await db.get_active_tasks()
    if not tasks:
        await callback.answer("এখন কোনো active task নেই।", show_alert=True)
        return

    await callback.message.answer(
        "📋 <b>উপলব্ধ টাস্কসমূহ</b>\n\nযেকোনো টাস্ক বেছে পয়েন্ট অর্জন করুন:",
        reply_markup=task_menu(tasks),
    )
    await callback.answer()


@router.callback_query(F.data == "nav:wallet")
async def nav_wallet(callback: CallbackQuery) -> None:
    await callback.answer("💰 Wallet দেখতে Mini App ব্যবহার করুন।", show_alert=True)


@router.callback_query(F.data == "nav:referral")
async def nav_referral(callback: CallbackQuery, db: Database, bot: Bot) -> None:
    has_access, _, had_error = await can_access_bot(bot, callback.from_user.id)
    if had_error:
        await callback.answer("Channel verification issue.", show_alert=True)
        return
    if not has_access:
        await callback.answer("আগে required channel join করুন।", show_alert=True)
        return

    ref_count = await db.get_referral_count(callback.from_user.id)
    ref_link = f"https://t.me/{BOT_USERNAME}?start=ref_{callback.from_user.id}"
    await callback.message.answer(
        f"👥 <b>রেফার করুন, আয় করুন!</b>\n\n"
        f"প্রতিটি সফল রেফারেলে আপনি <b>+{REFERRAL_REWARD} পয়েন্ট</b> পাবেন।\n\n"
        f"🔗 <b>আপনার রেফারেল লিংক:</b>\n"
        f"<code>{ref_link}</code>\n\n"
        f"👥 এখন পর্যন্ত রেফার করেছেন: <b>{ref_count}</b> জন",
    )
    await callback.answer()


@router.callback_query(F.data == "nav:leaderboard")
async def nav_leaderboard(callback: CallbackQuery, db: Database, bot: Bot) -> None:
    has_access, _, had_error = await can_access_bot(bot, callback.from_user.id)
    if had_error:
        await callback.answer("Channel verification issue.", show_alert=True)
        return
    if not has_access:
        await callback.answer("আগে required channel join করুন।", show_alert=True)
        return

    top = await db.get_top_users(10)
    if not top:
        await callback.answer("এখনো কোনো তথ্য নেই।", show_alert=True)
        return

    lines = ["🏆 <b>শীর্ষ ১০ আর্নার</b>\n"]
    medals = ["🥇", "🥈", "🥉"]
    for i, user in enumerate(top):
        medal = medals[i] if i < 3 else f"{i + 1}."
        name = user["full_name"] or user["username"] or "অজানা"
        lines.append(f"{medal} {name} — <b>{user['total_earned']}</b> পয়েন্ট")

    await callback.message.answer("\n".join(lines))
    await callback.answer()
