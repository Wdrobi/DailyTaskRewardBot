from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    WebAppInfo,
)
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder


# ──────────────────────────────────────────────
# মূল মেনু
# ──────────────────────────────────────────────
def main_menu() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text="🏠 ড্যাশবোর্ড"),
        KeyboardButton(text="✅ টাস্ক করুন"),
    )
    builder.row(
        KeyboardButton(text="💰 আমার ওয়ালেট"),
        KeyboardButton(text="👥 রেফার করুন"),
    )
    builder.row(
        KeyboardButton(text="🏆 লিডারবোর্ড"),
        KeyboardButton(text="📊 আমার প্রোফাইল"),
    )
    builder.row(KeyboardButton(text="ℹ️ সাহায্য"))
    return builder.as_markup(resize_keyboard=True)


def force_join_keyboard(channels: list[tuple[str, str]]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for label, url in channels:
        builder.row(InlineKeyboardButton(text=f"📢 {label}", url=url))
    builder.row(
        InlineKeyboardButton(text="✅ Join Done", callback_data="force_join:check")
    )
    return builder.as_markup()


def dashboard_action_keyboard(
    mini_app_url: str,
    tutorial_url: str,
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if mini_app_url:
        builder.row(
            InlineKeyboardButton(
                text="💸 ইনকাম শুরু করুন",
                web_app=WebAppInfo(url=mini_app_url),
            )
        )
    builder.row(
        InlineKeyboardButton(text="🎥 টিউটোরিয়াল ভিডিও", url=tutorial_url)
    )
    builder.row(
        InlineKeyboardButton(text="🏆 Leaderboard", callback_data="nav:leaderboard"),
        InlineKeyboardButton(text="👥 Invite & Earn", callback_data="nav:referral"),
    )
    builder.row(
        InlineKeyboardButton(text="✅ Tasks", callback_data="nav:tasks"),
        InlineKeyboardButton(text="💰 Wallet", callback_data="nav:wallet"),
    )
    return builder.as_markup()


# ──────────────────────────────────────────────
# টাস্ক মেনু
# ──────────────────────────────────────────────
def task_menu(tasks: list[dict]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for task in tasks:
        builder.row(
            InlineKeyboardButton(
                text=f"{task['title']}  (+{task['reward_points']} পয়েন্ট)",
                callback_data=f"task:start:{task['task_key']}",
            )
        )
    return builder.as_markup()


# ──────────────────────────────────────────────
# ডাইনামিক টাস্ক কীবোর্ড
# ──────────────────────────────────────────────
def task_action_keyboard(task: dict) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if task.get("target_url"):
        builder.row(
            InlineKeyboardButton(text=task["button_text"], url=task["target_url"])
        )
    if task["task_kind"] == "link":
        builder.row(
            InlineKeyboardButton(
                text="✅ Done, Claim Reward",
                callback_data=f"task:claim:{task['task_key']}",
            )
        )
    builder.row(
        InlineKeyboardButton(text="❌ বাতিল", callback_data="task:cancel")
    )
    return builder.as_markup()


# ──────────────────────────────────────────────
# উইথড্রয়াল — পেমেন্ট মেথড
# ──────────────────────────────────────────────
def withdrawal_methods_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📱 বিকাশ",  callback_data="wd_method:bkash"),
        InlineKeyboardButton(text="📱 নগদ",    callback_data="wd_method:nagad"),
    )
    builder.row(
        InlineKeyboardButton(text="📱 রকেট", callback_data="wd_method:rocket"),
    )
    builder.row(
        InlineKeyboardButton(text="❌ বাতিল", callback_data="wd:cancel")
    )
    return builder.as_markup()


# ──────────────────────────────────────────────
# উইথড্রয়াল নিশ্চিতকরণ
# ──────────────────────────────────────────────
def confirm_withdrawal_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ নিশ্চিত করুন", callback_data="wd:confirm"),
        InlineKeyboardButton(text="❌ বাতিল",         callback_data="wd:cancel"),
    )
    return builder.as_markup()


# ──────────────────────────────────────────────
# অ্যাডমিন — উইথড্রয়াল অনুমোদন/প্রত্যাখ্যান
# ──────────────────────────────────────────────
def admin_withdrawal_keyboard(withdrawal_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="✅ অনুমোদন", callback_data=f"admin_wd:approve:{withdrawal_id}"
        ),
        InlineKeyboardButton(
            text="❌ প্রত্যাখ্যান", callback_data=f"admin_wd:reject:{withdrawal_id}"
        ),
    )
    return builder.as_markup()


# ──────────────────────────────────────────────
# অ্যাডমিন প্যানেল
# ──────────────────────────────────────────────
def admin_panel_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📊 পরিসংখ্যান",          callback_data="admin:stats")
    )
    builder.row(
        InlineKeyboardButton(text="⏳ পেন্ডিং উইথড্রয়াল",  callback_data="admin:pending_wd")
    )
    builder.row(
        InlineKeyboardButton(text="📢 ব্রডকাস্ট",           callback_data="admin:broadcast")
    )
    builder.row(
        InlineKeyboardButton(text="🚫 ব্যান ইউজার",         callback_data="admin:ban"),
        InlineKeyboardButton(text="✅ আনব্যান ইউজার",       callback_data="admin:unban"),
    )
    return builder.as_markup()
