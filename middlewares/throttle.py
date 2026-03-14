import time
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject

from config import THROTTLE_RATE


class ThrottlingMiddleware(BaseMiddleware):
    """
    প্রতিটি ইউজারের মেসেজের মধ্যে সর্বনিম্ন THROTTLE_RATE সেকেন্ড বিরতি নিশ্চিত করে।
    এটা স্প্যাম এবং বট-অ্যাবিউজ প্রতিরোধ করে।
    """

    def __init__(self) -> None:
        self._last_message: dict[int, float] = {}

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if not isinstance(event, Message):
            return await handler(event, data)

        user_id = event.from_user.id if event.from_user else None
        if user_id is None:
            return await handler(event, data)

        now = time.monotonic()
        last = self._last_message.get(user_id, 0.0)

        if now - last < THROTTLE_RATE:
            # অতিরিক্ত মেসেজ উপেক্ষা করুন
            return None

        self._last_message[user_id] = now
        return await handler(event, data)
