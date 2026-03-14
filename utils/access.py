import logging
from typing import Iterable

from aiogram import Bot
from aiogram.enums import ChatMemberStatus
from aiogram.exceptions import TelegramAPIError

from config import FORCE_JOIN_CHANNELS

logger = logging.getLogger(__name__)

_ALLOWED_STATUSES = {
    ChatMemberStatus.CREATOR,
    ChatMemberStatus.ADMINISTRATOR,
    ChatMemberStatus.MEMBER,
    ChatMemberStatus.RESTRICTED,
}


def normalize_channel_ref(channel: str) -> str:
    value = channel.strip()
    if not value:
        return value
    if value.startswith("https://t.me/"):
        return "@" + value.removeprefix("https://t.me/").strip("/")
    if value.startswith("http://t.me/"):
        return "@" + value.removeprefix("http://t.me/").strip("/")
    if value.startswith("@") or value.startswith("-100"):
        return value
    return f"@{value}"


def channel_button_url(channel: str) -> str:
    normalized = normalize_channel_ref(channel)
    if normalized.startswith("@"):
        return f"https://t.me/{normalized[1:]}"
    return f"https://t.me/c/{normalized.replace('-100', '')}"


def channel_label(channel: str) -> str:
    normalized = normalize_channel_ref(channel)
    return normalized if normalized.startswith("@") else channel


async def get_missing_channels(bot: Bot, user_id: int) -> tuple[list[str], bool]:
    if not FORCE_JOIN_CHANNELS:
        return [], False

    missing_channels: list[str] = []
    had_error = False

    for channel in FORCE_JOIN_CHANNELS:
        chat_id = normalize_channel_ref(channel)
        try:
            member = await bot.get_chat_member(chat_id, user_id)
        except TelegramAPIError as exc:
            logger.warning("Channel join check failed for %s: %s", chat_id, exc)
            had_error = True
            continue

        if member.status not in _ALLOWED_STATUSES:
            missing_channels.append(channel)

    return missing_channels, had_error


async def can_access_bot(bot: Bot, user_id: int) -> tuple[bool, list[str], bool]:
    missing_channels, had_error = await get_missing_channels(bot, user_id)
    return not missing_channels and not had_error, missing_channels, had_error


def format_channel_lines(channels: Iterable[str]) -> str:
    return "\n".join(f"• {channel_label(channel)}" for channel in channels)
